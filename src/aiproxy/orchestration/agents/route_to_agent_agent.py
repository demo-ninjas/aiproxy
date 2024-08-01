from typing import Callable
import logging
from aiproxy import ChatContext, ChatResponse
from aiproxy.proxy import CompletionsProxy, GLOBAL_PROXIES_REGISTRY
from ..agent import Agent

_DEFAULT_SELECTOR_PROMPT = """You are tasked with selecting the best agent to handle the provided user prompt. 
Please select the agent that you believe is best suited to handle the user prompt by returning only the agent name.

The format of the agent list is as follows: 

- Agent Name: Description of the agent
- Agent Name: Description of the agent


The agent list will be provided below, followed by the user prompt.

[START AGENT LIST]
{AGENT_LIST}
[END AGENT LIST]

[START USER PROMPT]
{USER_PROMPT}
[END USER PROMPT]

Respond only with the name of the agent you believe is best suited to handle the user prompt, do not include any additional information.
"""

class RouteToAgentAgent(Agent):
    proxy:CompletionsProxy
    _selector_prompt_template:str = None
    _custom_model:str = None
    _agents:list[Agent]
    _selector_prompt:str = None

    def __init__(self, name:str = None, description:str = None, config:dict = None, agents:list[Agent] = None) -> None:
        super().__init__(name, description, config)

        if self.config is None: 
            self._selector_prompt_template = _DEFAULT_SELECTOR_PROMPT
            self._agents = agents
            proxy_name = name
        else: 
            self._selector_prompt_template = self.config.get("selector-prompt", None) or self.config.get("selector", None) or self.config.get("system-message", None) or self.config.get("system-prompt", None) or _DEFAULT_SELECTOR_PROMPT
            self._custom_model = self.config.get("model", None)
            self._agents = agents or self.config.get("agents") or []
            proxy_name = self.config.get("proxy-name", name)
        
        self.proxy = GLOBAL_PROXIES_REGISTRY.load_proxy(proxy_name, CompletionsProxy)
        
    def set_agents(self, agents:list[Agent]):
        if agents is None or len(agents) == 0: 
            raise AssertionError("No agents provided, you must provide at least one agent")
        self._agents = agents

    def _build_agent_list(self) -> str:
        agent_list = "\n"
        for agent in self._agents:
            agent_list += f"- {agent.name}: {agent.description}\n"
        return agent_list
    
    def reset(self):
        pass
    
    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        prompt_context = context.clone_for_single_shot()
        selector_prompt = self._selector_prompt_template.format(AGENT_LIST=self._build_agent_list(), USER_PROMPT=message)
        selector_response = self.proxy.send_message(selector_prompt, prompt_context, override_model=self._custom_model, use_functions=False)
        if selector_response.error or selector_response.filtered: 
            return selector_response
        else: 
            selected_agent_name = selector_response.message.strip()
            selected_agent = next((agent for agent in self._agents if agent.name == selected_agent_name), None)
            if selected_agent is None:
                ## Assume the AI has added some prose before the agent name, look for the last ':' and the agent name will be after it
                last_colon = selected_agent_name.rfind(":")
                if last_colon > 0:
                    selected_agent_name = selected_agent_name[last_colon+1:].strip()
                    selected_agent = next((agent for agent in self._agents if agent.name == selected_agent_name), None)

            if selected_agent is None: 
                response = ChatResponse()
                response.error = True
                response.message = f"Selected agent {selected_agent_name} not found in agent list"
                return response
            else: 
                logging.debug(f"Selected agent: {selected_agent.name} to answer prompt: {message}")
                resp = selected_agent.process_message(message, context)
                resp.add_metadata("responder", selected_agent.name)
                return resp