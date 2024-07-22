from abc import abstractmethod

from aiproxy import ChatContext, ChatResponse

class Agent: 
    name:str = None
    description:str = None
    config:dict = None

    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        self.name = name
        self.description = description
        self.config = config or {}

    @abstractmethod
    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        pass

    def reset(self):
        pass
