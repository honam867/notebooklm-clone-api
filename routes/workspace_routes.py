"""
Workspace API routes.
Handles workspace CRUD operations.
"""

from fastapi import APIRouter

from models.schemas import WorkspaceCreate
from services.workspace_service import (
    create_workspace_service,
    list_workspaces_service,
    get_workspace_info,
    delete_workspace_service
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

@router.post("")
async def create_workspace(workspace_data: WorkspaceCreate):
    """Create a new workspace"""
    return await create_workspace_service(workspace_data.name, workspace_data.description)

@router.get("")
async def list_workspaces():
    """List all workspaces from database and merge with in-memory data"""
    workspaces_list = list_workspaces_service()
    return {"workspaces": workspaces_list}

@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get workspace details from database and merge with in-memory data"""
    workspace_info = await get_workspace_info(workspace_id)
    return {"workspace": workspace_info}

@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str):
    """Delete entire workspace from external storage, memory, and database"""
    return await delete_workspace_service(workspace_id)
