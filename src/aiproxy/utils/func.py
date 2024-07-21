from typing import Callable
import json
import logging

from aiproxy import ChatContext
from aiproxy.functions import GLOBAL_FUNCTIONS_REGISTRY

FAILED_INVOKE_RESPONSE = "Failed"

def invoke_registered_function(function_name:str, function_args:str|dict, context:ChatContext = None, cast_result_to_string:bool = True,  arg_preprocessor:Callable[[dict[str,any]], dict[str,any]] = None, predefined_args:dict[str,any] = None, sys_objects:dict[str,any] = None) -> any:
    try:
        ## Load the args
        args = None
        if function_args is None:
            args = {}
        elif type(function_args) is str:
            args = json.loads(function_args)
        else:
            args = function_args

        ## Override supplied args with the predefined ones
        if predefined_args is not None:
            args.update(predefined_args)
            
        ## Get the function definition
        function_def = GLOBAL_FUNCTIONS_REGISTRY[function_name]
        if function_def is None:
            raise ValueError(f"Function with name: {function_name} not found in the Global Functions Registry")            

        ## Add the arg defaults from the function definition that are not already in the args
        for arg_name, arg_val in function_def.arg_defaults.items():
            if arg_name not in args:
                args[arg_name] = arg_val

        ## Pre-process the arguments using the provided pre-processor or the context's function_args_preprocessor
        if arg_preprocessor is not None:
            args = arg_preprocessor(args)
        elif context is not None and context.function_args_preprocessor is not None:
            args = context.function_args_preprocessor(args, function_def, context)
  
        ## Add any system supplied args (if needed by the function and not already supplied by the pre-processor)
        if context is not None and 'context' in function_def.args and 'context' not in args:
            args['context'] = context
        if sys_objects is not None:
            for k,v in sys_objects.items():
                if k in function_def.args and k not in args:
                    args[k] = v

        ## Remove any args that are not in the function's signature
        args_to_remove = []
        for arg_name in args.keys():
            if not arg_name in function_def.args:
                ## Remove arg from kwargs
                args_to_remove.append(arg_name)
        for arg_name in args_to_remove:
            logging.debug(f"Removing invalid arg: {arg_name} from function call to function: {function_name}")
            del args[arg_name]
        
        ## Invoke the function
        logging.debug(f"Invoking function: {function_name}")
        result = function_def.func(**args)

        ## Return the result as is if not casting to string
        if not cast_result_to_string: return result

        ## Ensure response is a string
        r_type = type(result)
        if r_type is not str:
            if r_type is dict or r_type is list:
                result = json.dumps(result, indent=4)
            elif r_type is bool:
                result = "true" if result else "false"
            elif hasattr(result, 'to_dict'):
                result = json.dumps(result.to_dict(), indent=4)
            elif hasattr(result, 'to_json'):
                tmp = result.to_json()
                if type(tmp) is str: 
                    result = tmp
                else: 
                    result = json.dumps(tmp, indent=4)
            else: 
                result = str(result)
        return result
    except Exception as e:
        logging.warning(f"Failed to invoke function '{function_name}' with Error: {e}")
        logging.error(e)
        return FAILED_INVOKE_RESPONSE