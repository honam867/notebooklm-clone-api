"""
Document API routes.
Handles document operations within workspaces.
"""

from fastapi import APIRouter, UploadFile, File

from services.document_service import (
    upload_documents_service,
    list_workspace_documents_service,
    delete_workspace_document_service
)

router = APIRouter(prefix="/workspaces", tags=["documents"])

@router.post("/{workspace_id}/documents")
async def upload_documents(workspace_id: str, files: list[UploadFile] = File(...)):
    """Upload documents to a specific workspace"""
    return await upload_documents_service(workspace_id, files)

@router.get("/{workspace_id}/documents")
async def list_workspace_documents(workspace_id: str):
    """List documents in a specific workspace"""
    documents = list_workspace_documents_service(workspace_id)
    return documents

@router.delete("/{workspace_id}/documents/{doc_id}")
async def delete_workspace_document(workspace_id: str, doc_id: str):
    """Delete a document from a specific workspace"""
    return await delete_workspace_document_service(workspace_id, doc_id)

