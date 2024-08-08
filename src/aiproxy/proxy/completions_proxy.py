from typing import Callable
from uuid import uuid4
from time import time
import logging

import openai
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, Choice as StreamChoice
from openai.types.chat import ChatCompletionMessageToolCall

from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse, ChatCitation
from aiproxy.data.chat_chunk import ChunkData
from aiproxy.data.chat_message import ChatMessage
from aiproxy.streaming import SimpleStreamMessage, PROGRESS_UPDATE_MESSAGE, INTERIM_RESULT_MESSAGE
from aiproxy.functions.function_registry import GLOBAL_FUNCTIONS_REGISTRY

from .abstract_proxy import AbstractProxy
from .completions_extensions_adapter import CompletionsWithExtensionsAdapter

class CompletionsProxy(AbstractProxy):
    def __init__(self, config:ChatConfig|str) -> None:
        super().__init__(config)
        self.__load_oai_data_source_config()

    def _get_or_create_thread(self, context:ChatContext, override_system_prompt:str = None) -> str:
        ## Create a new Thread ID
        thread_id = context.thread_id or uuid4().hex

        ## Initialise the Thread History (if needed)
        context.init_history(thread_id, override_system_prompt or self._config.system_prompt)
        
        ## Return Thread ID
        return thread_id
    
    def _parse_prompt_template(self, prompt:str, context:ChatContext) -> str:
        ## Extract each key from the prompt (wrapped in squiggly brackets) and then find the matching value in metadata or config and replace the key with the value
        ## If the key is not found, then leave the key in the string
        if prompt is None: return None
        from_pos = 0
        start = prompt.find("{", from_pos)
        while start >= 0:
            if prompt[start:start+2] == "{{":    ## Ignore any double squiggly brackets
                from_pos = start + 2
                start = prompt.find("{", from_pos)
                continue

            
            end = prompt.find("}", start)
            if end < 0: break

            key = prompt[start+1:end]

            if key == "date": 
                from datetime import datetime
                value = datetime.now().strftime("%Y-%m-%d")
            elif key == "time": 
                from datetime import datetime
                value = datetime.now().strftime("%H:%M:%S")
            elif key == "datetime":
                from datetime import datetime
                value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif key == "utcdate": 
                from datetime import datetime, tzinfo                
                value = datetime.now(tz=tzinfo.utcoffset).strftime("%Y-%m-%d")
            elif key == "utctime": 
                from datetime import datetime, tzinfo                
                value = datetime.now(tz=tzinfo.utcoffset).strftime("%H:%M:%S")
            elif key == "utcdatetime": 
                from datetime import datetime, tzinfo                
                value = datetime.now(tz=tzinfo.utcoffset).strftime("%Y-%m-%d %H:%M:%S")
            elif key == "iso8601":
                from datetime import datetime
                value = datetime.now().isoformat()
            elif key.startswith("date-format:"):
                from datetime import datetime
                value = datetime.now().strftime(key[12:])
            else:
                ## Key - it's either going to be in the context metadata, or a config value
                value = context.get_metadata(key) or (self._config.prompt_vars.get(key) if self._config.prompt_vars is not None else None)

            ## If the key is not found, then leave it, and move on to the next key
            if value is None:
                from_pos = start + 2
                start = prompt.find("{", from_pos)
                continue

            ## Replace the key with the value                
            prompt = prompt[:start] + str(value) + prompt[end+1:]
            from_pos = start + len(value)
            start = prompt.find("{", from_pos)
        return prompt

    def send_message(self, 
                     message:str, 
                     context:ChatContext, 
                     override_model:str = None, 
                     override_system_prompt:str = None, 
                     function_filter:Callable[[str,str], bool] = None, 
                     use_functions:bool = None, 
                     timeout_secs:int = 0, 
                     use_completions_data_source_extensions:bool = False
                     ) -> ChatResponse:
        
        ## Add the user message to the thread history
        system_prompt_to_use = override_system_prompt or self._config.system_prompt
        if self._config.system_prompt_is_template: 
            system_prompt_to_use = self._parse_prompt_template(system_prompt_to_use, context)
        
        context.push_stream_update(SimpleStreamMessage("Recalling our conversation so far", PROGRESS_UPDATE_MESSAGE))
        thread_id = self._get_or_create_thread(context, system_prompt_to_use)     ## This will trigger the context to load the history if it hasn't been loaded already...
        if message is not None and len(message) > 0:
            if self._config.user_prompt_is_template: 
                message = self._parse_prompt_template(message, context)
            context.add_prompt_to_history(message, "user")
        elif len(context.history) == 0:
            context.add_prompt_to_history(system_prompt_to_use, "system")
        
        ## If the length of the conversation is getting long, summarise the conversation and drop the history
        if len(context.history) >= self._config.max_history:
            # self.__summarise_thread( metadata)
            pass

        ## Create the response object
        response = ChatResponse()
        response.thread_id = thread_id

        try:
            ## Continuously send messages to the model until we get a final response
            more_steps = True
            step_count = 0
            remaining_secs = timeout_secs if timeout_secs > 0 else self._config.timeout_secs
            model = override_model or self._config.oai_model
            using_functions = use_functions if use_functions is not None else self._config.use_functions
            filter_for_tool_calls = function_filter or context.function_filter

            tool_list = GLOBAL_FUNCTIONS_REGISTRY.generate_tools_definition(filter_for_tool_calls) if using_functions else None
            chunk_data = ChunkData() if context.has_stream() else None
            while more_steps and step_count < self._config.max_steps:
                if remaining_secs <= 0:
                    raise TimeoutError("The request timed out")
            
                start = time()
                step_count += 1

                ## Build the Message list from the history
                messages = [ history_item.to_openid_message() for history_item in context.history ]
                
                ## Send a progress Update
                if step_count == 1:
                    context.push_stream_update("Thinking about what you said", PROGRESS_UPDATE_MESSAGE)
                else: 
                    context.push_stream_update("Analysing the data I've collected so far", PROGRESS_UPDATE_MESSAGE)

                ## Send the messages to the model
                if self.completions_data_sources is not None and use_completions_data_source_extensions:
                    ## Pass a data source configuration to the Completions API and let it do the RAG operations itself
                    ## This approach simplifies the work done by this function, but is limited to only supporting the 
                    ## data sources and operations supported by the Azure OpenAI Data Sources API 
                    result = self.completions_adapter.client().chat.completions.create(
                        messages=messages,
                        model=model,
                        temperature=self._config.temperature,
                        extra_body={ "dataSources": self.completions_data_sources},
                        timeout=remaining_secs,
                        top_p=self._config.top_p,
                        max_tokens=self._config.max_tokens,
                        stop=None,
                        stream=context.has_stream(),
                    )
                else: 
                    ## Pass a tool configuration to the Completions API and handle the RAG + other function calls ourselves
                    ## This approach allows for more flexibility in the data sources and operations that can be supported, 
                    ## essentially allowing for any function to be called and any data source to be queried :) 
                    result = self._client.chat.completions.create(
                        messages=messages, 
                        model=model,
                        temperature=self._config.temperature,
                        max_tokens=self._config.max_tokens,
                        top_p=self._config.top_p,
                        tools=tool_list,
                        tool_choice=None if not use_functions else "auto" if step_count < self._config.max_steps - 1 else "none",
                        timeout=remaining_secs,
                        stream=context.has_stream(),
                    )

                ## Process the response from the model
                if type(result) is openai.Stream:
                    more_steps = self._process_streaming_results(result, response, context, chunk_data)
                else: 
                    context.push_stream_update("Writing a response", PROGRESS_UPDATE_MESSAGE)
                    more_steps = self._process_choices(result, response, context) 
                
                ## Update the remaining time
                remaining_secs -= time() - start
                
            
            ## Now, parse the response and update the context if needed
            self._parse_response(response, context)

            ## Request the context to save the history (with the updated messages list)
            context.push_stream_update("Documenting our conversation", PROGRESS_UPDATE_MESSAGE)
            context.save_history()

        except Exception as e:
            if hasattr(e, 'code') and str(e.code or "") == "content_filter":
                data = e.body if e.body is not None and type(e.body) is dict else {}
                response.failed = True
                response.error = "Content Filtered"
                response.filtered = True
                response.filter_reason = None
                logging.debug(f"This prompt triggered the content policy: {message}")
                if "content_filter_result" in data:
                    response.filter_reason = data["content_filter_result"]
                response.message = "I'm sorry, I can't respond to that message, maybe try asking again in a slightly different way."
            else: 
                import traceback
                traceback.print_exception(e)
                logging.error(f"Failed to send a prompt to the model with error: {e}, Prompt: {message}")
                response.failed = True
                response.error = "Unexpected Error Occurred. Please try again later."
                response.message = "I'm sorry, I'm having trouble responding right now. Please try again later."

        return response
    
    def _process_streaming_results(self, result:list[ChatCompletionChunk], response:ChatResponse, context:ChatContext, chunk_data:ChunkData) -> bool:
        more_steps = True 
        for chunk in result:
            more_steps = self._process_choices(chunk, response, context, chunk_data)
        return more_steps


    def _process_choices(self, result, response:ChatResponse, context:ChatContext, chunk_data:ChunkData = None) -> bool:
        ### Process the Choices from the AI Model
        more_steps = True

        if len(result.choices) > 1: 
            ## First, if there are multiple choices, sort them by the index field
            result.choices = sorted(result.choices, key=lambda x: x.index if x.index else 0)

        for choice in result.choices:
            if type(choice) is StreamChoice:
                ## Record the next chunk from the stream and continue
                more_steps = self.__process_stream_chunk(choice, response, context, chunk_data)
            elif choice.model_extra is not None and choice.model_extra.get('messages') is not None: 
                ## Process the messages from the model_extra - this is a special case for the OpenAI Data Sources API
                self.__process_data_source_api_response(choice.model_extra.get('messages'), response)
            elif choice.message is None: 
                logging.warning(f"No message in choice: {choice} [Not doing anything with it atm.]") ## TODO: Check if we should do something with this choice or just simply continue?!
                continue   ## No message yet, so continue
            elif choice.message.tool_calls is not None and len(choice.message.tool_calls) > 0:
                ## Process Tool Calls
                ## Put the tool call into the history, it needs to be in the history when we return the tool response back to the AI
                context.add_message_to_history(ChatMessage.from_tool_calls_message(choice.message))
                self.__process_tool_calls(choice.message.tool_calls, context)
            else: 
                ## This is a normal message from the AI
                ## So, grab the content, add it to the history and return the message
                msg = ChatMessage(message = choice.message.content, role = choice.message.role)
                context.add_message_to_history(msg)
                response.message = choice.message.content if response.message is None else response.message + "\n" + choice.message.content
                more_steps = False  ## We've got the complete response from the AI, so no more steps

        return more_steps

    def __process_stream_chunk(self, choice:StreamChoice, response:ChatResponse, context:ChatContext, chunk_data:ChunkData) -> bool:
        ## Process the streaming choice response from the AI
        more_steps = True

        if chunk_data.accumulated_delta is None or len(chunk_data.accumulated_delta) == 0:
            context.push_stream_update("Writing a response", PROGRESS_UPDATE_MESSAGE)

        if choice.finish_reason is not None:
            more_steps = self.__process_finished_stream_chunk(choice, response, context, chunk_data)
        elif choice.delta is None:
            ## This is stream message from the Data Source Extensions API - add the delta to the chunk
            more_steps = self.__process_stream_chunk_from_data_extensions_api(choice, response, context, chunk_data)
        else:
            ## This is a delta message from the normal completion API
            chunk_data.add_chunk_delta(choice.delta)
            self._publish_interim_result(chunk_data, context)
            
        return more_steps
    
    def __process_stream_chunk_from_data_extensions_api(self, choice:StreamChoice, response:ChatResponse, context:ChatContext, chunk_data:ChunkData) -> bool:
        messages = choice.model_extra.get('messages')
        end_turn, content_updated = chunk_data.add_data_source_delta(messages)

        ## If the content was updated by this delta, then publish the interim result
        if content_updated:
            self._publish_interim_result()

        ## If it's the end of the turn, then we're done, publish any remaining updates, add the message to the history and return
        if end_turn: 
            ## If there are citations stored in the chunk, then add them to the response
            if chunk_data.has_tool_citations():
                if response.citations is not None: 
                    response.citations.extend(chunk_data.get_tool_citations())
                else: 
                    response.citations = chunk_data.get_tool_citations()
            
            ## Publish any accumulated deltas
            self._publish_interim_result(chunk_data, context, force_publish=True) ## Force publishing even if we only just recently published
            
            ## Add the Message to the History
            context.add_message_to_history(ChatMessage(message=chunk_data.content, role=chunk_data.role, citations=[c.to_api_response() for c in response.citations]))
            
            ## And finally, add the message to the response
            response.message = chunk_data.content if response.message is None else response.message + "\n" + chunk_data.content
            return False
        else: 
            return True
        

    def __process_finished_stream_chunk(self, choice:StreamChoice, response:ChatResponse, context:ChatContext, chunk_data:ChunkData) -> bool:
        more_steps = True
        ## We've got everything, so process it as normal...
        if choice.finish_reason == "tool_calls": 
            # Add the tool calls to the history
            context.add_message_to_history(ChatMessage.from_tool_calls_message(chunk_data))
            self.__process_tool_calls(chunk_data.tool_calls, context)
            chunk_data.tool_calls = None
        elif choice.finish_reason == "content_filter":
            logging.warning(f"Finish Reason: Content Filtered, for Choice: {choice}")
            response.failed = True
            response.error = "Content Filtered"
            response.filtered = True
            response.filter_reason = None
            if "content_filter_result" in choice.model_extra:
                response.filter_reason = choice.model_extra["content_filter_result"]
            response.message = "I'm sorry, I can't respond to that message, maybe try asking again in a slightly different way."
            more_steps = False
        elif choice.finish_reason == "function_call": 
            logging.warning(f"Finish Reason: Function Call, for Choice {choice} [Doing Nothing with this for now]")
        elif choice.finish_reason == "stop":
            self._publish_interim_result(chunk_data, context, force_publish=True) ## Force publishing even if we only just recently published, this will ensure any dangling deltas are published
            context.add_message_to_history(ChatMessage(message=chunk_data.content, role=chunk_data.role))
            response.message = chunk_data.content if response.message is None else response.message + "\n" + chunk_data.content
            more_steps = False
        elif choice.finish_reason == "length": 
            logging.warning(f"Finish Reason: Length, for Choice: {choice}")
            response.failed = True
            response.error = "Content too Long"
            response.message = "I'm sorry, I wasn't able to succinctly answer your question in the space I had available, I might need to reduce the verbosity of my response next time."
        return more_steps

    def __process_data_source_api_response(self, messages, response:ChatResponse, context:ChatContext) -> bool:
        ### Process the response from the Azure OpenAI Data Sources API
        ## There will be multiple messages in this response

        more_steps = True
        msg_content = None
        msg_citations = []
        for message in messages:
            role = message.get('role', None)
            if role and role == 'assistant': 
                ## This is content from the backing assistant, add it to the message content
                msg_content = message.get('content', '')
            elif role and role == 'tool':
                ## This is usually the citations from the tool 
                tool_content = message.get('content', '')
                if tool_content is not None and tool_content.startswith("{"):
                    import json
                    tool_content = json.loads(tool_content)
                    if "citations" in tool_content:
                        msg_citations.extend(tool_content["citations"])
                    else: 
                        logging.warning(f"Tool Content from Data Source API: {tool_content} [Not doing anything with it atm.]")

            ## If this is the end of the turn, then we're done, so set more_steps to False
            if message.get('end_turn') == True:
                more_steps = False

            ## This API can return an intent, grab it if it's there
            user_intent = message.get('intent', None)
            if user_intent is not None: 
                response.intent = user_intent if response.intent is None else response.intent + "\n" + user_intent

        ## If we recieved a message from the assistant, then add it to the response
        if msg_content is not None: 
            response.message = msg_content if response.message is None else response.message + "\n" + msg_content
            ## Convert the format of the citations into a ChatCitation
            if len(msg_citations) > 0: 
                if response.citations is None: 
                    response.citations = []
                for m_citation in msg_citations: 
                    response.citations.append(ChatCitation.from_data_source_citation(m_citation).to_api_response())
            
            ## Add the message to the history
            context.add_message_to_history(ChatMessage(message=msg_content, role='assistant', citations=[c.to_api_response() for c in response.citations]))

        return more_steps
    
    def __process_tool_calls(self, tool_calls:list[ChatCompletionMessageToolCall], context:ChatContext):
        for tool in tool_calls:
            if tool.function is not None:
                result = self._invoke_function_tool(tool.function.name, tool.function.arguments, context=context)
                context.add_message_to_history(ChatMessage(message=result, role='tool', tool_call_id = tool.id, tool_name=tool.function.name))

    def _publish_interim_result(self, chunk_data:ChunkData, context:ChatContext, force_publish:bool = False, publish_frequency:float = 0): 
        if publish_frequency <= 0: 
            publish_frequency = self._config.interim_result_publish_frequency_secs if self._config.interim_result_publish_frequency_secs > 0 else 0.032
        if force_publish or time() - chunk_data.last_stream_publish > publish_frequency:
            if chunk_data.accumulated_delta is not None and len(chunk_data.accumulated_delta) > 0: ## Only publish if there is actually something to publish
                context.push_stream_update({ "delta": chunk_data.accumulated_delta, "id": chunk_data.assigned_id }, INTERIM_RESULT_MESSAGE)
                chunk_data.last_stream_publish = time()
                chunk_data.accumulated_delta = None


    def __load_oai_data_source_config(self):
        self.completions_data_sources = None

        ## Only continue if the data source configuration is enabled
        if self._config.use_data_source_config is False: return

        ## If no data source config is provided, then return
        if self._config.data_source_config is None or len(self._config.data_source_config) == 0: return

        ## There is a data source configuration, so load it
        import utils.config as config_utils
        data_source_config = config_utils.load_named_config(self._config.data_source_config, raise_if_not_found=True)

        ## If a data source configuration has been provided, then configure the proxy to use the OpenAI Data Source extensions API instead of the standard completions API
        if data_source_config is not None:
            self.completions_data_sources = data_source_config.get("data-sources", data_source_config) ## Assume data-sources are an array in a field
            if type(self.completions_data_sources) is not list: 
                self.completions_data_sources = [self.completions_data_sources]
                
            self.completions_adapter = CompletionsWithExtensionsAdapter(self._build_base_url(False), self._config.oai_model, self.__get_version_for_datasource_completions(), self._config.oai_key)

    def __get_version_for_datasource_completions(self)->str:
        key = self._config.data_source_api_version if self._config is not None else None
        if key is None:
            import os
            key = os.environ.get('AZURE_OAI_DATA_SOURCES_API_VERSION', self._config.oai_version)
        if key is None: 
            raise ValueError("The data source API version must be provided in the ChatConfig or as an environment variable")
        return key
