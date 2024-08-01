from typing import Callable
import json

from aiproxy import ChatContext, ChatResponse
from aiproxy.utils.func import invoke_registered_function, FAILED_INVOKE_RESPONSE

from ..agent import Agent

class UrlAgent(Agent):
    _url:str
    _url_template_params:list[str] = None
    _method:str = "GET"
    _headers:dict[str,str] = None
    _post_message_as_body:bool = False

    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        super().__init__(name, description, config)
        
        self._url = self.config.get("url") or self.config.get("url-template")
        if self._url is None:
            raise AssertionError(f"The URL (or URL template) this agent uses must be defined using the 'url' or 'url-template' configuration")

        self._url_template_params = self.config.get("url-template-params") or self.config.get("url-params") or None
        if type(self._url_template_params) is str:
            self._url_template_params = self._url_template_params.split(",")
        if self._url_template_params is None and '{' in self._url and '}' in self._url:
            raise AssertionError(f"The URL template parameters must be defined using the 'url-params' configuration")

        self._post_message_as_body = self.config.get("post-message-as-body") or self.config.get("message-as-body") or False
        self._method = self.config.get("method") or self.config.get("http-method") or "GET"
        self._headers = self.config.get("headers") or self.config.get("http-headers") or None
        if type(self._headers) is str: 
            self._headers = json.loads(self._headers)

    def reset(self):
        pass
    
    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        from aiproxy.functions.url_functions import load_url_response

        url = self._url
        if '{' in url and '}' in url:
            if self._url_template_params is None:
                raise AssertionError(f"The URL template parameters must be defined using the 'url-params' configuration")
            
            ## Load the url params...
            params = {}
            for param in self._url_template_params:
                value = context.get_metadata(param)
                if value is None: 
                    value = self.config.get(param)
                if value is None:
                    raise AssertionError(f"URL template parameter '{param}' was not found")
                params[param] = value

            url = url.format(**params)

        body = message if self._post_message_as_body else None
        status, result = load_url_response(url, method=self._method, headers=self._headers, body=body)
        
        response = ChatResponse()
        if status != 200:
            response.error = True
            response.message = result
        else:
            response.message = result
        return response