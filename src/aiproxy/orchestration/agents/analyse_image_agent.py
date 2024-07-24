from typing import Callable

from aiproxy import ChatContext, ChatResponse
from aiproxy.data import ChatMessage
from aiproxy.proxy import CompletionsProxy, GLOBAL_PROXIES_REGISTRY
from ..agent import Agent

class AnalyseImageAgent(Agent):
    proxy:CompletionsProxy
    _custom_system_prompt:str = None
    _analyse_prompt:str = None
    _custom_model:str = None
    _single_shot:bool = False
    _thread_isolated:bool = False
    _isolated_thread_id:str = None
    _function_filter:Callable[[str,str], bool] = None
    _default_image_extension:str = None

    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        super().__init__(name, description, config)

        proxy_name = self.config.get("proxy-name", name)
        self.proxy = GLOBAL_PROXIES_REGISTRY.load_proxy(proxy_name, CompletionsProxy)
        self._custom_system_prompt = self.config.get("system-prompt", None)
        self._analyse_prompt = self.config.get("analyse-prompt", None)
        self._custom_model = self.config.get("model", None)
        self._single_shot = self.config.get("single-shot", True)
        self._thread_isolated = self.config.get("thread-isolated", False)
        self._default_image_extension = self.config.get("default-image-extension") or self.config.get("default-image-type") or 'jpg'
        
    def set_function_filter(self, function_filter:Callable[[str,str], bool]):
        self._function_filter = function_filter

    def reset(self):
        self._isolated_thread_id = None
    
    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        if self._single_shot:
            context = context.clone_for_single_shot()
        elif self._thread_isolated:
            context = context.clone_for_thread_isolation(self._isolated_thread_id)

        ## If the msg is bytes, then base64 it, otherwise assume it's already base64'd
        if isinstance(message, bytes):
            import base64
            message = base64.b64encode(message).decode('utf-8')
        
        # Check with the context if the it knows the extension of the image
        img_ext = context.get_metadata("image-extension", self._default_image_extension)
    
        # Send message to the proxy
        img_msg = ChatMessage(
            role="user", 
            content=[{
                "type": "image_url",
                "image_url": {
                    "url": f'data:image/{img_ext};base64,{message}',
                    "detail": "low"
                }
            }, 
            {
                "type": "text",
                "text": self._analyse_prompt or 'process this image'
            }],
        )
        context.add_message_to_history(img_msg)
        response = self.proxy.send_message(None, context, override_model=self._custom_model, override_system_prompt=self._custom_system_prompt, function_filter=self._function_filter)
        # If the agent is using an isolated thread, store the thread-id for use later 
        if self._thread_isolated:
            self._isolated_thread_id = context.thread_id

        return response