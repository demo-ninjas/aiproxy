## Load .env into environment
from dotenv import load_dotenv
load_dotenv()


from aiproxy.functions import register_ai_chat_functions, register_maths_functions, register_string_functions
register_ai_chat_functions()
register_maths_functions()
register_string_functions()



## Setup History Provider
from aiproxy.history import CosmosHistoryProvider
from aiproxy import  GLOBAL_PROXIES_REGISTRY, CompletionsProxy, ChatContext
from aiproxy.data import ChatConfig
from aiproxy.streaming import FunctionStreamWriter

def pub_msg(msg):
    print(msg)


streamer = FunctionStreamWriter(stream_function=pub_msg)

## Create a stream factory and pass that in as the stream writer will need a different stream ID for different conversations

config = ChatConfig.load('default')
context = ChatContext(None, stream=streamer)
comp = GLOBAL_PROXIES_REGISTRY.load_proxy(config, CompletionsProxy)
resp = comp.send_message("Hello", context)
print(resp.message)


## Test the Agent Select Orchestrator
from aiproxy.orchestration.agent_select_orchestrator import AgentSelectOrchestrator 
from aiproxy.data import ChatConfig
config = ChatConfig('selector')
config.extra['agents'] = [
    {
        "name": "Maths Professor",
        "description": "An tenured, highly experienced professor of mathematics",
        "type": "completion", 
        "system-message": "You are a highly distinguished and experienced Maths Professor. You are an expert in the field of mathematics and can answer any question related to mathematics",
    },
    {
        "name": "Computer Science Professor",
        "description": "An tenured, highly experienced professor of computer science who specialises in the field of Softwware Engineering",
        "type": "completion", 
        "system-message": "You are a highly distinguished and experienced Computer Science Professor. You are an expert in the field of computer science with a particular focus on software engineering. You can answer any question related to computer science, and you are an expert in writing code",
    },
    {
        "name": "History Professor",
        "description": "An tenured, highly experienced professor of history",
        "type": "completion", 
        "system-message": "You are a highly distinguished and experienced History Professor. You are an expert in the field of history and can answer any question related to history",
    },
    {
        "name": "English Professor",
        "description": "An tenured, highly experienced professor of English",
        "type": "completion", 
        "system-message": "You are a highly distinguished and experienced English Professor. You are an expert in the field of English and can answer any question related to English",
    },
    {
        "name": "AI Chatbot",
        "description": "A highly advanced AI chatbot, with no specific area of expertise",
        "type": "completion", 
        "system-message": "You are a highly advanced AI chatbot. You are capable of answering a wide range of questions and engaging in conversation on a variety of topics",
    },
]

orchestrator = GLOBAL_PROXIES_REGISTRY.load_proxy(config, AgentSelectOrchestrator)
context = ChatContext(None, stream=streamer)
q = "Who was Napolean and was he a great leader?"
print(f"Question: {q}")
resp = orchestrator.send_message(q, context)
print(resp.message)

q = "What is the capital of France?"
print(f"Question: {q}")
resp = orchestrator.send_message(q, context)
print(resp.message)

q = "What is the square root of 144?"
print(f"Question: {q}")
resp = orchestrator.send_message(q, context)
print(resp.message)

q = "What is the difference between a linked list and an array?"
print(f"Question: {q}")
resp = orchestrator.send_message(q, context)
print(resp.message)
