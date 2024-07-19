from ..interfaces.abstract_history_provider import HistoryProvider
from aiproxy.data.chat_message import ChatMessage

from aiproxy.functions.cosmosdb import get_item, upsert_item, ROOT_CONFIG_NAME

class CosmosHistoryProvider(HistoryProvider):
    _config_name:str
    def __init__(self, config_name:str = ROOT_CONFIG_NAME):
        self._config_name = config_name

    def load_history(self, thread_id:str) -> list[ChatMessage]:
        item = get_item(thread_id, source=self._config_name)
        if item is None: return None
        return [ ChatMessage.from_dict(item) for item in item.get('history', []) ]


    def save_history(self, thread_id:str, history:list[ChatMessage], ttl:int = None):
        item = {
            'id': thread_id,
            'history': [ item.to_dict() for item in history ]
        }
        upsert_item(item, ttl=ttl, source=self._config_name)