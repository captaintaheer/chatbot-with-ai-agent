from datetime import datetime
from typing import List
from pydantic import BaseModel

class Message(BaseModel):
    content: str
    role: str  # 'human' or 'assistant'
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    thread_id: str
    messages: List[Message]
    language: str