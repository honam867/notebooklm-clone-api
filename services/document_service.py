"""
Document processing service.
Handles file uploads, processing, and document management.
"""

import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException
from raganything import RAGAnything

from app_init.lightrag_boot import ensure_workspace_dirs
from core.state import add_workspace_doc, remove_workspace_doc, get_workspace_docs
from storage.delete_strategies import delete_document_everywhere
from services.workspace_service import get_or_create_workspace_rag

async def save_uploaded_file(workspace_id: str, file: UploadFile, paths: dict) -> dict:
    """Save uploaded file to workspace and return file info"""
    doc_id = str(uuid.uuid4())
    dest_dir = os.path.join(paths["uploads"], doc_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, file.filename)

    # Save file to disk
    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # Store in workspace document mapping
    add_workspace_doc(workspace_id, doc_id, dest_path)

    return {
        "id": doc_id,
        "filename": file.filename,
        "file_path": dest_path,
        "dest_dir": dest_dir,
    }

async def process_document_with_rag(
    rag: RAGAnything,
    file_path: str,
    output_dir: str,
    doc_id: str,
    parse_method: str = "auto",
) -> dict:
    """
    Process document with RAGAnything - separated flow for clarity
    Based on raganything_example.py pattern
    """
    try:
        print(f"🔄 Processing document: {file_path}")
        print(f"📁 Output directory: {output_dir}")
        print(f"🆔 Document ID: {doc_id}")
        print(f"⚙️ Parse method: {parse_method}")

        # Process document with RAGAnything (like raganything_example.py)
        await rag.process_document_complete(
            file_path=file_path,
            output_dir=output_dir,
            doc_id=doc_id,
            parse_method=parse_method,
        )

        print(f"✅ Successfully processed document: {doc_id}")

        return {
            "status": "success",
            "doc_id": doc_id,
            "file_path": file_path,
            "output_dir": output_dir,
            "parse_method": parse_method,
            "message": f"Document {doc_id} processed successfully",
        }

    except Exception as e:
        print(f"❌ Error processing document {doc_id}: {str(e)}")
        return {
            "status": "error",
            "doc_id": doc_id,
            "file_path": file_path,
            "error": str(e),
            "message": f"Failed to process document {doc_id}",
        }

async def process_uploaded_files(
    workspace_id: str, files: list[UploadFile], rag: RAGAnything, paths: dict
) -> list[dict]:
    """Process uploaded files for a workspace and return document info"""
    uploaded_docs = []

    for f in files:
        # Step 1: Save file to workspace
        file_info = await save_uploaded_file(workspace_id, f, paths)

        # Step 2: Process document with RAG
        processing_result = await process_document_with_rag(
            rag=rag,
            file_path=file_info["file_path"],
            output_dir=paths["output"],
            doc_id=file_info["id"],
            parse_method="auto",
        )

        # Step 3: Combine file info with processing result
        doc_result = {
            "id": file_info["id"],
            "filename": file_info["filename"],
            "processing_status": processing_result["status"],
            "processing_message": processing_result["message"],
        }

        if processing_result["status"] == "error":
            doc_result["error"] = processing_result["error"]

        uploaded_docs.append(doc_result)

    return uploaded_docs

async def upload_documents_service(workspace_id: str, files: list[UploadFile]) -> dict:
    """Upload documents to a specific workspace"""
    print(f"🚀 Uploading documents to workspace: {workspace_id}")
    
    # Get or create RAG instance (uses smart caching)
    rag = await get_or_create_workspace_rag(workspace_id)
    paths = ensure_workspace_dirs(workspace_id)

    # Process uploaded files using the extracted function
    uploaded_docs = await process_uploaded_files(workspace_id, files, rag, paths)

    return {"ok": True, "documents": uploaded_docs}

def list_workspace_documents_service(workspace_id: str) -> list[dict]:
    """List documents in a specific workspace"""
    # Check if workspace exists in database
    try:
        from repos.workspaces import get_workspace as db_get_workspace
        db_workspace = db_get_workspace(workspace_id)
        if not db_workspace:
            raise HTTPException(404, "Workspace not found")
    except Exception as e:
        print(f"⚠️  Database check failed: {e}")
        raise HTTPException(404, "Workspace not found")

    docs = get_workspace_docs(workspace_id)
    return [
        {"id": k, "path": v, "filename": os.path.basename(v)} for k, v in docs.items()
    ]

async def delete_workspace_document_service(workspace_id: str, doc_id: str) -> dict:
    """Delete a document from a specific workspace"""
    # Check if workspace exists in database
    try:
        from repos.workspaces import get_workspace as db_get_workspace
        db_workspace = db_get_workspace(workspace_id)
        if not db_workspace:
            raise HTTPException(404, "Workspace not found")
    except Exception as e:
        print(f"⚠️  Database check failed: {e}")
        raise HTTPException(404, "Workspace not found")

    workspace_docs_dict = get_workspace_docs(workspace_id)
    if doc_id not in workspace_docs_dict:
        raise HTTPException(404, "Document not found in workspace")

    try:
        # Get or create RAG instance for deletion (uses smart caching)
        rag = await get_or_create_workspace_rag(workspace_id)
        # Use unified deletion strategy to remove from external storage
        deletion_result = await delete_document_everywhere(rag.lightrag, doc_id)
        print(f"🗑️ Document deletion result: {deletion_result}")

        # Remove physical files
        paths = ensure_workspace_dirs(workspace_id)
        doc_dir = os.path.join(paths["uploads"], doc_id)
        if os.path.exists(doc_dir):
            shutil.rmtree(doc_dir)

        # Remove from workspace document mapping
        remove_workspace_doc(workspace_id, doc_id)

        return {
            "ok": True,
            "message": f"Document {doc_id} deleted from workspace {workspace_id}",
        }

    except Exception as e:
        raise HTTPException(500, f"Error deleting document: {str(e)}")
