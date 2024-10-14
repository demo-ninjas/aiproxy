from typing import Annotated

from aiproxy import GLOBAL_FUNCTIONS_REGISTRY
from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.data import ChatConfig
from aiproxy.orchestration.step_plan_orchestrator import StepPlanOrchestrator
from aiproxy.streaming import StreamWriter

def save_family_note(note:Annotated[str, "The note to save"], family:Annotated[str, "The family to save the note for"]) -> str:
    print(f"  <--- Saved note '{note}' for family '{family}' -->")
    return "Done"
GLOBAL_FUNCTIONS_REGISTRY.register_base_function('save-family-note', "Save a note for a family", save_family_note, { 'family': 'The Dudes'} )

GLOBAL_FUNCTIONS_REGISTRY.register_function_alias('search', 
                                                  alias='recipe-search', 
                                                  description="The search criteria in Lucene format. So, for example, if you want to exclude something from the search results, then prefix it with a '-' symbol, eg. '-mushroom' to exclude results that contain the word 'mushroom'", 
                                                  arg_defaults={ 
                                                      'source':'recipe-index',
                                                      'complexQuery':True
                                                    } 
                                                )
def run(streamer:StreamWriter):
    print("Running a test using the Step Plan Orchestrator")

    config = ChatConfig('step_plan')
    config["response-type"] = "adaptive-card"
    config['functions'] = [
        'ai_chat',
        'ai_assistants_chat',
        'recipe-search',
        'save-family-note',
        'get_dict_val', 
        'get_obj_field',
        'set_obj_field', 
        'obj_to_json', 
        'json_to_obj', 
        'random_choice', 
        'merge_lists',
        "filter_list",
        'run_code',
        'calculate-maths-expression'
    ]
    config['planner-preamble'] = """You are a personal assistant for families. You can save notes for the family, chat with the AI, chat with other AI assistants, and search for recipes that the family might be interested in.

    You are currently talking with the "Stanbrook" family.
    """

    config['responder-preamble'] = """You are a personal assistant for families.

    You are currently talking with the "Stanbrook" family.

    You are responding in adaptive card format.

    The card should include the following information:
    * The name of the recipe
    * The ingredients required for the recipe
    * The steps to make the recipe
    * The image of the dish (if available)
    """
    config['rules'] = """Additional Rules/Considerations when generating a plan: 
    * If the user gives some information about their family, you should record a note about that, so that you can refer to it later, use the function 'save-family-note' to save the note
    * If the user gives multiple pieces of information about their family, you should record a separate note for each 
    * If the user asks a question that could be answered by an AI, you can use the 'ai_chat' function to pose the question to an AI
    * If the use is interested in recipes, you can use the 'recipe-search' function to search for recipes
    * If the user asks for the result of a maths forumla/equation, you can use the 'calculate-maths-expression' function to calculate-maths-expression the result
    * If you need to run some code to generate a response, you can use the 'run_code' function to run the code
    """

    step_orchestrator = GLOBAL_PROXIES_REGISTRY.load_proxy(config, StepPlanOrchestrator)
    if step_orchestrator is None:
        raise Exception("Could not load proxy")
    if type(step_orchestrator) is not StepPlanOrchestrator:
        raise Exception("Loaded proxy is not a StepPlanOrchestrator")
    
    context = ChatContext(None, stream=streamer)
    # q = "I have a family of 4, 2 adults and 2 children. We all love pasta and pizza. The kids dislike mushrooms. I am looking for some easy to make recipes that the whole family will enjoy."
    q = """I have a family of 4, 2 adults and 2 children. We all love pasta and pizza. 
    The kids dislike mushrooms and olives and garlic. 
    I want to make sure that it doesn't take more than about 30 minutes to prepare the meal.
    Start by finding a pizza recipe that works for the family. 
    Have a look at the pizza recipes you find, and if they look like they'll work, then tell me their names and the ingredients in them. 
    If you don't like the look of the pizza recipes, then find a suitable pasta recipe.
    Again, if they don't look good, then find a curry recipe that works for the family.
    """
    resp = step_orchestrator.send_message(q, context)

    print(f"Question: {q}")
    print("\n\nResponse:\n\n")
    print(resp.message)
    print(f"\n\nOutput Format: {resp.metadata.get('response-type', 'Unknown')}")
    print('\n\nSteps used to respond to this prompt:')
    for step in resp.metadata.get('steps', []) if resp.metadata else []:
        print("* " + step)
