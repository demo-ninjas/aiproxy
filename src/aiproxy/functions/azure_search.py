import os
from typing import Annotated

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.identity import DefaultAzureCredential

from aiproxy.data.azure_search_config import ROOT_CONFIG_NAME, AzureSearchConfig

INDEX_CONNECTIONS = {}
CACHE_INDEX_CONNECTIONS = os.environ.get('CACHE_INDEX_CONNECTIONS', "true").lower() == "true"

def get_azure_search_client(config_name:str = None) -> tuple[SearchClient, AzureSearchConfig]:
    global INDEX_CONNECTIONS
    global CACHE_INDEX_CONNECTIONS
    
    if config_name is None:
        config_name = ROOT_CONFIG_NAME
    
    if CACHE_INDEX_CONNECTIONS and config_name in INDEX_CONNECTIONS:
        return INDEX_CONNECTIONS[config_name]
    
    ## Load the Config
    config = AzureSearchConfig.load_config(config_name)

    ## Load the Client
    ## Looks like Connection String aren't supported, so we'll just use the key or Managed Identity only 
    credential = AzureKeyCredential(config.key) if config.key is not None else DefaultAzureCredential()
    client = SearchClient(config.endpoint, config.index_name, credential)
    
    ## Cache the Connection if needed
    if CACHE_INDEX_CONNECTIONS:
        INDEX_CONNECTIONS[config_name] = (client, config)
    
    return (client, config)



def encode_query(query:str, embedding_model:str = None)->list[float]:
    from proxy.proxy_registry import GLOBAL_PROXIES_REGISTRY
    from proxy.embedding_proxy import EmbeddingProxy
    encoder = GLOBAL_PROXIES_REGISTRY[EmbeddingProxy]
    if encoder is None: return None
    if type(encoder) is not EmbeddingProxy: return None
    return encoder.get_embeddings(query, embedding_model)
    

def search(
        query:Annotated[str, "The search criteria"], 
        complexQuery:Annotated[bool, "When set to True, this will enable the criteria to be specified using 'Lucene' query format"] = False, 
        vectorSearch:Annotated[bool, "Whether or not to use vector search when searching"] = True, 
        matchAll:Annotated[bool, "Whether or not to require all terms within the search to be matched"] = False,
        numResults:Annotated[int, "The number of relevant results to return"] = 10, 
        facets:Annotated[list[str]|None, "If facets are desired, specifies the list of facets to return with the search results"] = None, 
        useSemanticRanking:Annotated[bool, "Whether or not to sort ther results using semantic ranking"] = True,
        onlyResults:Annotated[bool, "Whether or not to only return the results without the count"] = False,
        skip:Annotated[int, "Skip the first n results and return results from that point"] = None,
        source:Annotated[str|None, "The name of the source configuration to use for the search"] = None
        ) -> list:
    search_client,source_config = get_azure_search_client(source)
    vec_tokens = encode_query(query, source_config.embedding_model) if vectorSearch else None

    if vec_tokens is None: 
        result = search_client.search(search_text=query, include_total_count=True, facets=facets, 
                                      query_type="full" if complexQuery else "semantic" if source_config.semantic_config is not None and useSemanticRanking == True else "simple", 
                                      search_mode="all" if matchAll else "any",
                                      scoring_profile=source_config.scoring_profile, 
                                      skip=skip,
                                      semantic_configuration_name=source_config.semantic_config
                                      )
    else: 
        vec_queries = []
        for vec_config in source_config.vector_fields:
            q_tokens = vec_tokens + [0] * (int(vec_config.dim) - len(vec_tokens))
            vec_queries.append(VectorizedQuery(vector=q_tokens, fields=vec_config.field, k_nearest_neighbors=int(vec_config.knn or "3")))
        
        result = search_client.search(search_text=query, include_total_count=True, vector_queries=vec_queries, facets=facets, 
                                      query_type="full" if complexQuery else "semantic" if source_config.semantic_config is not None and useSemanticRanking == True else "simple", 
                                      search_mode="all" if matchAll else "any",
                                      skip=skip,
                                      scoring_profile=source_config.scoring_profile, 
                                      semantic_configuration_name=source_config.semantic_config
                                      )
    
    out_list = []
    for _ in range(0, min(result.get_count(), numResults)):
        try: 
            doc = result.next()
            out_list.append(doc)
        except StopIteration:
            break

    if facets is not None:
        out = {
            "count": result.get_count(),
            "results": out_list,
            "facets": result.get_facets()
        }
    elif onlyResults:
        out = out_list
    else: 
        out = {
            "count": result.get_count(),
            "results": out_list
        }

    return out

def get_document(id:Annotated[str, "The ID of the document to retrieve"],
                source:Annotated[str|None, "The name of the source configuration to use for the search"] = None) -> dict:
    search_client, _ = get_azure_search_client(source)
    if id is None or len(id) == 0: return None
    if ' ' in id: return None    ## Not a valid ID
    try:
        return search_client.get_document(id)
    except:
        return None

def lookup_document_by_field(fieldName:Annotated[str, "The name of the field to search by"],
                             fieldVal:Annotated[str, "The value of the field to search for, aka. only return documents that have this exact value in the specified field"],
                             source:Annotated[str|None, "The name of the source configuration to use for the search"] = None) -> dict:
    res = search(f"{fieldName}:\"{fieldVal}\"", complexQuery=True, matchAll=True, numResults=1, useSemanticRanking=False, vectorSearch=False, source=source)
    results = res.get("results", [])
    return results[0] if len(results) > 0 else None


def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("search", "Searches the Azure Search index using the specified query. If you set the 'complexQuery' argument to True, then you can use Lucene search syntax within your search query", search)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("get_document", "Retrieves a specific document (by it's ID) from the Azure Search index", get_document)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("lookup_document_by_field", "Retrieves a specific document from the Azure Search index by searching for a specific field value", lookup_document_by_field)
