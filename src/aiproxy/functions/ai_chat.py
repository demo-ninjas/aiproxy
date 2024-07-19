from typing import Annotated

from aiproxy.data.chat_context import ChatContext
from aiproxy.proxy.proxy_registry import GLOBAL_PROXIES_REGISTRY

def ai_chat(
        prompt:Annotated[str, "The prompt to send to the AI model to generate a response from"],
        systemPrompt:Annotated[str, "The system prompt that describes to the AI model the behaviour it should exhibit. Leave blank to not use a system prompt"] = None,
        use_functions:Annotated[bool, "If true, the AI will be allowed to make use of the full suite of functions that are available (and allowed by the context) when processing the prompt."] = False,
        use_model:Annotated[str, "Allows you to specify the specific model deployment to use for this interaction. Do not set this without knowing that the model deployment exists"] = None,
        isolated:Annotated[bool, "If true, this prompt will not be concatenated with previous prompts to form a conversation history. This is useful for generating single shot responses, ignorining past history."] = True,
        proxy_name:Annotated[str, "If specified, will use the CompletionsProxy registered with that name to interact with the AI Model, otherwise the default will be used"] = None,
        context:ChatContext = None,
    ) -> str:
    """
    Add a completion to the chat response
    """
    from proxy.completions_proxy import CompletionsProxy
    ctx_to_use = context
    if isolated: 
        ctx_to_use = context.clone_for_single_shot()
    
    comp_proxy = GLOBAL_PROXIES_REGISTRY.load_proxy(proxy_name, CompletionsProxy)
    if comp_proxy is None:
        return "#ERROR No completions proxy found to process the request"
    
    result = comp_proxy.send_message(prompt, ctx_to_use, override_system_prompt=systemPrompt, use_functions=use_functions, override_model=use_model)
    if result.filtered:
        return f"#FILTERED Sorry, I can't respond to that."
    elif result.failed:
        return f"#ERROR Sorry, I couldn't generate a response due to an error"
    return result.message

def ai_assistants_chat(
        prompt:Annotated[str, "The prompt to send to the AI assistants model to generate a response from"], 
        assistant:Annotated[str, "The name or ID of the assistant to use for generating the response."],
        isolated:Annotated[bool, "If true, this prompt will not be concatenated with previous prompts to form a conversation history. This is useful for generating responses to single prompts."] = True,
        proxy_name:Annotated[str, "If specified, will use the CompletionsProxy registered with that name to interact with the AI Model, otherwise the default will be used"] = None,
        context:ChatContext = None
    ) -> str:
    """
    Add a completion to the chat response
    """
    from proxy.assistant_proxy import AssistantProxy

    ctx_to_use = context
    if isolated: 
        ctx_to_use = context.clone_for_single_shot()
    
    ass_proxy = GLOBAL_PROXIES_REGISTRY[proxy_name or AssistantProxy]
    if ass_proxy is None: 
        return "#ERROR No Assistant Proxy found to process the request"

    if type(ass_proxy) is AssistantProxy: 
        ## Send the prompt to the assistant
        results = ass_proxy.send_message_and_return_outcome(prompt, ctx_to_use, assistant_name_or_id=assistant)
        output_message = ""
        for result in results:
            if len(output_message) > 0: 
                output_message += "\n\n"
            output_message += result.message
            if result.citations is not None and len(result.citations) > 0: 
                output_message += '\n[Citations: '
                first = True
                for citation in result.citations:
                    if first: first = False
                    else: output_message += ', '
                    output_message += citation.title
                output_message += ']'
    else: 
        raise AssertionError("Expected proxy to be an Assistant Proxy, but it was not")
    return output_message

def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function('ai_chat', 'Send a prompt to an AI model and return the response', ai_chat)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function('ai_assistants_chat', 'Send a prompt to an AI Assistant and return the response', ai_assistants_chat)