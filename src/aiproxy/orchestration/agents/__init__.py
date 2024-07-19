from ..agent import Agent
from aiproxy.utils.config import load_named_config

def agent_factory(config: dict|str, **kwargs) -> Agent:
    if type(config) is str:
        config = load_named_config(config)

    name = config.get("name", None)
    if name is None: 
        raise AssertionError("Agent name not specified in config, this is a mandatory field")
    description = config.get("description", None)
    agent_type = config.get("type", None)
    if agent_type is None:
        raise AssertionError("Agent type not specified in config")
    
    agent_type = agent_type.lower()
    if agent_type == "assistant" or agent_type == "assistantagent":
        from .assistant_agent import AssistantAgent
        return AssistantAgent(name, description, config, **kwargs)
    elif agent_type == "completion" or agent_type == "completions" or agent_type == "completionsagent":
        from .completions_agent import CompletionsAgent
        return CompletionsAgent(name, description, config, **kwargs)
    elif agent_type == "route-to-agent" or agent_type == "route-to-agent-agent":
        from .route_to_agent_agent import RouteToAgentAgent
        return RouteToAgentAgent(name, description, config, **kwargs)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")