"""
Chat API routes.
Handles RAG-based chat interactions within workspaces.
"""

from fastapi import APIRouter, Depends

from services.chat_service import get_chat_data, chat_in_workspace_service

router = APIRouter(prefix="/workspaces", tags=["chat"])

@router.post("/{workspace_id}/chat")
async def chat_in_workspace(
    workspace_id: str, chat_data: dict = Depends(get_chat_data)
):
    """Chat with workspace using RAG"""
    return await chat_in_workspace_service(workspace_id, chat_data)
