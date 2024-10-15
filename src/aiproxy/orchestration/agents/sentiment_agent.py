import json
from typing import Callable

from aiproxy import ChatContext, ChatResponse
from aiproxy.proxy import CompletionsProxy, GLOBAL_PROXIES_REGISTRY
from aiproxy.functions.string_functions import extract_code_block_from_markdown
from ..agent import Agent

DEFAULT_SYSTEM_PROMPT = """Given a recent message history (provided as the user prompt), you are tasked with determining the sentiment of the user, along with defining an emotion for them.

The following are the possible sentiments: 
- positive
- neutral
- negative

The following are the possible emotions:
- Admiration
- Adoration
- Aesthetic Appreciation
- Amusement
- Anger
- Anxiety
- Awe
- Awkwardness
- Boredom
- Calmness
- Confusion
- Craving
- Disgust
- Empathetic pain
- Entrancement
- Excitement
- Fear
- Horror
- Interest
- Joy
- Nostalgia
- Relief
- Romance
- Sadness
- Satisfaction
- Sexual desire
- Surprise

You should also provide a confidence score for your prediction and a brief description of your reasoning.

The user prompt will be a list of messages (sorted from most-recent to oldest), with each message formatted as follows: "[role] message"
Each message will be precceeded by a single line with three asterisks ("***").
eg. 
***
[user] I'm angry! I purchased your product for $400, but you now sell it the next day for only $100. This is unacceptable!
***
[assistant] I'm good, how are you?
***
[user] Hello, how are you?
***

Respond with a JSON object like this:
{
    "sentiment": "negative",
    "emotion": "Anger",
    "reasoning": "The user is expressing anger at the company for reducing the price of a product they recently purchased.",
    "sentiment-emoji": "😡",
    "emotion-emoji": "😡",
    "confidence": 0.95
}

You are determining the sentiment of the user based on the recent conversation history provided in the user prompt, the sentiment of the assistant is not relevant.
Return only the JSON object as the response.
"""

class SentimentAgent(Agent):
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
            resp.metadata = { "response-type": "json" }
            resp.message = """{
                "sentiment": "neutral",
                "confidence": 0.5
            }"""  ## No history, no suggestions
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

        ## Process sentiment response
        response.message = response.message.strip()
        response.message = extract_code_block_from_markdown(response.message, return_original_if_not_found=True)

        try:
            response.add_metadata("sentiment", json.loads(response.message))
        except:
            response.message = ""
            response.error = "Failed to parse the suggestions"
            response.failed = True
            
        return response