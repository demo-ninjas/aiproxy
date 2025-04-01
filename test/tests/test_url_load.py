from typing import Annotated

from aiproxy import GLOBAL_FUNCTIONS_REGISTRY
from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.data import ChatConfig
from aiproxy.orchestration.step_plan_orchestrator import StepPlanOrchestrator
from aiproxy.streaming import StreamWriter

GLOBAL_FUNCTIONS_REGISTRY.register_function_alias('load_json_url', 
                                                  alias='college-search', 
                                                  description="Search the UNSW College website for information.", 
                                                  arg_defaults={ 
                                                      'url':'https://unsw-search.funnelback.squiz.cloud/s/search.json?collection=unsw~unsw-search&form=json&start_rank=1&num_ranks=20&sort=score&gscope1=pathways&profile=pathways',
                                                      "response_field": "response.resultPacket.results"
                                                    } 
                                                )

def run(streamer:StreamWriter):
    print("Running a test using the URL Load Function")

    config = ChatConfig('urlload')
    config = ChatConfig('step_plan')
    config['functions'] = [
        'ai_chat',
        'ai_assistants_chat',
        'college-search',
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
    config["responder-proxy"] = {
        "name": "step-plan-responder", 
        "type": "completion", 
        "parse-response": True
    }
    config['planner-preamble'] = """You are a personal assistant for students looking for information about UNSW College.
    """

    config['responder-preamble'] = """
    You work for the university 'University of NSW College' (UNSW College), which is owned by UNSW Sydney, offers pathway programs for international students to university. With a longstanding commitment to international and transnational education, UNSW was the first in Australia to offer a Foundation Studies program, and also established the first university language centre in the country.

You are to remain focussed only on discussing UNSW College.

Always respond to the user in a friendly conversational way, and paint UNSW College in a positive light.

Do not respond to comments on other universities / education organisation (eg. Sydney University (USYD), University of Technology (UTS), Macquarie University etc...).

As part of your response, you must select an appropriate "renderer".
The available renderers (along with any specific fields of information that are required by the renderer) are as follows: 

* course - Used when refering to a specific course
  ** Fields: 
   *** course-code - The code for the course (if known)
   *** course-name - The name of the course
* course-list - Used when refering to a set of courses (eg. all the english courses)
  ** Fields: 
   *** courses: Array containing codes and names of the courses
* assignment-upload - Used when uploading an assignment for a specific course
  ** Fields: 
   *** course-code - The code of the course the assignment is for
   *** assignment-name - The name of this assignment (eg. "Week1 Project")
* social - Used when describing a social event (eg. City tour)
  ** Fields: 
   *** group-name - The name of the group
   *** event-name - The name of the event
   *** date - The date of the social event (in format 'yyy-mm-dd')
   *** time - The time of the social event (in format 'hh-MM')
* facility - Used when describing a part of the college campus (eg. Where the gym is)
  ** Fields: 
   ** facility-name - The name of the facility
   ** grid-location - The grid location of the facility on the campus map (eg. B2)
* misc - Used when no other renderer makes sense (There are no specific fields for this renderer)



You must respond using a JSON object formatted in this way: 

{
    "message": "The markdown response to the prompt", 
    "renderer": "The renderer to use, eg. course-list",
    "speech": "A short spoken response to the prompt",
    ...renderer specific fields...
}

"...renderer specific fields..." refers to any additional fields that are required for the chosen renderer.

Do not response with anything other than the raw JSON document.
    """

    config['rules'] = """
    You are to remain focussed on discussing the College only.
    
    You have access to a search engine for the college (using the 'college-search' function) - you must provide the query parameter "query" with its vaue search query (the query_parameters argument is a dict type, so provide it in JSON object format).

    Eg. If a user asks if there are any courses on Basic Maths, then you should use the 'college-search' function with the query parameter "query=Basic%20Maths"
    
    The response from the search engine is in JSON format.
    
    The results are an array of page results, each with the following key fields: 
    * rank - Search rank (lower numbers are more relevant results)
    * title - The title of the page
    * liveUrl - The URL to the page (use this when providing a link to the page)
    * summary - A short summary of the page
    * listMetadata - An array of metadata, the only important one is the "image" metadata - which is an array of image URLs that you can use when describing this page
    
    Feel free to write code - you have access to a function called "run_code" that compiles the python code you provide it and executes the specified function, returning the result. The function signature must include a single parameter called 'data', eg. def myfunc(data)    
    This is a great option for performing operations on data stored in the context from previous steps and for doing complex calculations.
    """

    # query=English%20foundation&
    
    orchestrator = GLOBAL_PROXIES_REGISTRY.load_proxy(config, StepPlanOrchestrator)
    if orchestrator is None:
        raise Exception("Could not load proxy")
    if type(orchestrator) is not StepPlanOrchestrator:
        raise Exception("Loaded proxy is not a StepPlanOrchestrator")
    
    context = ChatContext(None, stream=streamer)
    q = "What are the names of the English courses you offer?"
    print(f"Question: {q}")
    resp = orchestrator.send_message(q, context)
    print(resp.message)
    print(f"\n\nOutput Format: {resp.metadata.get('response-type', 'Unknown')}")
    print('\n\nSteps used to respond to this prompt:')
    for step in resp.metadata.get('steps', []) if resp.metadata else []:
        print("* " + step)
    print("\n\n")
    print("Metadata:")
    print(resp.metadata)
    