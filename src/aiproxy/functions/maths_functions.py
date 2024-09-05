from typing import Annotated

from aiproxy.utils.simple_eval import SimpleEval
evaluator = SimpleEval(operators=None, functions=None, names=None)

def calculate(
        expression:Annotated[str, "The mathematical expression to calculate"]) -> any:
    """
    Calculates a mathematical expression
    """
    return evaluator.eval(expression)

def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("calculate-maths-expression", "Calculates a mathematical expression, returning the result. This calculates maths expressions, do not pass python syntax to this or attempt to use it like the Python eval function - it is a maths calculator. Eg. '(16.1 x 12) / 3.14 + 6^3'", calculate)