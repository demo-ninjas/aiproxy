from typing import Annotated

from aiproxy import GLOBAL_FUNCTIONS_REGISTRY
from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.data import ChatConfig
from aiproxy.orchestration.consensus_orchestrator import ConsensusOrchestrator
from aiproxy.streaming import StreamWriter

def run(streamer:StreamWriter):
    print("Running a test using a previously configured Consensus Orchestrator")

    config = ChatConfig.load('Dev Team Group Chat')
    step_orchestrator = GLOBAL_PROXIES_REGISTRY.load_proxy(config, ConsensusOrchestrator)
    if step_orchestrator is None:
        raise Exception("Could not load proxy")
    if type(step_orchestrator) is not ConsensusOrchestrator:
        raise Exception("Loaded proxy is not a ConsensusOrchestrator")
    
    context = ChatContext(None, stream=streamer)
    # context.set_metadata('all_agents_must_respond_first_time', True)
    context.set_metadata('include_interim_responses', True)
    

    q = """I would like to design a game of pong in Rust.
    The game should be playable in a web browser, so it should use WebAssembly.
    The game should have a simple user interface with a ball and two paddles and be playable by either 1 or 2 users.
    When there is only one user, the second paddle should be controlled by the computer.
    The game should have a scoring system and keep track of the score.
    The game should be playable on both desktop and mobile devices.
    The game should be responsive and adapt to different screen sizes.
    The game should have sound effects and music.
    THe game should be fast and efficient, and not use too much memory or system resources.
    Please go ahead and design this game for me, including writing the code.
    """
    print(f"Question: {q}")
    resp = step_orchestrator.send_message(q, context)
    # print(resp.message)

    print('\nParticipants:')
    for participant in resp.metadata.get('participants', []) if resp.metadata else []:
        print("* " + participant)

    num_turns = resp.metadata.get('turns', 0) if resp.metadata else 0
    print(f"\n\nNo. of Turns: {num_turns}")
    
    print("\n\n\n")

    ## Print the Full History
    print("Interim Resopnses:")
    for i, msg in enumerate(resp.metadata.get('interim_responses', [])):
        print(f"Interim Response {i}:")
        print(msg[:500] + '...' if len(msg) > 520 else msg)
        print("\n\n")

    print("\n\n\n")

    print("Final Response:")
    print(resp.message)

    
