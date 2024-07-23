## Load src into path
import sys
sys.path.insert(0, 'src')

## Load .env into environment
from dotenv import load_dotenv
load_dotenv()

from aiproxy import GLOBAL_FUNCTIONS_REGISTRY
from aiproxy import  GLOBAL_PROXIES_REGISTRY, CompletionsProxy, ChatContext
from aiproxy.data import ChatConfig

# Register all functions
from aiproxy.functions import register_all_base_functions
register_all_base_functions()

## Create a Console printing stream writer
from aiproxy.streaming import FunctionStreamWriter, SimpleStreamMessage
def print_stream_msg(msg):
    if msg is None:
        return
    if type(msg) is SimpleStreamMessage: 
        print(f"Stream: {msg.to_json()}")
    elif hasattr(msg, 'to_json'):
        print(f"Stream: {msg.to_json()}")
    elif hasattr(msg, 'to_dict'):
        print(f"Stream: {msg.to_dict()}")
    else:
        print(f"Stream: {msg}")
streamer = FunctionStreamWriter(stream_function=print_stream_msg)

import tests

# ## Test the Completions Proxy
# from tests.test_completions_proxy import run as test_completions_proxy
# test_completions_proxy(streamer)
# print("\n------------------------\n")

# ## Test the Assistants Proxy
# from tests.test_assistant_proxy import run as test_assistants_proxy
# test_assistants_proxy(streamer)
# print("\n------------------------\n")

# ## Test the Step Plan Orchestrator
# from tests.test_step_plan_orchestrator import run as test_step_plan_orchestrator
# test_step_plan_orchestrator(streamer)
# print("\n------------------------\n")

# ## Test the Select Agent Orchestrator
# from tests.test_select_agent_orchestrator import run as test_select_agent_orchestrator
# test_select_agent_orchestrator(streamer)
# print("\n------------------------\n")

# ## Test a configured Step Plan Orchestrator
# from tests.test_configured_orchestrator import run as test_configured_orchestrator
# test_configured_orchestrator(streamer)
# print("\n------------------------\n")

# Test the Image Agent
from tests.test_image_agent import run as test_image_agent
test_image_agent(streamer)
print("\n------------------------\n")
