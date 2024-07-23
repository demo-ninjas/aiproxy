
from typing import Tuple
from aiproxy.data.chat_message import ChatMessage

from ..interfaces.abstract_history_provider import HistoryProvider

class MapHistoryProvider(HistoryProvider):
    _map:dict[str, list[ChatMessage]]
    def __init__(self):
        self._map = {}

    def load_history(self, thread_id:str) -> Tuple[list[ChatMessage], dict[str,any]]:
        data = self._map.get(thread_id)
        if data is None: return None, None
        return data.get('messages'), data.get('metadata')

    def save_history(self, thread_id:str, history:list[ChatMessage], metadata:dict[str,any] = None):
        self._map[thread_id] = { 'messages':history, 'metadata': metadata }