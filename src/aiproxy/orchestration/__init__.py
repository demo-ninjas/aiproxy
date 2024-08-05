from ..proxy import AbstractProxy, GLOBAL_PROXIES_REGISTRY
from ..data import ChatConfig
from .agent import Agent

def orchestrator_factory(config: dict|str|ChatConfig, **kwargs) -> AbstractProxy:
    name = None
    if type(config) is str:
        name = config
        config = ChatConfig.load(name)
    elif type(config) is dict:
        name = config["name"] or config['orchestrator'] or config['orchestrator-name']
        config = ChatConfig.load(config)
    elif type(config) is ChatConfig:
        name = config["name"] or config['orchestrator'] or config['orchestrator-name']
    else:
        raise ValueError("Unknown config type provided, you must provide a ChatConfig, a config dictionary, or a config name")

    if name is None: 
        raise AssertionError("Orchestrator name not specified, this is a mandatory field")

    ## Grab the orchestrator type from the config (or default to the basic CompletionsProxy)
    orchestrator_type = config.get("orchestrator-type") or config.get("type", name)
    orchestrator_type = orchestrator_type.lower()
    if orchestrator_type == "agentselect" or orchestrator_type == "agent-select" or orchestrator_type == "agentselectorchestrator":
        from .agent_select_orchestrator import AgentSelectOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, AgentSelectOrchestrator, **kwargs)
    elif orchestrator_type == "step" or orchestrator_type == "steporchestrator" or orchestrator_type == "step-plan" or orchestrator_type == "stepplanorchestrator":
        from .step_plan_orchestrator import StepPlanOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, StepPlanOrchestrator, **kwargs)
    elif orchestrator_type == "consensus" or orchestrator_type == "consensusorchestrator" or orchestrator_type == "group-chat" or orchestrator_type == "groupchatorchestrator":
        from .consensus_orchestrator import ConsensusOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, ConsensusOrchestrator, **kwargs)
    elif orchestrator_type == "multiagent" or orchestrator_type == "multi-agent" or orchestrator_type == "multiagentorchestrator":
        from .multi_agent_orchestrator import MultiAgentOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, MultiAgentOrchestrator, **kwargs)
    elif orchestrator_type == "sequential" or orchestrator_type == "sequential-agent" or orchestrator_type == "sequentialagentorchestrator":
        from .sequential_agent_orchestrator import SequentialAgentOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, SequentialAgentOrchestrator, **kwargs)
    elif orchestrator_type == "image" or orchestrator_type == "imageorchestrator" or orchestrator_type == "imageproxy" or orchestrator_type == "image-analyser":
        from .image_orchestrator import ImageOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, ImageOrchestrator, **kwargs)
    elif orchestrator_type == "agent" or orchestrator_type == "agentorchestrator" or orchestrator_type == "agentproxy" or orchestrator_type == "single-agent":
        from .agent_orchestrator import AgentOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, AgentOrchestrator, **kwargs)
    elif orchestrator_type == "completion" or orchestrator_type == "completions" or orchestrator_type == "completionsorchestrator" or orchestrator_type == "completionsproxy":
        from ..proxy import CompletionsProxy
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, CompletionsProxy, **kwargs)
    elif orchestrator_type == "assistant" or orchestrator_type == "assistantorchestrator" or orchestrator_type == "assistantproxy" or orchestrator_type == "assistant-agent":
        from .assistant_orchestrator import AssistantOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, AssistantOrchestrator, **kwargs)
    elif orchestrator_type == "embedding" or orchestrator_type == "embeddings" or orchestrator_type == "embeddingorchestrator" or orchestrator_type == "embeddingproxy":
        from ..proxy import EmbeddingProxy
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, EmbeddingProxy, **kwargs)
    else:
        raise ValueError(f"Unknown orchestrator type: {orchestrator_type}")
    