import inspect  
from inspect import Parameter
from typing import Callable

from openai.types.chat import ChatCompletionToolParam
from openai.types.shared_params import FunctionDefinition

from aiproxy.interfaces import FunctionDef

class FunctionRegistry: 
    functions:dict[str, FunctionDef]
    aliases:dict[str, FunctionDef]

    def __init__(self):
        self.functions = dict()
        self.aliases = dict()

    def register_base_function(self, name:str, description:str, func:Callable, arg_defaults:dict[str,any] = None, aliases:list[str] = None):
        if not callable(func):
            raise ValueError(f"Function {func} is not callable")
        fdef = FunctionDef(name, description, func=func, arg_defaults=arg_defaults, aliases=aliases)
        self.functions[name] = fdef
        if aliases is not None:
            for alias in aliases:
                self.aliases[alias] = fdef

    def unregister_function(self, name:str, and_aliases:bool = True):
        if name in self.functions:
            if and_aliases:
                fndef = self.functions[name]
                for alias in fndef.aliases:
                    del self.aliases[alias]
            del self.functions[name]
        elif name in self.aliases:  ## Unregister the alias
            del self.aliases[name]

    def register_function_alias(self, function_name:str, alias:str):
        if function_name not in self.functions:
            raise ValueError(f"Function {function_name} is not registered")
        self.functions[function_name].aliases.append(alias)
        self.aliases[alias] = self.functions[function_name]

    def generate_tools_definition(self, function_filter:Callable[[str, str], bool] = None) -> list[dict]:
        global GLOBAL_FUNCTIONS_FILTER

        tools = []
        for func_def in self.functions.values():
            ## Skip functions that don't match the global functions filter
            if not GLOBAL_FUNCTIONS_FILTER(func_def.name, func_def.base_func_name):
                continue

            ## Skip functions that don't match the filter
            if function_filter is not None and not function_filter(func_def.name, func_def.base_func_name):
                continue

            tools.append(func_def.tool_param)
            for alias in func_def.aliases:
                 ## Skip functions that don't match the global functions filter
                if not GLOBAL_FUNCTIONS_FILTER(alias, func_def.base_func_name):
                    continue

                ## Skip functions that don't match the filter
                if function_filter is not None and not function_filter(alias, func_def.base_func_name):
                    continue
                
                tool = func_def.tool_param.copy()
                tool['function']['name'] = alias
                tools.append(tool)

        return tools

    def __getitem__(self, name:str) -> FunctionDef:
        fdef = self.functions.get(name)
        if fdef is None:
            fdef = self.aliases.get(name)
        return fdef

    def __contains__(self, name:str):
        return name in self.functions or name in self.aliases

GLOBAL_FUNCTIONS_REGISTRY = FunctionRegistry()
GLOBAL_FUNCTIONS_FILTER = lambda x,y: True