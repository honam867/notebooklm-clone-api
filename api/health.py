"""
Health check endpoints for external storage services.
Monitors Neo4j, Chroma, and Supabase Postgres connectivity.
"""

import os
import asyncio
from fastapi import APIRouter, HTTPException
import httpx
from neo4j import AsyncGraphDatabase
import asyncpg

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Environment variables from system only.")
    pass


# All imports for external storage health checks

router = APIRouter(prefix="/healthz", tags=["health"])


@router.get("/")
async def health_overview():
    """Overall health status of the RAG API with external storage"""
    # Check all external services in parallel
    checks = await asyncio.gather(
        check_chroma_health(),
        check_neo4j_health(),
        check_postgres_health(),
        return_exceptions=True,
    )

    chroma_ok = not isinstance(checks[0], Exception)
    neo4j_ok = not isinstance(checks[1], Exception)
    postgres_ok = not isinstance(checks[2], Exception)

    all_healthy = chroma_ok and neo4j_ok and postgres_ok

    return {
        "status": "healthy" if all_healthy else "degraded",
        "storage_mode": "external",
        "services": {
            "chroma": "healthy" if chroma_ok else "unhealthy",
            "neo4j": "healthy" if neo4j_ok else "unhealthy",
            "postgres": "healthy" if postgres_ok else "unhealthy",
        },
        "details": {
            "chroma": str(checks[0]) if isinstance(checks[0], Exception) else "OK",
            "neo4j": str(checks[1]) if isinstance(checks[1], Exception) else "OK",
            "postgres": str(checks[2]) if isinstance(checks[2], Exception) else "OK",
        },
    }


@router.get("/chroma")
async def chroma_health():
    """Check Chroma vector database health"""
    try:
        result = await check_chroma_health()
        return {"status": "healthy", "details": result}
    except Exception as e:
        raise HTTPException(503, f"Chroma health check failed: {str(e)}")


@router.get("/neo4j")
async def neo4j_health():
    """Check Neo4j graph database health"""
    try:
        result = await check_neo4j_health()
        return {"status": "healthy", "details": result}
    except Exception as e:
        raise HTTPException(503, f"Neo4j health check failed: {str(e)}")


@router.get("/postgres")
async def postgres_health():
    """Check Supabase Postgres health"""
    try:
        result = await check_postgres_health()
        return {"status": "healthy", "details": result}
    except Exception as e:
        raise HTTPException(503, f"Postgres health check failed: {str(e)}")


# Internal health check functions


async def check_chroma_health() -> dict:
    """Internal Chroma health check"""
    chroma_host = os.getenv("CHROMA_HOST")
    chroma_port = os.getenv("CHROMA_PORT", "8000")

    if not chroma_host:
        raise Exception("CHROMA_HOST not configured")

    # Build URL based on port (assume HTTPS for 443, HTTP otherwise)
    protocol = "https" if chroma_port == "443" else "http"
    url = f"{protocol}://{chroma_host}:{chroma_port}/api/v1/heartbeat"

    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()

        return {
            "url": url,
            "status_code": response.status_code,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
            "body": response.text,
        }


async def check_neo4j_health() -> dict:
    """Internal Neo4j health check"""
    try:

        uri = os.getenv("NEO4J_URI")
        print(f"NEO4J_URI: {uri}")
        username = os.getenv("NEO4J_USERNAME")
        print(f"NEO4J_USERNAME: {username}")
        password = os.getenv("NEO4J_PASSWORD")
        print(f"NEO4J_PASSWORD: {'***' if password else None}")

        if not all([uri, username, password]):
            missing = []
            if not uri: missing.append("NEO4J_URI")
            if not username: missing.append("NEO4J_USERNAME") 
            if not password: missing.append("NEO4J_PASSWORD")
            raise Exception(f"Neo4j configuration incomplete. Missing: {', '.join(missing)}")

        driver = AsyncGraphDatabase.driver(uri, auth=(username, password))

        async with driver.session() as session:
            result = await session.run("RETURN 1 as health_check")
            record = await result.single()

        await driver.close()

        return {
            "uri": uri,
            "connection": "successful",
            "health_check_result": record["health_check"],
        }

    except ImportError:
        raise Exception("neo4j driver not installed (pip install neo4j)")
    except Exception as e:
        raise Exception(f"Neo4j connection failed: {str(e)}")


async def check_postgres_health() -> dict:
    """Internal Postgres health check"""
    try:

        postgres_uri = os.getenv("POSTGRES_URI")
        if not postgres_uri:
            raise Exception("POSTGRES_URI not configured")

        conn = await asyncpg.connect(postgres_uri)

        # Simple health check query
        result = await conn.fetchval("SELECT 1")
        version = await conn.fetchval("SELECT version()")

        await conn.close()

        return {
            "connection": "successful",
            "health_check_result": result,
            "postgres_version": version.split()[0:2] if version else "unknown",
        }

    except ImportError:
        raise Exception("asyncpg not installed (pip install asyncpg)")
    except Exception as e:
        raise Exception(f"Postgres connection failed: {str(e)}")


# Add main execution block to run as standalone FastAPI server
if __name__ == "__main__":
    from fastapi import FastAPI
    import uvicorn

    # Create FastAPI application
    app = FastAPI(
        title="LightRAG Health Check API",
        description="Health check endpoints for LightRAG external storage services",
        version="1.0.0",
    )

    # Include the health router
    app.include_router(router)

    # Add root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with basic information."""
        return {
            "message": "LightRAG Health Check API",
            "endpoints": {
                "health_overview": "/healthz/",
                "chroma_health": "/healthz/chroma",
                "neo4j_health": "/healthz/neo4j",
                "postgres_health": "/healthz/postgres",
                "docs": "/docs",
                "redoc": "/redoc",
            },
        }

    print("🏥 Starting LightRAG Health Check API...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Overview: http://localhost:8000/healthz/")
    print("⚠️  Note: Install dependencies first: pip install neo4j asyncpg")

    uvicorn.run(app, host="0.0.0.0", port=8070, log_level="info")
