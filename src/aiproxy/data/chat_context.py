from typing import Callable

from aiproxy.interfaces import StreamWriter, SimpleStreamMessage, HistoryProvider, NoOpHistoryProvider, FunctionDef
from .chat_message import ChatMessage
from .chat_response import ChatResponse

class ChatContext:
    thread_id:str = None
    history:list[ChatMessage] = None
    stream_writer:StreamWriter = None
    history_provider:HistoryProvider = None
    function_args_preprocessor:Callable[[dict, FunctionDef, 'ChatContext'], dict] = None
    function_filter:Callable[[str,str], bool] = None
    metadata:dict[str, any] = None
    metadata_transient_keys:list[str] = None
    current_msg_id:str = None
    stream_paused:bool = False

    def __init__(self, 
                 thread_id:str = None, 
                 history_provider:HistoryProvider = None, 
                 stream:StreamWriter = None, 
                 function_args_preprocessor:Callable[[dict, FunctionDef, 'ChatContext'], dict] = None, 
                 function_filter:Callable[[str,str], bool] = None,
                 metadata:dict[str,any] = None, 
                 metadata_transient_keys:list[str] = None
                 ):
        self.history = None
        self.thread_id = thread_id
        self.history_provider = history_provider or NoOpHistoryProvider()
        self.stream_writer = stream
        self.function_args_preprocessor = function_args_preprocessor
        self.function_filter = function_filter
        self.metadata = metadata
        self.metadata_transient_keys = metadata_transient_keys

    def clone_for_single_shot(self, with_streamer:bool = False) -> 'ChatContext':
        return ChatContext(
            history_provider=None,  ## Don't need to clone the history provider 
            stream=self.stream_writer if with_streamer else None,
            function_args_preprocessor=self.function_args_preprocessor,
            function_filter=self.function_filter,
            metadata=self.metadata.copy() if self.metadata is not None else None, 
            metadata_transient_keys=self.metadata_transient_keys, 
        )
    
    def clone_for_thread_isolation(self, thread_id_to_use:str = None, with_streamer:bool = False) -> 'ChatContext':
        return ChatContext(
            stream=self.stream_writer if with_streamer else None,
            history_provider=self.history_provider,
            function_args_preprocessor=self.function_args_preprocessor,
            function_filter=self.function_filter,
            thread_id=thread_id_to_use,
            metadata=self.metadata.copy() if self.metadata is not None else None, 
            metadata_transient_keys=self.metadata_transient_keys, 
        )

    def init_history(self, thread_id:str = None, system_prompt:str = None):
        if thread_id is None and self.thread_id is None:
            import uuid
            self.thread_id = uuid.uuid4().hex
        elif thread_id is not None: 
            self.thread_id = thread_id
        if self.history is not None and len(self.history) > 0: return   ## Already have history, no need to init...

        ## Load the history from the provider if it exists
        if self.history_provider is None:
            self.history_provider = NoOpHistoryProvider()
        
        ## Load the history from the provider if it exists
        history, metadata = self.history_provider.load_history(self.thread_id)
        self.history = history or []
        if self.metadata is None:
            self.metadata = metadata or {}
        elif metadata is not None: 
            self.metadata.update(metadata)

        if len(self.history) == 0 and system_prompt is not None:
            self.add_prompt_to_history(system_prompt, "system")

    def has_stream(self) -> bool: 
        return self.stream_writer is not None
    
    def push_stream_update(self, message:dict|str, message_type:str = None):
        """
        Pushes the provided stream update to the stream referenced by this context (if there is one, otherwise it does nothing)
        """
        if self.stream_writer is not None:
            if self.stream_paused: return
            if message_type is not None:
                if type(message) is dict: 
                    if "type" not in message and message_type is not None: 
                        message["type"] = message_type
                else: 
                    message = SimpleStreamMessage(message, message_type).to_dict()

            self.stream_writer.push_message(message)

    def add_prompt_to_history(self, message:str, role:str):
        msg = ChatMessage()
        msg.message = message
        msg.role = role
        self.add_message_to_history(msg)

    def add_response_to_history(self, response:ChatResponse):
        if response.failed or response.filtered: return
        msg = ChatMessage()
        msg.message = response.message
        msg.role = "assistant"
        msg.assistant_id = response.assistant_id
        if response.metadata is not None: 
            msg.metadata = response.metadata.copy()
            msg.run_id = msg.metadata.pop('run_id', None)
        if response.citations is not None: 
            msg.citations = response.citations
        self.add_message_to_history(msg)

    def add_message_to_history(self, message:ChatMessage):
        if self.history is None: 
            self.history = []
        self.history.append(message)

    def save_history(self):
        if self.history_provider is None: return
        if self.history is not None and len(self.history) > 0:
            if self.thread_id is None: 
                import uuid
                self.thread_id = uuid.uuid4().hex
                
            metadata = self.metadata.copy() if self.metadata is not None else None
            if metadata is not None and self.metadata_transient_keys is not None:
                for key in self.metadata_transient_keys:
                    if key in metadata:
                        metadata.pop(key)

            self.history_provider.save_history(self.thread_id, self.history, metadata=metadata)

    def get_metadata(self, key:str, default: any = None) -> any:
        return self.metadata.get(key, default) if self.metadata is not None else default
    
    def set_metadata(self, key:str, value:any, transient:bool = False):
        if self.metadata is None: 
            self.metadata = {}
        self.metadata[key] = value
        if transient: 
            if self.metadata_transient_keys is None: 
                self.metadata_transient_keys = []
            if key not in self.metadata_transient_keys:
                self.metadata_transient_keys.append(key)

    def parse_prompt_key(self, key:str) -> str:
        if key is None: return None
        ## Return the Thread ID 
        if key == 'thread_id' or key == 'thread': return self.thread_id
        ## If it matches a metadata key, return the metadata value
        return self.get_metadata(key)