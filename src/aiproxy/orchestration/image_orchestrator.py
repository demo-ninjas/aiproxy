
from typing import Callable
from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse
from aiproxy.proxy import AbstractProxy, ProxyRegistry
from .agents.analyse_image_agent import AnalyseImageAgent
from .agents import agent_factory

class ImageOrchestrator(AbstractProxy):
    _agent:AnalyseImageAgent

    def __init__(self, config: ChatConfig | str) -> None:
        super().__init__(config)
        agent_name = config['agent-name'] or "image-analyser"
        agent_desc = config['description'] or "An agent that analyses images"
        agent_config = ChatConfig.load(config)
        self._agent = AnalyseImageAgent(agent_name, agent_desc, agent_config)
        
    def send_message(self, message: str, context: ChatContext, override_model: str = None, override_system_prompt: str = None, function_filter: Callable[[str, str], bool] = None, use_functions: bool = True, timeout_secs: int = 0, use_completions_data_source_extensions: bool = False) -> ChatResponse:
        image_bytes = context.get_metadata("image-bytes") or context.get('image-metadata') or context.get('bytes')
        if image_bytes is not None:
            return self._agent.process_message(image_bytes, context)
        else:
            return self._agent.process_message(message, context)
