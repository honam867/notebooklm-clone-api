"""
Bootstrap helpers for per-workspace LightRAG initialization.
Provides clean interface for creating workspace-specific RAG instances.
"""

import os
from pathlib import Path
from storage.storage_factory import build_lightrag, validate_external_storage_config

WORKDIR_BASE = os.getenv("WORKDIR_BASE", "./workspaces")

# def init_storage_system():
#     """Set up global storage environment variables (called once at startup)"""
#     print("✨ Setting up global storage environment variables")

#     # Configure storage types via environment variables
#     os.environ["LIGHTRAG_GRAPH_STORAGE"] = "Neo4JStorage"
#     os.environ["LIGHTRAG_VECTOR_STORAGE"] = "ChromaVectorDBStorage"
#     os.environ["LIGHTRAG_KV_STORAGE"] = "PGKVStorage"
#     os.environ["LIGHTRAG_DOC_STATUS_STORAGE"] = "PGDocStatusStorage"

#     # Neo4j configuration - these are global connection settings
#     neo4j_uri = os.getenv("NEO4J_URI")
#     neo4j_username = os.getenv("NEO4J_USERNAME")
#     neo4j_password = os.getenv("NEO4J_PASSWORD")

#     if neo4j_uri and neo4j_username and neo4j_password:
#         os.environ["NEO4J_URI"] = neo4j_uri
#         os.environ["NEO4J_USERNAME"] = neo4j_username
#         os.environ["NEO4J_PASSWORD"] = neo4j_password

#     # Chroma configuration - global connection settings
#     chroma_host = os.getenv("CHROMA_HOST")
#     if chroma_host:
#         os.environ["CHROMA_HOST"] = chroma_host
#         os.environ["CHROMA_PORT"] = os.getenv("CHROMA_PORT", "8000")
#     else:
#         chroma_dir = os.getenv("CHROMA_DIR")
#         if chroma_dir:
#             os.environ["CHROMA_DIR"] = chroma_dir

#     # PostgreSQL configuration - global connection settings
#     postgres_uri = os.getenv("POSTGRES_URI")
#     if postgres_uri:
#         os.environ["POSTGRES_URI"] = postgres_uri

#     print("🔗 Global storage environment variables configured")


# def setup_workspace_storage_env(workspace_id: str):
#     """Set up workspace-specific storage environment variables"""
#     print(f"🔧 Setting up workspace-specific storage env for: {workspace_id}")

#     # Neo4j workspace isolation
#     os.environ["NEO4J_WORKSPACE"] = workspace_id

#     # Chroma workspace isolation via collection name
#     os.environ["CHROMA_COLLECTION_NAME"] = f"vectors_{workspace_id}"

#     # PostgreSQL workspace isolation
#     os.environ["POSTGRES_WORKSPACE"] = workspace_id

#     print(f"✅ Workspace storage env configured for: {workspace_id}")


async def init_workspace_lightrag(workspace_id: str):
    """
    Initialize LightRAG instance for a specific workspace with external storage.

    Args:
        workspace_id: Unique workspace identifier

    Returns:
        Configured LightRAG instance with external storage

    Raises:
        ValueError: If external storage configuration is invalid
    """
    # Validate external storage configuration
    missing_vars = validate_external_storage_config()
    if missing_vars:
        raise ValueError(
            f"External storage configuration incomplete. Missing: {', '.join(missing_vars)}"
        )

    ws_dir = Path(WORKDIR_BASE) 
    ws_dir.mkdir(parents=True, exist_ok=True)

    # Build LightRAG instance with external storage backends
    rag = await build_lightrag(str(ws_dir), workspace_id)

    return rag

def ensure_workspace_dirs(workspace_id: str) -> dict:
    """
    Ensure necessary workspace directories exist for file uploads and processing.
    Returns dictionary with all workspace paths. Data storage is external.
    """
    base_dir = Path(WORKDIR_BASE) / workspace_id

    paths = {
        "workspace_dir": str(base_dir),
        "uploads": str(base_dir / "uploads"),  # For uploaded files
        "output": str(base_dir / "output"),  # For processed documents
    }

    # Create directories
    for path in paths.values():
        Path(path).mkdir(parents=True, exist_ok=True)

    return paths
