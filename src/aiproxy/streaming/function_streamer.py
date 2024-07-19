from typing import Callable
from ..interfaces.abstract_streamer import StreamWriter

class FunctionStreamWriter(StreamWriter):
    def __init__(self, stream_function:Callable, stream_id:str = None, message_filter:Callable[[dict|str], bool] = None) -> None:
        super().__init__(stream_id, message_filter)
        self.stream_function = stream_function

    def _push_message(self, message:dict|str, content_type:str = "application/json"):
        self.stream_function(message)
