import inspect  
from inspect import Parameter
from typing import Callable

from aiproxy.interfaces import FunctionDef

class FunctionRegistry: 
    functions:dict[str, FunctionDef]
    aliases:dict[str, FunctionDef]

    def __init__(self):
        self.functions = dict()
        self.aliases = dict()

    def register_base_function(self, name:str, description:str, func:Callable, arg_defaults:dict[str,any] = None):
        if not callable(func):
            raise ValueError(f"Function {func} is not callable")
        fdef = FunctionDef(name, description, func=func, arg_defaults=arg_defaults)
        self.functions[name] = fdef
        
    def unregister_function(self, name:str, and_aliases:bool = True):
        if name in self.functions:
            if and_aliases:
                fndef = self.functions[name]
                for alias in fndef.aliases:
                    del self.aliases[alias]
            del self.functions[name]
        elif name in self.aliases:  ## Unregister the alias
            del self.aliases[name]

    def register_function_alias(self, function_name:str, alias:str, description:str = None, arg_defaults:dict[str,any] = None):
        if function_name not in self.functions:
            raise ValueError(f"Function '{function_name}' is not registered, cannot register alias '{alias}' to it, you must register the base function before registering aliases to it")
        if alias in self.aliases:
            if self.aliases[alias].base_func_name != function_name:
                raise ValueError(f"Alias '{alias}' is already registered to a different base function, please choose a different alias name")
            return ## Alais already registered, no need to re-register it (This is a small risk, as the presented alias def could be different to the existing, but we'll take that risk for now)
        
        base_def = self.functions[function_name]
        args = base_def.arg_defaults.copy()
        if args is not None and arg_defaults is not None:
            args.update(arg_defaults)
        if args is None and arg_defaults is not None: 
            args = arg_defaults
        self.aliases[alias] = FunctionDef(alias, description or base_def.description, func=base_def.func, arg_defaults=args)

    def get_all_function_names(self) -> list[str]:
        return list(self.functions.keys()) + list(self.aliases.keys())
    
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

        ## Add the aliases to the tools list
        for func_def in self.aliases.values():
             ## Skip functions that don't match the global functions filter
            if not GLOBAL_FUNCTIONS_FILTER(func_def.name, func_def.base_func_name):
                continue

            ## Skip functions that don't match the filter
            if function_filter is not None and not function_filter(func_def.name, func_def.base_func_name):
                continue

            tools.append(func_def.tool_param)

        return tools

    def __getitem__(self, name:str) -> FunctionDef:
        fdef = self.functions.get(name)
        if fdef is None:
            fdef = self.aliases.get(name)
        ## Check if the function was misspelt by the AI (eg. swapping '-' and '_' in the name)
        name_alterations = [name.replace('-', '_'), name.replace('_', '-'), name.replace(' ', '-') , name.replace(' ', '_')]
        for alt_name in name_alterations:
            if fdef is None:
                fdef = self.functions.get(alt_name)
            if fdef is None:
                fdef = self.aliases.get(alt_name)
            if fdef is not None:
                break
        return fdef

    def __contains__(self, name:str):
        return self.__getitem__(name) is not None

GLOBAL_FUNCTIONS_REGISTRY = FunctionRegistry()
GLOBAL_FUNCTIONS_FILTER = lambda x,y: True