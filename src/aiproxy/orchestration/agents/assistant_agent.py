from aiproxy import ChatContext, ChatResponse
from aiproxy.proxy import AssistantProxy, GLOBAL_PROXIES_REGISTRY
from ..agent import Agent

class AssistantAgent(Agent):
    proxy:AssistantProxy
    _custom_system_message:str = None
    _assistant_name:str = None
    _thread_isolated:bool = True
    _isolated_thread_id:str = None
    
    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        super().__init__(name, description, config)

        proxy_name = self.config.get("proxy-name", name)
        self.proxy = GLOBAL_PROXIES_REGISTRY.load_proxy(proxy_name, AssistantProxy)
        self._assistant_name = self.config.get("assistant-name") or self.config.get("assistant")
        self._thread_isolated = self.config.get("thread-isolated", False)
    
    def reset(self):
        self._isolated_thread_id = None
        
    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        context.init_history()
        assistant_thread_id = context.get_metadata('assistant-thread-id')
        context_for_assistant = context.clone_for_thread_isolation(with_streamer=True)
        context_for_assistant.thread_id = assistant_thread_id
        
        if self._thread_isolated:
            context = context.clone_for_thread_isolation(self._isolated_thread_id)

        # Send message to the proxy
        assistant_name = self._assistant_name or context.get_metadata('assistant') or context.get_metadata('assistant-id') or context.get_metadata('assistant-name') or self.config.get('name') or self.name
        responses = self.proxy.send_message_and_return_outcome(message, context_for_assistant, assistant_name_or_id=assistant_name)
        # If the agent is using an isolated thread, store the thread-id for use later 
        if self._thread_isolated:
            self._isolated_thread_id = context.thread_id

        ## Save the assistant thread id for future reference
        context.set_metadata('assistant-thread-id', context_for_assistant.thread_id)
        
        ## Check for errors and filtered responses
        if len(responses) == 0:
            response = ChatResponse()
            response.error = True
            response.message = "No response from assistant"
            return response
        elif responses[0].error or responses[0].filtered:
            return responses[0]

        
        ## Collect up the messages from the assistant run and create a single message
        responses.reverse()
        response = ChatResponse()
        for resp in responses:
            if not resp.error and not resp.filtered:
                if response.message is None: 
                    response.message = resp.message
                else: 
                    response.message += '\n\n' + resp.message
                if resp.citations is not None: 
                    if response.citations is None: 
                        response.citations = resp.citations
                    else: 
                        response.citations.extend(resp.citations)
                if resp.assistant_id is not None: 
                    response.assistant_id = resp.assistant_id
                if resp.intent is not None: 
                    response.intent = resp.intent
                if resp.metadata is not None: 
                    if response.metadata is None: 
                        response.metadata = resp.metadata
                    else: 
                        response.metadata.update(resp.metadata)
        
        context.add_prompt_to_history(message, "user")
        context.add_prompt_to_history(response.message, "assistant")
        context.save_history()
        return response