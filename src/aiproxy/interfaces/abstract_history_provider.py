import aiproxy.data as data

class HistoryProvider:
    def load_history(self, thread_id:str) -> list[data.ChatMessage]:
        raise NotImplementedError("This method must be implemented by the subclass")
    
    def save_history(self, thread_id:str, history:list[data.ChatMessage]):
        raise NotImplementedError("This method must be implemented by the subclass")
    

class NoOpHistoryProvider(HistoryProvider):
    def load_history(self, thread_id:str) -> list[data.ChatMessage]:
        return None
    
    def save_history(self, thread_id:str, history:list[data.ChatMessage]):
        pass