
<h1 align="center">
  :robot: Azure OpenAI Chat Proxy Library :toolbox:
</h1>

> [!IMPORTANT]
> This project has been built for use in $\color{BrickRed}{demos}$ and $\color{BrickRed}{prototypes}$ - use this code with discretion - it is not designed with production usage in mind.

## Azure OpenAI Chat Proxy Library
This is a simple Python library that makes it super easy to work with Azure OpenAI.

In essence, it's really just a wrapper around the OpenAI python library, with a few extra bells + whistles attached to make it easy to add function calling, streaming + bare-bones orchestration to your AI applications.


Some high-level Features: 

* **CompletionsProxy** - A proxy to the Chat Completions API
* **AssistantsProxy** - A proxy to the Assistants API
* **EmbeddingsProxy** - A proxy to enable using an Embeddings Model
* **Function Calling** - Support for function calling 
* **History** - A few simple implementations for storing + recalling chat history
* **Streaming Results** - A few simple implementations for streaming results
* **Basic Orchestration** - A few simple orchestration patterns, such as choosing an agent to respond from a group of agents, multi-agent chat, and a step-plan approach


## Table of Contents

* [Installation](#installation)
* [Usage](#usage)
* [Function Calling](#function-calling)
* [Configuration](#configuration)
* [Available AI Proxies](#available-proxies)
* [Available Orchestrators](#available-orchestrators)
* [Available Agents](#agents)


## Installation

To use this library in your AI projects, simply add a reference to this repo in your `requirements.txt`, like this: `git+https://github.com/demo-ninjas/aiproxy.git`

[Alternatively, you could clone the repo and refer to the local copy of the repo like this: `git+file:///path/to/this/repo`]


## Usage

This library is installed under the module name `aiproxy`.

There are two ways to interact with this library, either by directly using the AI Proxy classes (in the `aiproxy.proxy` module), or via the orchestration classes (in the `aiproxy.orchestration` module).

In both cases, if you want some caching etc..., you can use a global static registry to load the proxy or orchestrator, but you can also just load the classes directly.

You can see implementations of a few examples in the `test/tests` folder, and you can run them by running the `test/test.py` file (and setting appropriate environment variables)

Here's a simple example that uses the `CompletionsProxy`: 

```Python
from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.proxy import CompletionsProxy

## Load the CompletionsProxy (with the 'demo' config, if there is one defined)
proxy = GLOBAL_PROXIES_REGISTRY.load_proxy('demo', CompletionsProxy)
if proxy is None:
    raise Exception("Could not load proxy")

## Send a message to the Completions endpoint, get a response back + print it
resp = proxy.send_message("What is the capital of France?", ChatContext())
print(resp.message)
```


And, here's an example that uses the agent selector orchestrator (which chooses the best agent to respond to the provided prompt): 

```Python
from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.proxy import CompletionsProxy
from aiproxy.orchestration import orchestrator_factory
from aiproxy.data import ChatConfig

## Create a config for the orchestrator that contains a list of agents, along with their descriptions
config = ChatConfig.load('selector')
config['type'] = 'agent-select'
config['agents'] = [
    {
        "name": "Maths Professor",
        "description": "A tenured, highly experienced professor of mathematics",
        "type": "completion", 
        "system-prompt": "You are a highly distinguished and experienced Maths Professor. You are an expert in the field of mathematics and can answer any question related to mathematics.",
    },
    {
        "name": "Computer Science Professor",
        "description": "A tenured, highly experienced professor of computer science who specialises in the field of Softwware Engineering",
        "type": "completion", 
        "system-prompt": "You are a highly distinguished and experienced Computer Science Professor, you are an expert in the field of computer science with a particular focus on software engineering.",
    },
    {
        "name": "History Professor",
        "description": "A tenured, highly experienced professor of history",
        "type": "completion", 
        "system-prompt": "You are a highly distinguished and experienced History Professor. You are an expert in the field of history and can answer any question related to history.",
    }
]

## Creat the Orchestrator
orchestrator = orchestrator_factory(config)
if orchestrator is None:
    raise Exception("Could not load proxy")

context = ChatContext()
q = "Who was Napolean and was he a great leader?"
print(f"Question: {q}")
resp = orchestrator.send_message(q, context)
print(f"Answered by: {resp.metadata.get('responder', '?')}:\nAnswer: {resp.message}\n")

q = "What is the square root of 144?"
print(f"Question: {q}")
resp = orchestrator.send_message(q, context)
print(f"Answered by: {resp.metadata.get('responder', '?')}:\nAnswer: {resp.message}\n")

q = "What is the difference between a linked list and an array?"
print(f"Question: {q}")
resp = orchestrator.send_message(q, context)
print(f"Answered by: {resp.metadata.get('responder', '?')}:\nAnswer: {resp.message}\n")
```

## Function Calling

Giving the AI models an opportunity to invoke local Python functions to aid in fulfilling the user prompt is a very powerful feature.

The completions proxy supports this, and uses a global functions registry to both describe functions to the AI models, and to find and invoke them when required.

This library provides a number of built in functions that can be used and you can also provide your own.

By default, the functions registry has no functions registered (not even the built-in provided ones), so any function you want to use must first be registered with the registry before it can be made available to an AI model.

You can get a reference to the global functions registry like this: `from aiproxy import GLOBAL_FUNCTIONS_REGISTRY`

And register a function like this: 

```Python 
from aiproxy import GLOBAL_FUNCTIONS_REGISTRY

def save_user_note(note:Annotated[str, "The note to save for the user"], category:Annotated[str, "The category of the note, eg. 'Dislikes'"] = None) -> str:
    print(f"Saved a {category or 'general'} note: '{note}'")
    return "Done"

GLOBAL_FUNCTIONS_REGISTRY.register_base_function('save-user-note', "Recod a note for the user that can be retrieved later", save_user_note)
```

You can also register an `alias` of one of a previously registered base function, which can be useful when you want to register a function that uses an existing function but with some function arguments pre-defined, eg.

```Python
from aiproxy import GLOBAL_FUNCTIONS_REGISTRY

## Register the Azure Search base functions (which includes a function called 'search')
from aiproxy.functions import register_azure_search_functions
register_azure_search_functions()

## Register an alias of the 'search' function that has a different description, and a few pre-defined arguments
GLOBAL_FUNCTIONS_REGISTRY.register_function_alias('search', 
        alias='recipe-search', 
        description="The search criteria in Lucene format. So, for example, if you want to exclude something from the search results, then prefix it with a '-' symbol, eg. '-mushroom' to exclude results that contain the word 'mushroom'", 
        arg_defaults={ 
            'source':'recipe-index',
            'complexQuery':True
        } 
    )
```

If you're feeling lazy, you can register all the built-in functions in one go like this: 

```Python
from aiproxy.functions import register_all_base_functions
register_all_base_functions()
```

### Limiting the scope of the functions that the AI can use

When sending a message to a proxy, you can limit the scope of functions that are available by providing a function filter, eg: 

```Python
from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.proxy import CompletionsProxy

## Register all functions
from aiproxy.functions import register_all_base_functions
register_all_base_functions()

## Load the CompletionsProxy (with the 'demo' config, if there is one defined)
proxy = GLOBAL_PROXIES_REGISTRY.load_proxy('demo', CompletionsProxy)
if proxy is None:
    raise Exception("Could not load proxy")


## Filter that limits the scope of functions available to only 3 specific functions
def function_filter(name:str, base_name:str) -> bool: 
    return name in [ 'calculate', 'filter_list', 'random_choice' ]

## Send a message to the Completions endpoint, get a response back + print it
resp = proxy.send_message("What is 564/12 + 8(4/2)? Only respond with the result, do not add any additional commentary", ChatContext(), function_filter=function_filter)
print(resp.message)     # Should print: 63.0 ;p
```


## Configuration

The `ChatConfig` class is used as the basis for all configuration within the library.

When you provide the name of a config to load, it will attempt to load the configuration from a file, the environment or (optionally) from a CosmosDB container.

If the named config is not found, then a default config will be used which is dervied by loading the core settings from the Environment.

To load a config, use the `ChatConfig.load` function, like this: 

```Python
from aiproxy.data import ChatConfig
config = ChatConfig.load('my-config')
```

A config can contain any keys + values, but there are a number of core config values that can be set, which are as follows: (there are some alternative aliases for these which you can find in the `ChatConfig` class file)

* `ai-key` - The Azure OpenAI Access Key
* `ai-endpoint` - The Azure OpenAI Endpoint URL
* `ai-version` - The version of the Azure OpenAI API to use
* `ai-model` - The model deployment to use
* `assistant` - The name of the assistant to use (when using the Azure OpenAI Assistants API)
* `assistant-id` - The ID of the assistant to use (when using the Azure OpenAI Assistants API)
* `system-prompt` - The system prompt to use when interacting with the AI model
* `use-functions` - A boolean flag indicating whether or not to allow the AI model to use function calling 
* `timeout-secs` - The number of seconds after which to timeout calls to the AI model (can be fractions of a second)
* `publish-frequency` - (If using streaming) The minimum amount of time that must pass between updates to the stream (can be fractions of a second)
* `temperature` - The temperature to set on the model 
* `use-data-source-extensions` - A boolean flag indicating whether or not to use the Azure OpenAI Data Source Extensions capability (where the Azure AI service will directly access the data sources, rather than using function calling)
* `max-steps` - The maximum number of times that the AI Model can be called for a single user prompt (aka. limiting the number of back + forths with the AI model when using function calling for example) 
* `max-history` - The maximum number of messages to retain in the history before the history should be summarised 
* `top-p` - The `top-p` to set on the AI Model
* `max-tokens` - Limts the max number of tokens the AI Model can generate
* `function-aliases` - A list (or dictionary) of function aliases to register (see below)
* `prompt-vars` - A dictionary of variables that can be injected into a system (or user) prompt when using a prompt template
* `system-prompt-is-template` - A boolean flag indicating whether or not to treat the system prompt as a template
* `user-prompt-is-template` - A  boolean flag indicating whether or not to treat the user prompt as a template (only set this if you have control over the user prompt and are completely sure of the safety of enabling this)
* `parse-ai-response` - A boolean flag indicating whether or not to treat the response from the AI model as a JSON object that contains both the actual response message and additional metadata
* `persist-parsed-ai-response-metadata` - (if AI responses are being parsed) A boolean flag indicating whether or not the parsed response metadata should by default also be persisted into the conversation history

Each of these settings will also be set to a default value derived from the environment or a sensible value.

NB: Some configs values (eg. `ai-key`) are required for the library to operate and must be specified in either the environment or in a config.

### Core Environment Configs

The following environment variables are used to set the default value for the core configs: (Custom configs override these values, these are considered defaults only) 

* `AZURE_OAI_API_KEY` - Sets the Access Key for the Azure OpenAI API
* `AZURE_OAI_ENDPOINT` - Sets the Endpoint to use for the Azure OpenAI API
* `AZURE_OAI_REGION` - Informs the region within which the API resides (and also used to derive the endpoint if no endpoint is provided)
* `AZURE_OAI_API_VERSION` - The API version to use for the Azure OpenAI API
* `AZURE_OAI_MODEL_DEPLOYMENT` - The name of the model deployment to use
* `OAI_ASSISTANT_NAME` - The name of the Assistant to use (when using the Azure OpenAI Assistants API)
* `OAI_ASSISTANT_ID` - The ID of the Assistant to use (when using the Azure OpenAI Assistants API)
* `OAI_SYSTEM_PROMPT`- The default system prompt to use when interacting with an AI Model
* `AI_USE_FUNCTIONS` - Whether or not to allow function calling
* `AI_TIMEOUT_SECS` - The default timeout in seconds when waiting for a response from an AI Model
* `INTERIM_RESULT_PUBLISH_FREQUENCY_SECS` - (If using streaming) The minimum amount of time that must pass between updates to the stream (can be fractions of a second)
* `AI_TEMPERATURE` - The temperature to set on the model
* `AI_USE_DATA_SOURCE_CONFIG` - An indicator as to whether or not to use the Azure OpenAI Data Source Extensions capability (where the Azure AI service will directly access the data sources, rather than using function calling)
* `AI_DATA_SOURCE_CONFIG` - The default data source config to use when using the Data Source Extensions
* `AZURE_OAI_DATA_SOURCES_API_VERSION` - The API version to use when using the Data Source Extension (if it's different to the `AZURE_OAI_API_VERSION`)
* `AI_MAX_STEPS` - The maximum number of times that the AI Model can be called for a single user prompt (aka. limiting the number of back + forths with the AI model when using function calling for example) 
* `AI_MAX_HISTORY` - The maximum number of messages to retain in the history before the history should be summarised 
* `AI_TOP_P` - The `top-p` to set on the AI Model
* `AI_MAX_TOKENS` - Limts the max number of tokens the AI Model can generate


### Function Aliases via Config

A configuration can register function aliases using the `function-aliases` config key, setting it to a list of alias configurations.

An alias config defines: 

* `alias` - The name of the alias (The name that will be used when presenting the function to an AI Model)
* `function` - The name of the *base function* that this alias points to
* `description` - (optional) Sets the description of this function (enabling the alias to have a different description to the base function)
* `args` - (optional) A dictionary of pre-defined arguments (that won't be presented to the AI)

For example, here is a config that defines an alias function called `recipe-search` that points to the `search` base function, with a new description and some pre-defined arguments: 

```JSON
{
    "id": "recipe-step-planner",
    "type": "step-plan",
    "planner-preamble": "You work for the company 'Contoso Foods', which is a large supermarket chain who specialises in supplying customers with great fresh produce, everyday low prices and a wide selection of products. You are to remain focussed on discussing food, recipes and meal plans with the user, along with keep track of any details they provide about themselves and their families.",
    "function-aliases": [
        {
            "function": "search",
            "alias": "recipe-search",
            "description": "The search criteria in Lucene format. So, for example, if you want to exclude something from the search results, then prefix it with a '-' symbol, eg. '-mushroom' to exclude results that contain the word 'mushroom'",
            "args": {
                "source": "recipe-index",
                "complexQuery": true
            }
        }
    ]
}
```

### Refering to environment variables in Config

Sometimes you do not want to put a secret value into a config file / CosmosDB item, but rather have that value injected into the environment at runtime (eg. Perhaps from a KeyVault).

To facilitate this, you can prefix a value with a `$` symbol - this informs the config loader that the value is the name of an environment variable that the real value should be derived from.

eg. The following is a configuration for the provided `search` base function, it defines some non secret fields like the index name, but derives the query key from the environment: 

```JSON
{
    "id": "recipe-index",
    "endpoint": "$SEARCH_API_ENDPOINT",
    "index": "recipes",
    "query-key": "$SEARCH_API_KEY",
    "embedding-model": "text-embedding-ada-002",
    "semantic-config": "Default",
    "scoring-profile": "Default",
    "vector-fields": [
        {
            "field": "vector",
            "dim": 1536,
            "knn": 500
        }
    ]
}
```

In this case, the `endpoint` and `query-key` will be set to the environment variables `SEARCH_API_ENDPOINT` and `SEARCH_API_KEY`.


### Refering to other configs

Sometimes it makes sense to separate a field value into a separate config. To facilitate this, you can prefix a value with an `@` symbol - this informs the config loader that the value is the name of a config to use as the value for this field.

eg. The following is a configuration for the `search` base function that loads a the vector fields configuration from a separate config: 

```JSON
{
    "id": "recipe-index",
    "endpoint": "$SEARCH_API_ENDPOINT",
    "index": "recipes",
    "query-key": "$SEARCH_API_KEY",
    "embedding-model": "text-embedding-ada-002",
    "semantic-config": "Default",
    "scoring-profile": "Default",
    "vector-fields": "@core-vector-fields"
}
```
In this case, the value of `vector-fields` will be the parsed result of the `core-vector-fields` config.

### Refering to a local text file

Sometimes is makes sense to separate a field value into a separate text file that is stored locally within the local configs directory. To facilitate this, you can prefix a value with a `!` symbol - this informs the config loader that the value is the name of a text file to load from the local configs directory.

eg. The following config loads the system prompt from a text file: 

```JSON
{
    "id": "awesome-config", 
    "type": "completion",
    "system-prompt": "!system-prompt.txt"
}
```
In this case, the value of the `system-prompt` field will be the contents of the `system-prompt.txt` file located within the local configs directory.

### Prompt Templates

When you define system prompts (and optionally for user prompts) you can treat them as a template, and apply substitutions within the prompt at runtime.

To apply a substitution, wrap the substitution within squiggly brackets, eg: `{my-key}`

When system prompts are being treated as templates (true by default), if you want the prompt to contain a squiggly bracket without beingn treated as a substitution, use two squiggly brackets, eg: `{{my data that isn't a substitution}}`

If you do not want your system prompt to be treated as a template at all, you can set the `system-prompt-is-template` config value to `false`.

The substitution is applied based on the following: 

* `{date}` - will convert to today's date (in local time to the server) formatted as: `year-month-day` (aka. `%Y-%m-%d`)
* `{time}` - will convert to the current time (in local time to the server) formatted as `hour:min:sec` (aka. `%H:%M:%S`)
* `{datetime}` - will convert to the current time (in local time to the server) formatted as `year-month-day hour:min:sec` (aka. `%Y-%m-%d %H:%M:%S`)
* `{date-format:formatstring}` - will convert to the date string as defined by the format string (eg. `{dateformat:%Y}` will convert to the current 4-digit year)
* `{utcdate}` - will convert to today's date (in UTC) formatted as: `year-month-day` (aka. `%Y-%m-%d`)
* `{utctime}` - will convert to the current time (in UTC) formatted as `hour:min:sec` (aka. `%H:%M:%S`)
* `{utcdatetime}` - will convert to the current time (in UTC) formatted as `year-month-day hour:min:sec` (aka. `%Y-%m-%d %H:%M:%S`)
* `{iso8601}` - will convert to the current time in ISO8601 format (aka. equivalent of: `%Y-%m-%d %H:%M:%S.%f%z`)
* `{context-metadata-key}` - if matched to a context metadata variable will be replaced with that
* `{config-prompt-var}` - if matched to a config prompt key, then it will be replaced with that (aka. matches a value in the `prompt-vars` dictionary within the config)
* [Not matched] - then the substitution string will be left in the prompt untouched

If you wish to define prompt key values in the config, you can set them in the `prompt-vars` dictionary, eg. 

```JSON
{
    "id": "my-config", 
    "prompt-vars": {
        "my-var": "You are happy to be here",
        "my-other-var": 1234
    }
}
```

Then, if the prompt template looks like this: 

```
You are an AI Assistant, and you are answering questions from users.

{my-var}

The magic number for today is: {my-other-var}
```

Then, the system prompt passed to the AI model will be: 
```
You are an AI Assistant, and you are answering questions from users.

You are happy to be here

The magic number for today is: 1234
```


### CosmosDB as a Config Provider

If you wish to store your configs in a CosmosDB container, you must configure the connect to the CosmosDB instance.

The config loader passes a `source` of `configs` to the `get_item` function (within the CosmosDB base functions). 
The source refers to a `CosmosDBConfig` config of that name, which in this case allows you to configure the configs CosmosDB Connection using a local config file, or using the default environment variables for the CosmosDB Configuration.

The environment variables that set the default CosmosDB configuration values are: 

* `COSMOS_CONNECTION_STRING` - The connection string to the CosmosDB instance 
* `COSMOS_DATABASE_ID` - The database ID to use
* `COSMOS_CONTAINER_ID` - The container within the database to use (For Configs this defaults to `configs`)
* `COSMOS_ACCOUNT_HOST` - If not using a connection string, this sets the URL of the CosmosDB Account Host
* `COSMOS_KEY` - If not using a connection string, this sets the Access Key for the CosmosDB

Configurations within the cosmos container can be any valid JSON, with the only manadatory field being `id` (which is the *name* of the config)

Here's an example of a config that sets a few common config options: 

```JSON
{
    "id": "default",
    "ai-key": "$AZURE_OAI_API_KEY",
    "ai-endpoint": "$AZURE_OAI_ENDPOINT",
    "ai-region": "aueast",
    "ai-version": "$AZURE_OAI_API_VERSION",
    "ai-model": "$AZURE_OAI_MODEL_DEPLOYMENT",
    "ai-prompt": "You are an AI assistant, your job is to answer questions and provide information. You can also help with tasks like scheduling and reminders. You can ask me anything.",
    "timeout": 300,
    "publish-frequency": 0.032,
    "ai-temperature": 0.35,
    "use-data-source-config": false,
    "max-steps": 20,
    "max-history": 30,
    "top-p": 1,
    "max-tokens": 2500,
}
```

### Parsing AI Responses into custom ChatResponses

Sometimes it can be useful for the AI to respond with a JSON object that contains both the response message and additional metadata (which might be handled differently to the response message).

To facilitate this, you can set the `parse-ai-response` config field to `true` - which will trigger the response parsing.

When  theAI response is parsed, if the response message is a valid JSON object, then the response message will be parsed into a dictionary, and then that dictionary will be processed to extract the response message + associated metadata.

The final response message text is extraccted from the `message` or `response` field of the dictionary, with all other fields treated as metadata.

For the metadata fields, you can add directives into the start of the field name to indicate how the metadata should be handled.

By default, the metadata fields will be added as metadata into both the `ChatResponse` and also the `ChatContext` (And therefore also persisted into the conversation history [Unless the `persist-parsed-ai-response-metadata` config value is set to `false`]).

To change this behaviour on a field by field basis, you can add directives to the beginning of the field name (wrapped by `_` characters).

A directive is a `+` or `-` followed by a `target`, of which there are three targets: 

* `R` - The ChatResponse
* `C` - The ChatContext
* `H` - The conversation History

A `+` indicates that the metadata should be sent to that target, and a `-` indicates that it should not.

Eg. The following field name: `_+R-H_my-field` - indicates that the metadata should be added to the `ChatResponse` and the `ChatContext` but not persisted to the Conversation History.

For example, given the following response message from the AI:
```JSON
{
    "response": "Certainly, I have updated your travel plan to include a 3 night stay at the Hotel Grande de Paris, checking in on Monday 3rd and checking out on Thursday 6th.", 
    "hotel-confirmation-number": "ABC123", 
    "trip-reference": "XYZ123", 
    "_-C+R_speech": "Done, you are booked for 3 nights at the Hotel Grande de Paris from Monday"
}
```

Then, the ChatResponse message will be set to: `Certainly, I have updated your travel plan to include a 3 night stay at the Hotel Grande de Paris, checking in on Monday 3rd and checking out on Thursday 6th.`
The ChatResponse metadata will be set to: 
```JSON
{
    "hotel-confirmation-number": "ABC123", 
    "trip-reference": "XYZ123", 
    "speech": "Done, you are booked for 3 nights at the Hotel Grande de Paris from Monday"
}
```
And the ChatContext metadata will be set to: 
```JSON
{
    "hotel-confirmation-number": "ABC123", 
    "trip-reference": "XYZ123"
}
```

[Note: The "speech" is automatically not persisted to the conversation history because it is not added to the ChatContext]


Here's another example, let's say you set your config as follows: 
```JSON
{
    "id": "chat-metadata-test",
    "type": "completion",
    "system-prompt": "You are an AI Assistant who answers questions.\nYou are in a friendly mood, and your response message can often be in the form of a limerick or poem, rather than plain English. \n\nYou work for \"Super Fresh Markets\", you are known as \"Bob the AI\".\nToday's date is '{date}' and the current time is '{time}'.\n\nThe user who you are talking talking to is: \"John Smith\" and his user id is \"js1579\".\n\nYour response is to be a JSON object with the following structure: \n\n{\n    \"response\": \"Your friendly response to the users prompt\", \n    \"bot-name\": \"Your name, or how you are known as\", \n    \"user-id\": \"The ID of the user\", \n    \"msg-time\": \"The current time\"\n}\n\nDo not add any additional commentary, only respond with the JSON object as described above.\n",
    "parse-ai-response": true,
}
```

If you send the following prompt: `What is the Capital of France?`
The ChatResponse (as an API Response) should look something like this: 

```JSON
{
    "message": "The capital of France is Paris, it's true,\nA city of lights and a lovely view.",
    "bot-name": "Bob the AI",
    "user-id": "js1579",
    "msg-time": "09:59:07"
}
```


## Available Proxies

Following are the list of AI Proxies currently implemented: 

* **Completions** - Send prompts directly to the completions API
* **Assistants** - Send prompts directly to the Assistants API
* **Embedding** - Get an embeddings vector for a given string


*Coming Soon:*
* **Image** (DALLE / Gpt-4o)
* **Video** (Gpt-4o)

The easiest way to create a proxy is to use the Global Proxy Registry, passing the name of the config to use + the proxy type:

```Python
from aiproxy import  GLOBAL_PROXIES_REGISTRY
from aiproxy.proxy import CompletionsProxy

## Load a CompletionsProxy (with the 'demo' config, if there is one defined)
proxy = GLOBAL_PROXIES_REGISTRY.load_proxy('demo', CompletionsProxy)
```

Alternatively, you can use the `orchestrator_factory` to load a proxy by passing the proxy type like this: 

```Python
from aiproxy.orchestration import orchestrator_factory
proxy = orchestrator_factory('completions')
```

Or, by passing a config that has a `type` field that matches one of the proxies, eg: 

```Python
from aiproxy.orchestration import orchestrator_factory
proxy = orchestrator_factory({ "name":"my-proxy", "type":"completions" })
```


## Available Orchestrators

Follow are the list of AI Prompt Orchestrators currently implemented: 

* **All of the Proxies** - eg. Completions, Assistants, etc...
* [**Agent Select Orchestator**](#agent-select-orchestrator) - For a given prompt will choose an agent from a list of agents to fulfill the prompt
* [**Multi-Agent Orchestrator**](#multi-agent-orchestrator) - Pass the prompt to multiple agents then interpret their responses into a single succinct response
* [**Step-plan Orchestrator**](#step-plan-orchestrator) - For a given prompt, write a plan for how to fulfill the prompt's goal, then execute each step in the plan and finally respond based on the outcome of the plan
* [**Sequential-Agents Orchestrator**](#sequential-agents-orchestrator) - Sequentially prompt each agent, passing the response from the previous agent to the next. The final agent in the list is the ultimate responder to the original prompt.
* [**Group Chat Consensus Orchestrator**](#group-chat-consensus-orchestrator) - Conducts a coordinated group chat with a group of agents, and once a consensus is agreed by the majority of participating agents, provides the outcome of the chat.


To load an orchestrator, use the `orchestrator_factory`, passing a config (or the name of a config).

The following example will load a config called `agent-select` (if it exists) and use that to load the **Agent Select Orchestrator**: 

```Python
from aiproxy.orchestration import orchestrator_factory
orchestrator = orchestrator_factory('agent-select')
```

You can also pass your own config to the orchestrator factory, like the below which loads a config called `my-orchestrator`, and the **Multi-agent Orchestrator**: 

```Python
from aiproxy.orchestration import orchestrator_factory
orchestrator = orchestrator_factory({ "name":"my-orchestrator", "type":"multi-agent" })
```


### Agent Select Orchestrator

The Agent select orchestrator uses the descriptions of a list of agents to determine for a given prompt which agent is best suited to fulfill the prompt goal. It then passes that prompt to the chosen agent and return the outcome.

#### Configuring the Agent List

To configure the agent list, add an `agents` config entry, which should contain a list of the agents (either their names or configs).

eg. The following config defines an Agent Select Orchestrator with three agents, each of which are Completions Agents with differing descriptions + system prompts: 

```JSON
{
    "name": "my-selector-config", 
    "type": "agent-select",
    "agents": [
        {
            "name": "Maths Professor",
            "description": "A tenured, highly experienced professor of mathematics",
            "type": "completion", 
            "system-prompt": "You are a highly distinguished and experienced Maths Professor. You are an expert in the field of mathematics and can answer any question related to mathematics.",
        },
        {
            "name": "Computer Science Professor",
            "description": "A tenured, highly experienced professor of computer science who specialises in the field of Softwware Engineering",
            "type": "completion", 
            "system-prompt": "You are a highly distinguished and experienced Computer Science Professor, you are an expert in the field of computer science with a particular focus on software engineering.",
        },
        {
            "name": "History Professor",
            "description": "A tenured, highly experienced professor of history",
            "type": "completion", 
            "system-prompt": "You are a highly distinguished and experienced History Professor. You are an expert in the field of history and can answer any question related to history.",
        }
    ],
}
```

The config entry for each agent is passed to the `agent_factory` to load the agent, see the Configuring Agents section below for more detail on configuring the agents.

#### Configuring the Agent that makes the selection

The agent that makes the selection is the `RouteToAgentAgent` - and you can control the config passed to that agent using the `selector` field.

eg. 

```JSON
{
    "name": "my-selector-config", 
    "type": "agent-select",
    "selector": {
        "model": "gpt-3.5", 
    }, 
    ...
}
```

### Multi-Agent Orchestrator

The multi-agent orchestrator gives a number of agents the opportunity to all participate in responding to a given prompt, after which all the responses will be interpreted and a single succinct response will be returned.

The pattern is as follows: 
* Fan-out the prompt to all agents (in the agent list)
* Collate all responses
* Interpret the responses, and write a single response, using the collated responses as context data for the AI writing the final response


#### Configuring the Agent List

The agent list is configured in the same way as the `Agent Select Orchestrator` (as described above), so add an `agents` config entry, which should contain a list of the agents (either their names or configs).


#### Configuring the Interpreter

The interpreter is a regular Completions proxy with a pre-defined system prompt.

You can customise the configuration for that proxy with the `interpreter` config item (this config entry is used directly when loading the proxy), this could be the name of the proxy config to use, or it could be the proxy configuration itself, eg: 

This sets the completions proxy to use as the `interpreting-proxy` 
```JSON
{
    "interpreter": "interpreting-proxy"
}
```

Whereas, this directly sets the completions proxy config: 
```JSON
{
    "interpreter": {
        "name": "interpreting-proxy", 
        "ai-model": "gpt-4o", 
        "temperature": 0.6, 
        "max-tokens": 2500
    }
}
```


### Step-Plan Orchestrator

The step-plan orchestrator for a given prompt first plans out the steps required to fulfill the prompt, then it executes the plan and finally returns a response based on the outcome of the plan.

The pattern is as follows: 
* Prepare a plan as a series of steps (function calls)
* Execute each step in order, optionally saving the outcome of the step into a context map for later use
* Write a response based on the outcome of the step plan


#### Configuring the Step Planner

Using the config, you can customise a number of aspects of the operations of the planner, its execution and the authoring of the response.

Following are the available configuration options you can use to customise the orchestrator: 

* `planner-preamble` - Allows you to add a preamble to the planner system prompt, enabling you to specify some specific information that might be relevant to the planner for this specific config (this might include informing the AI of the name of the company that it is operating on behalf of for example)
* `responder-preamble` - Allows you to add a preamble to the responder system prompt, enabling you to apply some specific guardrails to the AI that is authoring the final response
* `rules` - Allows you to specify a set of *rules* for the planner - these rules can provide certain restrictions on how the planner should operate, or some examples/notes that might be useful for the planner to know
* `functions` - A list of the names of the function(s) that are available to be used for steps of the plan (where a step is the invocation of one of these functions) [Note not specifying a list of functions will result in the full list of registered functions being made available]
* `exclude-functions` - A list of the names of the functions that you want excluded from the function list (only applies if you don't specify a function list and the global function list is used)
* `planner-model` - The AI model deployment to use for the planner
* `responder-model` - The AI model deployment to use for the responder
* `proxy` - The name/config of the proxy to use for both the planner and the responder
* `include-step-names-in-result` - A boolean flag indicating whether or not to include a list of the step names in the metadata of the responsse 


### Sequential-Agents Orchestrator

The sequential-agent orchestrator calls each agent in sequence, passing the response from the previous agent to the next.

The pattern is as follows: 
* Pass user prompt to first agent
* Pass response from first agent to second agent
* Continue for each agent in list 
* Response from final agent is returned

You can optionally collect up all the responses and carry them, along with the original user-prompt, to each subsequent agent.
To enable this, set the `carry-over-prompt` config to `true`.

If you enable carry over, a default template is used to construct the subsequent prompts, however if you wish to provide a custom one, you can do that using the `carry-over-template` config field (you must have both the '{AGENT_RESPONSES}' and '{USER_PROMPT}' parameters in your custom template).

#### Configuring the Agent List

The agent list is configured in the same way as the `Agent Select Orchestrator` (as described above), so add an `agents` config entry, which should contain a list of the agents (either their names or configs).



### Group Chat Consensus Orchestrator

The group chat orchestrator works with a group of agents to collectively agree to an outcome.

The pattern is as follows: 
* Two chat conversations are established, one with the user and one with the group of agents
* The "co-ordinator" agent is the only agent that participates in both conversations
* The coordinator starts by introducing the prompt to the agents
* Then, the coordinator chooses an agent to speak and poses a prompt to that agent 
* The agent responds (or declines to repond)
* The coordinator then decides on one of three next steps: 
  - Conclude the Conversation (outcome achieved)
  - Pose a prompt/question to another agent (continue the conversation)
  - Pose a question back to the user (pause the conversation)
* This continues ongoingly until a consensus is reached, or a maximum number of turns is reached.

#### Configuring the Agent list

The agent list is configured in the same way as the `Agent Select Orchestrator` (as described above), so add an `agents` config entry, which should contain a list of the agents (either their names or configs).

#### Configuring the Coordination

You can set the maximum number of turns with the `max-turns` config property.

To provide any rules for responding to the user, you can set them with the `summary-rules` config property (eg. `"summary-rules": "You must always respond in English"`)

You can control the config for the coordinator agent by setting the `coordinator` config property (to either an agent config or the name of an agent config).

You can control the config for the responding agent (agent that authors responses to the user) with the `responder` config property (as either an agent config or the name of an agent config).

You can also override the prompt templates used by the coordinator + responder (before you do, make sure to look at the built in templates to ensure you're covering all expectations of the system).

Here's the templates you can override: 

* `intro-template` - Introduces the user + agents to the conversation (must include the `{AGENT_LIST}` and `{USER_PROMPT}` variables)
* `coordinator-template` - Describes to the coordinator it's rules of engagement (must include the `{AGENT_LIST}`, `{USER_PROMPT}`, and `{AGENT_RESPONSES}` variables)
* `carry-over-template` - The prompt used to pass the conversation to the next agent (must include the `{AGENT_NAME}` and `{NUDGE}` variables)
* `question-template` - The prompt used to author the questions back to the user (must include the `{QUESTION}` variable)
* `summary-template` - The prompt used to author the final response back to the user (must include the `{SUMMARY_RULES}`, `{AGENT_LIST}`, `{USER_PROMPT}`, and `{AGENT_RESPONSES}` variables)

Here's an example config for a "Dev Team": 

```JSON
{
    "id": "Dev Team Group Chat",
    "type": "consensus",
    "agents": [
        {
            "id": "Programmer",
            "type": "completion",
            "description": "A highly experienced senior software engineer.",
            "system-message": "You are a highly distinguished and experienced Software Engineer.\n\nYou have been writing software for many years and you are an expert in your craft.\n\nYou have knowledge of most software design patterns, and readily accept feedback and happily rewrite code to improve as needed.\n\nYou are expert in writing software in many software development languages."
        },
        {
            "id": "Computer Science Professor",
            "type": "completion",
            "description": "An tenured, highly experienced professor of computer science, with a deep understanding of all core computer science principles, and a particular strength in understanding how software implementations affect performance from a hardware level.",
            "system-message": "You are a highly distinguished and tenured Computer Science Professor.\n\nYou are an expert in the field of computer science, you understand exactly how software is executed within the computer hardware.\n\nYou are an expert in understanding how particular code patterns can be optimised for things like performance, memory and power consumption."
        },
        {
            "id": "Product Manager",
            "type": "completion",
            "description": "A designer of products, with a particular focus on understanding the correct features needed by end users of applications.",
            "system-message": "You are an experience product manager. You understand the end user very well, and are very experienced in interpreting end user requirements into use cases for software engeineers to work from."
        },
        {
            "id": "Code Reviewer",
            "type": "completion",
            "description": "A very senior software engineer who has a particular focus on ensuring all code written meets safety, performance and quality standards.",
            "system-message": "You are a highly experienced software code reviewer.\n\nYou review code with a focus on ensuring it meets your exceptionally high bar for quality, performance, memory management and safety.\n\nYou are a critical reviewer, but also pragmatic and understand that code doesn't have to be perfect, but that it does need to meet all your quality standards."
        }
    ]
}
```


## Agents

Some of the orchestrators work by sending prompts to "Agents" - where an agent is a piece of code that takes a prompt, performs some action in response to that prompt and then responds.

There are a few built in agents, and you can provide your own as well.

The current list of built in agents is: 

* [**Completions Agent**](#completions-agent) - An agent that passes the prompt directly to a Completions Proxy
* [**Assistants Agent**](#assistants-agent) - An agent that passes the prompt directly to an Assistants Proxy 
* [**Function Agent**](#function-agent) - An agent that invokes the configured function using the prompt as the function args (assumed to be a JSON string of the args)
* [**Orchestrator Proxy Agent**](#orchestrator-proxy-agent) - An agent that passes the prompt to a configured orchestrator
* [**Route to Agent Agent**](#route-to-agent-agent) - An agent that given a list of other agents (or their names), selects for a given prompt the best agent to respond and uses that agent to respond to the prompt
* [**URL Agent**](#url-agent) - An agent that retrieves the contents from a configured URL and returns the response
* [**HTML Parser Agent**](#html-parser-agent) - An agent that parses an HTML document and returns select portions of the document based on a set of configurable rules
* [**HTML Markdown Agent**](#html-markdown-agent) - An agent that converts an HTML document to Markdown
* [**Image Analyser Agent**](#image-analyser-agent) - An agent that uses a GPT model to analyse an image, also when reqiuired, intelligently breaks up images into smaller chunks if the image it large or needs more focussed analysis



To load an agent, use the `agent_factory`, like this: 

```Python
from aiproxy.orchestration.agents import agent_factory
agent = agent_factory('my-agent')
```

If you have created a custom agent, you can register it using the `register_agent` function like this: 

```Python
from aiproxy.orchestration.agents import register_agent
register_agent(agent)
```

And, if you wish to unregister your custom agent, use the `unregister_agent` like this: 

```Python
from aiproxy.orchestration.agents import unregister_agent
unregister_agent(agent)
```

### Custom Agents

Here's a custom agent that passes the prompt to an API and then returns the response: 

```Python 
from requests import post
from aiproxy import ChatContext, ChatResponse
from aiproxy.orchestration import Agent

class MyApiAgent(Agent): 
    _headers:dict[str,str]
    _url:str
    _acess_key:str

    def __init__(self, config:dict = None):
        super().__init__('myapi-agent', 'Calls my API  to invoke the awesome functionality provided by it', config)
        self._url = self.config.get('api-url') or 'https://myapi.net/api/'
        self._acess_key = self.config.get('key')
        self._headers = {
            'content-type': 'application/json',
            'accepts': 'application/json'
        }

    def process_message(self, message:str, context:ChatContext) -> ChatResponse:
        resp = post(self._url, headers=headers, json={ "data":message, "key":self._acess_key })
        return "ok" if resp.status_code >= 200 and resp.status_code < 300 else "failed"
```

You could register this agent like this: 

```Python
from aiproxy.orchestration.agents import register_agent
agent = MyApiAgent(agent_config)
register_agent(agent)
```

Then, this agent will now be available via the `agent_factory` using the name `myapi-agent`, eg: 

```Python
from aiproxy.orchestration.agents import agent_factory
agent = agent_factory('myapi-agent')
```



### Completions Agent

This agent is a simple proxy to the Completions Proxy - it will literally just pass the prompt directly to the completions proxy.

You can configure this agent with the following config properties: 

* `proxy-name` - Set the name of the proxy to load (if there is a specifically configured proxy with that name in the system that you want to use), rather than the default CompletionsProxy
* `system-prompt` - Set the system prompt to use for conversations with this agent
* `model` - Set the name of the model deployment to use 
* `single-shot` - When set to `true`, this agent will always assume it's being used for single-shot conversations (it will ensure it's working in a completely isolated context and not save it's history)
* `thread-isolated` - When set to `true`, this agent will work in an isolated thread, but will be enabled to save it's history


### Assistants Agent

This agent is a simple proxy to the Assistant Proxy - it will post the prompt into the assistant thread, trigger a run and wait for the outcome of the run before responding.

You can configure the agent with the following config settings: 

* `proxy-name` - Set the name of the proxy to load (if there is a specifically configured proxy with that name in the system that you want to use), rather than the default AssistantProxy
* `assistant` - Set the name of the assistant to interact with
* `thread-isolated` - When set to `true`, this agent will work in an isolated thread, but will be enabled to save it's history

If you do not configure the assistant to use in the config, you can set the assistant by setting the `assistant` key in the context metadata.


### Function Agent

This agent will invoke the configured function using the prompt as the function arguments (it assumes the prompt is a JSON string that represents the arguments).

Eg. Assume a function has 2 arguments: criteria (str) and count (int), then the prompt should look like this: 

```JSON
{ "criteria": "my search", "count":  10 }
```

You can configure the agent with the following config settings: 

* `function` - The name of the function to invoke
* `args` - A map of predefined arguments (will override the same arguments if they are supplied in the prompt)
* `result-as-string` - When `true`, the result of the function will be cast to a string [Default: `true`] (Note: Objects will be written as JSON if they support it)

### Orchestrator Proxy Agent

This agent will pass the prompt to an orchestrator - which can be useful when you want an orchestrator to use another orchestrator as one of it's agents.

You can configure the agent with the following config settings: 

* `orchestrator` - The name of the orchestrator to load
* `orchestrator-type` - If you want to use a different name to the type, this allows you to specify the type of orchestrator to use
* `single-shot` - When set to `true`, this agent will always assume it's being used for single-shot conversations (it will ensure it's working in a completely isolated context and not save it's history)
* `thread-isolated` - When set to `true`, this agent will work in an isolated thread, but will be enabled to save it's history

### Route to Agent Agent

This agent will, given a prompt, choose which agent, from a list of agents, should response to the prompt. 
It will then pass the prompt to the selected agent and return it's response.

You can configure this agent with the following config settings: 

* `agents` - The list of agents to choose from (names or configs of agents)
* `selector-prompt` - Allows you to override the default prompt used for selecting agents (you must include the `{AGENT_LIST}` and `{USER_PROMPT}` variables in your prompt)
* `model` - The name of the model deployment to use for the selector
* `proxy-name` - The name of the proxy to use (if you want to use a different proxy to the default completions proxy)

### URL Agent

This agent will respond with the content obtained from the configured URL, optionally posting the prompt as the body content of the HTTP request.

You can configure this agent with the following config settings: 

* `url` - The URL to retrieve (or URL Template)
* `message-as-body` - When `true`, the HTTP request body will be set to the prompt message (Default: `false`)
* `method` - The HTTP method for the request (Default: `GET`)
* `headers` - The headers to add to the request

If the `url` is a template with parameters, then those parameters will be retrieved from the context metadata.

eg. Assume the `url` config is set to: `https://example.com/{customerid}?id={id}`

And assume the context metadata has the following values: 
```JSON 
{
    "customerid": "abc123", 
    "plan": "Gold", 
    "id": 456
}
```

Then, the URL will be set to: `https://example.com/abc123?id=456`


### HTML Parser Agent

This agent expects to recieve an HTML (or XML) document as the prompt. It will parse the document using a `beautifulsoup` parser.

The agent will build a response based on the extraction rules defined in the config.

You can configure this agent with the following config settings: 

* `extraction-rules` - An array of rules for extracting content from the document
* `as-string` - When `true`, the extracted dictionary will be converted to a JSON string [Default: `true`]
* `soup-parser` - Sets the parser to use [Default: `html.parser` (the built-in Python HTML parser)]

Extract rules are defined as follows: 

* `name` - The name of the field that the extracted content will be written to (either in the result or the temp storage)
* `action` - The extract action to apply [Default: `select`]
  * `select` - Perform a CSS selection operation (using the `selector`)
  * `find` - Find the first matching element  (using the `selector`)
  * `find_all` - Find all the matching elements (using the `selector`)
* `selector` - The selector rule passed to the action (eg. `div[name=GridItem]`)
* `args` - A dictionary of any extra arguments that should be passed to the action
* `attrs` - If you wish to extract specific attribtues / elements from the matches, specify them as an array here (see below for details)
* `limit` - Limit the number of elements matched by the action [Default: unlimited]
* `index` - From the list of elements matched by the action, only extract the n'th element defined by this value
* `default` - Specifies a default value to set the output field to if no elements match the action selector
* `store-tmp` - When `true` the output of this rule will not be written to the result, but rather it will be written to a temporary storage that can be retrieved by a later rule
* `var` - Run this rule on a previously stored rule result (where the value of `var` is the name of the rule to retrieve the value for)

The attributes list defines the attributes to set on the output record for each matching element in the document.

Each attribute is defined as follows: 

* `name` - The name of the attribute to set
* `selector` - The selector function to use, one of: 
  * `find` - Find matching child elements
  * `find_all` - Find all mathcing child elements
  * `select` - Find using a CSS Selector
  * `get` - Get the value of an attribute on the element
  * `text` - The text content of the element (and it's children)
* `args` - A dictionary of arguments to pass to the selector

Here's an example config: 

```JSON
{
    "id": "Parse HTML",
    "type": "html-parser",
    "rules": [
    {
        "name": "cards",
        "selector": "div[data-component=item]",
        "limit": 2,
        "attributes": [
        {
            "args": {
                "data-component": "description",
                "name": "div"
            },
            "name": "description",
            "selector": "find"
        },
        {
            "args": {
                "data-component": "heading",
                "name": "h3"
            },
            "name": "title",
            "selector": "find"
        },
        {
            "args": {
                "data-component": "summary",
                "name": "div"
            },
            "name": "summary",
            "selector": "find"
        }
        ]
    }
    ]
}
```

This config will extract the first 2 divs with an attribute of "data-component" equal to "item". 
Then, for each of those div, it will output a record with three fields: 
* "title" - set to the text value of the child H3 element with the attribute "data-component=heading"
* "description" - set to the text value of the child div with the attribute "data-component=description"
* "summary" - set to the text value of the child div with the attribute "data-component=summary"

eg. The output would look something like this: 
```JSON
[
    { "title": "Card 1", "description": "The primary card", "summary": "A card that is about blah blah... " }, 
    { "title": "Card 2", "description": "A second card", "summary": "A card that is about blah blah... " }
]
```

### HTML Markdown Agent

This agent expects to recieve an HTML document as the prompt, and returns the document converted into markdown.

You can configure this agent using the following config settings:

* `exclude-tags` - The HTML tags to exclude from the markdown output (As an array of strings, or a comma separated string)

By default, the `exclude-tags` is set to: `["script", "style", "link", "head", "meta", "title"]`


### Image Analyser Agent

This agent expects to recieve an image as the prompt (either the raw bytes of the image or the base64 of the image).

When the bytes of the image are provided, the image will be loaded and potentially split up into smaller overlapping images, allowing the GPT model to focus on more discrete areas of the image, rather than simply observe the image as a whole.

You can configure this agent using the following config settings: 

* `proxy-name` - The name of the proxy to use if you don't wish to use the default completions proxy
* `system-prompt` - The system prompt to use for the GPT model
* `analyse-prompt` - The prompt to send to the GPT model with the image  (Default: `process this image`)
* `model` - The name of the model deployment to use
* `single-shot` - When set to `true`, this agent will always assume it's being used for single-shot conversations (it will ensure it's working in a completely isolated context and not save it's history)
* `thread-isolated` - When set to `true`, this agent will work in an isolated thread, but will be enabled to save it's history
* `default-image-type` - When the image type cannot be determined, this is the fallback image type to specify the image as

Note: You can specify a context metadata variable `file-extension` to set the image type on a per context basis.

You can also specify a context metadata variable `slice-image` to `false` if you wish to prevent image splicing.
