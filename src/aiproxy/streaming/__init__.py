from typing import Callable

from ..interfaces.abstract_streamer import StreamWriter, SimpleStreamMessage, INTERIM_RESULT_MESSAGE, PROGRESS_UPDATE_MESSAGE, ERROR_MESSAGE, INFO_MESSAGE
from .pubsub_streamer import PubsubStreamWriter
from .botframework_streamer import BotframeworkStreamWriter
from .http_post_streamer import HttpPostStreamWriter
from .function_streamer import FunctionStreamWriter

def stream_factory(stream_type:str, stream_id:str = None, stream_config:str = None, message_filter:Callable[[dict|str], bool] = None, **kwargs) -> StreamWriter:
    if stream_type == "pubsub" or stream_type == "azure" or stream_type == "webpubsub":
        return PubsubStreamWriter(stream_id, stream_config, message_filter, **kwargs)
    elif stream_type == "botframework" or stream_type == "bot" or stream_type == "msbot":
        return BotframeworkStreamWriter(stream_id, stream_config, message_filter, **kwargs)
    elif stream_type == "http" or stream_type == "https" or stream_type == "webhook" or stream_type == "web" or stream_type == "post":
        return HttpPostStreamWriter(stream_id, stream_config, message_filter, **kwargs)
    elif stream_type == "function" or stream_type == "func" or stream_type == "lambda":
        return FunctionStreamWriter(stream_id, stream_config, message_filter, **kwargs)
    else:
        raise ValueError(f"Unknown stream type: {stream_type}")