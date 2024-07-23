
from typing import Callable
from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse
from aiproxy.proxy import AbstractProxy, ProxyRegistry
from .agent import Agent
from .agents import agent_factory

class AgentOrchestrator(AbstractProxy):
    _agent:Agent

    def __init__(self, config: ChatConfig | str) -> None:
        super().__init__(config)
        agent_config = ChatConfig.load(config)
        self._agent = agent_factory(agent_config)
        
    def send_message(self, message: str, context: ChatContext, override_model: str = None, override_system_prompt: str = None, function_filter: Callable[[str, str], bool] = None, use_functions: bool = True, timeout_secs: int = 0, use_completions_data_source_extensions: bool = False) -> ChatResponse:
        return self._agent.process_message(message, context)