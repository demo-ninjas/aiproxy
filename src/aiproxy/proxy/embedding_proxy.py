import os

from aiproxy.data.chat_config import ChatConfig
from aiproxy.data.chat_response import ChatResponse

from .abstract_proxy import AbstractProxy

DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING_MODEL", "text-embedding-ada-002")

class EmbeddingProxy(AbstractProxy):
    def __init__(self, config:ChatConfig|str) -> None:
        super().__init__(config or 'default-embedding')
        self._model = config.oai_model or DEFAULT_EMBEDDING_MODEL
        
    def get_embeddings(self, message:str, override_model:str = None) -> list[float]:
        use_model = override_model or self._model
        result = self._client.embeddings.create(input=message, model=use_model, encoding_format='float')
        return result.data[0].embedding