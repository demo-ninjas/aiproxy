from aiproxy import ChatContext, ChatResponse
from aiproxy.proxy import AbstractProxy, GLOBAL_PROXIES_REGISTRY
from ..agent import Agent
from .. import orchestrator_factory

class OrchestratorProxyAgent(Agent):
    _orchestrator:AbstractProxy
    _custom_system_message:str = None
    _assistant_name:str = None
    _thread_isolated:bool = True
    _isolated_thread_id:str = None
    
    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        super().__init__(name, description, config)
        orch_config = self.config.copy()
        orch_config['name'] = config.get('orchestrator') or config.get('orchestrator-name') or config.get('name')
        orch_config['type'] = config.get('orchestrator-type') or config.get('type')
        self._orchestrator = orchestrator_factory(orch_config)
        self._single_shot = self.config.get("single-shot", False)
        self._thread_isolated = self.config.get("thread-isolated", False)
    
    def reset(self):
        self._isolated_thread_id = None
        
    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        original_context = context
        if self._thread_isolated:
            context = context.clone_for_thread_isolation(self._isolated_thread_id)
        elif self._single_shot:
            context = context.clone_for_single_shot()

        # Send message to the Orchestrator
        context.current_msg_id = original_context.current_msg_id
        response = self._orchestrator.send_message(message, context)

        # If the agent is using an isolated thread, store the thread-id for use later 
        if self._thread_isolated:
            self._isolated_thread_id = context.thread_id

        return response