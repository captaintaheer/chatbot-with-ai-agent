from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    language: str = "English"
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    language: str
    timestamp: datetime = None