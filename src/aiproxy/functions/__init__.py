from .function_registry import FunctionRegistry, FunctionDef, GLOBAL_FUNCTIONS_REGISTRY, GLOBAL_FUNCTIONS_FILTER
from .ai_chat import register_functions as register_ai_chat_functions
from .azure_search import register_functions as register_azure_search_functions
from .cosmosdb import register_functions as register_cosmosdb_functions
from .maths_functions import register_functions as register_maths_functions
from .string_functions import register_functions as register_string_functions
from .object_functions import register_functions as register_object_functions
from .url_functions import register_functions as register_url_functions
from .dates import register_functions as register_dates_functions

def register_all_base_functions():
    register_ai_chat_functions()
    register_azure_search_functions()
    register_cosmosdb_functions()
    register_maths_functions()
    register_string_functions()
    register_object_functions()
    register_url_functions()
    register_dates_functions()