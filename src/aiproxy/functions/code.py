from typing import Annotated

from RestrictedPython import compile_restricted

def run_code(code:Annotated[str, "The python code to compile and execute. You must write the code as a function that takes a single parameter: data. The function signature must include this parameter, eg. def myfunc(data)"],
                function_name:Annotated[str, "The name of the function within the code to execute. This function will be called with a single parameter: data. The function signature must include this parameter, eg. def myfunc(data)"] = "myfunc",
                vars:dict[str, any] = None) -> any:
    """
    Execute the provided code and return the result of the specified function
    """
    # Compile the code
    compiled_code = compile_restricted(code, "<string>", "exec")
    # Execute the code
    loc = {}
    exec(compiled_code, _build_safe_globals(), loc)
    return loc[function_name](data=vars)

def eval_code(code:Annotated[str, "A python statement to compile and execute - returning the result of the statement."]) -> any:
    """
    Execute the provided python statement and return the result
    """
    # Compile the code
    compiled_code = compile_restricted(code, "<string>", "eval")
    # Execute the code
    return eval(compiled_code, _build_safe_globals())
    
def _build_safe_globals() -> dict:
    from RestrictedPython import safe_globals, safe_builtins, limited_builtins, utility_builtins
    from RestrictedPython.Guards import full_write_guard
    from RestrictedPython.PrintCollector import PrintCollector
    import statistics
    allowed_globals = {}
    allowed_globals.update(safe_globals.get('__builtins__'))
    allowed_globals.update(limited_builtins)
    allowed_globals.update(utility_builtins)
    allowed_globals.update(safe_builtins)
    allowed_globals.update({ "statistics": statistics })
    allowed_globals.update({ "min": min })
    allowed_globals.update({ "max": max })
    allowed_globals.update({ "sum": sum })
    allowed_globals.update({ "len": len })
    allowed_globals.update({ "sorted": sorted })
    allowed_globals.update({ "print": PrintCollector })
    allowed_globals.update({ "dict": full_write_guard(dict)})  ## Allow writing to the dict
    allowed_globals.update({ "list": full_write_guard(list)})  ## Allow writing to the dict
    allowed_globals.update({ "_write_": full_write_guard})  ## Allow writing to the dict
    allowed_globals.update({ "_getattr_ ": full_write_guard})  ## Allow writing to the dict
    return { '__builtins__': allowed_globals }

def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("run_code", "Compiles the provided python code and executes the specified function, returning the result. The function signature must include a single parameter called 'data', eg. def myfunc(data)", run_code)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("eval_code", "Compiles the provided python statement and executes it, returning the result", eval_code)


data = { "my_items": [1, 2, 3, 2, 3, 2, 6, 2, 8, 10] }
run_code("def calculate_min_and_max(data):\n    items = data.get('my_items')\n    data['my_items_min'] = min(items)\n    data['my_items_max'] = max(items)", "calculate_min_and_max", data)
print(data)