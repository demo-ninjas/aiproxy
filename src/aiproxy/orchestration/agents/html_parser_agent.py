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
        
        self.extraction_rules = self.config.get("extraction-rules", self.config.get("rules", self.extraction_rules))
        self.convert_to_string = self.config.get("convert-to-string", self.config.get('as-string', True))
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
                rule_attr = rule.get("attr") or rule.get('attrs') or rule.get('attribute') or rule.get('attributes')
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
                        write_to[rule_name] = self.process_element(rule_attr, rule_store_tmp, element)
                    else:
                        data = []
                        for element in elements:
                            data.append(self.process_element(rule_attr, rule_store_tmp, element))
                        write_to[rule_name] = data
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

    def process_element(self, rule_attr, rule_store_tmp, element):
        if rule_attr is not None:
            data = {}
            for attr in rule_attr: 
                attr_name = attr.get('name')
                attr_selector = attr.get('selector')
                attr_args = attr.get('args')
            
                if attr_selector is None:
                    attr_selector = 'find'
                
                attr_value = None
                if attr_selector == 'find':
                    attr_value = element.find(**attr_args)
                elif attr_selector == 'find_all':
                    attr_value = element.find_all(**attr_args)
                elif attr_selector == 'select':
                    attr_value = element.select(**attr_args)
                elif attr_selector == 'get':
                    attr_value = element.get(**attr_args)
                elif attr_selector == 'text':
                    attr_value = element.get_text()
                
                if attr_value is not None:
                    if type(attr_value) is list: 
                        if len(attr_value) > 1:
                            data[attr_name] = [ e.get_text() if type(e) is not str else e for e in attr_value ]
                        elif len(attr_value) == 1:
                            data[attr_name] = attr_value[0].get_text() if type(attr_value[0]) is not str else attr_value[0]
                        else:
                            data[attr_name] = None
                    elif type(attr_value) is str:
                        data[attr_name] = attr_value
                    else:
                        data[attr_name] = attr_value.get_text()
            return data
        else:
            return element if rule_store_tmp else element.get_text()