import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")


def get_sb() -> Client:
    """Get Supabase client instance"""
    if not SUPABASE_URL:
        raise RuntimeError("Missing SUPABASE_URL env var")
    if not SUPABASE_ANON_KEY:
        raise RuntimeError("Missing SUPABASE_ANON_KEY env var")
    # Using a dummy key since we disabled RLS
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
