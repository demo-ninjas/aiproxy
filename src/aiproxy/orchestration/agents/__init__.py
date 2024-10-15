from ..agent import Agent
from aiproxy.utils.config import load_named_config
from aiproxy.data import ChatConfig

GLOBAL_AGENTS_REGISTRY = {}
GLOBAL_TYPES_REGISTRY = {}

def reset_agents():
    global GLOBAL_AGENTS_REGISTRY, GLOBAL_TYPES_REGISTRY
    GLOBAL_AGENTS_REGISTRY = {}
    GLOBAL_TYPES_REGISTRY = {}

def agent_factory(config: dict|str|ChatConfig, **kwargs) -> Agent:
    global GLOBAL_AGENTS_REGISTRY
    global GLOBAL_TYPES_REGISTRY
    name = None
    if type(config) is str:
        tmp_name = config
        config = ChatConfig.load(config)
        name = config.get("agent-name") or config.get('agent') or config.get('name') or tmp_name
    elif type(config) is dict:
        config = ChatConfig.load(config)
        name = config.get("agent-name") or config.get('name')
    elif type(config) is ChatConfig:
        name = config.get("agent-name") or config.get('name')
    else:
        raise ValueError("Unknown config type provided, you must provide a ChatConfig, a config dictionary, or a config name")

    if name is None: 
        raise AssertionError("Agent name could not be determined - you must specify the Agent name, either in a config field called 'agent-name' or in the 'name' field")
    
    ## If the agent is already registered, return it
    if name in GLOBAL_AGENTS_REGISTRY:
        return GLOBAL_AGENTS_REGISTRY[name]

    
    description = config.get("description", None)
    agent_type = config.get('agent-type') or config.get("type", name)
    if agent_type is None:
        raise AssertionError("Agent type not specified in config")
    
    ## Load the agent based on the agent type as specified in the config
    agent_type = agent_type.lower()
    agent = None

    if agent_type in GLOBAL_TYPES_REGISTRY:
        agent = GLOBAL_TYPES_REGISTRY[agent_type](name, description, config, **kwargs)
    elif agent_type == "assistant" or agent_type == "assistantagent":
        from .assistant_agent import AssistantAgent
        agent = AssistantAgent(name, description, config, **kwargs)
    elif agent_type == "completion" or agent_type == "completions" or agent_type == "completionsagent":
        from .completions_agent import CompletionsAgent
        agent = CompletionsAgent(name, description, config, **kwargs)
    elif agent_type == "route-to-agent" or agent_type == "route-to-agent-agent":
        from .route_to_agent_agent import RouteToAgentAgent
        agent = RouteToAgentAgent(name, description, config, **kwargs)
    elif agent_type == 'url' or agent_type == 'url-agent' or agent_type == 'urlagent':
        from .url_agent import UrlAgent
        agent = UrlAgent(name, description, config, **kwargs)
    elif agent_type == 'html-parser' or agent_type == 'html' or agent_type == 'htmlparser' or agent_type == 'html-parser-agent':
        from .html_parser_agent import HtmlPaserAgent
        agent = HtmlPaserAgent(name, description, config, **kwargs)
    elif agent_type == 'html-markdown' or agent_type == 'markdown' or agent_type == 'htmlmarkdown':
        from .html_markdown_agent import HtmlMarkdownAgent
        agent = HtmlMarkdownAgent(name, description, config, **kwargs)
    elif agent_type == 'function' or agent_type == 'function-agent' or agent_type == 'functions':
        from .function_agent import FunctionAgent
        agent = FunctionAgent(name, description, config, **kwargs)
    elif agent_type == 'suggestion' or agent_type == 'suggestions' or agent_type == 'next-action' or agent_type == 'next-action-agent' or agent_type == 'suggestions-agent':
        from .suggestions_agent import SuggestionsAgent
        agent = SuggestionsAgent(name, description, config, **kwargs)
    elif agent_type == 'analyse-image' or agent_type == 'analyse-image-agent' or agent_type == 'image':
        from .analyse_image_agent import AnalyseImageAgent
        agent = AnalyseImageAgent(name, description, config, **kwargs)
    elif agent_type == 'orchestrator-agent' or agent_type == 'orchestrator-proxy' or agent_type == 'orchestratoragent' or agent_type == 'orchestrator-proxy-agent':
        from .orchestrator_proxy_agent import OrchestratorProxyAgent
        agent = OrchestratorProxyAgent(name, description, config, **kwargs)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    register_agent(agent)
    return agent
    

def register_agent(agent: Agent):
    global GLOBAL_AGENTS_REGISTRY
    GLOBAL_AGENTS_REGISTRY[agent.name] = agent

def unregister_agent(agent_name:str):
    global GLOBAL_AGENTS_REGISTRY
    if agent_name in GLOBAL_AGENTS_REGISTRY:
        del GLOBAL_AGENTS_REGISTRY[agent_name]

def register_agent_type(type_name:str, agent_type:type):
    global GLOBAL_TYPES_REGISTRY
    GLOBAL_TYPES_REGISTRY[type_name.lower()] = agent_type