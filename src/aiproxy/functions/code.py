from typing import Annotated

from RestrictedPython import compile_restricted

def run_code(code:Annotated[str, "The python code to compile and execute. You must write the code as a function that takes a single parameter: data. The function signature must include this parameter, eg. def myfunc(data)"],
                function_name:Annotated[str, "The name of the function within the code to execute. This function will be called with a single parameter: data. The function signature must include this parameter, eg. def myfunc(data)"] = "myfunc",
                fix_broken_code:Annotated[bool, "Flag to enable the function to attempt to automatically fix broken code if possible"] = True,
                max_attempts:Annotated[int, "The maximum number of attempts to try and fix the code before giving up"] = 3,
                vars:dict[str, any] = None) -> any:
    """
    Execute the provided code and return the result of the specified function
    """
    attempts = 0
    while attempts < max_attempts:
        try:
            # Compile the code
            compiled_code = compile_restricted(code, "<string>", "exec")
            # Execute the code
            loc = {}
            exec(compiled_code, _build_safe_globals(), loc)
            return loc[function_name](data=vars)
        except Exception as e:
            if fix_broken_code:
                attempts += 1
                code = _fix_code(code, str(e))
                if code is None:
                    return f"#ERROR {str(e)}"
            else:
                return f"#ERROR {str(e)}"

def eval_code(code:Annotated[str, "A python statement to compile and execute - returning the result of the statement."],
                fix_broken_code:Annotated[bool, "Flag to enable the function to attempt to automatically fix broken code if possible"] = True,
                max_attempts:Annotated[int, "The maximum number of attempts to try and fix the code before giving up"] = 3,
                ) -> any:
    """
    Execute the provided python statement and return the result
    """
    attempts = 0
    while attempts < max_attempts:
        try:
            # Compile the code
            compiled_code = compile_restricted(code, "<string>", "eval")
            # Execute the code
            return eval(compiled_code, _build_safe_globals())
        except Exception as e:
            if fix_broken_code:
                attempts += 1
                code = _fix_code(code, str(e))
                if code is None:
                    return f"#ERROR {str(e)}"
            else:
                return f"#ERROR {str(e)}"

    

def _fix_code(code:str, error:str) -> str:
    """
    Attempt to fix the provided code if it is broken
    """
    from aiproxy.functions.ai_chat import ai_chat
    from aiproxy.data import ChatContext

    user_prompt = f"""The provided code is probably broken.
When attempting to compile the code, the following error was encountered: 

{error}

Here is the code that failed: 

{code}

Please consider the error and then provide the corrected code.

ONLY provide the code, do NOT include any commentaries or explanations, and do not wrap the code in markdown - just provide the (corrected) raw python code.
"""
    res = ai_chat(user_prompt, context=ChatContext())

    ## Check if the response is an error
    if res.startswith("#ERROR"):
        return None
    
    ## Check if the response is filtered
    if res.startswith("#FILTERED"):
        return None

    ## Check if the response is wrapped in a markdown code block
    start_of_code_block = res.find("```")
    if start_of_code_block > -1:    
        start_of_code_in_block = res.find("\n", start_of_code_block+3)
        end_of_code_block = res.rfind("```", start_of_code_block+3)
        res = res[start_of_code_in_block:end_of_code_block].strip()
    
    return res
    

def _build_safe_globals() -> dict:
    from RestrictedPython import safe_globals, safe_builtins, utility_builtins
    from RestrictedPython.Guards import full_write_guard
    from RestrictedPython.Eval import default_guarded_getattr, default_guarded_getitem, default_guarded_getiter
    from RestrictedPython.PrintCollector import PrintCollector
    import statistics
    import bs4
    import json
    import re
    import datetime
    import requests
    import urllib
    import pandas
    import numpy
    import math

    allowed_globals = {}
    allowed_globals.update(safe_globals.get('__builtins__'))
    allowed_globals.update(utility_builtins)
    allowed_globals.update(safe_builtins)
    allowed_globals.update({ "statistics": statistics })
    allowed_globals.update({ "bs4": bs4 })
    allowed_globals.update({ "json": json })
    allowed_globals.update({ "re": re })
    allowed_globals.update({ "datetime": datetime })
    allowed_globals.update({ "requests": requests })
    allowed_globals.update({ "urllib": urllib })
    allowed_globals.update({ "pd": pandas })
    allowed_globals.update({ "np": numpy })
    allowed_globals.update({ "pandas": pandas })
    allowed_globals.update({ "numpy": numpy })
    allowed_globals.update({ "math": math })
    allowed_globals.update({ "abs": abs })
    allowed_globals.update({ "min": min })
    allowed_globals.update({ "max": max })
    allowed_globals.update({ "sum": sum })
    allowed_globals.update({ "len": len })
    allowed_globals.update({ "sorted": sorted })
    allowed_globals.update({ "print": PrintCollector })
    allowed_globals.update({ "dict": full_write_guard(dict)})  ## Allow writing to dict
    allowed_globals.update({ "list": full_write_guard(list)})  ## Allow writing to list
    allowed_globals.update({ "_write_": full_write_guard})  
    allowed_globals.update({ "_getattr_": default_guarded_getattr})
    allowed_globals.update({ "_getitem_": default_guarded_getitem})
    allowed_globals.update({ "_getiter_": default_guarded_getiter})
    
    return { '__builtins__': allowed_globals }

def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("run_code", "Compiles the provided python code and executes the specified function, returning the result. The function signature must include a single parameter called 'data', eg. def myfunc(data). The following libraries are provided: bs4, requests, pandas, numpy, statistics, json, re, datetime, urllib, math", run_code)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("eval_code", "Compiles the provided python statement and executes it, returning the result. The following libraries are provided: bs4, requests, pandas, numpy, statistics, json, re, datetime, urllib, math", eval_code)
