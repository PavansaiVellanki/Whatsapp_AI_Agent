"""
Pydantic models for chat messages
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from app.utils.constants import ROLE_BOT, ROLE_USER

class ChatMessageCreate(BaseModel):
    """Model for creating a new chat message"""
    user_phone: str = Field(..., max_length=20, description="User phone number")
    role: Literal["bot", "user"] = Field(..., description="Role of the message sender")
    message: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    """Model for chat request"""
    message: str = Field(..., description="User's message")

class ChatMessageResponse(BaseModel):
    """Model for chat message response"""
    id: str
    user_phone: str
    role: str
    message: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

