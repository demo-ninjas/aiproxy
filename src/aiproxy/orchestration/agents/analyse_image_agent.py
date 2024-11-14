from typing import Callable
from PIL import Image


from aiproxy import ChatContext, ChatResponse
from aiproxy.data import ChatMessage
from aiproxy.proxy import CompletionsProxy, GLOBAL_PROXIES_REGISTRY
from ..agent import Agent

class AnalyseImageAgent(Agent):
    proxy:CompletionsProxy
    _custom_system_prompt:str = None
    _analyse_prompt:str = None
    _custom_model:str = None
    _single_shot:bool = False
    _thread_isolated:bool = False
    _isolated_thread_id:str = None
    _function_filter:Callable[[str,str], bool] = None
    _default_image_extension:str = None

    def __init__(self, name:str = None, description:str = None, config:dict = None) -> None:
        super().__init__(name, description, config)

        proxy_name = self.config.get("proxy-name", name)
        self.proxy = GLOBAL_PROXIES_REGISTRY.load_proxy(proxy_name, CompletionsProxy)
        self._custom_system_prompt = self.config.get("system-prompt", None)
        self._analyse_prompt = self.config.get("analyse-prompt", None)
        self._custom_model = self.config.get("model", None)
        self._single_shot = self.config.get("single-shot", True)
        self._thread_isolated = self.config.get("thread-isolated", False)
        self._default_image_extension = self.config.get("default-image-extension") or self.config.get("default-image-type") or 'jpg'
        
    def set_function_filter(self, function_filter:Callable[[str,str], bool]):
        self._function_filter = function_filter

    def reset(self):
        self._isolated_thread_id = None
    
    def process_message(self, message:str, context:ChatContext, **kwargs) -> ChatResponse:
        if self._single_shot:
            context = context.clone_for_single_shot()
        elif self._thread_isolated:
            context = context.clone_for_thread_isolation(self._isolated_thread_id)

        ## If the msg is bytes, then base64 it, otherwise assume it's already base64'd
        if isinstance(message, bytes):
            return self.process_native_image(message, context)
        elif isinstance(message, list):
            return self.process_image_list(message, context)
        

        # Check with the context if the it knows the extension of the image
        img_ext = context.get_metadata("image-extension") or context.get_metadata("file-extension") or self._default_image_extension
    
        # Send message to the proxy
        img_msg = ChatMessage(
            role="user", 
            content=[{
                "type": "image_url",
                "image_url": {
                    "url": f'data:image/{img_ext};base64,{message}',
                    "detail": "high"
                }
            }, 
            {
                "type": "text",
                "text": self._analyse_prompt or 'process this image'
            }],
        )
        context.add_message_to_history(img_msg)
        response = self.proxy.send_message(None, context, override_model=self._custom_model, override_system_prompt=self._custom_system_prompt, function_filter=self._function_filter)
        # If the agent is using an isolated thread, store the thread-id for use later 
        if self._thread_isolated:
            self._isolated_thread_id = context.thread_id

        return response
    

    def process_native_image(self, message:bytes, context:ChatContext) -> ChatResponse: 
        import io
        import base64
        import math

        content = []
        if isinstance(message, bytes) and context.get_metadata('slice-image', 'true') == 'true':
            ## Load the image
            image = Image.open(io.BytesIO(message))
            
            # If the image is larger than 512x512, break it up into smaller images
            tiles = []
            if image.width >  1536 or image.height > 1536:
                # Break up the image into smaller images (overlapping each image by ~30%)
                desired_width = 1024
                desired_height = 1024
                cols = math.ceil(image.width / desired_width * 1.33)
                rows = math.ceil(image.height / desired_height * 1.33)
                if cols * rows > 10: 
                    cols = 3
                    rows = 3
                    desired_height = image.height // rows
                    desired_width = image.width // cols
                
                for i in range(int(cols)):
                    for j in range(int(rows)):
                        left = int(i * desired_width * 0.7)
                        upper = int(j * desired_height * 0.7)

                        right = left + desired_width
                        lower = upper + desired_height
                        if right > image.width: 
                            right = image.width
                            left = right - desired_width
                        if lower > image.height: 
                            lower = image.height
                            upper = lower - desired_height

                        tile = image.crop((left, upper, right, lower))
                        tiles.append(tile)
            else: 
                tiles = [image]

            
            # Check with the context if the it knows the extension of the image
            img_ext = context.get_metadata("image-extension") or context.get_metadata("file-extension") or image.format or self._default_image_extension
            img_ext = img_ext.upper()
            if img_ext == 'JPG': 
                img_ext = 'JPEG'
            # img_ext = context.get_metadata("image-extension", image.format or self._default_image_extension)
        
            for tile in tiles:
                # Convert the image to base64
                buffered = io.BytesIO()
                tile.save(buffered, format=img_ext)
                img_str = base64.b64encode(buffered.getvalue()).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f'data:image/{img_ext};base64,{img_str}',
                        "detail": "high"
                    }
                })
            
            content.append({
                "type": "text",
                "text": f"Here are {len(tiles)} images that are overlapping cutouts from a single large image. {self._analyse_prompt or 'Process these images'}"
            })

            context.set_metadata("image-tiles", len(tiles))
        else:
            # Check with the context if the it knows the extension of the image
            img_ext = context.get_metadata("image-extension") or context.get_metadata("file-extension") or self._default_image_extension
            # img_ext = context.get_metadata("image-extension", self._default_image_extension)
            img_str = base64.b64encode(message).decode()
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f'data:image/{img_ext};base64,{img_str}',
                    "detail": "high"
                }
            })

            content.append({
                "type": "text",
                "text": self._analyse_prompt or 'Process this image'
            })



        # Send message to the proxy
        img_msg = ChatMessage(
            role="user", 
            content=content,
        )
        context.add_message_to_history(img_msg)
        response = self.proxy.send_message(None, context, override_model=self._custom_model, override_system_prompt=self._custom_system_prompt, function_filter=self._function_filter)
        # If the agent is using an isolated thread, store the thread-id for use later 
        if self._thread_isolated:
            self._isolated_thread_id = context.thread_id

        return response
    

    def process_image_list(self, message:list[bytes], context:ChatContext) -> ChatResponse: 
        import base64
        content = []

        # Check with the context if the it knows the extension of the image
        img_ext = context.get_metadata("image-extension") or context.get_metadata("file-extension") or self._default_image_extension
        # img_ext = context.get_metadata("image-extension", self._default_image_extension)
        for img in message:
            img_str = base64.b64encode(img).decode()
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f'data:image/{img_ext};base64,{img_str}',
                    "detail": "high"
                }
            })

        content.append({
            "type": "text",
            "text": self._analyse_prompt or 'Process these video frames'
        })

        # Send message to the proxy
        img_msg = ChatMessage(
            role="user", 
            content=content,
        )
        context.add_message_to_history(img_msg)
        response = self.proxy.send_message(None, context, override_model=self._custom_model, override_system_prompt=self._custom_system_prompt, function_filter=self._function_filter)
        # If the agent is using an isolated thread, store the thread-id for use later 
        if self._thread_isolated:
            self._isolated_thread_id = context.thread_id

        return response
    