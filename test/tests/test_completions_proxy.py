from typing import Annotated

from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.data import ChatConfig
from aiproxy.proxy import CompletionsProxy
from aiproxy.streaming import StreamWriter

def run(streamer:StreamWriter):
    print("Running a test using the Completions Proxy")

    config = ChatConfig.load('test-completions')
    comp = GLOBAL_PROXIES_REGISTRY.load_proxy(config, CompletionsProxy)
    if comp is None:
        raise Exception("Could not load proxy")
    if type(comp) is not CompletionsProxy:
        raise Exception("Loaded proxy is not a CompletionsProxy")
    
    ## Test the Completions Proxy
    context = ChatContext(None, stream=streamer)
    resp = comp.send_message("What is the capital of France?", context)
    print(resp.message)

