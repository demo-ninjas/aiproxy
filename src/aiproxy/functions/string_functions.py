from typing import Annotated

def str_concatenate(
        string1:Annotated[str, "The first string"],
        string2:Annotated[str, "The second string to concatenate onto the end of the first string"],
        delimiter:Annotated[str, "The delimiter to use between the two strings (default is nothing)"] = ""
    ) -> str:
    """
    Concatenate two strings together
    """
    return string1 + delimiter + string2

def str_replace(
        string:Annotated[str, "The string to replace a substring in"],
        old:Annotated[str, "The substring to replace"],
        new:Annotated[str, "The new substring to replace the old one with"], 
        occurances:Annotated[int, "The maximum number of occurances to replace. Set to -1 to replace all occurances"] = -1
    ) -> str:
    """
    Replace a substring in a string
    """
    return string.replace(old, new, occurances)

def str_upper(string:Annotated[str, "The string to convert to uppercase"]) -> str:
    """
    Convert a string to uppercase
    """
    return string.upper()

def str_lower(string:Annotated[str, "The string to convert to lowercase"]) -> str:
    """
    Convert a string to lowercase
    """
    return string.lower()

def str_split(
        string:Annotated[str, "The string to split"],
        delimiter:Annotated[str, "The delimiter to split the string by"]
    ) -> list[str]:
    """
    Split a string into a list of strings
    """
    return string.split(delimiter)

def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("str_concatenate", "Concatenate two strings together", str_concatenate)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("str_replace", "Replace a substring in a string", str_replace)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("str_upper", "Convert a string to uppercase", str_upper)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("str_lower", "Convert a string to lowercase", str_lower)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("str_split", "Split a string into a list of strings", str_split)