from typing import Annotated
import os

from aiproxy import  GLOBAL_PROXIES_REGISTRY, ChatContext
from aiproxy.data import ChatConfig
from aiproxy.proxy import CompletionsProxy
from aiproxy.streaming import StreamWriter
from aiproxy.orchestration.agents import agent_factory

def run(streamer:StreamWriter):
    print("Running a test using the Image Agent")

    config = ChatConfig.load('analyse-image')
    config['analyse-prompt'] = "What do you see in this picture?"
    agent = agent_factory(config)
    if agent is None:
        raise Exception("Could not load agent")
    
    ## Load test image from file
    
    image_path = os.environ.get('IMAGE_PATH') or './test/tests/test-pic.png'
    if not os.path.exists(image_path):
        raise Exception(f"Image file not found at {image_path}")
    
    with open(image_path, "rb") as f:
        img_bytes = f.read()

        ## Test the Image Agent
        context = ChatContext(stream=streamer)
        context.set_metadata("image-extension", "png")
        response = agent.process_message(img_bytes, context)
        print(response.message)