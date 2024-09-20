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
    from RestrictedPython import safe_globals, safe_builtins, utility_builtins
    from RestrictedPython.Guards import full_write_guard
    from RestrictedPython.Eval import default_guarded_getattr, default_guarded_getitem, default_guarded_getiter
    from RestrictedPython.PrintCollector import PrintCollector
    import statistics
    allowed_globals = {}
    allowed_globals.update(safe_globals.get('__builtins__'))
    allowed_globals.update(utility_builtins)
    allowed_globals.update(safe_builtins)
    allowed_globals.update({ "statistics": statistics })
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
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("run_code", "Compiles the provided python code and executes the specified function, returning the result. The function signature must include a single parameter called 'data', eg. def myfunc(data)", run_code)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("eval_code", "Compiles the provided python statement and executes it, returning the result", eval_code)


# data = {
#     "PIZZA_RECIPES": [
#         {
#             "name": "Margherita",
#             "ingredients": ["tomato", "mozzarella", "basil"]
#         },
#         {
#             "name": "Pepperoni",
#             "ingredients": ["tomato", "mozzarella", "pepperoni"]
#         },
#         {
#             "name": "Hawaiian",
#             "ingredients": ["tomato", "mozzarella", "ham", "pineapple"]
#         }
#     ]
# }
# x = run_code("def find_recipe_with_most_ingredients(data):\n    recipes = data.get('PIZZA_RECIPES')\n    max_ingredients_recipe = max(recipes, key=lambda recipe: len(recipe['ingredients']))\n    return max_ingredients_recipe", "find_recipe_with_most_ingredients", data)
# print(x)