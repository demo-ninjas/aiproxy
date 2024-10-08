from typing import Callable
import json
from markdownify import markdownify as md


from aiproxy import ChatContext, ChatResponse
from ..agent import Agent

class HtmlMarkdownAgent(Agent):
    _tags_to_exclude:list[str] = ["script", "style", "link", "head", "meta", "title"]
    
    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        super().__init__(name, description, config)
        
        self._tags_to_exclude = self.config.get("tags-to-exclude") or self.config.get("exclude-tags") or self._tags_to_exclude
        if  type(self._tags_to_exclude) is str: 
            self._tags_to_exclude = self._tags_to_exclude.split(",")

    def reset(self):
        pass
    
    def process_message(self, message:str, context:ChatContext, **kwargs) -> ChatResponse:
        from aiproxy.functions.url_functions import load_url_response

        try:
            result = None
            if self._tags_to_exclude is None or len(self._tags_to_exclude) == 0:
                result = md(message)
            else: 
                result = md(message, strip=self._tags_to_exclude)

            response = ChatResponse()
            if result is not None and len(result) > 0:
                response.message = result
            else:
                response.error = True
                response.message = "No markdown content was produced from the HTML message"
            return response
        except Exception as e:
            response = ChatResponse()
            response.error = True
            response.message = f"Error processing HTML into markdown: {str(e)}"
            return response