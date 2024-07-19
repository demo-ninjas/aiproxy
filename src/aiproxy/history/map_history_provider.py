

from aiproxy.data.chat_message import ChatMessage

from ..interfaces.abstract_history_provider import HistoryProvider

class MapHistoryProvider(HistoryProvider):
    _map:dict[str, list[ChatMessage]]
    def __init__(self):
        self._map = {}

    def load_history(self, thread_id:str) -> list[ChatMessage]:
        return self._map.get(thread_id)

    def save_history(self, thread_id:str, history:list[ChatMessage], ttl:int = None):
        self._map[thread_id] = history