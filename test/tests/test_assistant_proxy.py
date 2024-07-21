from typing import Annotated

from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.data import ChatConfig
from aiproxy.proxy import AssistantProxy
from aiproxy.streaming import StreamWriter

def run(streamer:StreamWriter):
    print("Running a test using the Assistant Proxy")

    config = ChatConfig.load('test-assistant')
    comp = GLOBAL_PROXIES_REGISTRY.load_proxy(config, AssistantProxy)
    if comp is None:
        raise Exception("Could not load proxy")
    if type(comp) is not AssistantProxy:
        raise Exception("Loaded proxy is not an AssistantProxy")
    
    ## Test the Completions Proxy
    context = ChatContext(None, stream=streamer)
    resps = comp.send_message_and_return_outcome("What is the capital of France?", assistant_name_or_id='Mr Limerick', context=context)
    for resp in resps: 
        print(f"{resp.metadata.get('assistant') or resp.assistant_id}: {resp.message}")

    