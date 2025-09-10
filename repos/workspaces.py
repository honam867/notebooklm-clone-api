from typing import Optional, Dict, Any, List
from supabase import Client
from infra.supabase_client import get_sb

def create_workspace(name: str, description: str = "") -> Dict[str, Any]:
    sb: Client = get_sb()
    res = sb.table("workspaces").insert({
        "name": name,
        "description": description
    }).execute()
    return res.data[0] if res.data else None

def get_workspace(workspace_id: str) -> Optional[Dict[str, Any]]:
    sb = get_sb()
    res = sb.table("workspaces").select("*").eq("id", workspace_id).execute()
    return res.data[0] if res.data else None

def list_workspaces(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    sb = get_sb()
    # paginate with range(start, end) inclusive
    start, end = offset, offset + limit - 1
    res = (sb.table("workspaces")
             .select("*")
             .order("created_at", desc=True)
             .range(start, end)
             .execute())
    return res.data or []

def update_workspace(workspace_id: str, **patch) -> Optional[Dict[str, Any]]:
    if not patch:
        return get_workspace(workspace_id)
    sb = get_sb()
    res = (sb.table("workspaces")
             .update(patch)
             .eq("id", workspace_id)
             .execute())
    return res.data[0] if res.data else None

def delete_workspace(workspace_id: str) -> bool:
    sb = get_sb()
    res = sb.table("workspaces").delete().eq("id", workspace_id).execute()
    return (res.count or 0) > 0
