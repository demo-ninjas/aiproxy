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


## WHETHER TO RENDER THE INTERIM (DELTA) MESSAGES
RENDER_INTERIM_MESSAGES = False 
RENDER_PROGRESS_MESSAGES = True

## Create a Console printing stream writer
from aiproxy.streaming import FunctionStreamWriter, SimpleStreamMessage
__LAST_PROGRESS_MESSAGE = None
def print_stream_msg(msg):
    global RENDER_INTERIM_MESSAGES, RENDER_PROGRESS_MESSAGES, __LAST_PROGRESS_MESSAGE
    
    if msg is None:
        return
    
    msg_data = None
    if type(msg) is SimpleStreamMessage: 
        msg_data = msg.to_json()        
    elif type(msg) is dict:
        msg_data = msg
    elif hasattr(msg, 'to_json'):
        msg_data = msg.to_json() 
    elif hasattr(msg, 'to_dict'):
        msg_data = msg.to_dict()
    
    if msg_data is not None:
        msg_type = msg_data.get('type', 'Unknown')
        if msg_type == 'interim' and not RENDER_INTERIM_MESSAGES:
            return
        if msg_type == 'progress' and not RENDER_PROGRESS_MESSAGES:
            return
        if msg_type == 'progress':
            msg_txt = msg_data.get('message', '')
            if __LAST_PROGRESS_MESSAGE is not None and msg_txt == __LAST_PROGRESS_MESSAGE:  ## Don't print the same message over and over ...
                return
            __LAST_PROGRESS_MESSAGE = msg_txt
            print(f"Progress: {msg_txt}")
        elif msg_type == 'interim':
            delta = msg_data.get('delta', '')
            print(f" Interim: {delta}")
        elif msg_type == "step": 
            msg_txt = msg_data.get('message', '')
            print(f"    Step: {msg_txt}")
        else:
            print(f"  Stream: {msg_data}")
    else: 
        print(f"  Stream: {msg}")
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

# # Test the Step Plan Orchestrator
# from tests.test_step_plan_orchestrator import run as test_step_plan_orchestrator
# test_step_plan_orchestrator(streamer)
# print("\n------------------------\n")

# # Test the Step Plan Orchestrator (with adaptive card response)
# from tests.test_step_plan_orchestrator_card_response import run as test_step_plan_orchestrator_card_resopnse
# test_step_plan_orchestrator_card_resopnse(streamer)
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

# # Test the Code Function
# from tests.test_code_function import run as test_code_function
# test_code_function(streamer)
# print("\n------------------------\n")

