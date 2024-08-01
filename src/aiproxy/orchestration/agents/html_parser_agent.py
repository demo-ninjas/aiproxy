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
                rule_attr = rule.get("attr") or rule.get('attribute')
                rule_limit = rule.get("limit") or None
                rule_index = rule.get("index")
                rule_default = rule.get("default")
                rule_store_tmp = rule.get("as-var") or rule.get("store-tmp") or False
                rule_element = rule.get("var") or rule.get('on-var') or rule.get('for-element')
                
                write_to = extraction_ctx if rule_store_tmp else result
                basis = soup if rule_element is None else extraction_ctx.get(rule_element, soup)

                if rule_action is None and rule_selector is not None:
                    rule_action = "select"
                
                if rule_action is None:
                    write_to[rule_name] = rule_default
                    continue

                elements = None
                rule_action = rule_action.lower()
                if rule_action == "select":
                    elements = basis.select(rule_selector, limit=rule_limit)
                elif rule_action == "find":
                    e = basis.find(rule_selector, limit=rule_limit)
                    if e is not None:
                        elements = [ e ]
                elif rule_action == "find_all":
                    elements = basis.find_all(rule_selector, limit=rule_limit)
                

                ## Process Element List...
                if elements is None or len(elements) == 0:
                    if rule_default is not None:
                        write_to[rule_name] = rule_default
                else: 
                    if rule_index is not None and rule_index >= 0 and rule_index < len(elements):
                        ## Pick a specific element from the list
                        element = elements[rule_index]
                        if rule_attr is not None:
                            if ',' in rule_attr:
                                attrs = rule_attr.split(',')
                                data = {}
                                for attr in attrs:
                                    attr_name = attr
                                    attr_value = attr
                                    if ':' in attr:
                                        attr_name, attr_value = attr.split(':')

                                    if attr_value == "text":
                                        attr_value = element.get_text()
                                    elif attr_value.startswith("select("):
                                        attr_value = element.select(attr[7:-1]).get_text()
                                    else:
                                        attr_value = element.get(attr)
                                    data[attr_name] = attr_value

                                write_to[rule_name] = data
                            else: 
                                attr_name = rule_name
                                attr_value = attr
                                if ':' in attr:
                                    attr_name, attr_value = attr.split(':')
                                
                                if attr_value == "text":
                                    write_to[attr_name] = element.get_text()
                                elif attr_value.startswith("select("):
                                    write_to[attr_name] = element.select(attr[7:-1]).get_text()
                                else:
                                    write_to[attr_name] = element.get(rule_attr)
                        else:
                            write_to[rule_name] = element if rule_store_tmp else element.get_text()
                    else:
                        if rule_attr is not None:
                            if rule_attr == "text":
                                write_to[rule_name] = element.get_text()
                            else:
                                write_to[rule_name] = element.get(rule_attr)
                        else:
                            write_to[rule_name] = elements if rule_store_tmp else [ e.get_text() for e in elements ]

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