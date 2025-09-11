"""
Workspace business logic service.
Handles workspace creation, initialization, and management.
"""

import os
import uuid
import shutil
from fastapi import HTTPException
from raganything import RAGAnything, RAGAnythingConfig

from app_init.lightrag_boot import init_workspace_lightrag, ensure_workspace_dirs
from storage.storage_factory import create_llm_model_func, create_vision_model_func
from core.state import (
    init_workspace_docs, remove_workspace_docs, get_workspace_doc_count,
    get_current_workspace_rag, set_current_workspace_rag, clear_current_workspace
)
from storage.delete_strategies import delete_workspace_data

# Create function instances from storage factory
llm_model_func = create_llm_model_func()
vision_model_func = create_vision_model_func()

def rebuild_workspace_docs_mapping(workspace_id: str):
    """Rebuild DOCS mapping for a specific workspace"""
    paths = ensure_workspace_dirs(workspace_id)
    init_workspace_docs(workspace_id)

    if not os.path.exists(paths["uploads"]):
        return

    # Scan each UUID directory in uploads
    for doc_id in os.listdir(paths["uploads"]):
        doc_dir = os.path.join(paths["uploads"], doc_id)
        if os.path.isdir(doc_dir):
            files = os.listdir(doc_dir)
            if files:
                file_path = os.path.join(doc_dir, files[0])
                from core.state import add_workspace_doc
                add_workspace_doc(workspace_id, doc_id, file_path)
                print(
                    f"Restored document mapping for workspace {workspace_id}: {doc_id} -> {files[0]}"
                )


async def get_or_create_workspace_rag(workspace_id: str) -> RAGAnything:
    """Smart factory: reuse cached RAG or create new one"""
    
    # Try to get cached RAG for same workspace
    cached_rag = get_current_workspace_rag(workspace_id)
    if cached_rag:
        print(f"✅ Reusing cached RAG for workspace: {workspace_id}")
        return cached_rag
    
    # Create new RAG instance and cache it
    print(f"🚀 Creating new RAG for workspace: {workspace_id}")
    rag = await initialize_workspace_rag(workspace_id)
    set_current_workspace_rag(workspace_id, rag)
    print(f"💾 Cached RAG instance for workspace: {workspace_id}")
    return rag

async def initialize_workspace_rag(workspace_id: str) -> RAGAnything:
    """Create a new RAG instance for a specific workspace (internal factory)"""
    print(f"🔧 Initializing RAG components for workspace: {workspace_id}")

    # Validate external storage configuration
    from storage.storage_factory import validate_external_storage_config
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
        print(f"✨ Creating new RAGAnything instance...")
        rag_anything = RAGAnything(
            lightrag=lightrag_instance,
            llm_model_func=llm_model_func,
            vision_model_func=vision_model_func,
            config=config,
        )
        print(f"✨ RAGAnything instance created successfully")

    except Exception as e:
        error_msg = f"Failed to create RAG instance for workspace {workspace_id}: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"🔍 Exception details: {type(e).__name__}: {str(e)}")
        raise HTTPException(500, error_msg)

    return rag_anything

async def create_workspace_service(name: str, description: str = "") -> dict:
    """Create a new workspace with RAG initialization and database persistence"""
    print(f"🆕 Creating new workspace")
    print(f"📝 Name: {name}")
    print(f"📄 Description: {description}")

    workspace_id = None
    
    try:
        # Step 1: Save to database first to get the ID
        try:
            from repos.workspaces import create_workspace as db_create_workspace
            db_workspace = db_create_workspace(name, description or "")
            workspace_id = db_workspace['id']
            print(f"💾 Workspace saved to database with ID: {workspace_id}")
        except Exception as db_error:
            print(f"⚠️  Database save failed: {db_error} - using UUID fallback")
            workspace_id = str(uuid.uuid4())
            print(f"🔄 Generated UUID fallback: {workspace_id}")

        print(f"🆔 Using workspace ID: {workspace_id}")

        # Step 2: Create workspace directories using the database ID
        paths = ensure_workspace_dirs(workspace_id)
        print(f"📁 Created workspace paths: {paths}")

        # Step 3: Initialize empty document mapping
        init_workspace_docs(workspace_id)
        print(f"📋 Initialized empty document mapping")

        # Step 4: Initialize workspace setup and cache RAG instance
        print(f"🚀 Setting up workspace structure and initializing RAG...")
        # Initialize RAG and set as current workspace (user just created it, they'll likely use it next)
        await get_or_create_workspace_rag(workspace_id)
        # Rebuild document mapping
        rebuild_workspace_docs_mapping(workspace_id)
        print(f"✅ Workspace setup and RAG initialization completed")

    except Exception as e:
        print(f"❌ Error during workspace creation: {str(e)}")
        # Clean up on failure
        if workspace_id:
            remove_workspace_docs(workspace_id)
        raise

    # Return workspace info
    return {
        "ok": True,
        "workspace": {
            "id": workspace_id,
            "name": name,
            "description": description,
            "created_at": "now",  # Will be replaced with actual timestamp
            "document_count": 0,
            "storage_mode": "external",
        },
    }

async def delete_workspace_service(workspace_id: str) -> dict:
    """Delete entire workspace from external storage, memory, and database"""
    # Check if workspace exists in database
    try:
        from repos.workspaces import get_workspace as db_get_workspace
        db_workspace = db_get_workspace(workspace_id)
        if not db_workspace:
            raise HTTPException(404, "Workspace not found")
    except Exception as e:
        print(f"⚠️  Database check failed: {e}")
        raise HTTPException(404, "Workspace not found")

    try:
        # Create RAG instance to perform deletion
        rag = await get_or_create_workspace_rag(workspace_id)
        deletion_result = await delete_workspace_data(rag.lightrag, workspace_id)
        print(f"🗑️ External storage cleanup result: {deletion_result}")

        # Clear current workspace cache if we're deleting the current workspace
        from core.state import get_current_workspace_id
        if get_current_workspace_id() == workspace_id:
            clear_current_workspace()
            print(f"🗑️ Cleared current workspace cache")

        # Remove from memory
        remove_workspace_docs(workspace_id)

        # Remove physical directory (uploads/temp files)
        paths = ensure_workspace_dirs(workspace_id)
        if os.path.exists(paths["workspace_dir"]):
            shutil.rmtree(paths["workspace_dir"])

        # Delete from database
        try:
            from repos.workspaces import delete_workspace as db_delete_workspace
            db_deleted = db_delete_workspace(workspace_id)
            if db_deleted:
                print(f"💾 Workspace {workspace_id} deleted from database")
            else:
                print(f"⚠️  Workspace {workspace_id} not found in database")
        except Exception as db_error:
            print(f"⚠️  Database deletion failed: {db_error} - continuing")

        return {"ok": True, "message": f"Workspace {workspace_id} deleted successfully"}

    except Exception as e:
        raise HTTPException(500, f"Error deleting workspace: {str(e)}")

async def get_workspace_info(workspace_id: str) -> dict:
    """Get workspace details from database and merge with in-memory data"""
    try:
        # Try to get from database first
        from repos.workspaces import get_workspace as db_get_workspace
        db_workspace = db_get_workspace(workspace_id)
        
        if db_workspace:
            doc_count = get_workspace_doc_count(workspace_id)
            
            # Initialize RAG for this workspace (user is accessing it, likely will use it)
            await get_or_create_workspace_rag(workspace_id)
            
            return {
                "id": db_workspace["id"],
                "name": db_workspace["name"],
                "description": db_workspace["description"],
                "document_count": doc_count,
                "storage_mode": "external",
                "status": "active",  # All database workspaces are considered active
                "created_at": db_workspace["created_at"],
                "updated_at": db_workspace["updated_at"],
            }
        
    except Exception as e:
        print(f"⚠️  Database query failed: {e} - checking memory only")
    
    # If not found in database, workspace doesn't exist
    raise HTTPException(404, "Workspace not found")

def list_workspaces_service() -> list[dict]:
    """List all workspaces from database and merge with in-memory data"""
    try:
        # Get workspaces from database
        from repos.workspaces import list_workspaces as db_list_workspaces
        db_workspaces = db_list_workspaces()
        print(f"📊 Found {len(db_workspaces)} workspaces in database")
        
        workspaces_list = []
        for db_ws in db_workspaces:
            doc_count = get_workspace_doc_count(db_ws["id"])
            
            workspace_info = {
                "id": db_ws["id"],
                "name": db_ws["name"],
                "description": db_ws["description"],
                "document_count": doc_count,
                "storage_mode": "external",
                "status": "active",  # All database workspaces are considered active
                "created_at": db_ws["created_at"],
                "updated_at": db_ws["updated_at"],
            }
            workspaces_list.append(workspace_info)
                
        return workspaces_list
        
    except Exception as e:
        print(f"⚠️  Database query failed: {e} - returning empty list")
        return []
