
from typing import Callable
from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse
from aiproxy.proxy import AbstractProxy, ProxyRegistry
from .agent import Agent
from .agents import agent_factory

class AgentOrchestrator(AbstractProxy):
    _agent:Agent = None

    def __init__(self, config: ChatConfig | str) -> None:
        super().__init__(config)
        
        name = config.get("agent-name") or config.get('agent') or config.get('agent-type') or config.get('agent-id') or config.get('type') or config.get('name')
        if name is not None:
            try:
                agent_config = ChatConfig.load(config)
                self._agent = agent_factory(agent_config)
            except Exception as e:
                estr = str(e).lower()
                if 'not found' not in estr and 'unknown' not in estr:
                    raise ValueError(f"Failed to create agent from config: {estr}")
        
    def send_message(self, message: str, 
                     context: ChatContext, 
                     override_model: str = None, 
                     override_system_prompt: str = None, 
                     function_filter: Callable[[str, str], bool] = None, 
                     use_functions: bool = True, timeout_secs: int = 0, 
                     use_completions_data_source_extensions: bool = False,
                     working_notifier:Callable[[], None] = None,
                     **kwargs) -> ChatResponse:
        if self._agent is None: 
            agent = context.get_metadata('agent') or context.get('agent-type') or context.get('agent-name') or context.get('agent-id')
            self._agent = agent_factory(agent)

        if self._agent is None: 
            raise ValueError("No agent specified for the message")
        
        if working_notifier is not None: working_notifier()
        result = self._agent.process_message(message, context.clone_for_single_shot(with_streamer=True))
        context.add_prompt_to_history(message, 'user')
        context.add_response_to_history(result)
        context.save_history()
        return result