from typing import Annotated

from aiproxy.utils.simple_eval import SimpleEval
evaluator = SimpleEval(operators=None, functions=None, names=None)

def calculate(
        expression:Annotated[str, "The mathematical expression to calculate"],
        vars:dict = None) -> any:
    """
    Calculates a mathematical expression
    """

    if expression is None or len(expression) == 0:
        return None
    
    if '$' in expression and vars is not None:
        for k,v in vars.items():
            if f"${k}" in expression:
                expression = expression.replace(f"${k}", str(v))

    if 'NoneType' in expression:
        expression = expression.replace('NoneType', '0')
    if 'None' in expression:
        expression = expression.replace('None', '0')
    if 'nan' in expression:
        expression = expression.replace('nan', '0')
    
    if expression.startswith('='):
        expression = expression[1:]
    elif expression.startswith('length(') and expression.endswith(')'):
        expression = expression[7:-1]
        return _calculate_length(expression)
    elif expression.startswith('len(') and expression.endswith(')'):
        expression = expression[4:-1]
        return _calculate_length(expression)
    elif expression.startswith('count(') and expression.endswith(')'):
        expression = expression[6:-1]
        return _calculate_length(expression)
    elif expression.startswith('size(') and expression.endswith(')'):
        expression = expression[5:-1]
        return _calculate_length(expression)
    elif expression.startswith("abs(") and expression.endswith(")"):
        expression = expression[4:-1]
        val = evaluator.eval(expression)
        return abs(val)
    elif expression.startswith("round(") and expression.endswith(")"):
        expression = expression[6:-1]
        arr = expression.split(',')
        val = evaluator.eval(arr[0])
        if len(arr) > 1:
            return round(val, int(arr[1]))
        else:
            return round(val)
    elif expression.startswith("ceil(") and expression.endswith(")"):
        expression = expression[5:-1]
        val = evaluator.eval(expression)
        return float(val).__ceil__()
    elif expression.startswith("floor(") and expression.endswith(")"):
        expression = expression[6:-1]
        val = evaluator.eval(expression)
        return float(val).__floor__()
    elif expression.startswith("sqrt(") and expression.endswith(")"):
        expression = expression[5:-1]
        val = evaluator.eval(expression)
        return float(val)**0.5
    elif expression.startswith("pow(") and expression.endswith(")"):
        expression = expression[4:-1]
        arr = expression.split(',')
        val1 = evaluator.eval(arr[0])
        val2 = evaluator.eval(arr[1])
        return float(val1)**float(val2)
    
    return evaluator.eval(expression)



def _calculate_length(expression:str) -> int:
    try:
        import json
        val = json.loads(expression)
        if type(val) is list:
            return len(val)
        elif type(val) is dict:
            return len(val.keys())
        else:
            return len(str(expression))
    except:
        return len(str(expression))

def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("calculate-maths-expression", "Calculates a mathematical expression, returning the result. This calculates maths expressions, do not pass python syntax to this or attempt to use it like the Python eval function - it is a maths calculator. Eg. '(16.1 x 12) / 3.14 + 6^3'", calculate)