
from typing import Callable
from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse
from aiproxy.proxy import AbstractProxy, ProxyRegistry
from .agent import Agent
from .agents import agent_factory
from .agents.route_to_agent_agent import RouteToAgentAgent

class AgentSelectOrchestrator(AbstractProxy):
    _selector:RouteToAgentAgent
    _agents:list[Agent]

    def __init__(self, config: ChatConfig | str) -> None:
        super().__init__(config)
        self._load_agent_config()
        self._load_selector()

    def _load_selector(self):
        selector_config = self._config.get("selector") or self._config.get("selector-config", None)
        self._selector = RouteToAgentAgent('route-to-agent', 'Route to Agent', config=selector_config, agents=self._agents)
        
    def _load_agent_config(self): 
        agent_configs = self._config["agents"]
        if agent_configs is None or len(agent_configs) == 0: 
            raise AssertionError("No agents configured - you need to define at least one agent to use this orchestrator")
        
        self._agents = []
        for agent_config in agent_configs:
            agent = agent_factory(agent_config)
            if agent.description is None: 
                raise AssertionError(f"Agent {agent.name} does not have a description - all agents must have a description")
            self._agents.append(agent)

    def send_message(self, message: str, 
                     context: ChatContext, 
                     override_model: str = None, 
                     override_system_prompt: str = None, 
                     function_filter: Callable[[str, str], bool] = None, 
                     use_functions: bool = True, timeout_secs: int = 0, 
                     use_completions_data_source_extensions: bool = False,
                     working_notifier:Callable[[], None] = None,
                     **kwargs) -> ChatResponse:
        ## Fill the selector history with the conversation so far
        selector_context = context.clone_for_single_shot(with_streamer=True)
        context.init_history()
        if context.history: 
            for msg in context.history:
                selector_context.add_prompt_to_history(msg.message, msg.role)
        if working_notifier is not None: working_notifier()
        result = self._selector.process_message(message, selector_context)

        
        context.add_prompt_to_history(message, 'user')
        context.add_response_to_history(result)
        context.save_history()
        return result
    