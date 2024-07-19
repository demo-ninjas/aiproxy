
class ChatMessage: 
    message:str
    tool_calls:dict
    tool_call_id:str
    tool_name:str
    citations:list
    role:str
    timestamp:str
    content:dict
    id:str
    assistant_id:str
    run_id:str

    def __init__(self, message:str = None, role:str = None, timestamp:str = None, content:dict = None, id:str = None, tool_calls:dict = None, citations:list = None, tool_call_id:str = None, tool_name:str = None, assistant_id:str = None, run_id:str = None) -> None:
        self.message = message
        self.role = role
        self.timestamp = timestamp
        if self.timestamp is None: 
            # Set to current time in ISO Format
            from datetime import datetime
            self.timestamp = datetime.now().isoformat()
        self.content = content
        self.id = id
        self.tool_calls = tool_calls
        self.citations = citations
        self.tool_call_id = tool_call_id
        self.tool_name = tool_name
        self.assistant_id = assistant_id
        self.run_id = run_id

    def from_dict(data:dict) -> 'ChatMessage':
        return ChatMessage(
            message = data.get('message'),
            role = data.get('role'),
            timestamp = data.get('timestamp'),
            content = data.get('content'),
            tool_calls = data.get('tool_calls'),
            citations = data.get('citations'),
            tool_name = data.get('tool_name'),
            tool_call_id = data.get('tool_call_id'),
            assistant_id=data.get('assistant_id'),
            run_id=data.get('run_id'),
            id = data.get('id')
        )
    
    def to_dict(self) -> dict: 
        return {
            'message': self.message,
            'role': self.role,
            'timestamp': self.timestamp,
            'content': self.content,
            'tool_calls': self.tool_calls,
            'tool_name': self.tool_name,
            'tool_call_id': self.tool_call_id,
            'citations': self.citations,
            'assistant_id': self.assistant_id,
            'run_id': self.run_id,
            'id': self.id
        }
    
    def to_openid_message(self) -> dict: 
        msg = {            
            'role': self.role
        }
        msg['content'] = self.content or self.message
        if self.tool_calls is not None: 
            msg['tool_calls'] = self.tool_calls
        if self.tool_name is not None: 
            msg['name'] = self.tool_name
        if self.tool_call_id is not None: 
            msg['tool_call_id'] = self.tool_call_id
        if self.assistant_id is not None: 
            msg['assistant_id'] = self.assistant_id
        if self.run_id is not None:
            msg['run_id'] = self.run_id
            
        return msg

    def from_tool_calls_message(data) -> 'ChatMessage':
        return ChatMessage(
            role = data.role,
            tool_calls = [{ "id":tool.id, "function":{ "arguments":tool.function.arguments, "name":tool.function.name }, "type":"function" } for tool in data.tool_calls]
        )