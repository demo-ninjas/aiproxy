import os
from typing import Annotated
import azure.cosmos.cosmos_client as cosmos_client
from azure.cosmos import ContainerProxy
from azure.cosmos.errors import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from aiproxy.data.cosmosdb_config import ROOT_CONFIG_NAME, CosmosDBConfig

CONTAINER_CONNECTIONS = {}
CACHE_CONTAINER_CONNECTIONS = os.environ.get('CACHE_CONTAINER_CONNECTIONS', "true").lower() == "true"

def connect_to_cosmos_container(config_name:str = None) -> ContainerProxy:
    global CONTAINER_CONNECTIONS
    global CACHE_CONTAINER_CONNECTIONS
    
    if config_name is None:
        config_name = ROOT_CONFIG_NAME
    
    if CACHE_CONTAINER_CONNECTIONS and config_name in CONTAINER_CONNECTIONS:
        return CONTAINER_CONNECTIONS[config_name]
    
    ## Load the Config
    config = CosmosDBConfig.load_config(config_name)

    ## Load the Client
    client = None
    if config.connection_string is not None:
        client = cosmos_client.CosmosClient.from_connection_string(config.connection_string)
    elif config.key is not None:
        client = cosmos_client.CosmosClient(config.host, {'masterKey': config.key})
    else:
        client = cosmos_client.CosmosClient(config.host, DefaultAzureCredential())

    ## Connect to the DB + Container
    db = client.get_database_client(config.database_id)
    connection = db.get_container_client(config.container_id)

    ## Cache the Connection if needed
    if CACHE_CONTAINER_CONNECTIONS:
        CONTAINER_CONNECTIONS[config_name] = connection

    return connection

def get_item(
        id:Annotated[str, "The ID of the item to retrieve"], 
        partitionKey:Annotated[str, "The partition key of the item (leave blank if the ID field is also the partition key)"] = None,
        source:Annotated[str, "The name of the configuration to use for connecting to the Cosmos DB. When not specified, the root config will be used"] = None
        ):
    client = connect_to_cosmos_container(source)
    try:
        pk = partitionKey if partitionKey is not None else id
        return client.read_item(item=id, partition_key=pk)
    except CosmosResourceNotFoundError: 
        return None

def get_item_list(
        id_list:Annotated[list[str], "The list of IDs of the items to retrieve"],
        partitionKey:Annotated[str, "If all the items in the ID list share the same partition key, then set this to that partition key value, otherwise leave it blank to enable a cross-partition query"] = None,
        source:Annotated[str, "The name of the configuration to use for connecting to the Cosmos DB. When not specified, the root config will be used"] = None
        ):
    client = connect_to_cosmos_container(source)
    try:
        if partitionKey is None: 
            return list(client.query_items(
                query="SELECT * FROM c WHERE ARRAY_CONTAINS(@items, c.id)",
                enable_cross_partition_query=True, 
                parameters=[ { "name":"@items", "value": id_list }, ]
            ))
        else: 
            return list(client.query_items(
                query=f"SELECT * FROM c WHERE c.partitionKey=@partition_key AND ARRAY_CONTAINS(@items, c.id)",
                parameters=[ { "name":"@partition_key", "value": partitionKey }, { "name":"@items", "value": id_list }, ],
                enable_cross_partition_query=False
            ))
    except CosmosResourceNotFoundError: 
        return None


def get_partition_items(
        partitionKey:Annotated[str, "The partition key of the items to retrieve"], 
        source:Annotated[str, "The name of the configuration to use for connecting to the Cosmos DB. When not specified, the root config will be used"] = None
        ):
    client = connect_to_cosmos_container(source)
    return list(client.query_items(
        query="SELECT * FROM c WHERE c.partitionKey=@partition_key ORDER BY c._ts DESC",
        parameters=[
            { "name":"@partition_key", "value": partitionKey }
        ]
    ))

def upsert_item(
        item:Annotated[dict, "The item to insert or update in the Cosmos DB"], 
        ttl:Annotated[int, "The number of seconds that this item should live for before it is automatically deleted by the database"] = None,
        source:Annotated[str, "The name of the configuration to use for connecting to the Cosmos DB. When not specified, the root config will be used"] = None
        ):
    try:
        client = connect_to_cosmos_container(source)
        if ttl is not None: 
            if type(ttl) is str:
                if ttl.isnumeric():
                    ttl = int(ttl)
                elif source is None:
                    source = ttl
                    ttl = None 

            if ttl is not None: 
                item = { "ttl":ttl, **item }

        client.upsert_item(body=item)
    except Exception as e: 
        print("failed to upsert this item:", item)
        raise e
    
def delete_item(
        id:Annotated[str, "The ID of the item to delete"], 
        partitionKey:Annotated[str, "The partition key of the item to delete"],
        source:Annotated[str, "The name of the configuration to use for connecting to the Cosmos DB. When not specified, the root config will be used"] = None
        ):
    client = connect_to_cosmos_container(source)
    client.delete_item(item=id, partition_key=partitionKey)


def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("get_item", "Retrieve a specific item from a Cosmos DB container", get_item)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("get_item_list", "Retrieve a list of specific items from a Cosmos DB container", get_item_list)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("get_partition_items", "Get all the items within the specified partition from a Cosmos DB container", get_partition_items)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("upsert_item", "Update or insert an item into a Cosmos DB container", upsert_item)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("delete_item", "Delete an item from a Cosmos DB Container", delete_item)
