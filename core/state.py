"""
Global state management for RAG workspaces.
Centralized storage for document mappings and current workspace cache.
"""

from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from raganything import RAGAnything

# Global variables
workspace_docs: Dict[str, Dict[str, str]] = {}  # workspace_id -> {doc_id: file_path}

# Single workspace cache - only store currently active workspace
current_workspace_id: Optional[str] = None
current_workspace_rag: Optional["RAGAnything"] = None

def get_workspace_docs(workspace_id: str) -> Dict[str, str]:
    """Get document mapping for workspace"""
    return workspace_docs.get(workspace_id, {})

def add_workspace_doc(workspace_id: str, doc_id: str, file_path: str) -> None:
    """Add document to workspace mapping"""
    if workspace_id not in workspace_docs:
        workspace_docs[workspace_id] = {}
    workspace_docs[workspace_id][doc_id] = file_path

def remove_workspace_doc(workspace_id: str, doc_id: str) -> None:
    """Remove document from workspace mapping"""
    if workspace_id in workspace_docs and doc_id in workspace_docs[workspace_id]:
        del workspace_docs[workspace_id][doc_id]

def remove_workspace_docs(workspace_id: str) -> None:
    """Remove all documents for workspace"""
    if workspace_id in workspace_docs:
        del workspace_docs[workspace_id]

def init_workspace_docs(workspace_id: str) -> None:
    """Initialize empty document mapping for workspace"""
    workspace_docs[workspace_id] = {}


def get_workspace_doc_count(workspace_id: str) -> int:
    """Get document count for workspace"""
    return len(workspace_docs.get(workspace_id, {}))

# Current workspace cache management
def get_current_workspace_rag(workspace_id: str) -> Optional["RAGAnything"]:
    """Get cached RAG if same workspace, None if different/not cached"""
    if current_workspace_id == workspace_id and current_workspace_rag:
        return current_workspace_rag
    return None

def set_current_workspace_rag(workspace_id: str, rag: "RAGAnything") -> None:
    """Cache the current workspace RAG instance"""
    global current_workspace_id, current_workspace_rag
    current_workspace_id = workspace_id
    current_workspace_rag = rag

def clear_current_workspace() -> None:
    """Clear current workspace cache"""
    global current_workspace_id, current_workspace_rag
    current_workspace_id = None
    current_workspace_rag = None

def get_current_workspace_id() -> Optional[str]:
    """Get current cached workspace ID"""
    return current_workspace_id
