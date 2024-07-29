
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
        
        name = config.get("agent-name") or config.get('agent') or config.get('name')
        if name is not None:
            agent_config = ChatConfig.load(config)
            self._agent = agent_factory(agent_config)
        
    def send_message(self, message: str, context: ChatContext, override_model: str = None, override_system_prompt: str = None, function_filter: Callable[[str, str], bool] = None, use_functions: bool = True, timeout_secs: int = 0, use_completions_data_source_extensions: bool = False) -> ChatResponse:
        if self._agent is None: 
            agent = context.get_metadata('agent') or context.get('agent-type') or context.get('agent-name') or context.get('agent-id')
            self._agent = agent_factory(agent)

        if self._agent is None: 
            raise ValueError("No agent specified for the message")
        
        return self._agent.process_message(message, context)