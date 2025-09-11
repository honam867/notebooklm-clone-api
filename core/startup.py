"""
Application startup and shutdown logic.
Handles database initialization and workspace RAG setup.
"""

import os
from storage.storage_factory import validate_external_storage_config

BASE_WORKSPACES_DIR = os.getenv("WORKSPACES_DIR", "./workspaces")

async def startup_initialize():
    """Initialize system at startup with external storage and database"""

    # Step 1: Initialize database schema
    print("🔧 Initializing database...")
    try:
        from infra.db_init import initialize_database
        db_ready = await initialize_database()
        if not db_ready:
            print("⚠️  Database initialization incomplete - app will run without database persistence")
    except Exception as e:
        print(f"⚠️  Database initialization failed: {e}")
        print("📝 App will continue without database persistence")

    # Step 2: Validate external storage configuration
    missing_vars = validate_external_storage_config()
    if missing_vars:
        print(
            f"❌ External storage configuration incomplete. Missing: {', '.join(missing_vars)}"
        )
        print("💡 Please configure all required environment variables and restart")
        return

    print(
        f"🚀 Startup complete. RAG instances will be created on-demand for each request."
    )

async def shutdown_cleanup():
    """Cleanup resources on shutdown"""
    # Add any cleanup logic here if needed
    print("🛑 Shutting down gracefully...")
    pass
