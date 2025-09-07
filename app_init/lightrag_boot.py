"""
Bootstrap helpers for per-workspace LightRAG initialization.
Provides clean interface for creating workspace-specific RAG instances.
"""

import os
from pathlib import Path
from storage.storage_factory import build_lightrag, validate_external_storage_config

WORKDIR_BASE = os.getenv("WORKDIR_BASE", "./workspaces")

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
