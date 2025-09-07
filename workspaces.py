# workspaces.py
"""
Updated version of workspaces.py with external storage support.
Demonstrates integration with the new storage factory while maintaining backward compatibility.
"""
import os, uuid, shutil, asyncio, json
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request, Depends
from pydantic import BaseModel
from dotenv import load_dotenv
from raganything import RAGAnything, RAGAnythingConfig
import pprint

# Import new storage components
from app_init.lightrag_boot import (
    init_workspace_lightrag,
    ensure_workspace_dirs,
)
from storage.delete_strategies import delete_document_everywhere, delete_workspace_data
from storage.storage_factory import validate_external_storage_config
from api.health import router as health_router
from lightrag.llm.openai import openai_complete_if_cache

from typing import Dict, Optional

load_dotenv(dotenv_path=".env", override=False)

BASE_WORKSPACES_DIR = os.getenv("WORKSPACES_DIR", "./workspaces")
API_KEY = os.getenv("LLM_BINDING_API_KEY")
BASE_URL = os.getenv("LLM_BINDING_HOST")

# Global variables
workspace_rags: Dict[str, RAGAnything] = {}  # workspace_id -> RAGAnything instance
workspace_docs: Dict[str, Dict[str, str]] = {}  # workspace_id -> {doc_id: file_path}


def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
    return openai_complete_if_cache(
        "gpt-4o-mini",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=API_KEY,
        base_url=BASE_URL,
        **kwargs,
    )


def vision_model_func(
    prompt,
    system_prompt=None,
    history_messages=[],
    image_data=None,
    messages=None,
    **kwargs,
):

    print("✨ Check promp", prompt)

    if messages:
        return openai_complete_if_cache(
            "gpt-4o",
            "",
            system_prompt=None,
            history_messages=[],
            messages=messages,
            api_key=API_KEY,
            base_url=BASE_URL,
            **kwargs,
        )

    # Fallback to regular LLM
    from storage.storage_factory import create_llm_model_func

    llm_func = create_llm_model_func()
    return llm_func(prompt, system_prompt, history_messages, **kwargs)


def rebuild_workspace_docs_mapping(workspace_id: str):
    """Rebuild DOCS mapping for a specific workspace"""
    paths = ensure_workspace_dirs(workspace_id)
    workspace_docs[workspace_id] = {}

    if not os.path.exists(paths["uploads"]):
        return

    # Scan each UUID directory in uploads
    for doc_id in os.listdir(paths["uploads"]):
        doc_dir = os.path.join(paths["uploads"], doc_id)
        if os.path.isdir(doc_dir):
            files = os.listdir(doc_dir)
            if files:
                file_path = os.path.join(doc_dir, files[0])
                workspace_docs[workspace_id][doc_id] = file_path
                print(
                    f"Restored document mapping for workspace {workspace_id}: {doc_id} -> {files[0]}"
                )


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
    if workspace_id not in workspace_docs:
        workspace_docs[workspace_id] = {}
    workspace_docs[workspace_id][doc_id] = dest_path

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


def get_workspace_rag(workspace_id: str) -> RAGAnything:
    """Get RAG instance for workspace (must be already initialized)"""
    print(f"🔍 Looking for workspace: {workspace_id}")
    print(f"📊 Available workspaces: {list(workspace_rags.keys())}")

    if workspace_id not in workspace_rags:
        error_msg = f"Workspace {workspace_id} RAG not initialized. Available workspaces: {list(workspace_rags.keys())}"
        print(f"❌ {error_msg}")
        raise HTTPException(404, error_msg)

    print(f"✅ Found workspace: {workspace_id}")
    return workspace_rags[workspace_id]


async def initialize_workspace_rag(workspace_id: str) -> RAGAnything:
    """Initialize RAG system for a specific workspace using external storage"""
    print(f"🚀 Initializing RAG system for workspace: {workspace_id}")

    if workspace_id in workspace_rags:
        print(f"✅ RAG already initialized for workspace: {workspace_id}")
        return workspace_rags[workspace_id]

    # Validate external storage configuration
    missing_vars = validate_external_storage_config()
    if missing_vars:
        error_msg = f"External storage configuration incomplete. Missing: {', '.join(missing_vars)}"
        print(f"❌ {error_msg}")
        raise HTTPException(500, error_msg)

    try:
        paths = ensure_workspace_dirs(workspace_id)
        lightrag_instance = await init_workspace_lightrag(workspace_id)

        # Create RAGAnything config
        config = RAGAnythingConfig(
            working_dir=paths["workspace_dir"],
            parser=os.getenv("PARSER", "mineru"),
            parse_method="auto",
            enable_image_processing=True,
            enable_table_processing=True,
            enable_equation_processing=False,
        )

        # Initialize RAGAnything with the pre-initialized LightRAG instance
        print(f"✨ Initializing RAGAnything... with config")
        rag_anything = RAGAnything(
            lightrag=lightrag_instance,
            llm_model_func=llm_model_func,
            vision_model_func=vision_model_func,
            config=config,
        )
        print(f"✨ RAGAnything created successfully")

        # Cache the RAG instance
        workspace_rags[workspace_id] = rag_anything
        print(f"💾 Cached RAG instance for workspace: {workspace_id}")

    except Exception as e:
        error_msg = f"Failed to initialize RAG for workspace {workspace_id}: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"🔍 Exception details: {type(e).__name__}: {str(e)}")
        # Don't add to workspace_rags if initialization failed
        raise HTTPException(500, error_msg)

    # Rebuild document mapping for this workspace
    rebuild_workspace_docs_mapping(workspace_id)
    print(
        f"✅ Initialized RAG for workspace {workspace_id} with {len(workspace_docs.get(workspace_id, {}))} documents\n\n"
    )
    return rag_anything


async def startup_initialize():
    """Initialize system at startup with external storage"""

    # Validate external storage configuration
    missing_vars = validate_external_storage_config()
    if missing_vars:
        print(
            f"❌ External storage configuration incomplete. Missing: {', '.join(missing_vars)}"
        )
        print("💡 Please configure all required environment variables and restart")
        return

    # Initialize RAG for existing workspaces (discover from directory structure)
    initialized_count = 0
    if os.path.exists(BASE_WORKSPACES_DIR):
        for workspace_id in os.listdir(BASE_WORKSPACES_DIR):
            workspace_path = os.path.join(BASE_WORKSPACES_DIR, workspace_id)
            if os.path.isdir(workspace_path) and len(workspace_id) == 36:  # UUID format
                try:
                    await initialize_workspace_rag(workspace_id)
                    initialized_count += 1
                except Exception as e:
                    print(f"Error initializing workspace {workspace_id}: {e}")

    print(
        f"Startup complete. Initialized {initialized_count} workspaces with external storage."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_initialize()
    yield
    # Shutdown - cleanup any resources if needed
    pass


app = FastAPI(lifespan=lifespan)

# Include health check router
app.include_router(health_router)


# Pydantic models
class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class ChatReq(BaseModel):
    question: str
    mode: str = "hybrid"


class ChatJsonReq(BaseModel):
    question: str
    mode: str = "hybrid"


async def get_chat_data(
    request: Request,
    question: str = Form(None),
    mode: str = Form(default="hybrid"),
    files: list[UploadFile] = File(default=[]),
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


# Workspace CRUD endpoints
@app.post("/workspaces")
async def create_workspace(workspace_data: WorkspaceCreate):
    """Create a new workspace"""
    workspace_id = str(uuid.uuid4())
    print(f"🆕 Creating new workspace: {workspace_id}")
    print(f"📝 Name: {workspace_data.name}")
    print(f"📄 Description: {workspace_data.description}")

    try:
        # Create workspace directories
        paths = ensure_workspace_dirs(workspace_id)
        print(f"📁 Created workspace paths: {paths}")

        # Initialize empty document mapping
        workspace_docs[workspace_id] = {}
        print(f"📋 Initialized empty document mapping")

        # Initialize RAG for the new workspace (this will handle all storage setup)
        print(f"🚀 Starting RAG initialization...")
        await initialize_workspace_rag(workspace_id)
        print(f"✅ RAG initialization completed")

    except Exception as e:
        print(f"❌ Error during workspace creation: {str(e)}")
        # Clean up on failure
        if workspace_id in workspace_docs:
            del workspace_docs[workspace_id]
        raise

    # Return workspace info (metadata will be stored in external storage)
    return {
        "ok": True,
        "workspace": {
            "id": workspace_id,
            "name": workspace_data.name,
            "description": workspace_data.description,
            "created_at": asyncio.get_event_loop().time(),
            "document_count": 0,
            "storage_mode": "external",
        },
    }


@app.get("/workspaces")
async def list_workspaces():
    """List all active workspaces from memory"""
    workspaces_list = []
    for workspace_id in workspace_rags.keys():
        doc_count = len(workspace_docs.get(workspace_id, {}))
        workspace_info = {
            "id": workspace_id,
            "document_count": doc_count,
            "storage_mode": "external",
            "status": "active",
        }
        workspaces_list.append(workspace_info)

    return {"workspaces": workspaces_list}


@app.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get workspace details"""
    if workspace_id not in workspace_rags:
        raise HTTPException(404, "Workspace not found")

    workspace_info = {
        "id": workspace_id,
        "document_count": len(workspace_docs.get(workspace_id, {})),
        "storage_mode": "external",
        "status": "active",
    }

    return {"workspace": workspace_info}


@app.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str):
    """Delete entire workspace from external storage and memory"""
    if workspace_id not in workspace_rags:
        raise HTTPException(404, "Workspace not found")

    try:
        # Delete from external storages
        rag = workspace_rags[workspace_id]
        deletion_result = await delete_workspace_data(rag.lightrag, workspace_id)
        print(f"🗑️ External storage cleanup result: {deletion_result}")

        # Remove from memory
        del workspace_rags[workspace_id]
        if workspace_id in workspace_docs:
            del workspace_docs[workspace_id]

        # Remove physical directory (uploads/temp files)
        paths = ensure_workspace_dirs(workspace_id)
        if os.path.exists(paths["workspace_dir"]):
            shutil.rmtree(paths["workspace_dir"])

        return {"ok": True, "message": f"Workspace {workspace_id} deleted successfully"}

    except Exception as e:
        raise HTTPException(500, f"Error deleting workspace: {str(e)}")


# Document operations within workspace
@app.post("/workspaces/{workspace_id}/documents")
async def upload_documents(workspace_id: str, files: list[UploadFile] = File(...)):
    print(f"🚀 Uploading documents to workspace: {workspace_id}")
    """Upload documents to a specific workspace"""
    if workspace_id not in workspace_rags:
        raise HTTPException(404, "Workspace not found")

    # Get RAG instance (should already be initialized)
    rag = get_workspace_rag(workspace_id)
    paths = ensure_workspace_dirs(workspace_id)

    # Process uploaded files using the extracted function
    uploaded_docs = await process_uploaded_files(workspace_id, files, rag, paths)

    return {"ok": True, "documents": uploaded_docs}


@app.get("/workspaces/{workspace_id}/documents")
async def list_workspace_documents(workspace_id: str):
    """List documents in a specific workspace"""
    if workspace_id not in workspace_rags:
        raise HTTPException(404, "Workspace not found")

    docs = workspace_docs.get(workspace_id, {})
    return [
        {"id": k, "path": v, "filename": os.path.basename(v)} for k, v in docs.items()
    ]


@app.delete("/workspaces/{workspace_id}/documents/{doc_id}")
async def delete_workspace_document(workspace_id: str, doc_id: str):
    """Delete a document from a specific workspace"""
    if workspace_id not in workspace_rags:
        raise HTTPException(404, "Workspace not found")

    if workspace_id not in workspace_docs or doc_id not in workspace_docs[workspace_id]:
        raise HTTPException(404, "Document not found in workspace")

    try:
        # Get workspace RAG instance
        rag = workspace_rags.get(workspace_id)
        if rag:
            # Use unified deletion strategy to remove from external storage
            deletion_result = await delete_document_everywhere(rag.lightrag, doc_id)
            print(f"🗑️ Document deletion result: {deletion_result}")

        # Remove physical files
        paths = ensure_workspace_dirs(workspace_id)
        doc_dir = os.path.join(paths["uploads"], doc_id)
        if os.path.exists(doc_dir):
            shutil.rmtree(doc_dir)

        # Remove from workspace document mapping
        del workspace_docs[workspace_id][doc_id]

        return {
            "ok": True,
            "message": f"Document {doc_id} deleted from workspace {workspace_id}",
        }

    except Exception as e:
        raise HTTPException(500, f"Error deleting document: {str(e)}")


@app.post("/workspaces/{workspace_id}/chat")
async def chat_in_workspace(
    workspace_id: str, chat_data: dict = Depends(get_chat_data)
):
    if workspace_id not in workspace_rags:
        raise HTTPException(404, "Workspace not found")

    if not chat_data["question"]:
        raise HTTPException(400, "question is required")

    # Get RAG instance (should already be initialized)
    rag = get_workspace_rag(workspace_id)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("workspaces:app", host="0.0.0.0", port=8000, reload=True)
