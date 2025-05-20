import os
import logging
from typing import Tuple
from ..interfaces.abstract_history_provider import HistoryProvider
from aiproxy.data.chat_message import ChatMessage
from concurrent.futures import ThreadPoolExecutor

from aiproxy.functions.cosmosdb import get_item, upsert_item, ROOT_CONFIG_NAME

def do_upsert(item:dict[str,any], config_name:str = None):
        try:
            upsert_item(item, source=config_name)
        except Exception as e:
            logging.error(f"Error upserting item {item['id']}: {e}")
            import traceback
            logging.error(traceback.format_exc())
            # print(f"Error upserting item {item['id']}: {e}")
            # raise e
        
class CosmosHistoryProvider(HistoryProvider):
    _config_name:str
    _executor:ThreadPoolExecutor
    def __init__(self, config_name:str = ROOT_CONFIG_NAME):
        self._config_name = config_name
        self._work_async = os.environ.get('COSMOS_HISTORY_ASYNC', 'true').lower() == 'true'
        if self._work_async:
            max_workers = int(os.environ.get('COSMOS_HISTORY_MAX_WORKERS', 4))
            self._executor = ThreadPoolExecutor(thread_name_prefix="history-",max_workers = max_workers)

    def load_history(self, thread_id:str) -> Tuple[list[ChatMessage], dict[str,any]]:
        item = get_item(thread_id, source=self._config_name)
        if item is None: return None, None

        messages = [ ChatMessage.from_dict(item) for item in item.get('history', []) ]
        metadata = item.get('metadata', None)
        return messages, metadata

    

    def save_history(self, thread_id:str, history:list[ChatMessage], metadata:dict[str,any] = None):
        item = {
            'id': thread_id,
            'history': [ item.to_dict() for item in history ]
        }
        if metadata is not None:
            item_meta = {}
            for k,v in metadata.items():
                if k not in ('id', 'history'):
                    ## If v has a to_dict method, use it
                    if hasattr(v, 'to_dict'):
                        item_meta[k] = v.to_dict()
                    elif hasattr(v, 'to_api_response'):
                        item_meta[k] = v.to_api_response()
                    elif hasattr(v, '__dict__'):
                        item_meta[k] = v.__dict__
                    else:
                        item_meta[k] = v
                    item_meta[k] = v
            item['metadata'] = item_meta
        if self._work_async:
            self._executor.submit(do_upsert, item, self._config_name)
        else:
            do_upsert(item, self._config_name)