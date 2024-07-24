import os
from typing import Callable
from concurrent.futures import ThreadPoolExecutor

from ..interfaces.abstract_streamer import StreamWriter, SimpleStreamMessage, INTERIM_RESULT_MESSAGE, PROGRESS_UPDATE_MESSAGE, ERROR_MESSAGE, INFO_MESSAGE
from .pubsub_streamer import PubsubStreamWriter
from .botframework_streamer import BotframeworkStreamWriter
from .http_post_streamer import HttpPostStreamWriter
from .function_streamer import FunctionStreamWriter

__GLOBAL_STREAM_EXECUTOR:ThreadPoolExecutor = ThreadPoolExecutor(thread_name_prefix="streaming-", max_workers=int(os.environ.get('STREAMING_MAX_WORKERS', 4)))

def stream_factory(stream_type:str, stream_id:str = None, stream_config:str = None, message_filter:Callable[[dict|str], bool] = None, **kwargs) -> StreamWriter:
    global __GLOBAL_STREAM_EXECUTOR
    streamer = None
    if stream_type == "pubsub" or stream_type == "azure" or stream_type == "webpubsub":
        streamer = PubsubStreamWriter(stream_id, stream_config, message_filter, **kwargs)
    elif stream_type == "botframework" or stream_type == "bot" or stream_type == "msbot":
        streamer = BotframeworkStreamWriter(stream_id, stream_config, message_filter, **kwargs)
    elif stream_type == "http" or stream_type == "https" or stream_type == "webhook" or stream_type == "web" or stream_type == "post":
        streamer = HttpPostStreamWriter(stream_id, stream_config, message_filter, **kwargs)
    elif stream_type == "function" or stream_type == "func" or stream_type == "lambda":
        streamer = FunctionStreamWriter(stream_id, stream_config, message_filter, **kwargs)
    else:
        raise ValueError(f"Unknown stream type: {stream_type}")
    
    streamer.set_executor(__GLOBAL_STREAM_EXECUTOR)
    return streamer