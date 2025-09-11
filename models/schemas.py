"""
Pydantic models for API requests and responses.
"""

from typing import Optional
from pydantic import BaseModel

class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class ChatReq(BaseModel):
    question: str
    mode: str = "hybrid"

class ChatJsonReq(BaseModel):
    question: str
    mode: str = "hybrid"
