"""
Chat service for RAG-based conversations.
Handles chat requests with optional file processing.
"""

import pprint
from fastapi import HTTPException, UploadFile, Form, Request

from services.workspace_service import get_or_create_workspace_rag
from services.document_service import process_uploaded_files
from app_init.lightrag_boot import ensure_workspace_dirs

async def get_chat_data(
    request: Request,
    question: str = Form(None),
    mode: str = Form(default="hybrid"),
    files: list[UploadFile] = [],
):
    """
    Dependency to handle both JSON body and form-data for chat requests
    """
    content_type = request.headers.get("content-type", "")

    # Handle JSON body
    if content_type.startswith("application/json"):
        try:
            json_data = await request.json()
            return {
                "question": json_data.get("question"),
                "mode": json_data.get("mode", "hybrid"),
                "files": [],  # JSON requests don't support file uploads
            }
        except Exception as e:
            raise HTTPException(400, f"Invalid JSON body: {str(e)}")

    # Handle form-data (existing behavior)
    elif content_type.startswith("multipart/form-data"):
        if not question:
            raise HTTPException(400, "question is required")
        return {"question": question, "mode": mode, "files": files}

    else:
        raise HTTPException(
            400, "Content-Type must be application/json or multipart/form-data"
        )

async def chat_in_workspace_service(workspace_id: str, chat_data: dict) -> dict:
    """Process chat request in workspace with optional file uploads"""
    if not chat_data["question"]:
        raise HTTPException(400, "question is required")

    # Get or create RAG instance for chat (uses smart caching)
    rag = await get_or_create_workspace_rag(workspace_id)
    paths = ensure_workspace_dirs(workspace_id)

    uploaded_docs = []

    try:
        # Process uploaded files first if any (only for form-data requests)
        if (
            chat_data["files"]
            and len(chat_data["files"]) > 0
            and chat_data["files"][0].filename
        ):  # Check if files are actually provided
            print(f"Processing {len(chat_data['files'])} files before chat...")

            # Use the extracted function to process files
            uploaded_docs = await process_uploaded_files(
                workspace_id, chat_data["files"], rag, paths
            )

            for doc in uploaded_docs:
                print(f"Processed file: {doc['filename']}")

        # Now process the chat query
        ans = await rag.aquery(chat_data["question"], mode=chat_data["mode"])

        response = {"answer": ans}
        pprint.pprint(response)

        # Include uploaded document info if any were processed
        if uploaded_docs:
            response["uploaded_documents"] = uploaded_docs
            response["message"] = (
                f"Processed {len(uploaded_docs)} files and answered your question"
            )

        return response

    except Exception as e:
        raise HTTPException(500, f"Error processing chat with files: {str(e)}")

