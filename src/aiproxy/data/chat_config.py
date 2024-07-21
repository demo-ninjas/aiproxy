import os

class ChatConfig:
    name:str

    oai_key:str = None
    oai_endpoint:str = None
    oai_region:str = None
    oai_version:str = None
    oai_model:str = None

    system_prompt:str = None
    temperature:float = None
    top_p:float = None
    max_tokens:int = None
    
    assistant_name:str = None
    assistant_id:str = None
    use_functions:bool = True

    timeout_secs:int = None
    interim_result_publish_frequency_secs:float = 0.032

    max_steps:int = None
    max_history:int = None

    use_data_source_config:bool = False
    data_source_config:str = None
    data_source_api_version:str = None

    extra:dict[str, any]

    def __init__(self, name:str):
        import os
        self.name = name
        self.oai_key = os.environ.get('AZURE_OAI_API_KEY', None)
        self.oai_endpoint = os.environ.get('AZURE_OAI_ENDPOINT', None)
        self.oai_region = os.environ.get('AZURE_OAI_REGION', None)
        self.oai_version = os.environ.get('AZURE_OAI_API_VERSION', None)
        self.oai_model = os.environ.get('AZURE_OAI_MODEL_DEPLOYMENT', None)
        self.assistant_name = os.environ.get('OAI_ASSISTANT_NAME', None)
        self.assistant_id = os.environ.get('OAI_ASSISTANT_ID', None)
        self.system_prompt = os.environ.get('OAI_SYSTEM_PROMPT', None)
        self.use_functions = os.environ.get('AI_USE_FUNCTIONS', 'true').lower() in ['true', '1', 'y', 't', 'on', 'yes', 'enabled']
        self.timeout_secs = int(os.environ.get('AI_TIMEOUT_SECS', 300))
        self.interim_result_publish_frequency_secs = float(os.environ.get('INTERIM_RESULT_PUBLISH_FREQUENCY_SECS', 0.064))
        self.temperature = float(os.environ.get('AI_TEMPERATURE', 0.35))
        self.use_data_source_config = os.environ.get('AI_USE_DATA_SOURCE_CONFIG', 'false').lower() in ['true', '1', 'y', 't', 'on', 'yes', 'enabled']
        self.data_source_config = os.environ.get('AI_DATA_SOURCE_CONFIG', None)
        self.data_source_api_version = os.environ.get('AZURE_OAI_DATA_SOURCES_API_VERSION', None)
        self.max_steps = int(os.environ.get('AI_MAX_STEPS', 12))
        self.max_history = int(os.environ.get('AI_MAX_HISTORY', 25))
        self.top_p = float(os.environ.get('AI_TOP_P', 1.0))
        self.max_tokens = int(os.environ.get('AI_MAX_TOKENS', 2500))
        self.extra = {}

    def clone(self) -> 'ChatConfig':
        config = ChatConfig(self.name)
        for k,v in self.__dict__.items():
            if k != "extra":
                config[k] = v
        config.extra = self.extra.copy()
        return config

    def __getitem__(self, key:str) -> any:
        if key in self.__dict__: 
            return self.__dict__.get(key)
        elif key in self.extra: 
            return self.extra.get(key)
        else: 
            try: 
                attr = self.__getattribute__(key)
                return attr
            except: 
                pass
        return None

    def __contains__(self, name:str):
        return name in self.__dict__ or name in self.extra

    def __setitem__(self, key:str, value:any):
        self.__dict__[key] = value    

    def get(self, key:str, default_val:any = None) -> any:
        if key in self: 
            return self[key]
        return default_val

    def load(name:str|dict, raise_if_not_found:bool = False) -> 'ChatConfig':
        from aiproxy.utils.config import load_named_config
        config_item = name if type(name) is dict else load_named_config(name, raise_if_not_found)

        config = ChatConfig(config_item.get("name", name) if config_item is not None else name)
        
        if config_item is None:
            return config
        
        ## Map the config keys to the attribute names
        config_keys = {
            "oai_key": (str, ["oai-key", "ai-key"]),
            "oai_endpoint": (str, ["oai-endpoint", "ai-endpoint"]),
            "oai_region": (str, ["oai-region", "ai-region"]),
            "oai_version": (str, ["oai-version", "ai-version"]),
            "oai_model": (str, ["oai-model", "ai-model"]),
            "assistant_name": (str, ["oai-assistant", "assistant-name", "assistant"]),
            "assistant_id": (str, ["oai-assistant-id", "assistant-id", "assistantid"]),
            "system_prompt": (str, ["system-prompt", "ai-prompt"]),
            "use_functions": (bool, ["use-functions", "ai-use-functions"]),
            "timeout_secs": (int, ["timeout", "timeout-secs", "ai-timeout"]),
            "interim_result_publish_frequency_secs": (float, [ "publish-frequency", "interim-result-publish-frequency", "interim-result-publish-frequency-secs"]),
            "temperature": (float, ["temperature", "ai-temperature"]),
            "use_data_source_config": (bool, ["use-data-source-config", "use-data-source-extensions"]),
            "data_source_config": (str, ["data-source-config", "ai-source-config"]),
            "data_source_api_version": (str, ["data-source-oai-version", "ai-source-config-api-version"]),
            "max_steps": (int, ["max-steps", "ai-max-steps"]),
            "max_history": (int, ["max-history", "ai-max-history"]),
            "top_p": (float, ["top-p", "top_p"]),
            "max_tokens": (int, ["max-tokens", "max-tokens-generated"]),
        }

        ## Load the config from the configured keys
        collected_keys = []
        for config_attr, (attr_type, keys) in config_keys.items():
            for key in keys:
                val = config_item.get(key)
                if val is not None:
                    collected_keys.append(key) ## Keep a record of the keys that we've collected from the config

                    ## If the value is a reference to an environment variable, then replace it with the value of that env variable
                    if type(val) is str and val.startswith("$"):
                        val = os.getenv(val[2:], None)

                    ## Convert the value to the correct type
                    if attr_type == int:
                        val = int(val)
                    elif attr_type == float:
                        val = float(val)
                    elif attr_type == bool:
                        if type(val) == str:
                            vl = val.lower()
                            val = vl == "true" or vl == "1" or vl == "y" or vl == "t" or vl == "on" or vl == "yes" or vl == "enabled"
                        else: 
                            val = bool(val)
                    elif attr_type != dict: 
                        val = str(val)

                    ## Set the value
                    setattr(config, config_attr, val)
                    break
        
        ## Register Function Aliases
        if "function-aliases" in config_item:
            from aiproxy.functions import GLOBAL_FUNCTIONS_REGISTRY
            alias_configs = config_item["function-aliases"]
            if type(alias_configs) is list: 
                for alias_config in alias_configs:
                    func_name = alias_config.get("function", None)
                    alias_name = alias_config.get("alias",None)
                    if func_name is None or alias_name is None: 
                        raise ValueError("Function name and alias name are required for function alias registrations")
                    alias_desc = alias_config.get("description", None)
                    alias_args = alias_config.get("args", None)
                    GLOBAL_FUNCTIONS_REGISTRY.register_function_alias(func_name, alias_name, alias_desc, alias_args)
            else: 
                for alias_name, a_conf in alias_configs.items():
                    func_name = a_conf.get("function", None)
                    alias_name = alias_config.get("alias",alias_name)
                    if func_name is None or alias_name is None: 
                        raise ValueError("Function name and alias name are required for function alias registrations")
                    alias_desc = alias_config.get("description", None)
                    alias_args = alias_config.get("args", None)
                    GLOBAL_FUNCTIONS_REGISTRY.register_function_alias(func_name, alias_name, alias_desc, alias_args)

        ## Load any other fields that weren't collected so far
        for k, v in config_item.items():
            if k not in collected_keys: 
                setattr(config, k, v)
        
        return config
