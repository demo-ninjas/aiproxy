from typing import Callable
from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_context import ChatContext
from aiproxy.data.chat_response import ChatResponse
from aiproxy.proxy import AbstractProxy, ProxyRegistry
from .agent import Agent
from .agents import agent_factory
from .agents.route_to_agent_agent import RouteToAgentAgent


DEFAULT_COORDINATOR_PROMPT = """
You are coordinating a group of agents who are tasked with fulfilling the goal of a given user prompt.

Your role is to pass the state of the conversation between the agents, guiding the conversation and ultimately deciding when the agents have achieved the goal of the user prompt.
Before deciding that the agents have achieved the goal of the user prompt, ensure that the majority of agents have agreed (or passed on participating) that the goal has been achieved before you can decide to end the conversation.
There are {AGENT_COUNT} agents in this chat, so you must have contributions from at least half of the agents (aka. at least {HALF_AGENT_COUNT} agents) before you decide that the goal has been achieved.

You are to respond with one of two responses: 

1. AGENT:Agent Name:Prompt to the agent to continue the conversation
2. QUESTION:Question back to the user before continuing the conversation
2. COMPLETE

Option 1 is to route the conversation to the specified agent to continue the conversation.
Option 2 is to indicate that based on the conversation so far, you would like to pose a question back to the user (eg. to clarify something) before continuing the conversation.
Option 3 is to indicate that the agents have completed the goal of the user prompt and the conversation should end.

The format of option 1 is a colon separated string, starting with the literal string "AGENT", followed by a colon ":" followed by the Agent Name, followed by a colon, optionally followed by any comment you wish to make to the next agent to contribute. 

eg. To ask the agent with the name "History Professor" to provide a comment on the relevance of the Napoleonic Wars to the conversation, you would respond with:

AGENT:History Professor:Can you provide a comment on the relevance of the Napoleonic Wars to this?

The Agent Names are case-sensitive, and when reponding with the agent name, it should not be abbreviated or changed.
When choosing an agent, DO NOT provide a reason for the choice.

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

Following is the conversation between the agents so far, in the following format:

[Agent Name]: 
Agent Response

---

[Agent Name]:
Agent Response

---

etc....


[START AGENT RESPONSES]

{AGENT_RESPONSES}

[END AGENT RESPONSES]


Please provide your decision.
"""


CARRY_OVER_TEMPLATE = """Your name is: {AGENT_NAME}

{NUDGE}

ALWAYS Reply in the following format: 

[Your Name]
Your Response

If you have no further contributions to make, or you believe the goal of the user prompt has been achieved, then please respond only with your name and a response of "COMPLETE".
"""

INTRODUCTION_TEMPLATE = """
This is a group chat between multiple agents, each with their own unique capabilities and knowledge.
The agents participating in this conversation are as follows:

[START AGENT LIST]

{AGENT_LIST}

[END AGENT LIST]

The goal of this conversation is to fulfill the user prompt provided below.

[START USER PROMPT]

{USER_PROMPT}

[END USER PROMPT]
"""


QUESTION_TEMPLATE = """
The agents have decided to pose a question back to the user before continuing the conversation.
The question is as follows:

{QUESTION}

Please write a response to the user that poses the above question in a friendly conversational manner.
Use Markdown format.
"""

SUMMARY_TEMPLATE = """
Your role is to provide a succinct description of the outcome / consensus of the conversation between the agents.
The agents have worked together to achieve the goal of the user prompt, and you are to provide a response to the user, based on your interpretation of the outcome/consensus of the conversation.

You do not need to summarise everything that happened in the conversation, but you should provide a summary of the key points and the outcome of the conversation.

If the conversation includes an agreed upon answer to a question posed by the user, you should include that in your summary (eg. a some code, or a crafted paragraph of text).

You must reply in friendly conversational English, using markdown format.

{SUMMARY_RULES}

The agents participating in this conversation are as follows:

[START AGENT LIST]

{AGENT_LIST}

[END AGENT LIST]

The goal of this conversation was to fulfill the user prompt provided below.

[START USER PROMPT]

{USER_PROMPT}

[END USER PROMPT]

Following is the conversation between the agents, in the following format:

[Agent Name]:
Agent Response

---

[Agent Name]:
Agent Response

---

etc...

[START AGENT RESPONSES]

{AGENT_RESPONSES}

[END AGENT RESPONSES]
"""

class ConsensusOrchestrator(AbstractProxy):
    _agents:list[Agent] = None
    _coordinator:Agent = None
    _summariser:Agent = None

    _carry_over_template:str = None
    _coordinator_template:str = None
    _introduction_template:str = None
    _question_template:str = None
    _summary_template:str = None

    _max_turns:int = 20
    _summary_rules:str = None

    def __init__(self, config: ChatConfig | str) -> None:
        super().__init__(config)
        self._load_agent_config()
        self._load_coordinator()
        self._load_summariser()
        
        self._carry_over_template = self._config.get("carry-over-template", CARRY_OVER_TEMPLATE)
        self._coordinator_template = self._config.get("coordinator-template", DEFAULT_COORDINATOR_PROMPT)
        self._introduction_template = self._config.get("intro-template", INTRODUCTION_TEMPLATE)
        self._question_template = self._config.get("question-template", QUESTION_TEMPLATE)
        self._summary_template = self._config.get("summary-template", SUMMARY_TEMPLATE)

        self._max_turns = int(self._config.get("max-turns", 20))
        self._summary_rules = self._config.get("summary-rules", "")
        
    def _load_agent_config(self): 
        self._agents = []
        agent_configs = self._config["agents"]
        if agent_configs is not None and len(agent_configs) > 0: 
            self._agents = self._load_agents(agent_configs)
        
    def _load_coordinator(self):
        coordinator_config = self._config.get("coordinator") or self._config.get("selector", None)
        if coordinator_config is None:
            coordinator_config = {
                "agent-type": "completion",
                "name": "ConsensusCoordinator",
                "description": "Coordinates the conversation between multiple agents to achieve the goal of the user prompt"
            }
        self._coordinator = agent_factory(coordinator_config)
    
    def _load_summariser(self):
        summariser_config = self._config.get("summariser") or self._config.get("interpreter", None) or self._config.get("responder", None)
        if summariser_config is None:
            summariser_config = {
                "agent-type": "completion",
                "name": "ConsensusSummariser",
                "description": "Summarises the outcome of the conversation between multiple agents"
            }
        self._summariser = agent_factory(summariser_config)
    

    def _build_agent_list_str(self, agents:list[Agent]) -> str:
        agent_list = "\n"
        for agent in agents:
            agent_list += f"- {agent.name}: {agent.description}\n"
        return agent_list
    
    def _load_agents(self, agent_configs: list[dict]) -> list[Agent]:
        agents  = []
        for agent_config in agent_configs:
            agent = agent_factory(agent_config)
            agents.append(agent)
        return agents
    
    def build_agent_responses_str(self, responses: list[tuple[Agent, ChatResponse]]) -> str:
        response_str = ""
        for agent, response in responses:
            response_str += f"[{agent.name}]:\n{response.message}\n---\n"
        return response_str

    def send_message(self, message: str, context: ChatContext, override_model: str = None, override_system_prompt: str = None, function_filter: Callable[[str, str], bool] = None, use_functions: bool = True, timeout_secs: int = 0, use_completions_data_source_extensions: bool = False) -> ChatResponse:
        ## Setup the Agent List
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
        ## Build the Agent List String for use in prompts
        agent_list_str = self._build_agent_list_str(agents)
        agent_count = len(agents)
        half_agent_count = agent_count // 2
        max_turns = context.get_metadata("max_turns") or self._max_turns

        ## Setup the conversation context
        context.init_history()  ## Ensure the history has been loaded

        intro_prompt = self._introduction_template.format(AGENT_LIST=agent_list_str, USER_PROMPT=message)
        conversation_context = context.clone_for_thread_isolation(thread_id_to_use=context.get_metadata('linked-conversation')) ## Context used for sending conversation messages to agents 
        conversation_context.init_history()
        conversation_so_far:list[tuple[Agent,ChatResponse]] = []
        if conversation_context.history is None or len(conversation_context.history) == 0:
            conversation_context.add_prompt_to_history(intro_prompt, 'system')    
        
        context.set_metadata("linked-conversation", conversation_context.thread_id)
        conversation_context.add_prompt_to_history(message, 'user')

        question_back_to_user:str = None
        conversation_complete = False
        turn = 0
        while True: 
            turn += 1
            if turn > max_turns:
                break

            ## Step 1: Ask the Coordinator to select an agent or complete the conversation
            coordinator_prompt = self._coordinator_template.format(HALF_AGENT_COUNT=half_agent_count, AGENT_COUNT=agent_count, AGENT_LIST=agent_list_str, USER_PROMPT=message, AGENT_RESPONSES=self.build_agent_responses_str(conversation_so_far))
            coordinator_resp = self._coordinator.process_message(coordinator_prompt, context.clone_for_single_shot())

            ## Step 2: Check the response from the coordinator
            if coordinator_resp is None:
                return ChatResponse(message="Coordinator did not provide a response")
            elif coordinator_resp.message.lower().strip() == "complete":
                conversation_complete = True
                break
            elif coordinator_resp.message.lower().strip().startswith("question"):
                question = coordinator_resp.message.strip().split(":", 1)[1]
                conversation_context.add_prompt_to_history(f"Coordinator:\nPosing the following question back to the user:\n\n{question}", 'assistant')
                question_back_to_user = question
                break
            else: 
                arr = coordinator_resp.message.strip().split(":", 2)
                agent_name = arr[1].strip()
                agent = None
                for a in agents:
                    if a.name == agent_name:
                        agent = a
                        break
                if agent is None:
                    return ChatResponse(message=f"Agent {agent_name} not found in the list of agents")
                
                ## Step 3: Ask the selected agent to speak
                agent_nudge = arr[2] if len(arr) > 2 else "Please provide your next contribution to the conversation, considering the conversation so far."
                agent_prompt = self._carry_over_template.format(NUDGE=agent_nudge, AGENT_NAME=agent.name)
                agent_resp = agent.process_message(agent_prompt, conversation_context)
                if agent_resp is None: 
                    agent_resp = ChatResponse(message=f"{agent.name}:\nI have nothing to add to this conversation")
                
                ## Step 4: Add the agent response to the conversation
                conversation_so_far.append((agent, agent_resp))

        
        summary_prompt = None
        if conversation_complete:
            summary_prompt = self._summary_template.format(AGENT_LIST=agent_list_str, USER_PROMPT=message, AGENT_RESPONSES=self.build_agent_responses_str(conversation_so_far), SUMMARY_RULES=self._summary_rules)
        elif question_back_to_user is not None:
            summary_prompt = self._question_template.format(QUESTION=question_back_to_user)
        else:
            summary_prompt = "The conversation was not completed by the agents, perhaps they ran out of turns? Here's the conversation so far:\n\n" + self.build_agent_responses_str(conversation_so_far) + "\n\nPlease respond to the user and ask them how they would like to proceed."

        summary_resp = self._summariser.process_message(summary_prompt, context.clone_for_single_shot(with_streamer=True))
        if summary_resp is None:
            return ChatResponse(message="Summariser did not provide a response")
        else:
            summary_resp.add_metadata('participants', [a.name for a,m in conversation_so_far])
            context.add_prompt_to_history(message, 'user')
            context.add_response_to_history(summary_resp)
            context.save_history()
            conversation_context.save_history()
            return summary_resp