from typing import List, Optional

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    """Request model for chat messages."""

    prompt: str
    user_id: str
    local_time: Optional[str] = None
    dietary_preferences: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    selected_goals: Optional[List[str]] = None
    foodImage: Optional[str] = None
