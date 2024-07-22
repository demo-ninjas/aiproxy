from typing import Callable
import json

from aiproxy import ChatContext, ChatResponse
from aiproxy.utils.func import invoke_registered_function, FAILED_INVOKE_RESPONSE

from ..agent import Agent

class FunctionAgent(Agent):
    _function_name:str
    _predefined_args:dict[str,any]
    _arg_preprocessor:Callable[[dict[str,any]], dict[str,any]] = None
    _cast_result_to_string:bool = True

    def __init__(self, name:str = None, description:str = None, config:dict = None, arg_preprocessor:Callable[[dict[str,any]], dict[str,any]] = None) -> None:
        super().__init__(name, description, config)
        
        self._function_name = self.config.get("function") or self.config.get("function-name") or name
        if self._function_name is None:
            raise AssertionError(f"Function {self._function_name} was not defined, you must define the function this Agent will use")

        self._predefined_args = self.config.get("args", {})
        self.arg_preprocessor = arg_preprocessor
        self._cast_result_to_string = self.config.get("cast-result-to-string") or self.config.get("result-as-string") or True
        
    def set_arg_preprocessor(self, arg_preprocessor:Callable[[dict[str,any]], dict[str,any]]):
        self._arg_preprocessor = arg_preprocessor

    def set_predefined_arg(self, name:str, val:any):
        if name is None: 
            raise AssertionError("Name of the argument to set is required")
        if self._predefined_args is None: 
            self._predefined_args = {}
        self._predefined_args[name] = val

    def reset(self):
        pass
    
    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        result = invoke_registered_function(self._function_name, message, context, predefined_args=self._predefined_args, arg_preprocessor=self._arg_preprocessor, cast_result_to_string=self._cast_result_to_string)
        response = ChatResponse()
        if result == FAILED_INVOKE_RESPONSE:
            response.error = True
            response.message = "Failed to invoke function"
        else:
            response.message = result
            if self._cast_result_to_string:
                response.metadata = {"function": self._function_name, "result": result }
        return response