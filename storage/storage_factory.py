"""
Storage factory for LightRAG instances with external storage backends.
Supports both local (development) and external (production) storage modes.
"""

import os
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc
from lightrag.llm.openai import openai_embed, openai_complete_if_cache
from lightrag.kg.shared_storage import initialize_pipeline_status

# Configuration from environment
EMBED_DIM = int(os.getenv("EMBED_DIM", "3072"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")

LLM_BINDING_API_KEY = os.getenv("LLM_BINDING_API_KEY")
LLM_BINDING_HOST = os.getenv("LLM_BINDING_HOST")

LIGHTRAG_GRAPH_STORAGE = os.getenv("LIGHTRAG_GRAPH_STORAGE")
# LIGHTRAG_KV_STORAGE=os.getenv("LIGHTRAG_KV_STORAGE")
# LIGHTRAG_VECTOR_STORAGE=os.getenv("LIGHTRAG_VECTOR_STORAGE")
# LIGHTRAG_DOC_STATUS_STORAGE=os.getenv("LIGHTRAG_DOC_STATUS_STORAGE")


def create_embedding_func():
    """Create embedding function for LightRAG"""
    return EmbeddingFunc(
        embedding_dim=EMBED_DIM,
        max_token_size=8192,
        func=lambda texts: openai_embed(
            texts,
            model=EMBED_MODEL,
            api_key=LLM_BINDING_API_KEY,
            base_url=LLM_BINDING_HOST or None,
        ),
    )


def create_llm_model_func():
    """Create LLM model function for LightRAG"""
    print("✨ Check OPEN AI API KEY", LLM_BINDING_API_KEY, LLM_BINDING_HOST)

    def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return openai_complete_if_cache(
            "gpt-4o-mini",
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=LLM_BINDING_API_KEY,
            base_url=LLM_BINDING_HOST,
            **kwargs,
        )

    return llm_model_func


async def build_lightrag(workspace_dir: str, workspace_id: str) -> LightRAG:
    print(
        f"✨ Building LightRAG instance for workspace_dir: {workspace_dir}, workspace_id: {workspace_id}"
    )

    """
    Build a LightRAG instance with external storage backends.

    Args:
        workspace_dir: Working directory for temp/cache files only
        workspace_id: Workspace identifier for namespacing

    Returns:
        Configured LightRAG instance with external storage
    """
    # Create LightRAG instance with basic configuration
    # Storage configuration is handled via environment variables
    rag = LightRAG(
        working_dir=workspace_dir,
        workspace=workspace_id,
        llm_model_func=create_llm_model_func(),
        embedding_func=create_embedding_func(),
        graph_storage=LIGHTRAG_GRAPH_STORAGE,
        # vector_storage=LIGHTRAG_VECTOR_STORAGE,
        # doc_status_storage=LIGHTRAG_DOC_STATUS_STORAGE,
    )
    # Initialize storages (LightRAG will read storage config from environment variables)
    await rag.initialize_storages()
    await initialize_pipeline_status()
    print(f"✨ LightRAG instance built successfully for workspace: {workspace_id}")
    return rag


def validate_external_storage_config() -> list[str]:
    """
    Validate external storage configuration.
    Returns list of missing environment variables.
    """
    missing = []

    # Required for all external storage
    required_vars = [
        "LLM_BINDING_API_KEY",
        "NEO4J_URI",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
        "POSTGRES_URI",
    ]

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    # Chroma requires either HOST or DIR
    # if not os.getenv("CHROMA_HOST") and not os.getenv("CHROMA_DIR"):
    #     missing.append("CHROMA_HOST or CHROMA_DIR")

    return missing
