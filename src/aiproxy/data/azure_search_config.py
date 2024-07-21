from aiproxy.utils.config import load_named_config
ROOT_CONFIG_NAME = "ROOT"

class AzureSearchVectorFieldConfig:
    field:str
    dim:int
    knn:int

    def __init__(self, field:str = None, dim:int = 1024, knn:int = 5) -> None:
        self.field = field
        self.dim = dim
        self.knn = knn

class AzureSearchConfig:
    endpoint:str
    key:str
    index_name:str
    connection_string:str
    embedding_model:str
    semantic_config:str
    scoring_profile:str
    vector_fields:list[AzureSearchVectorFieldConfig]

    def load_config(config_name:str) -> 'AzureSearchConfig': 
        if config_name is None or config_name.upper() == ROOT_CONFIG_NAME:
            return AzureSearchConfig.__load_root_config()
        
        config_item = load_named_config(config_name)
        if config_item is None:
            raise ValueError(f"The Configuration with name '{config_name}' was not found")
        
        config = AzureSearchConfig()
        config.endpoint = config_item.get("endpoint", None) or config_item.get("host", None) or config_item.get("url", None)
        if config.endpoint is not None and config.endpoint.upper() == "DEFAULT":
            config.endpoint = AzureSearchConfig.__root_endpoint()

        config.key = config_item.get("key") or config_item.get("search-key", None) or config_item.get("query-key", None) or config_item.get("access-key", None)
        if config.key is not None and config.key.upper() == "DEFAULT":
            config.key = AzureSearchConfig.__root_key()

        config.index_name = config_item.get("index") or config_item.get("index-name", None) or config_item.get("collection", None)
        if config.index_name is not None and config.index_name.upper() == "DEFAULT":
            config.index_name = AzureSearchConfig.__root_index_name()

        config.connection_string = config_item.get("connection", None) or config_item.get("connectionString", None) or config_item.get("connection-string", None)
        if config.connection_string is not None and config.connection_string.upper() == "DEFAULT":
            config.connection_string = AzureSearchConfig.__root_connection_string()

        config.embedding_model = config_item.get("embedding-model") or config_item.get("embedding-model-name", None)
        if config.embedding_model is not None and config.embedding_model.upper() == "DEFAULT":
            config.embedding_model = AzureSearchConfig.__root_embedding_model()

        config.semantic_config = config_item.get("semantic-config") or config_item.get("semantic-config-name", None)
        if config.semantic_config is not None and config.semantic_config.upper() == "DEFAULT":
            config.semantic_config = AzureSearchConfig.__root_semantic_config()

        config.scoring_profile = config_item.get("scoring-profile") or config_item.get("scoring-profile-name", None) or config_item.get("scoring", None)
        if config.scoring_profile is not None and config.scoring_profile.upper() == "DEFAULT":
            config.scoring_profile = AzureSearchConfig.__root_scoring_profile()

        vf = config_item.get("vectors") or config_item.get("vector-fields", None) or config_item.get("vector-configs", None)
        if vf is not None and type(vf) is str and vf.upper() == "DEFAULT":
            config.vector_fields = AzureSearchConfig.__root_vector_fields()
        elif vf is not None and type(vf) is list:
            config.vector_fields = []
            for v in vf:
                if type(v) is dict:
                    field = v.get("field", None)
                    dim = v.get("dim", 1024)
                    knn = v.get("knn", 5)
                    if field is not None:
                        config.vector_fields.append(AzureSearchVectorFieldConfig(field, dim, knn))

        config.__validate()
        return config
    
    def __validate(self):
        if self.index_name is None:
            raise ValueError(f"Search config is missing required field 'index'")
        if self.endpoint is None and self.connection_string is None:
            raise ValueError(f"Search config is missing a required field either 'endpoint' or 'connection-string'")
        if self.endpoint is not None and self.key is None and self.connection_string is None:
            raise ValueError(f"Search config is missing a required field 'key' (when not using a connection string)")
        
        ## Currently, connection strings aren't supported by Azure AI Search, so we'll need to use the key or Managed Identity only - let's throw an error if we have a connection string
        if self.connection_string is not None:
            raise ValueError(f"Connection Strings are not supported by Azure AI Search, please use a key or Managed Identity")
        

    def __load_root_config() -> 'AzureSearchConfig':
        config = AzureSearchConfig()
        config.endpoint = AzureSearchConfig.__root_endpoint()
        config.key = AzureSearchConfig.__root_key()
        config.index_name = AzureSearchConfig.__root_index_name()
        config.embedding_model = AzureSearchConfig.__root_embedding_model()
        config.connection_string = AzureSearchConfig.__root_connection_string()
        config.semantic_config = AzureSearchConfig.__root_semantic_config()
        config.scoring_profile = AzureSearchConfig.__root_scoring_profile()
        config.vector_fields = AzureSearchConfig.__root_vector_fields()
        config.__validate()
        return config
    
    def __root_endpoint() -> str: 
        import os
        return os.environ.get('SEARCH_ENDPOINT', None) or os.environ.get('SEARCH_HOST', None)
    
    def __root_key() -> str: 
        import os
        return os.environ.get('SEARCH_KEY', None) or os.environ.get('SEARCH_QUERY_KEY', None)

    def __root_index_name() -> str: 
        import os
        return os.environ.get('SEARCH_INDEX', None) or os.environ.get('SEARCH_INDEX_NAME', None) or os.environ.get('SEARCH_COLLECTION', None)
    
    def __root_embedding_model() -> str: 
        import os
        return os.environ.get('SEARCH_EMBEDDING_MODEL', None) or os.environ.get('SEARCH_EMBEDDING_CONFIG', None)
    
    def __root_connection_string() -> str: 
        import os
        return os.environ.get('SEARCH_CONNECTION_STRING', None) or os.environ.get('SEARCH_CONNECTION', None)
    
    def __root_semantic_config() -> str:
        import os
        return os.environ.get('SEARCH_SEMANTIC_CONFIG', None) or os.environ.get('SEARCH_SEMANTIC_CONFIG_NAME', None)
    
    def __root_scoring_profile() -> str:
        import os
        return os.environ.get('SEARCH_SCORING_PROFILE', None) or os.environ.get('SEARCH_SCORING_PROFILE_NAME', None)
    
    def __root_vector_fields() -> list[AzureSearchVectorFieldConfig]:
        return None
    
