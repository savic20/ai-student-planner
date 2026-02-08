"""Chat models."""
from pydantic import BaseModel

class ChatMessage(BaseModel):
    id: int
    content: str
    role: str
