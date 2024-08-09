import os
from typing import Callable
from abc import abstractmethod
from time import time_ns
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor


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
    _executor:ThreadPoolExecutor = None


    def __init__(self, stream_id:str, message_filter:Callable[[dict|str], bool] = None) -> None:
        self._message_filter = message_filter
        self._stream_id = stream_id or uuid4().hex
        self._async = os.environ.get('STREAM_WRITER_ASYNC', 'true').lower() == 'true'
    
    def push_message(self, message:dict|str, content_type:str = "application/json"):
        import logging
        logging.info(f"Will push message to stream: {self._stream_id} - {message}")
        if self._message_filter is None or self._message_filter(message):
            if self._async and self._executor is not None: 
                logging.info(f"[ASYNC] Pushing message to stream: {self._stream_id} - {message}")
                self._executor.submit(self._execute_push_message, message, content_type)
            else: 
                logging.info(f"[SYNC] Pushing message to stream: {self._stream_id} - {message}")
                self._execute_push_message(message, content_type)
    
    def set_executor(self, excutor:ThreadPoolExecutor):
        self._executor = excutor

    def _execute_push_message(self, message:dict|str, content_type:str = "application/json"):
        try:
            import logging
            logging.info(f"Doing message push to stream: {self._stream_id} - {message}")
            self._push_message(message, content_type)
        except Exception as e:
            import logging
            import traceback
            logging.error(f"Error pushing message to stream: {e}")
            logging.error(traceback.format_exc())


    @abstractmethod
    def _push_message(self, message:dict|str, content_type:str = "application/json"):
        raise NotImplementedError("This method must be implemented by the subclass")
    