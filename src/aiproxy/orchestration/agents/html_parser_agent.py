from typing import Callable
import json
from bs4 import BeautifulSoup

from aiproxy import ChatContext, ChatResponse
from ..agent import Agent

class HtmlPaserAgent(Agent):
    extraction_rules:list[dict] = None
    convert_to_string:bool = True
    soup_parser:str = 'html.parser'


    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        super().__init__(name, description, config)
        
        self.extraction_rules = self.config.get("extraction-rules") or self.config.get("rules") or self.extraction_rules
        self.convert_to_string = self.config.get("convert-to-string") or self.config.get('as-string') or True
        self.soup_parser = self.config.get("soup-parser") or 'html.parser'

    def reset(self):
        pass
    
    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        try:
            extraction_ctx = {}
            result = {}
            soup = BeautifulSoup(message, self.soup_parser)
            for rule in self.extraction_rules:
                rule_name = rule.get("name")
                rule_action = rule.get("action")
                rule_selector = rule.get("selector")
                rule_attr = rule.get("attr")
                rule_index = rule.get("index")
                rule_default = rule.get("default")
                rule_store_tmp = rule.get("as-var") or rule.get("store-tmp") or False
                rule_element = rule.get("var") or rule.get('on-var') or rule.get('for-element')
                
                write_to = extraction_ctx if rule_store_tmp is False else result
                basis = soup if rule_element is None else extraction_ctx.get(rule_element) or soup

                if rule_action is None and rule_selector is not None:
                    rule_action = "select"
                
                if rule_action is None:
                    write_to[rule_name] = rule_default

                rule_action = rule_action.lower()
                if rule_action == "select":
                    elements = basis.select(rule_selector)
                    if len(elements) == 0:
                        write_to[rule_name] = rule_default
                    else:
                        if rule_index is not None and rule_index >= 0 and rule_index < len(elements):
                            element = elements[rule_index]
                            if rule_attr is not None:
                                if rule_attr == "text":
                                    write_to[rule_name] = element.get_text()
                                else:
                                    write_to[rule_name] = element.get(rule_attr)
                            else:
                                write_to[rule_name] = element.get_text()
                        else:
                            write_to[rule_name] = rule_default
                elif rule_action == "find":
                    element = basis.find(rule_selector)
                    if element is None:
                        write_to[rule_name] = rule_default
                    else:
                        if rule_attr is not None:
                            if rule_attr == "text":
                                write_to[rule_name] = element.get_text()
                            else:
                                write_to[rule_name] = element.get(rule_attr)
                        else:
                            write_to[rule_name] = element.get_text()
                elif rule_action == "find_all":
                    elements = basis.find_all(rule_selector)
                    if len(elements) == 0:
                        write_to[rule_name] = rule_default
                    else:
                        if rule_index is not None and rule_index >= 0 and rule_index < len(elements):
                            element = elements[rule_index]
                            if rule_attr is not None:
                                if rule_attr == "text":
                                    write_to[rule_name] = element.get_text()
                                else:
                                    write_to[rule_name] = element.get(rule_attr)
                            else:
                                write_to[rule_name] = element.get_text()
                        else:
                            write_to[rule_name] = rule_default
                else:
                    write_to[rule_name] = rule_default

            response = ChatResponse()
            if self.convert_to_string:
                response.message = json.dumps(result)
            else:
                response.message = result
            return response
        except Exception as e:
            response = ChatResponse()
            response.error = True
            response.message = f"Error parsing HTML: {str(e)}"
            return response