"""
Health check endpoints for external storage services.
Monitors Neo4j and Supabase Postgres connectivity.
"""

import os
import sys
import asyncio
from fastapi import APIRouter, HTTPException
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

# Setup project path for imports - DO THIS ONCE AT MODULE LEVEL
def setup_project_imports():
    """Add project root to Python path for infra module imports"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Call setup once when module loads
setup_project_imports()


# All imports for external storage health checks

router = APIRouter(prefix="/healthz", tags=["health"])


@router.get("/")
async def health_overview():
    """Overall health status of the RAG API with external storage and database schema"""
    # Check all external services and database schema in parallel
    checks = await asyncio.gather(
        check_neo4j_health(),
        check_postgres_health(),
        check_database_schema(),
        return_exceptions=True,
    )

    neo4j_ok = not isinstance(checks[0], Exception)
    postgres_ok = not isinstance(checks[1], Exception)
    schema_ok = not isinstance(checks[2], Exception)

    all_healthy = neo4j_ok and postgres_ok and schema_ok

    return {
        "status": "healthy" if all_healthy else "degraded",
        "storage_mode": "external",
        "services": {
            "neo4j": "healthy" if neo4j_ok else "unhealthy",
            "supabase": "healthy" if postgres_ok else "unhealthy",
            "database_schema": "healthy" if schema_ok else "unhealthy",
        },
        "details": {
            "neo4j": str(checks[0]) if isinstance(checks[0], Exception) else "OK",
            "supabase": str(checks[1]) if isinstance(checks[1], Exception) else "OK", 
            "database_schema": str(checks[2]) if isinstance(checks[2], Exception) else "OK",
        },
        "endpoints": {
            "database_init": "/healthz/database-init",
            "workspaces_table": "/healthz/workspaces-table",
            "postgres": "/healthz/postgres",
            "neo4j": "/healthz/neo4j",
        }
    }


@router.get("/supabase")
async def supabase_health():
    """Check Supabase Postgres health"""
    try:
        result = await check_postgres_health()
        return {"status": "healthy", "details": result}
    except Exception as e:
        raise HTTPException(503, f"Supabase health check failed: {str(e)}")


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
    """Check Supabase Postgres health (alias for /supabase)"""
    try:
        result = await check_postgres_health()
        return {"status": "healthy", "details": result}
    except Exception as e:
        raise HTTPException(503, f"Postgres health check failed: {str(e)}")


@router.get("/database-init")
async def database_init_health():
    """Check database schema initialization status"""
    try:
        from infra.db_init import initialize_database
        
        print("🔍 Running database initialization health check...")
        db_ready = await initialize_database()
        
        if db_ready:
            return {
                "status": "healthy",
                "schema_status": "initialized",
                "message": "Database schema is properly initialized"
            }
        else:
            return {
                "status": "degraded", 
                "schema_status": "missing",
                "message": "Database schema initialization failed",
                "action_required": "Check database connection and credentials"
            }
            
    except Exception as e:
        raise HTTPException(503, f"Database initialization check failed: {str(e)}")


@router.get("/workspaces-table")
async def workspaces_table_health():
    """Check if workspaces table exists and is accessible"""
    try:
        from infra.supabase_client import get_sb
        
        sb = get_sb()
        
        # Try to query the workspaces table
        result = sb.table("workspaces").select("id").limit(1).execute()
        
        # Count total workspaces
        count_result = sb.table("workspaces").select("id", count="exact").execute()
        total_workspaces = count_result.count or 0
        
        return {
            "status": "healthy",
            "table_status": "accessible",
            "total_workspaces": total_workspaces,
            "message": "Workspaces table is accessible via Supabase client"
        }
        
    except Exception as e:
        raise HTTPException(503, f"Workspaces table check failed: {str(e)}")


# Internal health check functions


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


async def check_database_schema() -> dict:
    """Internal database schema health check"""
    try:
        from infra.supabase_client import get_sb
        
        sb = get_sb()
        
        # Try to query the workspaces table to check if schema exists
        result = sb.table("workspaces").select("id").limit(1).execute()
        
        # Count total workspaces
        count_result = sb.table("workspaces").select("id", count="exact").execute()
        total_workspaces = count_result.count or 0
        
        return {
            "schema_status": "initialized",
            "workspaces_table": "accessible",
            "total_workspaces": total_workspaces,
        }
        
    except Exception as e:
        raise Exception(f"Database schema check failed: {str(e)}")


async def check_postgres_health() -> dict:
    """Internal Supabase Postgres health check using individual environment variables"""
    try:
        # Get individual connection parameters
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        database = os.getenv("POSTGRES_DATABASE")
        max_connections = os.getenv("POSTGRES_MAX_CONNECTIONS", "12")

        print(f"POSTGRES_HOST: {host}")
        print(f"POSTGRES_PORT: {port}")
        print(f"POSTGRES_USER: {user}")
        print(f"POSTGRES_PASSWORD: {'***' if password else None}")
        print(f"POSTGRES_DATABASE: {database}")
        print(f"POSTGRES_MAX_CONNECTIONS: {max_connections}")

        # Check for required parameters
        if not all([host, user, password, database]):
            missing = []
            if not host: missing.append("POSTGRES_HOST")
            if not user: missing.append("POSTGRES_USER")
            if not password: missing.append("POSTGRES_PASSWORD")
            if not database: missing.append("POSTGRES_DATABASE")
            raise Exception(f"Supabase configuration incomplete. Missing: {', '.join(missing)}")

        # Build connection string
        postgres_uri = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        # Connect and run health checks
        conn = await asyncpg.connect(postgres_uri)

        # Simple health check query
        result = await conn.fetchval("SELECT 1")
        version = await conn.fetchval("SELECT version()")
        
        # Check current connections
        current_connections = await conn.fetchval(
            "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
        )

        await conn.close()

        return {
            "connection": "successful",
            "host": host,
            "port": int(port),
            "database": database,
            "health_check_result": result,
            "postgres_version": version.split()[0:2] if version else "unknown",
            "max_connections": int(max_connections),
            "current_active_connections": current_connections,
        }

    except ImportError:
        raise Exception("asyncpg not installed (pip install asyncpg)")
    except Exception as e:
        raise Exception(f"Supabase connection failed: {str(e)}")


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
                "supabase_health": "/healthz/supabase",
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
