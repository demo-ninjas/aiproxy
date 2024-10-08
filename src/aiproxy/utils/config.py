import os
import json

from .fs import read_first_matching_file

CACHED_CONFIGS = {}
CONFIGS_DIR = os.environ.get("CONFIGS_DIR", "configs")
CHECK_COSMOS = os.environ.get("CONFIGS_CHECK_COSMOS", "true").lower() == "true"

def load_named_config(name:str, raise_if_not_found:bool = True, use_cache:bool = True) -> dict:
    """
    Loads a configuration with the specified name from one of the following locations: 
    * Environment variables
    * A file
    * The ROOT CosmosDB Configs Container (if enabled)
    """
    global CACHED_CONFIGS

    ## Check if the config is already loaded
    if use_cache and name in CACHED_CONFIGS:
        return CACHED_CONFIGS[name]
    
    ## Load the config
    config_item = None

    ## Check if the config is specified in the environment variables
    config_str = os.environ.get(f"CONFIG_{name.upper()}", None)
    if config_str is not None:
        config_item = json.loads(config_str)
    
    ## Check if the config is specified in a file
    if config_item is None:
        config_str = read_first_matching_file(name, [CONFIGS_DIR, ".local-configs"], [".json", ".conf"])
        if config_str is not None:
            config_item = json.loads(config_str)

    ## Check if the config is specified in the ROOT Cosmos Container
    if config_item is None and CHECK_COSMOS: 
        from aiproxy.functions.cosmosdb import get_item
        cosmos_config_name = os.environ.get("CONFIGS_COSMOS_CONFIG", "configs")
        if cosmos_config_name == name: 
            ## We're looking for the cosmos config, but that's not going to work if we're here, because this cosmos lookup requires having the cosmos lookup config...
            # Let's just use a default cosmos config (which points at the root cosmos database + the "configs" container within)
            config_item = {
                "connection": "DEFAULT",
                "database": "DEFAULT",
                "container": "configs"
            }
        else: 
            config_item = get_item(name, source=cosmos_config_name)
            if config_item is None: 
                config_item = get_item(name.lower(), source=cosmos_config_name)
    
    ## If config is not found, raise an error
    if raise_if_not_found and config_item is None:
        raise ValueError(f"The Configuration with name '{name}' was not found")
    
    ## Apply Replacements
    if config_item is not None: 
        if type(config_item) == dict:
            for k,v in config_item.items():
                if type(v) == str:
                    if v.startswith("$"):
                        config_item[k] = os.environ.get(v[1:], v)
                    elif v.startswith("@"):
                        config_item[k] = load_named_config(v[1:], raise_if_not_found, use_cache)
                    elif v.startswith("!"):
                        config_item[k] = load_text_file(v[1:])

        if use_cache: 
            ## Cache the config
            CACHED_CONFIGS[name] = config_item
    
    return config_item

def load_text_file(file_path:str) -> str:
    """
    Loads the contents of a text file
    """
    while file_path.startswith("/"):
        full_path = file_path[1:]
    if '..' in file_path:
        raise ValueError(f"Invalid file path: {file_path}")
    
    full_path = CONFIGS_DIR + "/" + file_path
    if not os.path.exists(full_path):
        full_path = CONFIGS_DIR + "/" + file_path + ".txt"
    if not os.path.exists(full_path):
        raise ValueError(f"File not found: {file_path}")

    with open(full_path, 'r') as f:
        return f.read()

def load_public_orchestrator_list() -> list[dict]:
    """
    Loads the list of orchestrators from the public orchestrators config
    """
  
    orchestrators = [
        { 
            'name': 'completion', 
            'description': 'A simple orchestrator that responds to any given prompt',
            'pattern': 'completion'
        },
        {
            'name': 'assistant', 
            'description': 'A simple orchestrator that passes the prompt to an assistant (that you specify) that has been previously defined in the OpenAI API',
            'pattern': 'assistant',
            'requirements': [
                'param: assistant (name or ID of assistant)'
            ]
        },
        {
            'name': 'multi-agent', 
            'description': 'Passes the prompt to multiple agents, then interprets the reponses and returns a single succinct response',
            'pattern': 'multi-agent',
            'requirements': [
                'param: agents (comma separated list of agent names/types)'
            ]
        },
        {
            'name': 'sequential-agent', 
            'description': 'Sequntially passes the prompt to a group of agents, providing both the user prompt + previous responses to subsequent agents. The last agent is the final responder.',
            'pattern': 'sequantial-agent',
            'requirements': [
                'param: agents (comma separated list of agent names/types)'
            ]
        },
        {
            'name': 'single-agent', 
            'description': 'Passes the prompt to an agent, and returns the response from the agent (you must specify the agent)',
            'pattern': 'single-agent', 
            'requirements': [
                'param: agent (name/type of Agent)'
            ]
        },
        {
            'name': 'step-plan', 
            'description': 'Prepares a plan for how to response to the prompt, then executes the plan and returns a succinct response after completing the plan',
            'pattern': 'step-plan'
        },
        {
            'name': 'agent-select', 
            'description': 'Selects which agent from a list of agents (must be known upfront) to pass the prompt to, then returns the response',
            'pattern': 'agent-select'
        },
        {
            'name': 'image', 
            'description': 'Analyses a given image (must be attached) and returns a response',
            'pattern': 'image',
            'requirements': [
                'file: attached (an image file)'
            ]
        },
        {
            'name': 'embedding', 
            'description': 'Provides the embedding of the prompt',
            'pattern': 'embedding'
        }
    ]

    ## Load the Public Orchestrators...
    orchestrators.extend(load_configs(True))
    
    orchestrators.sort(key=lambda x: x['name'])
    return orchestrators

def load_configs(only_public:bool = True) -> list[dict]:
    """
    Loads the list of configs from the configs collection
    """
    from aiproxy.functions.cosmosdb import get_all_items
    cosmos_config_name = os.environ.get("CONFIGS_COSMOS_CONFIG", "configs")

    ## Load the Default Orchestrators...
    orchestrators = []
    try:
        config_items = get_all_items(source=cosmos_config_name)
        for item in config_items:
            if not only_public or item.get("public", False) == True:
                name = item.get("name") or item.get('id') or None
                if name is not None: 
                    data = { 'name':name }
                    desc = item.get('short-description') or item.get('description')
                    if desc is not None: 
                        data['description'] = desc
                    pattern = item.get('pattern')
                    if pattern is not None:
                        data['pattern'] = pattern
                    requirements = item.get('requirements')
                    if requirements is not None:
                        data['requirements'] = requirements
                    
                    orchestrators.append(data)
    except Exception as e:
        print(f"Error loading public orchestrators: {e}")
    
    orchestrators.sort(key=lambda x: x['name'])
    return orchestrators

def update_config(config:dict, by_user:str = None):
    """
    Updates the config in the CosmosDB
    """
    from aiproxy.functions.cosmosdb import upsert_item
    from .date import now_millis
    import os
    
    if os.environ.get("BACKUP_CONFIGS_BEFORE_UPDATE", "true").lower() == "true":
        backup_config_name = os.environ.get("CONFIGS_BACKUP_COSMOS_CONFIG", "config-backups")
        bk_config = config.copy()
        bk_config["archived_ts"] = now_millis()
        bk_config["_id"] = config.get('id', "?")
        if by_user is not None:
            bk_config["archived_by"] = by_user
        bk_config["id"] = f"{config.get('id', '?')}_{bk_config['archived_ts']}"
        upsert_item(bk_config, source=backup_config_name)

    cosmos_config_name = os.environ.get("CONFIGS_COSMOS_CONFIG", "configs")
    upsert_item(config, source=cosmos_config_name)

def get_config_record(config_name:str):
    """
    Gets the config record from the CosmosDB
    """
    from aiproxy.functions.cosmosdb import get_item
    cosmos_config_name = os.environ.get("CONFIGS_COSMOS_CONFIG", "configs")
    item = get_item(config_name, source=cosmos_config_name)
    # Remove all keys that start with an underscore
    if item is not None:
        for key in list(item.keys()):
            if key.startswith("_"):
                del item[key]
    return item


def start_cache_refresh_thread():
    """
    Starts a thread that refreshes the cache every 10 minutes
    """
    import threading
    import time

    def refresh_cache():
        global CACHED_CONFIGS

        refresh_interval = float(os.environ.get("CONFIGS_REFRESH_INTERVAL_SECS", 60))
        while True:
            time.sleep(refresh_interval)
            try: 
                for k in CACHED_CONFIGS.keys():
                    updated_val = load_named_config(k, False, False)
                    if updated_val is not None:
                        CACHED_CONFIGS[k] = updated_val
            except Exception as e:
                print(f"Error refreshing cache: {e}")

    t = threading.Thread(target=refresh_cache, daemon=True)
    t.start()
    return t