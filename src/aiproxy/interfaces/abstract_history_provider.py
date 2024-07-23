from typing import Tuple
import aiproxy.data as data

class HistoryProvider:
    def load_history(self, thread_id:str) -> Tuple[list[data.ChatMessage], dict[str,any]]:
        raise NotImplementedError("This method must be implemented by the subclass")
    
    def save_history(self, thread_id:str, history:list[data.ChatMessage], metadata:dict[str,any] = None):
        raise NotImplementedError("This method must be implemented by the subclass")
    

class NoOpHistoryProvider(HistoryProvider):
    def load_history(self, thread_id:str) -> Tuple[list[data.ChatMessage], dict[str,any]]:
        return None, None
    
    def save_history(self, thread_id:str, history:list[data.ChatMessage], metadata:dict[str,any] = None):
        pass