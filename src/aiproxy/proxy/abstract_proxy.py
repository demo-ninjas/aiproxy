from abc import abstractmethod
from typing import Callable
import logging
import json

from openai import AzureOpenAI

from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse
from aiproxy.functions.function_registry import GLOBAL_FUNCTIONS_REGISTRY
from aiproxy.utils.func import invoke_registered_function

class AbstractProxy:
    _config:ChatConfig

    def __init__(self, config:ChatConfig|str) -> None:
        if config is None:
            config = 'default-' + str(type(self)).lower()
        if type(config) is str:
            config = ChatConfig.load(config, False)
        if type(config) is dict: 
            config = ChatConfig.load(config)
        self._config = config
        self._client = AzureOpenAI(
            azure_endpoint = self._build_base_url(False), 
            api_key=self._config.oai_key,  
            api_version=self._config.oai_version
        )

        logging.getLogger("httpx").setLevel(logging.ERROR) ## Stop the excessive logging from the httpx client library  

    @abstractmethod
    def send_message(self, 
                     message:str, 
                     context:ChatContext, 
                     override_model:str = None, 
                     override_system_prompt:str = None, 
                     function_filter:Callable[[str,str], bool] = None, 
                     use_functions:bool = True, 
                     timeout_secs:int = 0, 
                     use_completions_data_source_extensions:bool = False
                     ) -> ChatResponse:
        """
        Send a user message and return the response to the message
        """
        raise NotImplementedError("This method must be implemented by the subclass")


    @abstractmethod
    def _get_or_create_thread(self, context:ChatContext, override_system_prompt:str = None) -> str:
        """
        Create a new thread and return the thread id 
        
        (this must be implemented by the subclass as the concept of a thread differs between different APIs)
        """
        raise NotImplementedError("This method must be implemented by the subclass")


    def _build_base_url(self, include_path:bool = True)->str:
        if self._config.oai_endpoint is not None and len(self._config.oai_endpoint) > 0:
            return self._config.oai_endpoint
        else: 
            region = self._config.oai_region if self._config.oai_region is not None else "australiaeast"
            return f"https://aoai-{region}.openai.azure.com/{'openai' if include_path else ''}"

    def _invoke_function_tool(self, function_name:str, function_args:str|dict, context:ChatContext) -> str:
        return invoke_registered_function(function_name, function_args, context, sys_objects={ 'config': self._config, 'proxy': self })
    
    def _parse_response(self, response:ChatResponse, context:ChatContext): 
        if response is None or response.message is None or len(response.message) == 0:
            return response
        
        if self._config.parse_ai_response:
            try: 
                msg = response.message.strip()
                response_data = None
                ## Handle JSON responses + JSON in Markdown code blocks
                if msg[0] == '{' and msg[-1] == '}':
                    response_data = json.loads(response.message)
                elif msg.startswith('```') and msg.endswith('```'):
                    msg = msg[3:-3].strip()
                    squiggly_pos = msg.find('{')
                    if squiggly_pos > 0: 
                        response_data = json.loads(msg[squiggly_pos:])
                
                if response_data is not None and type(response_data) is dict:
                    response.add_metadata('_msg-parsed', True)
                    if self._config.get('save-raw-msg', True):
                        response.add_metadata('_raw-msg', response.message)

                    response.message = response_data.get('message') or response_data.get('response') or response.message
                    for key, val in response_data.items():
                        if key != 'message' and key != 'response':
                            add_to_response = True
                            add_to_context = True
                            persist_to_history = self._config.persist_parsed_ai_response_metadata
                            if key[0] == '_': 
                                u2 = key.find('_', 1)
                                key_args = key[1:u2]
                                key = key[u2+1:]
                                pos = 0
                                while pos < len(key_args): 
                                    arg_indicator = key_args[pos:pos+1]
                                    arg_target = key_args[pos+1:pos+2].upper()
                                    if arg_target == 'R':
                                        add_to_response = True if arg_indicator == '+' else False
                                    elif arg_target == 'C':
                                        add_to_context = True if arg_indicator == '+' else False
                                    elif arg_target == 'H':
                                        persist_to_history = True if arg_indicator == '+' else False
                                    pos += 2
                                
                            if add_to_response:
                                response.add_metadata(key, val)
                            if add_to_context:
                                context.set_metadata(key, val, persist_to_history)
            except: 
                pass

        return response
    