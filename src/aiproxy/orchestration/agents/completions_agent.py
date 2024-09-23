from typing import Callable

from aiproxy import ChatContext, ChatResponse
from aiproxy.proxy import CompletionsProxy, GLOBAL_PROXIES_REGISTRY
from ..agent import Agent

class CompletionsAgent(Agent):
    proxy:CompletionsProxy
    _custom_system_message:str = None
    _custom_model:str = None
    _single_shot:bool = False
    _thread_isolated:bool = True
    _isolated_thread_id:str = None
    _function_filter:Callable[[str,str], bool] = None

    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        super().__init__(name, description, config)

        proxy_name = self.config.get("proxy-name", name)
        self.proxy = GLOBAL_PROXIES_REGISTRY.load_proxy(proxy_name, CompletionsProxy)
        self._custom_system_message = self.config.get("system-prompt") or self.config.get("system-message")
        self._custom_model = self.config.get("model", None)
        self._single_shot = self.config.get("single-shot", False)
        self._thread_isolated = self.config.get("thread-isolated", False)
        
    def set_function_filter(self, function_filter:Callable[[str,str], bool]):
        self._function_filter = function_filter

    def reset(self):
        self._isolated_thread_id = None
    
    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        original_context = context
        if self._single_shot:
            context = context.clone_for_single_shot()
        elif self._thread_isolated:
            context = context.clone_for_thread_isolation(self._isolated_thread_id)

        # Send message to the proxy
        context.current_msg_id = original_context.current_msg_id
        response = self.proxy.send_message(message, context, override_model=self._custom_model, override_system_prompt=self._custom_system_message, function_filter=self._function_filter)
        # If the agent is using an isolated thread, store the thread-id for use later 
        if self._thread_isolated:
            self._isolated_thread_id = context.thread_id

        return response