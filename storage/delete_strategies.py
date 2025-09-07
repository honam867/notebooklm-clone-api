"""
Unified document deletion strategies for all storage backends.
Handles cleanup across Neo4j, Chroma, and Postgres storages.
"""
from typing import Optional
import asyncio

async def delete_document_everywhere(rag, doc_id: str) -> dict:
    """
    Purge a document from all storages (graph, vector, KV, doc status).
    
    Args:
        rag: LightRAG instance (or RAGAnything.lightrag)
        doc_id: Document ID to delete
        
    Returns:
        Dictionary with deletion results for each storage type
    """
    results = {
        "doc_id": doc_id,
        "vector_storage": {"success": False, "error": None},
        "graph_storage": {"success": False, "error": None},
        "kv_storage": {"success": False, "error": None},
        "doc_status": {"success": False, "error": None},
    }
    
    # Delete from vector store
    try:
        if hasattr(rag, 'vector_storage') and hasattr(rag.vector_storage, 'delete_by_doc_id'):
            await rag.vector_storage.delete_by_doc_id(doc_id)
            results["vector_storage"]["success"] = True
        elif hasattr(rag, 'adelete_by_doc_id'):
            # Fallback to general delete method
            await rag.adelete_by_doc_id(doc_id)
            results["vector_storage"]["success"] = True
    except Exception as e:
        results["vector_storage"]["error"] = str(e)
        print(f"❌ Error deleting from vector storage: {e}")
    
    # Delete from graph store
    try:
        if hasattr(rag, 'graph_storage') and hasattr(rag.graph_storage, 'delete_by_doc_id'):
            await rag.graph_storage.delete_by_doc_id(doc_id)
            results["graph_storage"]["success"] = True
        elif hasattr(rag, 'delete_graph_entities_by_doc_id'):
            await rag.delete_graph_entities_by_doc_id(doc_id)
            results["graph_storage"]["success"] = True
    except Exception as e:
        results["graph_storage"]["error"] = str(e)
        print(f"❌ Error deleting from graph storage: {e}")
    
    # Delete from KV store
    try:
        if hasattr(rag, 'kv_storage') and hasattr(rag.kv_storage, 'delete_by_doc_id'):
            await rag.kv_storage.delete_by_doc_id(doc_id)
            results["kv_storage"]["success"] = True
        elif hasattr(rag, 'kv_delete_profiles_by_doc_id'):
            await rag.kv_delete_profiles_by_doc_id(doc_id)
            results["kv_storage"]["success"] = True
    except Exception as e:
        results["kv_storage"]["error"] = str(e)
        print(f"❌ Error deleting from KV storage: {e}")
    
    # Update document status
    try:
        if hasattr(rag, 'doc_status_storage') and hasattr(rag.doc_status_storage, 'mark_deleted'):
            await rag.doc_status_storage.mark_deleted(doc_id)
            results["doc_status"]["success"] = True
        elif hasattr(rag, 'mark_doc_deleted'):
            await rag.mark_doc_deleted(doc_id)
            results["doc_status"]["success"] = True
    except Exception as e:
        results["doc_status"]["error"] = str(e)
        print(f"❌ Error updating document status: {e}")
    
    # Clear caches
    try:
        if hasattr(rag, 'aclear_cache'):
            await rag.aclear_cache()
    except Exception as e:
        print(f"⚠️ Warning: Could not clear cache: {e}")
    
    # Summary
    successful_deletions = sum(1 for result in results.values() if isinstance(result, dict) and result.get("success"))
    total_storages = len([k for k in results.keys() if k != "doc_id"])
    
    print(f"🗑️ Document {doc_id} deletion: {successful_deletions}/{total_storages} storages updated")
    
    return results

async def delete_workspace_data(rag, workspace_id: str) -> dict:
    """
    Delete all data for a workspace from external storages.
    
    Args:
        rag: LightRAG instance
        workspace_id: Workspace identifier
        
    Returns:
        Dictionary with cleanup results
    """
    results = {
        "workspace_id": workspace_id,
        "vector_cleanup": {"success": False, "error": None},
        "graph_cleanup": {"success": False, "error": None},
        "kv_cleanup": {"success": False, "error": None},
        "doc_status_cleanup": {"success": False, "error": None},
    }
    
    # Clean up vector storage (delete collection)
    try:
        if hasattr(rag, 'vector_storage'):
            collection_name = f"vectors_{workspace_id}"
            if hasattr(rag.vector_storage, 'delete_collection'):
                await rag.vector_storage.delete_collection(collection_name)
                results["vector_cleanup"]["success"] = True
    except Exception as e:
        results["vector_cleanup"]["error"] = str(e)
        print(f"❌ Error cleaning vector storage for workspace {workspace_id}: {e}")
    
    # Clean up graph storage (delete by workspace label)
    try:
        if hasattr(rag, 'graph_storage'):
            if hasattr(rag.graph_storage, 'delete_workspace'):
                await rag.graph_storage.delete_workspace(workspace_id)
                results["graph_cleanup"]["success"] = True
    except Exception as e:
        results["graph_cleanup"]["error"] = str(e)
        print(f"❌ Error cleaning graph storage for workspace {workspace_id}: {e}")
    
    # Clean up KV storage (delete by workspace)
    try:
        if hasattr(rag, 'kv_storage'):
            if hasattr(rag.kv_storage, 'delete_workspace'):
                await rag.kv_storage.delete_workspace(workspace_id)
                results["kv_cleanup"]["success"] = True
    except Exception as e:
        results["kv_cleanup"]["error"] = str(e)
        print(f"❌ Error cleaning KV storage for workspace {workspace_id}: {e}")
    
    # Clean up doc status storage
    try:
        if hasattr(rag, 'doc_status_storage'):
            if hasattr(rag.doc_status_storage, 'delete_workspace'):
                await rag.doc_status_storage.delete_workspace(workspace_id)
                results["doc_status_cleanup"]["success"] = True
    except Exception as e:
        results["doc_status_cleanup"]["error"] = str(e)
        print(f"❌ Error cleaning doc status for workspace {workspace_id}: {e}")
    
    return results
