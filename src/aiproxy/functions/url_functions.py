from typing import Annotated, Tuple

def load_url(
        url:Annotated[str, "The URL to load the response for"], 
        method:Annotated[str, "The HTTP method to use (GET, POST, PUT, DELETE, etc.)"] = "GET", 
        headers: dict[str,str] = None, 
        query_params: Annotated[dict[str,str], "Any Query Parameters to add to the URL"]  = None,
        body: str = None
        ) -> str:
    """
    Retrieves the response from loading the specified url
    """
    status, response = load_url_response(url, method, headers, query_params, body)
    if status != 200:
        if status == 404:
            return f"The URL was not found"
        elif status >= 500: 
            return f"The requested web server had an error processing the request: {response.status_code}"
        elif status == 400:
            return f"The request was invalid"
        elif status == 401: 
            return f"The request was not allowed because you are not authorised to access the URL"
        elif status == 403: 
            return f"The request was forbidden by the web server"
        else: 
            return f"Error loading the URL: {status}"
    
    return response if response is not None else "No Response"

def load_json_url(
        url:Annotated[str, "The URL to load the response for"], 
        method:Annotated[str, "The HTTP method to use (GET, POST, PUT, DELETE, etc.)"] = "GET", 
        headers: dict[str,str] = None, 
        query_params: Annotated[dict[str,str], "Any Query Parameters to add to the URL"]  = None,
        body: str = None,
        response_field:Annotated[str, "The field in the JSON response to return (eg. 'response' will return the response field from the result JSON). You can use the dot notation to retrieve sub fields (eg. 'response.data' will return the data field from within response)"] = None
        ) -> dict:
    result = load_url(url, method, headers, query_params, body)
    if result is None or len(result) == 0:
        return None
    import json
    from aiproxy.functions.object_functions import get_obj_field
    try: 
        data = json.loads(result)
        if response_field is not None:
            data = get_obj_field(data, response_field)
        return data
    except Exception as e:
        return None
    
    
def load_url_response(
        url:Annotated[str, "The URL to load the response for"], 
        method:Annotated[str, "The HTTP method to use (GET, POST, PUT, DELETE, etc.)"] = "GET", 
        headers: dict[str,str] = None, 
        query_params: dict[str,str] = None,
        body: str = None
        ) -> Tuple[int, str]:
    """
    Retrieves the response from loading the specified url
    """
    import requests
    method= method.upper()

    if query_params is not None:
        if "?" in url:
            url += "&"
        else:
            url += "?"
        url += "&".join([f"{k}={v}" for k,v in query_params.items()])

    response = None
    if method == "POST":
        response = requests.post(url, headers=headers, data=body)
    elif method == "PUT":
        response = requests.put(url, headers=headers, data=body)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    else:
        response = requests.get(url, headers=headers)

    return (response.status_code, response.text) if response is not None else (0, "No Response")


def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("load_url", "Retrieves the response from loading the specified url", load_url)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("load_json_url", "Retrieves the JSON response from loading the specified url, optionally returning only a subset of the response data", load_json_url)