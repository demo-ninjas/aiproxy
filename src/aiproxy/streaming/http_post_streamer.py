from uuid import uuid4
from requests import post
from typing import Callable

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

from aiproxy.utils.config import load_named_config
from ..interfaces.abstract_streamer import StreamWriter

class HttpPostStreamWriter(StreamWriter):
    _post_url:str
    _headers:dict[str, str]
    _add_stream_to_body:bool = False

    def __init__(self, stream_id:str = None, config_name:str = None, message_filter:Callable[[dict|str], bool] = None) -> None:
        super().__init__(stream_id, message_filter)

        import os
        config = load_named_config(config_name) or {}

        url = config.get('url') or config.get('stream-url') or config.get('post-url') or os.environ.get('STREAM_URL') or os.environ.get("POST_STREAM_URL")
        if url is None:
            raise ValueError("The Stream URL is not set - Please set the 'url' in the config or set the environment variable: STREAM_URL")
        self._post_url = url.replace("{stream_id}", self._stream_id)

        headers = config.get('headers') or os.environ.get('STREAM_HEADERS')
        if headers is None:
            headers = {
                'content-type': 'application/json',
                'accepts': 'application/json'
            }
        
        if type(headers) is str: 
            import json
            headers = json.loads(headers)
        
        self._headers = headers
        
        self._add_stream_to_body = config.get('add-stream-id-to-body') or os.environ.get('POST_STREAM_ADD_ID_TO_BODY', 'false').lower() == 'true'


    def _push_message(self, message:dict|str, content_type:str = "application/json"):
        if self._add_stream_to_body:
            if type(message) is str:
                message = {"message": message, "stream-id": self._stream_id}
            else:
                message["stream-id"] = self._stream_id

        headers = self._headers
        if 'content-type' in self._headers and self._headers['content-type'] != content_type:
            headers = self._headers.copy()
            headers['content-type'] = content_type

        resp = post(self._post_url, headers=headers, json=message)
        return resp.status_code >= 200 and resp.status_code < 300