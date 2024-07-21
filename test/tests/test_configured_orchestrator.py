from typing import Annotated

from aiproxy import GLOBAL_FUNCTIONS_REGISTRY
from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.data import ChatConfig
from aiproxy.orchestration.step_plan_orchestrator import StepPlanOrchestrator
from aiproxy.streaming import StreamWriter

def run(streamer:StreamWriter):
    print("Running a test using a previously configured Step Plan Orchestrator")

    config = ChatConfig.load('recipe-step-planner')
    step_orchestrator = GLOBAL_PROXIES_REGISTRY.load_proxy(config, StepPlanOrchestrator)
    if step_orchestrator is None:
        raise Exception("Could not load proxy")
    if type(step_orchestrator) is not StepPlanOrchestrator:
        raise Exception("Loaded proxy is not a StepPlanOrchestrator")
    
    context = ChatContext(None, stream=streamer)
    q = "I have a family of 4, 2 adults and 2 children. We all love pasta and pizza. The kids dislike mushrooms. I am looking for some easy to make recipes that the whole family will enjoy."
    print(f"Question: {q}")
    resp = step_orchestrator.send_message(q, context)
    print(resp.message)

    print('\n\nSteps used to respond to this prompt:')
    for step in resp.metadata.get('steps', []) if resp.metadata else []:
        print("* " + step)
