from typing import Callable
from abc import abstractmethod
from time import time_ns
from uuid import uuid4

INTERIM_RESULT_MESSAGE = "interim"
PROGRESS_UPDATE_MESSAGE = "progress"
ERROR_MESSAGE = "error"
INFO_MESSAGE = "info"

class SimpleStreamMessage:
    message:str
    message_type:str
    timestamp:int

    def __init__(self, message:str, message_type:str) -> None:
        self.message = message
        self.message_type = message_type
        self.timestamp = time_ns() / 1000000    ## timestamp in milliseconds
    
    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "type": self.message_type
        }
    
    def to_json(self) -> dict:
        return self.to_dict()
    

class StreamWriter:
    _message_filter:Callable[[dict|str], bool]
    _stream_id:str

    def __init__(self, stream_id:str, message_filter:Callable[[dict|str], bool] = None) -> None:
        self._message_filter = message_filter
        self._stream_id = stream_id or uuid4().hex
    
    def push_message(self, message:dict|str, content_type:str = "application/json"):
        if self._message_filter is None or self._message_filter(message):
            self._push_message(message, content_type)
    

    @abstractmethod
    def _push_message(self, message:dict|str, content_type:str = "application/json"):
        raise NotImplementedError("This method must be implemented by the subclass")
    