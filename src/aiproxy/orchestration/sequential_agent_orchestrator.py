from typing import Callable
from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse
from aiproxy.proxy import AbstractProxy, ProxyRegistry
from .agent import Agent
from .agents import agent_factory
from .agents.route_to_agent_agent import RouteToAgentAgent

CARRY_OVER_TEMPLATE = """
The responses collected from prior agents are provided below, followed by the user prompt.

[START AGENT RESPONSES]

{AGENT_RESPONSES}

[END AGENT RESPONSES]

[START USER PROMPT]

{USER_PROMPT}

[END USER PROMPT]

Please provide a response to the user prompt, considering the responses from the prior agents.
"""

class SequentialAgentOrchestrator(AbstractProxy):
    _agents:list[Agent] = None
    _carry_over_user_prompt:bool = False
    _carry_over_template:str = None


    def __init__(self, config: ChatConfig | str) -> None:
        super().__init__(config)
        self._load_agent_config()
        self._carry_over_user_prompt = self._config.get("carry-over-user-prompt", self._config.get("carry-over", self._config.get("carry-over-prompt", False)))
        self._carry_over_template = self._config.get("carry-over-template", CARRY_OVER_TEMPLATE)
        
    def _load_agent_config(self): 
        self._agents = []
        agent_configs = self._config["agents"]
        if agent_configs is not None and len(agent_configs) > 0: 
            self._agents = self._load_agents(agent_configs)
        
    def _load_agents(self, agent_configs: list[dict]) -> list[Agent]:
        agents  = []
        for agent_config in agent_configs:
            agent = agent_factory(agent_config)
            agents.append(agent)
        return agents

    def send_message(self, message: str, 
                     context: ChatContext, 
                     override_model: str = None, 
                     override_system_prompt: str = None, 
                     function_filter: Callable[[str, str], bool] = None, 
                     use_functions: bool = True, timeout_secs: int = 0, 
                     use_completions_data_source_extensions: bool = False,
                     working_notifier:Callable[[], None] = None,
                     **kwargs) -> ChatResponse:
        agents = self._agents
        if len(agents) == 0: 
            agent_list = context.get_metadata("agents")
            if agent_list is not None: 
                if type(agent_list) is str:
                    agent_list = agent_list.split(",")
                if len(agent_list) > 0:
                    agents = self._load_agents(agent_list)

        if len(agents) == 0: 
            return ChatResponse(message="No agents specified to handle the prompt")

        prev_responses = []
        for idx, agent in enumerate(agents):
            if working_notifier is not None: working_notifier()
            prompt = message
            if self._carry_over_user_prompt and len(prev_responses) > 0:
                prompt = self._carry_over_template.format(AGENT_RESPONSES="\n\n".join([f"{agent.name}:\n{response.message}" for agent, response in prev_responses]), USER_PROMPT=message)
            elif len(prev_responses) > 0:
                prompt = prev_responses[-1][1].message

            ## If this is the last agent, we want to set the with_streamer=True so that the context can push the response to the stream
            is_last_agent = idx == len(agents) - 1
            ctx = context.clone_for_single_shot(with_streamer=is_last_agent)
            if is_last_agent:
                ctx.current_msg_id = context.current_msg_id
            response = agent.process_message(prompt, ctx)
            if response is not None:
                prev_responses.append((agent, response))
        
        context.add_prompt_to_history(message, 'user')
        resp = None
        if len(prev_responses) > 0:
            resp = prev_responses[-1][1]
            context.add_response_to_history(resp)
        else: 
            resp = ChatResponse()
            resp.message = "No agents provided a response"

        context.save_history()
        return resp