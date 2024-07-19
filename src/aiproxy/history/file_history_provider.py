from pathlib import Path
import json

from aiproxy.data.chat_message import ChatMessage

from ..interfaces.abstract_history_provider import HistoryProvider

class FileHistoryProvider(HistoryProvider):
    _dir_path:str

    def __init__(self, dir_path:str):
        self._dir_path = dir_path

    def load_history(self, thread_id:str) -> list[ChatMessage]:
        ## If file with thread_id name does not exist in dir_path, return None
        ## Otherwise, read the file and return the list of ChatMessage objects

        file_path = Path(self._dir_path) / f"{thread_id}.json"
        if not file_path.exists(): return None

        with open(file_path, 'r') as f:
            return [ChatMessage.from_dict(msg) for msg in json.load(f)]
        

    def save_history(self, thread_id:str, history:list[ChatMessage], ttl:int = None):
        ## Save the provided list of ChatMessage objects to a file named thread_id.json in dir_path
        ## If ttl is provided, set the file to expire in ttl seconds
        file_path = Path(self._dir_path) / f"{thread_id}.json"
        with open(file_path, 'w') as f:
            json.dump([msg.to_dict() for msg in history], f)