from typing import Annotated

from aiproxy import GLOBAL_FUNCTIONS_REGISTRY
from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.data import ChatConfig
from aiproxy.orchestration.agent_select_orchestrator import AgentSelectOrchestrator 
from aiproxy.streaming import StreamWriter

def run(streamer:StreamWriter):
    print("Running a test using the Select Agent Orchestrator")

    config = ChatConfig('selector')
    config['agents'] = [
        {
            "name": "Maths Professor",
            "description": "An tenured, highly experienced professor of mathematics",
            "type": "completion", 
            "system-prompt": "You are a highly distinguished and experienced Maths Professor. You are an expert in the field of mathematics and can answer any question related to mathematics",
        },
        {
            "name": "Computer Science Professor",
            "description": "An tenured, highly experienced professor of computer science who specialises in the field of Softwware Engineering",
            "type": "completion", 
            "system-prompt": "You are a highly distinguished and experienced Computer Science Professor. You are an expert in the field of computer science with a particular focus on software engineering. You can answer any question related to computer science, and you are an expert in writing code",
        },
        {
            "name": "History Professor",
            "description": "An tenured, highly experienced professor of history",
            "type": "completion", 
            "system-prompt": "You are a highly distinguished and experienced History Professor. You are an expert in the field of history and can answer any question related to history",
        },
        {
            "name": "English Professor",
            "description": "An tenured, highly experienced professor of English",
            "type": "completion", 
            "system-prompt": "You are a highly distinguished and experienced English Professor. You are an expert in the field of English and can answer any question related to English",
        },
        {
            "name": "AI Chatbot",
            "description": "A highly advanced AI chatbot, with no specific area of expertise",
            "type": "completion", 
            "system-prompt": "You are a highly advanced AI chatbot. You are capable of answering a wide range of questions and engaging in conversation on a variety of topics",
        },
    ]

    orchestrator = GLOBAL_PROXIES_REGISTRY.load_proxy(config, AgentSelectOrchestrator)
    if orchestrator is None:
        raise Exception("Could not load proxy")
    if type(orchestrator) is not AgentSelectOrchestrator:
        raise Exception("Loaded proxy is not a AgentSelectOrchestrator")
    
    context = ChatContext(None, stream=streamer)
    q = "Who was Napolean and was he a great leader?"
    print(f"Question: {q}")
    resp = orchestrator.send_message(q, context)
    print(f"Answered by: {resp.metadata.get('responder', '?')}:\nAnswer: {resp.message}\n")

    q = "What is the capital of France?"
    print(f"Question: {q}")
    resp = orchestrator.send_message(q, context)
    print(f"Answered by: {resp.metadata.get('responder', '?')}:\nAnswer: {resp.message}\n")

    q = "What is the square root of 144?"
    print(f"Question: {q}")
    resp = orchestrator.send_message(q, context)
    print(f"Answered by: {resp.metadata.get('responder', '?')}:\nAnswer: {resp.message}\n")

    q = "What is the difference between a linked list and an array?"
    print(f"Question: {q}")
    resp = orchestrator.send_message(q, context)
    print(f"Answered by: {resp.metadata.get('responder', '?')}:\nAnswer: {resp.message}\n")
    

