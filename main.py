"""
Main FastAPI application entry point.
Modular architecture with database integration.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

# Import route modules
from routes.workspace_routes import router as workspace_router
from routes.document_routes import router as document_router
from routes.chat_routes import router as chat_router
from api.health import router as health_router

# Import startup/shutdown logic
from core.startup import startup_initialize, shutdown_cleanup

# Load environment variables
load_dotenv(dotenv_path=".env", override=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_initialize()
    yield
    # Shutdown
    await shutdown_cleanup()

# Create FastAPI application
app = FastAPI(
    title="RAG API",
    description="Modular RAG API with Supabase database integration",
    version="2.0.0",
    lifespan=lifespan
)

# Include all routers
app.include_router(workspace_router)
app.include_router(document_router) 
app.include_router(chat_router)
app.include_router(health_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG API - Modular Architecture",
        "version": "2.0.0",
        "endpoints": {
            "workspaces": "/workspaces",
            "documents": "/workspaces/{id}/documents", 
            "chat": "/workspaces/{id}/chat",
            "health": "/healthz",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
