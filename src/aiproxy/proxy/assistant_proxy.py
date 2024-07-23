from typing import Callable, Tuple
from time import time, sleep
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai.types import FileObject
from openai.types.beta.assistant import Assistant
from openai.types.beta.threads import Message, Run
from openai.types.beta.threads.run_submit_tool_outputs_params import ToolOutput


from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse, ChatCitation
from aiproxy.data.chat_message import ChatMessage
from aiproxy.streaming import SimpleStreamMessage, PROGRESS_UPDATE_MESSAGE, ERROR_MESSAGE

from .abstract_proxy import AbstractProxy

class AssistantProxy(AbstractProxy):
    active_tool_runs:dict[str,bool]
    action_executor:ThreadPoolExecutor
    run_monitors:ThreadPoolExecutor
    assistant_name_to_id:dict[str,str]
    assistant_id_to_name:dict[str,str]

    def __init__(self, config:ChatConfig|str) -> None:
        super().__init__(config)
        self.active_tool_runs = {}
        self.assistant_name_to_id = {}
        self.assistant_id_to_name = {}
        self.action_executor = ThreadPoolExecutor(thread_name_prefix="action-exec-",max_workers = self._config['max-concurrent-tool-actions'] or 10)
        self.run_monitors = ThreadPoolExecutor(thread_name_prefix="run-mon-", max_workers = self._config['max-concurrent-run-monitors'] or 5)
    
    def _get_or_create_thread(self, context:ChatContext, override_system_prompt:str = None) -> str:
        ## Create a new Thread ID
        thread_id = context.thread_id or self._client.beta.threads.create().id  ## Don't provide system prompt here, we're assuming that the assistant has one built in 

        ## Initialise the Thread History (if needed)
        context.init_history(thread_id, override_system_prompt or self._config.system_prompt)
        
        ## Return Thread ID
        return thread_id

    def send_message_and_return_outcome(self, 
                    message:str, 
                    context:ChatContext, 
                    assistant_name_or_id:str
                    ) -> list[ChatResponse]:
        
        ## Send the message...
        resp = self.send_message(message, context)
        
        ## Check that it went successfully
        if resp.filtered or resp.failed:
            return [resp]
        
        ## Now, trigger a run and await the results
        assistant_id = self.lookup_assistant_id(assistant_name_or_id)
        start_time = time()
        run_id = self.run_assistant(assistant_id=assistant_id, in_thread=context.thread_id)
        run = self.await_run_complete_or_fail(in_thread=context.thread_id, run_id=run_id, context=context)
        if run.status == 'completed': 
            msg_list = self.list_messages(in_thread=context.thread_id, count=30, filter_role='assistant')
            res = []
            for msg in msg_list:
                if msg.created_at is not None and msg.created_at > 0 and msg.created_at < start_time:
                    continue  # Skip any messages that are older than the prompt
                if msg.run_id is None or msg.run_id == run_id: # Only messages from this run 
                    res.append(msg)

            outcome = self.assistant_messages_to_chat_responses(res, context)
            for res in outcome:
                ## Now, parse the response and update the context if needed
                self._parse_response(res, context)

                context.add_message_to_history(ChatMessage(message=res.message, role="assistant", id=res.id, assistant_id=res.assistant_id))
            return outcome            
        
        elif run.status == 'expired':
            return [ChatResponse(error="Run expired before completion")]
        else: 
            return [ChatResponse(error=f"Run failed with status: {run.status}")]
        
        

    def send_message(self, 
                    message:str, 
                    context:ChatContext, 
                    override_model:str = None, 
                    override_system_prompt:str = None, 
                    function_filter:Callable[[str,str], bool] = None, 
                    use_functions:bool = True, 
                    timeout_secs:int = 0, 
                    use_completions_data_source_extensions:bool = False) -> ChatResponse:

        ## Add the user message to the thread history
        context.push_stream_update(SimpleStreamMessage("Recalling our conversation so far", PROGRESS_UPDATE_MESSAGE))
        thread_id = self._get_or_create_thread(context, override_system_prompt)     ## This will trigger the context to load the history if it hasn't been loaded already...
        context.add_prompt_to_history(message, "user")
        
        ## Create the response object
        response = ChatResponse()
        response.thread_id = thread_id

        try:
            ## Check that there's no active runs on the thread (only allowed one at a time)
            run_check_start = time()
            run_list = self.get_runs_on_thread(thread_id=thread_id, sort="desc", max_count=10)
            # Check if any run is active
            while any([run.status in ["queued", "in_progress", "cancelling"] for run in run_list]):
                run_list = self.get_runs_on_thread(thread_id=thread_id, sort="desc", max_count=10)
                if time() - run_check_start < timeout_secs: 
                    sleep(0.1)
                else: 
                    raise TimeoutError("Timeout waiting for all active runs to complete/fail before sending a message")

            ## Send the message to the thread
            msg = self._client.beta.threads.messages.create(thread_id=thread_id, content=message, role="user")
            response = ChatResponse()
            response.id = msg.id
            response.thread_id = thread_id
            return response

        except Exception as e:
            logging.error(f"Error sending message: {e}")
            response.error = str(e)
            context.push_stream_update(ERROR_MESSAGE, "error")
            return response
    
    def upsert_assistant(self, assistant:Assistant)->str:
        """
        Create or Update an assistant, returning the Assistant ID 
        """ 
        res_assistant = None
        if assistant.id is None or len(assistant.id) == 0: 
            ## If the Assistant ID is not set, then create a new assistant
            res_assistant = self._client.beta.assistants.create(
                    model=assistant.model, 
                    description=assistant.name,
                    name=assistant.name, 
                    instructions=assistant.instructions,
                    file_ids=assistant.file_ids, 
                    tools=assistant.tools,
                    metadata=assistant.metadata
                )
        else: 
            res_assistant = self._client.beta.assistants.update(
                    assistant_id=assistant.id,
                    model=assistant.model, 
                    description=assistant.name,
                    name=assistant.name, 
                    instructions=assistant.instructions,
                    file_ids=assistant.file_ids, 
                    tools=assistant.tools,
                    metadata=assistant.metadata
                )
        
        return res_assistant.id

    def list_assistants(self)->list[Assistant]:
        """
        List all available assistants
        """
        assistants = []
        res = self._client.beta.assistants.list(order="asc")
        if res.data:
            assistants.extend(res.data)
            while res.has_next_page():
                res = res.get_next_page()
                if res.data: assistants.extend(res.data)
            
        ## Add the assistants to the ID map
        for assistant in assistants:
            if assistant.name is not None: 
                self.assistant_name_to_id[assistant.name] = assistant.id
                self.assistant_id_to_name[assistant.id] = assistant.name
        return assistants
    
    def lookup_assistant_id(self, assistant_name_or_id:str)->str:
        """
        Find the assistant with the specified name
        """
        if assistant_name_or_id in self.assistant_name_to_id:
            return self.assistant_name_to_id[assistant_name_or_id]
        if assistant_name_or_id in self.assistant_id_to_name:
            return assistant_name_or_id

        ## Get the list of assistants, which will also fill the assistant ID/Name maps with the current data
        self.list_assistants()

        ## now, check again
        if assistant_name_or_id in self.assistant_name_to_id:
            return self.assistant_name_to_id[assistant_name_or_id]
        if assistant_name_or_id in self.assistant_id_to_name:
            return assistant_name_or_id

        return None

    def get_assistant(self, assistant_name_or_id:str)->Assistant:
        if assistant_name_or_id is None:
            raise ValueError("The assistant Name or ID must be provided")
        
        ## Get the Assistant ID (if we were passed the name)
        assistant_id = self.lookup_assistant_id(assistant_name_or_id)
        ## Return the asssistant details
        return self._client.beta.assistants.retrieve(assistant_id=assistant_id)
        

    def upload_data_source(self, file_name:str, file_data:bytes)->str:
        """
        Upload a data file, returning the assigned ID
        """
        res = self._client.files.create(purpose='assistants', file=(file_name, file_data))
        return res.id

    def list_data_sources(self, purpose:str = 'assistants')->list[FileObject]:
        """
        List all available data files that can be used by Assistants
        """
        files = []
        res = self._client.files.list(purpose=purpose)
        if res.data: files.extend(res.data)
        if res.has_next_page():
            res = res.get_next_page()
            if res.data: files.extend(res.data)
        return files


    def get_data_source(self, file_id:str)->Tuple[str, bytes]:
        """
        Get the file contents of a specific data file
        """
        info = self._client.files.retrieve(file_id=file_id)  ## Retrieve the file name
        res = self._client.files.content(file_id=file_id)    ## Retrieve the file contents
        return info.filename, res.content
    
    def list_messages(self, in_thread:str = None, count:int = 10, sort:str = "desc", filter_role:str = None) -> list[Message]:
        """
        List the most messages in the current thread (sorted by the sort param - default descending), returning only the messages matching the role filter (if provided)
        
        NB: Currently count + sort are not implemented, so they are ignored
        """
        messages = []
        res = self._client.beta.threads.messages.list(thread_id=in_thread, order="desc", limit=count*2)
        while len(messages) < count and res.data:
            filtered_messages = [data for data in res.data if filter_role is None or data.role == filter_role]
            messages.extend(filtered_messages[:count - len(messages)])
            if len(messages) < count and res.has_next_page():
                res = res.get_next_page()
        
        return messages
    
    def run_assistant(self, assistant_id:str, in_thread:str, metadata:dict[str,str] = None) -> str:
        """
        Run the assistant, return the Run ID
        """            
        ## Run the Assistant in the current thread
        run = self._client.beta.threads.runs.create(assistant_id=assistant_id, thread_id=in_thread, metadata=metadata)
        return run.id

    def get_run(self, in_thread:str, run_id:str) -> Run:
        """
        Return the details for the specified Run
        """
        run = self._client.beta.threads.runs.retrieve(thread_id=in_thread, run_id=run_id)
        return run
        
    def get_runs_on_thread(self, thread_id:str, max_count:int = 30, sort:str = "desc") -> list[Run]:
        """
        Return the details for all the runs on the specified thread
        """
        res = self._client.beta.threads.runs.list(thread_id=thread_id, order=sort, limit=max_count)
        runs = []
        while len(runs) < max_count and res.data:
            runs.extend(res.data)
            if len(runs) < max_count and res.has_next_page():
                res = res.get_next_page()
        return runs

    def await_run_complete_or_fail(self, in_thread:str, run_id:str, context:ChatContext, timeout_secs:float = 300) -> Run: 
        """
        Wait for the specified run to complete or fail, returning the final run details
        """
        remaining_secs = float(timeout_secs)
        while remaining_secs > 0:
            start = time()
            run = self.get_run(in_thread, run_id)
            ##  `queued`, `in_progress`, `requires_action`, `cancelling`, `cancelled`, `failed`, `completed`, or `expired`.
            if run.status in ["completed", "failed", "cancelled", "expired"]:
                return run
            elif run.status == "requires_action":
                if not self._are_run_tools_active(run.id):
                    fut = self.run_monitors.submit(self.__handle_run_actions, run, in_thread, context)
                    fut.result(remaining_secs)
                    # threading.Thread(target=self.__handle_run_actions, args=(run, in_thread, context), daemon=True).start()
            else: 
                sleep(0.5) # Wait for a bit and check again...
            
            remaining_secs -= time() - start
        raise TimeoutError("Run did not complete within the specified timeout period")


    def assistant_messages_to_chat_responses(self, messages:list[Message], context:ChatContext)->list[ChatResponse]:
        chat_responses = []
        for assistant_msg in messages:
            resp = ChatResponse()
            resp.assistant_id = assistant_msg.assistant_id
            resp.id = assistant_msg.id
            resp.thread_id = assistant_msg.thread_id
            resp.metadata = {}
            if assistant_msg.file_ids is not None and len(assistant_msg.file_ids) > 0:
                resp.metadata["file_ids"] = assistant_msg.file_ids
            for content in assistant_msg.content:
                if content.type == "text":
                    resp.message = content.text.value if resp.message is None else resp.message + "\n" + content.text
                    if content.text.annotations is not None and len(content.text.annotations) > 0: 
                        for annotation in content.text.annotations:
                            if annotation.type == "file_citation":
                                citation = ChatCitation()
                                citation.id = annotation.file_citation.file_id
                                citation.text = annotation.file_citation.quote
                                citation.start = annotation.start_index
                                citation.end = annotation.end_index
                                citation.replace_part = annotation.text
                                resp.citations = [citation] if resp.citations is None else resp.citations.append(citation)
                            elif annotation.type == "file_path":
                                citation = ChatCitation()
                                citation.id = annotation.file_path.file_id
                                citation.start = annotation.start_index
                                citation.end = annotation.end_index
                                citation.replace_part = annotation.text
                                resp.citations = [citation] if resp.citations is None else resp.citations.append(citation)
                            else: 
                                logging.warning(f"Unknown annotation type: {annotation.type}")
                elif content.type == "image":
                    resp.metadata["image"] = [ content.image_file.file_id ] if "image" not in resp.metadata else resp.metadata["image"].append(content.image_file.file_id)
            chat_responses.append(resp)
        return chat_responses

    def __handle_run_actions(self, run:Run, thread_id:str, context:ChatContext):
        if self._are_run_tools_active(run.id):
            return # Don't continue if there's already an active tool run for this run
        
        ## Mark the Tool Run as being active
        self._set_active_tool_run(run.id)

        try: 
            ## Invoke each of the run actions and submit them back to the run when they're complete
            if run.required_action and run.required_action.type == "submit_tool_outputs":
                call_futures = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    if tool_call.type == "function":
                        function_call = tool_call.function
                        call_futures.append(self.action_executor.submit(self.__invoke_function_tool, function_call.name, function_call.arguments, tool_call.id, context))
                    elif tool_call.type == "code_interpreter":
                        ## Ignore, this tool doesn't require any action on our part!
                        pass
                
                ## Now wait for them to finish, and collect the results up as they complete
                call_results = [future.result() for future in as_completed(call_futures) if future.result() is not None]
                self._client.beta.threads.runs.submit_tool_outputs(thread_id=thread_id, run_id=run.id, tool_outputs=call_results)
        except Exception as e:
            logging.error(f"Error handling run actions: {e}")
        finally: 
            self._clear_active_tool_run(run.id)

    def __invoke_function_tool(self, function_name, function_args, call_id, context:ChatContext) -> ToolOutput:
        result = self._invoke_function_tool(function_name, function_args, context)
        return ToolOutput(output=result, tool_call_id=call_id)

    def _are_run_tools_active(self, run_id:str) -> bool: 
        return run_id in self.active_tool_runs
    
    def _set_active_tool_run(self, run_id:str):
        self.active_tool_runs[run_id] = True

    def _clear_active_tool_run(self, run_id:str):
        if run_id in self.active_tool_runs:
            del self.active_tool_runs[run_id]


