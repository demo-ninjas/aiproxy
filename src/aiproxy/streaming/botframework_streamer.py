from uuid import uuid4
from requests import post
from typing import Callable

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

from aiproxy.utils.config import load_named_config
from ..interfaces.abstract_streamer import StreamWriter

class BotframeworkStreamWriter(StreamWriter):
    _convo_endpoint:str
    _headers:dict[str, str]

    def __init__(self, stream_id:str = None, config_name:str = None, message_filter:Callable[[dict|str], bool] = None) -> None:
        super().__init__(stream_id, message_filter)

        import os
        config = load_named_config(config_name) or {}

        bot_secret = config.get('secret') or config.get('bot-secret') or os.environ.get('BOT_SECRET')
        if bot_secret is None:
            raise ValueError("The Bot Secret is not set - Please set the 'secret' in the config or set the environment variable: BOT_SECRET")
        endpoint = config.get('endpoint') or config.get('bot-endpoint') or os.environ.get('BOT_ENDPOINT')
        if endpoint is None:
            raise ValueError("The Bot Endpoint is not set - Please set the 'endpoint' in the config or set the environment variable: BOT_ENDPOINT")

        self._headers = {
            "Content-Type": "application/json",
            "Accepts": "application/json",
            "Authorization": f"Bearer {bot_secret}"
        }
        self._stream_id = stream_id or config.get("stream-id") or config.get('conversation-id') or os.environ.get("BOT_CONVERSATION_ID")
        if self._stream_id is None:
            raise ValueError("The Stream ID is not set - Please provide the conversation id (stream_id) when initialising this class, or set the 'stream-id' in the config or the environment variable: BOT_CONVERSATION_ID")
        self._convo_endpoint = f"{endpoint}/conversations/{stream_id}/activities"


    def _push_message(self, message:dict|str, content_type:str = "application/json"):
        resp = post(self._convo_endpoint, headers=self._headers, json=message)
        return resp.status_code >= 200 and resp.status_code < 300