from typing import Annotated, Tuple

def load_url(
        url:Annotated[str, "The URL to load the response for"], 
        method:Annotated[str, "The HTTP method to use (GET, POST, PUT, DELETE, etc.)"] = "GET", 
        headers: dict[str,str] = None, 
        body: str = None
        ) -> str:
    """
    Retrieves the response from loading the specified url
    """
    status, response = load_url_response(url, method, headers, body)
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

def load_url_response(
        url:Annotated[str, "The URL to load the response for"], 
        method:Annotated[str, "The HTTP method to use (GET, POST, PUT, DELETE, etc.)"] = "GET", 
        headers: dict[str,str] = None, 
        body: str = None
        ) -> Tuple[int, str]:
    """
    Retrieves the response from loading the specified url
    """
    import requests
    method= method.upper()
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