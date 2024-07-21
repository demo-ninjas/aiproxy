import inspect  
from inspect import Parameter
from typing import Callable, Tuple

from openai.types.chat import ChatCompletionToolParam
from openai.types.shared_params import FunctionDefinition

class FunctionDef: 
    name:str
    base_func_name:str
    aliases:list[str]
    description:str
    func:Callable
    tool_param:ChatCompletionToolParam
    arg_defaults:dict[str,any]
    ai_args:dict[str, Tuple[str, str]]
    args:dict[str, Parameter]

    def __init__(self, name:str, description:str, func:Callable, aliases:list[str] = None, arg_defaults:dict[str,any] = None):
        self.name = name
        self.description = description
        self.func = func
        self.aliases = aliases or []
        self.base_func_name = getattr(func, '__name__', name)
        self.arg_defaults = arg_defaults or {}
        self.args = {}
        self.ai_args = {}
        self.tool_param = self._generate_tool_param(arg_defaults)

    def _params_to_skip(self) -> list[str]:
        return [ "self", "context", "metadata", "plan", "config", "args", "kwargs", "kwargs" ]
    
    def _generate_tool_param(self, arg_defaults:dict[str,any] = None) -> ChatCompletionToolParam:
        tool_param = ChatCompletionToolParam()
        tool_param['type'] = "function"
        tool_param['function'] = FunctionDefinition()
        tool_param['function']['name'] = self.name
        tool_param['function']['description'] = self.description
        tool_param['function']['parameters'] = {
            "type": "object",
            "properties": {},
            "required": []
        }

        props = tool_param['function']['parameters']['properties']
        req = tool_param['function']['parameters']['required']

        ## Inspect the Function signature + parameters and generate the argument descriptions 
        sig = inspect.signature(self.func)
        for param_name, param in sig.parameters.items():
            self.args[param_name] = param
            
            ## Skip any args that are pre-defined
            if arg_defaults is not None and param_name in arg_defaults:
                continue

            ## Skip any parameters that are never to be defined by the AI
            if param_name in self._params_to_skip(): continue
            
            ## Grab the class of the first type argument if it exists
            clazz = param.annotation.__origin__ if hasattr(param.annotation, "__origin__") else param.annotation
            ## Grab the description of the parameter from the annotation if it exists, otherwise use the docstring or a default description
            desc = param.annotation.__metadata__[0] if hasattr(param.annotation, "__metadata__") and len(param.annotation.__metadata__) > 0 \
                        else param.annotation.__doc__ if hasattr(param.annotation, "__doc__") \
                        else "The parameter " + param_name
            
            ## Determine the type of the parameter
            param_type = "string" if clazz  == str \
                            else "number" if clazz == int  \
                            else "object" if clazz == dict \
                            else "array" if clazz == list  \
                            else "boolean" if clazz == bool \
                            else "array" if "list" in str(param) \
                            else "object"
            
            ## Set the parameter type and description
            props[param_name] = {
                "type": param_type,
                "description": desc
            }

            ## If the parameter is an array, then we need to determine the type of the items in the array
            item_param_type = "string"
            if param_type == "array":
                if hasattr(clazz, "__args__") and len(clazz.__args__) > 0: ## For now, we're assuming the list type is the first type in the annotation and we're ignoring others
                    for i in range(len(clazz.__args__)):
                        first_type_arg = str(clazz.__args__[i])
                        if '[' in first_type_arg:
                            item_type_start = first_type_arg.index("[") + 1
                            first_type_item_type = first_type_arg[item_type_start : len(first_type_arg) - 1]
                            item_param_type = "string" if first_type_item_type  == "str" \
                                    else "number" if first_type_item_type == "int"  \
                                    else "object" if first_type_item_type.startswith("dict") \
                                    else "array" if first_type_item_type.startswith("list")  \
                                    else "boolean" if first_type_item_type == "bool" \
                                    else "object"
                            break
                else: 
                    item_param_type = "string"

                props[param_name]["items"] = {
                    "type": item_param_type
                }

            self.ai_args[param_name] = (param_type, desc)

            ## If no default value is provided, then the parameter is required
            if param.default == Parameter.empty:
                req.append(param_name)
        return tool_param
