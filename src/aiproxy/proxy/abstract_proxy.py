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