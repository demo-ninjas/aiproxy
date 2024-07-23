
from typing import Callable
from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse
from aiproxy.proxy import AbstractProxy, ProxyRegistry
from .agent import Agent
from .agents import agent_factory
from .agents.assistant_agent import AssistantAgent

class AssistantOrchestrator(AbstractProxy):
    _agent:AssistantAgent

    def __init__(self, config: ChatConfig | str) -> None:
        super().__init__(config)
        agent_config = ChatConfig.load(config) if type(config) is not ChatConfig else config.clone()
        agent_config['type'] = 'assistant'
        agent_config['name'] = config.get('agent-name') or config.get('name') or 'assistant'
        agent_config['description'] = config.get('agent-description') or config.get('description') or 'An AI Assistant'
        self._agent = agent_factory(agent_config)
        if not isinstance(self._agent, AssistantAgent):
            raise ValueError("Agent created is not an AssistantAgent")
        
    def send_message(self, message: str, context: ChatContext, override_model: str = None, override_system_prompt: str = None, function_filter: Callable[[str, str], bool] = None, use_functions: bool = True, timeout_secs: int = 0, use_completions_data_source_extensions: bool = False) -> ChatResponse:
        return self._agent.process_message(message, context)