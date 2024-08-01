from typing import Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse
from aiproxy.proxy import AbstractProxy, GLOBAL_PROXIES_REGISTRY, CompletionsProxy
from .agent import Agent
from .agents import agent_factory

_DEFAULT_INTERPETER_PROMPT = """You are tasked with interpreting the responses to a prompt from a set of agents and coming up with a succinct answer.
Please consider the accuracy and relevant of the responses from each agent in relation to your understanding of the intent of the prompt, and ignore any responses that are not useful.
With the support of the agent responses, please provide an accurate, detailed answer to the user prompt.

The format of the agent responses is as follows:

Agent: [Agent Name]
[Agent Response]

---

Agent: [Agent Name]
[Agent Response]

---

Note the '---' which is used as a separater between agent responses.

If an agent response is filtered due to a content violation, or the agent encountered an error, the response will be in the format: 'Failed due to [ERROR DESCRIPTION]'.

The responses to the user prompt are provided below, followed by the user prompt.

[START AGENT RESPONSES]

{AGENT_RESPONSES}

[END AGENT RESPONSES]

[START USER PROMPT]

{USER_PROMPT}

[END USER PROMPT]
"""

class MultiAgentOrchestrator(AbstractProxy):
    _agents:list[Agent] = None
    _interpreter:CompletionsProxy
    _interp_template:str = None
    _executor:ThreadPoolExecutor
    _raise_on_timeout:bool = False

    def __init__(self, config: ChatConfig | str) -> None:
        super().__init__(config)
        self._executor = ThreadPoolExecutor(thread_name_prefix="multiagent-",max_workers = self._config['concurrency'] or 4)
        self._load_agent_config()
        self._load_interpreter()
        self._raise_on_timeout = self._config.get("raise-on-timeout", False)

    def _load_interpreter(self):
        interp_config = self._config.get("interpreter") or self._config.get("interp") or None
        self._interpreter = GLOBAL_PROXIES_REGISTRY.load_proxy(interp_config, CompletionsProxy)
        self._interp_template = self._config.get("interpreter-prompt") or self._config.get('interp-prompt') or self._config.get("system-message", None) or _DEFAULT_INTERPETER_PROMPT
        
    def _load_agent_config(self): 
        agent_configs = self._config["agents"]
        if agent_configs is not None and len(agent_configs) > 0: 
            self._agents = self._load_agents(agent_configs)

    def _load_agents(self, agent_configs: list[dict|str]) -> list[Agent]:
        agent_list = []
        for agent_config in agent_configs:
            agent = agent_factory(agent_config)
            agent_list.append(agent)
        return agent_list

    def _send_message_to_agent(self, agent:Agent, message:str, context:ChatContext) -> Tuple[Agent, ChatResponse]:
        return (agent, agent.process_message(message, context))

    def send_message(self, message: str, context: ChatContext, override_model: str = None, override_system_prompt: str = None, function_filter: Callable[[str, str], bool] = None, use_functions: bool = True, timeout_secs: int = 0, use_completions_data_source_extensions: bool = False) -> ChatResponse:
        ## Send the message to each agent in turn
        
        ## Check if the configured agent list is empty + if so, check if the request is specifying the agents
        agent_list = self._agents
        if agent_list is None or len(agent_list) == 0:
            agent_configs = self._config.get("agents") or self._config.get("agent")
            if agent_configs is not None:
                if type(agent_configs) is list:
                    agent_list = self._load_agents(agent_configs)
                elif type(agent_configs) is dict:
                    agent_list = self._load_agents([agent_configs])
                elif type(agent_configs) is str:
                    agent_list = self._load_agents(agent_configs.split(","))
        
        if len(agent_list) == 0:
            raise ValueError("No agents configured for the MultiAgentOrchestrator, you must specify at least one agent")

        futs = []
        for agent in agent_list:
            futs.append(self._executor.submit(self._send_message_to_agent, agent, message, context.clone_for_thread_isolation()))        

        ## Wait for all the agents to complete
        timeout = 120.0
        if timeout_secs > 0:
            timeout = timeout_secs
        elif self._config.timeout_secs > 0: 
            timeout = self._config.timeout_secs
        
        timeout -= 10 ## Subtract 10 seconds to allow for the interpreter to process the responses
        if timeout <= 0: timeout = 30
        responses:list[Tuple[Agent, ChatResponse]] = []
        try:
            for fut in as_completed(futs, float(timeout)):
                responses.append(fut.result())
        except TimeoutError:
            if self._raise_on_timeout:
                raise

        ## Interpret the responses
        agent_responses = ""
        if len(responses) == 0:
            agent_responses = "No responses were received from the agents"
        else:
            for agent, response in responses:
                agent_responses += f"Agent: {agent.name}:\n"
                if response.filtered:
                    agent_responses += f"Failed due to content Filter\n"
                elif response.error:
                    agent_responses += f"Failed due to an Error: {response.message}\n"
                else:
                    agent_responses += f"{response.message}\n"
                agent_responses += "\n---\n"

        prompt = self._interp_template.format(AGENT_RESPONSES=agent_responses, USER_PROMPT=message)
        interp_context = context.clone_for_single_shot()
        response = self._interpreter.send_message(prompt, interp_context, use_functions=False)

        if not response.error and not response.filtered:
            ## Add the User Message + Final Response to the context history    
            context.add_prompt_to_history(message, 'user')
            context.add_prompt_to_history(response, 'assistant')
            context.save_history()
