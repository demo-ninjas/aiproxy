import logging
import json
from typing import Callable, Annotated

from ..proxy import AbstractProxy
from aiproxy.data import ChatConfig, ChatContext, ChatResponse
from aiproxy.functions import GLOBAL_FUNCTIONS_REGISTRY, FunctionDef
from aiproxy.proxy import GLOBAL_PROXIES_REGISTRY, CompletionsProxy
from aiproxy.utils.func import invoke_registered_function

STEP_PLAN_PROMPT_TEMPLATE = """Your role is to build a step by step plan to fulfill the goal of the user prompt.

{preamble}

A plan is a series of JSON steps, where each step describes a function call with arguments, where the plan has the explicit goal of fulfilling the intent of the user prompt by calling functions provided by the system.

The system provides a set of functions that can be used to fulfill the user prompt. 
These functions are listed in the [AVAILABLE FUNCTIONS] section below.

Always interact with functions in English, even if the prompt is provided in a different language.

The format for the list of available functions is as follows:

* <Function1 Name> - <Function1 Description>, args:
  ** <Argument1 Name> - [<Argument1 Type>] <Argument1 Description>
  ** <Argument2 Name> - [<Argument2 Type>] <Argument2 Description>
* <Function2 Name> - <Function2 Description>, args:
  ** <Argument1 Name> - [<Argument1 Type>] <Argument1 Description>
  ** <Argument2 Name> - [<Argument2 Type>] <Argument2 Description>
(...etc...)

[AVAILABLE FUNCTIONS]

{available_functions}

[END AVAILABLE FUNCTIONS]

To create a plan, follow these steps:
1. From a user prompt, create a [PLAN] to fulfill the prompt goal as a series of function calls (non "chat" functions are quick and can be used many times).
2. The outcome of each step (aka. function) can be saved into a context variable (defined by the "output" field of the step), these variables can be used in argument values for subsequent steps.
3. Before using any function in a plan, check that it is present in the [AVAILABLE FUNCTIONS] list. If it is not, do not use it. Do not invent functions that don't exist. Do not use arguments that are not in the function's argument list.
5. Always output a valid JSON for each [Step] in the plan. Do not return markdown, return a raw and valid JSON.
6. If the user prompt cannot be fulfilled using the [AVAILABLE FUNCTIONS], return the string "UNABLE".

A plan takes the form of a series of steps, where each step is a valid JSON string of the step, with each step separated by a newline, and after the last step a '##END##'.
Eg. Here is what a plan looks like: 

{{ "step": "Step 1: REASON FOR TAKING STEP", "function": "Function_Name", "args": {{ "arg1": "value1", "arg2": "value2", ... }}, "output": "$CONTEXT_VARIABLE_NAME" }}
{{ "step": "Step 2: REASON FOR TAKING STEP", "function": "Function_Name", "args": {{ "arg1": "$CONTEXT_VARIABLE_NAME", "arg2": 123, ... }} }}
{{ "step": "Step 3: REASON FOR TAKING STEP", "function": "Function_Name", "args": {{ "arg1": "prefix-${{CONTEXT_VARIABLE_NAME}}suffix", "arg2": "abc", ... }} }}
{{ "step": "Step 4: REASON FOR TAKING STEP", "function": "generate_final_response", "args": {{ "arg1": "prefix-${{CONTEXT_VARIABLE_NAME}}suffix", "arg2": "abc", ... }} }}
##END##

Note, the '##END##' after the last step in the plan is required, please always add '##END##' on a new line after the last step the plan.

Following describes the structure of a plan step:
* "step" - A string describing the reason for taking the step.
* "function" - The name of the function to call, aka The function that will perform the operation of this step - it must exactly match one of the [AVAILABLE FUNCTIONS] above (do not try and use a function not listed above).
* "args" - A dictionary of arguments to pass to the function. The keys are the parameter names of the function and the values are the values to pass to the function. The values can be strings, numbers, context variables (a string prefixed with a '$') or a combination of string and context variables (where context variabels are wrapped with squiggly brackets - eg. ${{VARIABLE_NAME}}). You can also retrieve an element from a context variable that is a list by using the index of the element in square brackets (eg. $list_name[0]), or an attribute of a context variable using the dot notation (eg. $context_variable_name.attribute_name).
* "output" - The name of the context variable to save the output of the function to. This is optional and only required if the output of the function is needed for a future step in the plan.

Important: The last step in the plan MUST always be the 'generate_final_response' function.

The last step must be a call to a special function (not listed in the function list above) called 'generate_final_response', and it should be called with the following arguments:
* original_prompt - The original prompt from the the user
* data - A list of context variables that would be relevant to An AI that is writing up the final response to the user's prompt
* intent - A string that describes what you believe is the intent of the user's prompt
* hint - A string that helps to describe what the answer to the user's prompt would be ( this will be passed as a hint to the AI generating the final response)

{rules}

Following is the user prompt between the [USER_PROMPT] and [END_USER_PROMPT], a list of notes between the [NOTES] and [END_NOTES], and a list of the recent messages in the conversation between the [RECENT_CONVERSATION] and [END_RECENT_CONVERSATION].

[USER_PROMPT]

{user_prompt}

[END_USER_PROMPT]


The recent conversation messages below are ordered from most recent to oldest, in the following format:

[role]
message
***
[role]
message
***

eg. 
[user]
Thank you.
***
[assistant]
The capital of France is Paris.
***
[user]
What is the capital of France?
***

NB: Take note that the example messages above are listed from newest to oldest as they will be in the actual recent conversation list below.

[RECENT_CONVERSATION]

{recent_conversation}

[END_RECENT_CONVERSATION]

Please provide a plan to fulfill the user prompt, do not add any commentary, do not use markdown or any other formatting, only return the JSON steps as described.
"""

GENERATE_FINAL_RESPONSE_TEMPLATE = """You are responding to a prompt from a user and your role is to write a nice friendly, conversational response to their prompt in markdown format.

You are to always respond in the language of the user prompt, and provide an appropriate level of detail as expected by the user prompt.
If you cannot definitively determine the language of the user's prompt, then reply in English.

{preamble}

The user prompt is provided below below [USER_PROMPT] and [END_USER_PROMPT]

[USER_PROMPT]

{user_prompt}

[END_USER_PROMPT]


The intent of the prompt has been identified as: {intent}


The planning AI has provided a hint for you: {hint}


The steps that were taken to action the user prompt / gather the required data, are provided below between [STEPS] and [END_STEPS]

They are in the form of a JSON array of steps, where each step is a dictionary with the following keys:
* "step" - A string describing the reason for taking the step.
* "function" - The name of the function that was called in this step.
* "args" - A dictionary of arguments that were passed to the function in this step.
* "output" - The name of the context variable that the output of the function was saved to in this step.

[STEPS]

{steps}

[END_STEPS]

For each step above that produced data, the outcome is listed below in the following format: 
Step: <Step Name> [Variable: <Variable Name>]
<Data Produced>

Step: <Step Name> [Variable: <Variable Name>]
<Data Produced>

etc...

[STEP_OUTCOMES]

{step_outcomes}

[END_STEP_OUTCOMES]

For each context variable referenced in the steps, you can obtain the value of the variable by using the function 'get_dict_val' with the variable name as the argument (eg. 'get_dict_val({"key":"variable_name"})').

The planner AI has suggested the following context variables are likely to be of use when generating your response, provided below between [DATA] and [END_DATA]

[DATA]

{data_string}

[END_DATA]


The recent messages in the conversation are provided below, ordered from most recent to oldest, between [RECENT_MESSAGES] and [END_RECENT_MESSAGES]

[RECENT_MESSAGES]

{recent_messages}

[END_RECENT_MESSAGES]

"""

class StepPlanOrchestrator(AbstractProxy):
    def __init__(self, config:ChatConfig):
        super().__init__(config)
        self._preamble = self._config['planner-preamble'] or ''
        self._responder_preamble = self._config['responder-preamble'] or ''
        self._rules = self._config['rules'] or ''
        self._function_list = self._config['functions'] or None
        self._functions = self._build_available_functions()
        self._planner_model = self._config['planner-model'] or self._config['model'] or None
        self._responder_model = self._config['responder-model'] or self._config['model'] or None
        self._proxy = GLOBAL_PROXIES_REGISTRY.load_proxy(self._config['proxy'], CompletionsProxy)
        self._include_step_names_in_result = self._config.get('include-step-names-in-result', True)
        self._final_response_template = self._config.get('final-response-template', GENERATE_FINAL_RESPONSE_TEMPLATE)


    def set_function_list(self, function_list:list[str]):
        self._function_list = function_list
        self._functions = self._build_available_functions()

    def _build_available_functions(self) -> str:
        # * <Function1 Name> - <Function1 Description>, args:
        #     ** <Argument1 Name> - [<Argument1 Type>] <Argument1 Description>
        #     ** <Argument2 Name> - [<Argument2 Type>] <Argument2 Description>

        if self._function_list is None: 
            self._function_list = GLOBAL_FUNCTIONS_REGISTRY.get_all_function_names()
            
        available_functions = ''
        for function in self._function_list:
            function_def = GLOBAL_FUNCTIONS_REGISTRY[function]
            if not function_def:
                logging.warning("Function %s not found in the global functions registry", function)
                continue

            available_functions += f"* {function_def.name} - {function_def.description}, args:\n"
            for arg_name, (arg_type, arg_desc)  in function_def.ai_args.items():
                available_functions += f"  ** {arg_name} - [{arg_type}] {arg_desc}\n"
        return available_functions
    

    def _build_recent_conversation(self, context:ChatContext) -> str:
        recent_conversation = ''
        if not context.history or len(context.history) == 0:
            return 'No recent conversation.'
        
        for message in context.history:
            recent_conversation += f"[{message.role}]\n{message.message}\n***"
        return recent_conversation

    def send_message(self, message: str, context: ChatContext, override_model: str = None, override_system_prompt: str = None, function_filter: Callable[[str, str], bool] = None, use_functions: bool = True, timeout_secs: int = 0, use_completions_data_source_extensions: bool = False) -> ChatResponse:
        planner_ctx = context.clone_for_single_shot()
        recent_conversation = self._build_recent_conversation(context)

        prompt = STEP_PLAN_PROMPT_TEMPLATE.format(
            preamble=self._preamble,
            rules=self._rules,
            available_functions=self._functions,
            user_prompt=message,
            recent_conversation=recent_conversation
        )
        plan_result = self._proxy.send_message(prompt, planner_ctx, self._planner_model, use_functions=False)
        plan_str = plan_result.message
        plan_arr = plan_str.split("\n")
        steps = []
        for step_str in plan_arr:
            if step_str.strip() == "##END##":
                break
            step_str = step_str.strip()
            if step_str.endswith(','):
                step_str = step_str[:-1]
            
            if not step_str.startswith("{") and not step_str.endswith("}"):
                logging.warn("Invalid step in the plan - skipping: {step_str}")
                continue

            step = json.loads(step_str.strip())
            steps.append(step)
        
        if steps[-1].get('function') != 'generate_final_response':
            logging.warn("The last step in the plan didn't contain the 'generate_final_response' step - adding a generic version of it")
            steps.append({
                "step": "Generate Final Response",
                "function": "generate_final_response",
                "args": {
                    "original_prompt": message,
                    "intent": "unknown",
                    "data": [ x.get('output') for x in steps if x.get('output') ]
                }
            })

        ## Execute the plan
        context_map = {}
        step_results = []
        for step in steps:
            func_name = step.get('function').strip()
            func_args = step.get('args') or {}
            output_var = step.get('output')
            if output_var is not None and output_var.startswith("$"):
                output_var = output_var[1:]
            
            if not func_name:
                raise ValueError("Function name not provided in the step")

            if func_name == 'generate_final_response':
                result = self.generate_final_response(message, 
                                                      data=args.get('data'),
                                                      intent=args.get('intent'), 
                                                      hint=args.get('hint'),
                                                      vars=context_map,
                                                      steps=steps,
                                                      context=context)
            else: 
                if func_name not in self._function_list and func_name != 'generate_final_response':
                    raise ValueError(f"Function {func_name} not in the list of available functions")

                func_def = GLOBAL_FUNCTIONS_REGISTRY[func_name]
                if not func_def:
                    raise ValueError(f"Function {func_name} not found in the global functions registry")

                ## Replace any context variables in the arguments
                args = {}
                for arg_name, arg_val in func_args.items():
                    if arg_name in func_def.ai_args:
                        self._parse_value_directives(context, context_map, args, arg_name, arg_val)
                

                ## Execute the function
                result = invoke_registered_function(func_name, args, context, cast_result_to_string=False, sys_objects={ 'vars': context_map,'steps':steps })
            
            if output_var:
                context_map[output_var] = result
            step_results.append(result)
        
        ## Setup the result of the plan
        plan_result = ChatResponse()
        plan_result.message = step_results[-1]
        if self._include_step_names_in_result:
            plan_result.metadata = {
                'steps': [ s.get('step') for s in steps]
            }

        ## Add the original message to the context
        context.add_prompt_to_history(message, 'user')
        ## Add the result to the context
        context.add_prompt_to_history(plan_result.message, 'assistant')
        context.save_history()
        return plan_result

    def _parse_value_directives(self, context:ChatContext, variables:dict, args:dict, key:str, value:any):
        """
        Parse the value of a step argument, replacing any directives with the actual values
        """
        if type(value) is str:
            ## If there are directives within the string itself, then they are specified using the ${directive} syntax
            if "${" in value: 
                ## Keep replacing the directives until there are no more directives left in the string
                while "${" in value: 
                    ## replace the part of the string that is the context variable (eg. "Hello${var_name}World", if the value of var_name is "John", then the value will be "HelloJohnWorld")
                    
                    # Step 1: Extract the Directive
                    start = value.index("${")
                    end = value.index("}")
                    directive = value[start+2:end]

                    # Step 2: Determine the variable name from the directive
                    var_name = directive
                    if '[' in var_name:
                        var_name = var_name[:directive.index("[")]
                    if '(' in var_name: 
                        var_name = var_name[:directive.index("(")]
                    if '.' in var_name:
                        var_name = var_name[:directive.index(".")]

                    ## Step 3: Get the value of the variable from the plan's variables
                    var_value = variables.get(var_name)
                    if var_value is None: var_value = ""

                    ## Step 4: If the directive is more than just the variable name, then it's a directive to get a field from the variable, so retrieve the requested path from the variable
                    if var_name != directive: 
                        # The remainder of the directive is the path to the actual field in the variable to retrieve
                        directive = directive[len(var_name):]
                        if directive.startswith('.'):
                            directive = directive[1:]
                        
                        ## Now, use the object functions to get the field from the object as described by the directive
                        import aiproxy.functions.object_functions as obj_funcs
                        var_value = obj_funcs.get_obj_field(var_value, directive)

                    ## As we're working with substrings, we need to convert the value to a string to be able to do the substitution into the string
                    if type(var_value) is list: 
                        var_value = ",".join(var_value)
                    elif type(var_value) is dict: 
                        var_value = json.dumps(var_value)
                    else: 
                        var_value = str(var_value)

                    ## Do the substitution - replacing the full directive with the resolved value
                    value = value[:start] + var_value + value[end+1:]
                args[key] = value

            elif value.startswith("$"):
                ## This is a directive that is the whole value, so we need to extract the variable name and get the value from the plan's variables
                ##  The difference compared with the above directive process is that there is no need to convert the resolved value to a string
                ##    this can be used to extract a variable (or field within a variable) in it's native type 
                directive = value[1:]   ## Skip first character, as it's the directive identifier

                ## Determine the name of the variable to lookup
                var_name = directive
                if '[' in var_name:
                    var_name = var_name[:directive.index("[")]
                if '(' in var_name: 
                    var_name = var_name[:directive.index("(")]
                if '.' in var_name:
                    var_name = var_name[:directive.index(".")]

                ## Get the value of the variable from the plan's variables
                var_value = variables.get(var_name)
                if var_value is None: var_value = ""

                ## If the directive is more than just the variable name, then it's a directive to get a field from the variable, so retrieve the requested path from the variable
                if var_name != directive: 
                    directive = directive[len(var_name):]
                    if directive.startswith('.'):
                        directive = directive[1:]

                    # Now, use the object functions to get the field from the object as described by the directive
                    import functions.object_functions as obj_funcs
                    var_value = obj_funcs.get_obj_field(var_value, directive)
                        
                args[key] = var_value
            else:
                args[key] = value
        else: 
            args[key] = value


    def generate_final_response(
        self,
        original_prompt:Annotated[str, "The prompt that was recieved from the user"],
        data:Annotated[str, "The list of context variables that are useful for writing the response to the user"],
        intent:Annotated[str, "The intent of the prompt from the user"] = None,
        hint:Annotated[str, "A hint for what the answer is, or how it should look"] = None,
        vars:dict = None,
        steps:list[dict] = None,
        context:ChatContext = None
    ) -> str:
        
        # Recent Messages
        recent_conversation = self._build_recent_conversation(context)

        ## Data Varaibles
        data_string = 'No data provided by the planner'
        if data is not None: 
            data_string = 'Specific Data Points listed below:\n'
            if type(data) is str:
                data = data.split(',')
            elif type(data) is dict: 
                data = data.values()
            data_string = "\n* ".join([ item for item in data ])
        
        step_outcomes = ""
        for step in steps: 
            output_var = step.get('output')
            if output_var is not None:
                var_name = output_var
                if var_name.startswith("$"):
                    var_name = var_name[1:]
                var = vars.get(var_name)
                if var is not None:
                    var_str = str(var)
                    if type(var) is dict or type(var) is list:
                        var_str = json.dumps(var, indent=2)
                    if len(var_str) > 1000:
                        var_str = var_str[:1000] + "...truncated [use 'get_dict_val({ \"key\":\"" + output_var + "\")' to retrieve whole value]..."
                    step_outcomes += f"\nStep: {step.get('name')} [Variable: {output_var}]\n{var_str}\n"

        prompt = self._final_response_template.format(
            preamble=self._responder_preamble or '',
            user_prompt=original_prompt,
            intent=intent or 'Not Provided',
            hint=hint or 'Not Provided',
            data_string=data_string,
            step_outcomes=step_outcomes,
            recent_messages=recent_conversation,
            steps=json.dumps(steps, indent=2)
        )

        resp_context = context.clone_for_single_shot()
        
        # Provide a custom arg pre-processor that will add the vars argument
        original_req_preprocessor = context.function_args_preprocessor
        def args_preprocessor(args:dict, func_def:FunctionDef, context:ChatContext) -> dict:
            if original_req_preprocessor is not None: 
                args = original_req_preprocessor(args, func_def, context)
            if 'vars' in func_def.args:
                args['vars'] = vars
            if 'steps' in func_def.args:
                args['steps'] = steps
            if func_def.name == 'get_dict_val': 
                if args.get('obj') is None: 
                    args['obj'] = vars
                if 'key' in args and args['key'].startswith("$"):
                    args['key'] = args['key'][1:]

            return args
        resp_context.function_args_preprocessor = args_preprocessor

        result = self._proxy.send_message(prompt, resp_context, self._responder_model, use_functions=True, function_filter=lambda x,y: x in ['get_dict_val', 'filter_list', 'get_obj_field', 'random_choice', 'merge_lists', 'calculate'], use_completions_data_source_extensions=False)

        if result.filtered:
            return f"Sorry, I can't respond to that."
        elif result.failed:
            return f"Sorry, I couldn't generate a response due to an error"        
        return result.message
