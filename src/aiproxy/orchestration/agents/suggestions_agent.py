import json
from typing import Callable

from aiproxy import ChatContext, ChatResponse
from aiproxy.proxy import CompletionsProxy, GLOBAL_PROXIES_REGISTRY
from ..agent import Agent

DEFAULT_SYSTEM_PROMPT = """Given a recent message history (provided as the user prompt), you are tasked with coming up with a list of questions (next best actions) that the user may wish to send given their recent conversation history.

The questions that you provide will be provided to the user as suggested next questions or actions.

The user prompt will be a list of messages, with each message formatted as follows: "[role] message"
Each message will be precceeded by a single line with three asterisks ("***").
eg. 
***
[assistant] It's it's on sale for $19.99
***
[user] What is the price of the blue shirt?
***
[assistant] I'm good, how are you?
***
[user] Hello, how are you?
***

Note: The messages are provided in reverse order, with the most recent message first.


You are to return the suggested questsions (actions) as a JSON array like this:
[
 "Question 1", 
 "Question 2", 
 "Question 3"
]

For example, given the above user prompt, you might return the following suggestions:

[
    "Is this shirt available in red?", 
    "Can you tell me what fabric this is made of?", 
    "What is the warranty on the shirt?"
]


The suggestions you provide should be what you think the user may wish to ask or do next, based on the recent conversation history provided in the user prompt.
"""


class SuggestionsAgent(Agent):
    proxy:CompletionsProxy
    _system_prompt:str = None
    _custom_model:str = None
    _single_shot:bool = False
    _thread_isolated:bool = True
    _isolated_thread_id:str = None
    _function_filter:Callable[[str,str], bool] = None

    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        super().__init__(name, description, config)

        proxy_name = self.config.get("proxy-name", name)
        self.proxy = GLOBAL_PROXIES_REGISTRY.load_proxy(proxy_name, CompletionsProxy)
        self._system_prompt = self.config.get("system-prompt") or self.config.get("system-message") or DEFAULT_SYSTEM_PROMPT
        self._custom_model = self.config.get("model", None)
        
    def set_function_filter(self, function_filter:Callable[[str,str], bool]):
        self._function_filter = function_filter

    def reset(self):
        self._isolated_thread_id = None
    
    def process_message(self, message:str, context:ChatContext, **kwargs) -> ChatResponse:        
        context.init_history()
        if context.history is None or len(context.history) == 0:
            resp = ChatResponse()
            resp.message = "[]"  ## No history, no suggestions
            return resp
        
        ## Grab the recent history (upto 20 messages) and format it for the model
        history_msgs = context.history[:20].copy()
        history_msgs.reverse()
        
        history = ""
        for msg in history_msgs:
            if msg.role not in ["user", "assistant"]: continue
            msg_text = msg.message
            if msg_text is None or len(msg_text.strip()) == 0: continue
            if "***" in msg_text: msg_text = msg_text.replace("***", "*-*-*")
            history += f"***\n[{msg.role}] {msg_text}\n"

        # Send message to the proxy
        response = self.proxy.send_message(history, context.clone_for_single_shot(), override_model=self._custom_model, override_system_prompt=self._system_prompt, function_filter=self._function_filter)

        ## Process suggestions response
        response.message = response.message.strip()
        if len(response.message) == 0:
            response.message = "[]"
        if "```" in response.message:
            start_of_code_block = response.message.index("```")
            start_of_code_in_block = response.message.index("\n", start_of_code_block+3)
            end_of_code_block = response.message.index("```", start_of_code_block+3)
            response.message = response.message[start_of_code_in_block:end_of_code_block+3].strip()
        if response.message[0] != "[":
            response.message = f"[{response.message}]"

        try:
            response.add_metadata("suggestions", json.loads(response.message))
        except:
            response.message = "[]"
            response.error = "Failed to parse the suggestions"
            response.failed = True
            
        return response