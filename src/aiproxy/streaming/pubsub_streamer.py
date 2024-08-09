from uuid import uuid4
from typing import Callable

from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

from aiproxy.utils.config import load_named_config
from ..interfaces.abstract_streamer import StreamWriter, SimpleStreamMessage

_STREAM_CLIENT_CACHE = {}

class PubsubStreamWriter(StreamWriter):
    _stream_client:WebPubSubServiceClient
    _stream_id:str
    _expiry_mins:int = 90
    _allow_sending:bool = False

    def __init__(self, stream_id:str = None, config_name:str = None, message_filter:Callable[[dict|str], bool] = None) -> None:
        global _STREAM_CLIENT_CACHE

        super().__init__(stream_id, message_filter)

        cache_name = config_name or "default"
        if cache_name in _STREAM_CLIENT_CACHE:
            self._stream_client = _STREAM_CLIENT_CACHE[cache_name]
        else:
            import os
            config = None
            if config_name is not None:
                config = load_named_config(config_name)
            if config is None:
                config = {}
            
            self._expiry_mins = config.get('expiry-mins') or os.environ.get('PUBSUB_EXPIRY_MINS', self._expiry_mins)
            self._allow_sending = config.get('allow-sending') or os.environ.get('PUBSUB_ALLOW_SENDING', self._allow_sending)
            self._stream_client = self._connect_to_pubsub(config)
            _STREAM_CLIENT_CACHE[cache_name] = self._stream_client
        
    def _push_message(self, message:dict|str|SimpleStreamMessage, content_type:str = "application/json"):
        import logging
        logging.info(f"[STARTING] Sending message to PubSub: {self._stream_id}")

        data = message
        if type(message) is SimpleStreamMessage:
            data = message.to_dict()
        elif hasattr(message, 'to_dict'):
            data = message.to_dict()
        elif hasattr(message, 'to_json'):
            data = message.to_json()

        logging.info(f"[DOING] Sending message to PubSub: {self._stream_id} - {data}")
        self._stream_client.send_to_group(group=self._stream_id, message=data, content_type=content_type)
        logging.info(f"[DONE] Have sent message to PubSub: {self._stream_id} - {data}")

    def generate_access_url(self) -> str:
        roles = [f"webpubsub.joinLeaveGroup.{self._stream_id}"]
        if self._allow_sending:
            roles.append(f"webpubsub.sendToGroup.{self._stream_id}")

        token = self._stream_client.get_client_access_token(groups=[self._stream_id], roles=roles, minutes_to_expire=self._expiry_mins)
        return token.get('url')

    def _connect_to_pubsub(self, config:dict) -> WebPubSubServiceClient:
        import os

        ## Determine the hub name
        hub = config.get('hub') or os.environ.get("PUBSUB_HUB", "hub")

        ## Use Connection String if provided
        connection_string = config.get('connection') or config.get('connection_string') or os.environ.get('PUBSUB_CONNECTION_STRING', None)
        if connection_string is not None:
            return WebPubSubServiceClient.from_connection_string(connection_string, hub=hub)

        ## Otherwise, use the endpoint and either access key or Managed Identity
        endpoint = config.get('endpoint') or os.environ.get('PUBSUB_ENDPOINT', None)
        if endpoint is None:
            raise ValueError("The PubSub endpoint is not set - Please set the 'endpoint' in the config or set the environment variable: PUBSUB_ENDPOINT")
        
        ## Configure the credential (either Access Key or Managed Identity)
        access_key = config.get('access-key') or config.get('key') or os.environ.get('PUBSUB_ACCESS_KEY', None)
        credential = AzureKeyCredential(access_key) if access_key is not None else DefaultAzureCredential()
        
        return WebPubSubServiceClient(endpoint=endpoint, hub=hub, credential=credential)