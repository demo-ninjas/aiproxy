\
ROOT_CONFIG_NAME = "ROOT"

class CosmosDBConfig:
    host:str = None
    key:str = None
    database_id:str = None
    container_id:str = None
    connection_string:str = None

    def load_config(config_name:str) -> 'CosmosDBConfig': 
        from aiproxy.utils.config import load_named_config
        
        if config_name is None or config_name.upper() == ROOT_CONFIG_NAME:
            return CosmosDBConfig.__load_root_config()
        
        config_item = load_named_config(config_name)
        if config_item is None:
            raise ValueError(f"The Configuration with name '{config_name}' was not found")
        
        config = CosmosDBConfig()
        config.host = config_item.get("host", None)
        if config.host is not None and config.host.upper() == "DEFAULT":
            config.host = CosmosDBConfig.__root_host_name()

        config.key = config_item.get("key") or config_item.get("masterKey", None)
        if config.key is not None and config.key.upper() == "DEFAULT":
            config.key = CosmosDBConfig.__root_key()

        config.database_id = config_item.get("database") or config_item.get("databaseId", None)
        if config.database_id is not None and config.database_id.upper() == "DEFAULT":
            config.database_id = CosmosDBConfig.__root_db_name()

        config.container_id = config_item.get("container") or config_item.get("containerId", None)
        if config.container_id is not None and config.container_id.upper() == "DEFAULT":
            config.container_id = CosmosDBConfig.__root_container_name()

        config.connection_string = config_item.get("connection", None) or config_item.get("connectionString", None)
        if config.connection_string is not None and config.connection_string.upper() == "DEFAULT":
            config.connection_string = CosmosDBConfig.__root_connection_string()

        config.__validate()
        return config
    
    def __validate(self):
        if self.database_id is None:
            raise ValueError(f"CosmosDB config is missing required field 'database'")
        if self.container_id is None:
            raise ValueError(f"CosmosDB config is missing required field 'container'")
        if self.host is None and self.connection_string is None:
            raise ValueError(f"CosmosDB config is missing a required field either 'host' or 'connectionString'")
        if self.host is not None and self.key is None and self.connection_string is None:
            raise ValueError(f"CosmosDB config is missing a required field 'key'")
        

    def __load_root_config() -> 'CosmosDBConfig':
        config = CosmosDBConfig()
        config.host = CosmosDBConfig.__root_host_name()
        config.key = CosmosDBConfig.__root_key()
        config.database_id = CosmosDBConfig.__root_db_name()
        config.container_id = CosmosDBConfig.__root_container_name()
        config.connection_string = CosmosDBConfig.__root_connection_string()
        config.__validate()
        return config
    
    def __root_host_name() -> str: 
        import os
        return os.environ.get('COSMOS_ACCOUNT_HOST', None) or os.environ.get('COSMOS_HOST', None)
    
    def __root_key() -> str: 
        import os
        return os.environ.get('COSMOS_KEY', None) or os.environ.get('COSMOS_MASTER_KEY', None)

    def __root_db_name() -> str: 
        import os
        return os.environ.get('COSMOS_DATABASE_ID', None) or os.environ.get('COSMOS_DATABASE', None)
    
    def __root_container_name() -> str: 
        import os
        return os.environ.get('COSMOS_CONTAINER_ID', None) or os.environ.get('COSMOS_CONTAINER', None)
    
    def __root_connection_string() -> str: 
        import os
        return os.environ.get('COSMOS_CONNECTION_STRING', None) or os.environ.get('COSMOS_CONNECTION', None)
    
