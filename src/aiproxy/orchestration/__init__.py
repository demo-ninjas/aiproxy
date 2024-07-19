from ..proxy import AbstractProxy, GLOBAL_PROXIES_REGISTRY


def orchestrator_factory(config: dict, **kwargs) -> AbstractProxy:
    name = config.get("name", None)
    if name is None: 
        raise AssertionError("Orchestrator name not specified in config, this is a mandatory field")
    
    ## Grab the orchestrator type from the config (or default to the basic CompletionsProxy)
    orchestrator_type = config.get("type", "completion").lower()
    if orchestrator_type == "agentselect" or orchestrator_type == "agent-select" or orchestrator_type == "agentselectorchestrator":
        from .agent_select_orchestrator import AgentSelectOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, AgentSelectOrchestrator, **kwargs)
    elif orchestrator_type == "multiagent" or orchestrator_type == "multi-agent" or orchestrator_type == "multiagentorchestrator":
        from .multi_agent_orchestrator import MultiAgentOrchestrator
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, MultiAgentOrchestrator, **kwargs)
    elif orchestrator_type == "completion" or orchestrator_type == "completions" or orchestrator_type == "completionsorchestrator" or orchestrator_type == "completionsproxy":
        from ..proxy import CompletionsProxy
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, CompletionsProxy, **kwargs)
    elif orchestrator_type == "assistant" or orchestrator_type == "assistantorchestrator" or orchestrator_type == "assistantproxy":
        from ..proxy import AssistantProxy
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, AssistantProxy, **kwargs)
    elif orchestrator_type == "embedding" or orchestrator_type == "embeddings" or orchestrator_type == "embeddingorchestrator" or orchestrator_type == "embeddingproxy":
        from ..proxy import EmbeddingProxy
        return GLOBAL_PROXIES_REGISTRY.load_proxy(config, EmbeddingProxy, **kwargs)
    else:
        raise ValueError(f"Unknown orchestrator type: {orchestrator_type}")
    