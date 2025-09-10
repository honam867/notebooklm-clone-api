"""
Database initialization module with automatic schema creation
Uses direct PostgreSQL connection for better SQL support
"""

import os
import asyncio
import psycopg2


def get_postgres_connection_params():
    """Get PostgreSQL connection parameters from environment variables"""
    # Use the same env vars as health.py
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DATABASE")

    # Check for required parameters
    if not all([host, user, password, database]):
        missing = []
        if not host:
            missing.append("POSTGRES_HOST")
        if not user:
            missing.append("POSTGRES_USER")
        if not password:
            missing.append("POSTGRES_PASSWORD")
        if not database:
            missing.append("POSTGRES_DATABASE")
        raise RuntimeError(
            f"PostgreSQL configuration incomplete. Missing: {', '.join(missing)}"
        )

    return {
        "host": host,
        "port": int(port),
        "database": database,
        "user": user,
        "password": password,
    }


async def initialize_database_with_postgres():
    """Initialize database schema using direct PostgreSQL connection"""
    print("🔍 Checking database schema with PostgreSQL...")

    try:
        conn_params = get_postgres_connection_params()

        # Connection params are already validated in get_postgres_connection_params()

        # Connect to PostgreSQL
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()

        # Check if workspaces table exists
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'workspaces'
            );
        """
        )

        table_exists = cursor.fetchone()[0]

        if table_exists:
            print("✅ Database schema already exists")
            cursor.close()
            conn.close()
            return True

        print("📋 Creating database schema...")

        # Create the schema
        schema_sql = """
        -- Extensions (usually enabled by default)
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- Workspaces table
        CREATE TABLE IF NOT EXISTS public.workspaces (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          name text NOT NULL,
          description text NOT NULL DEFAULT '',
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        -- Disable RLS (allows public access)
        ALTER TABLE public.workspaces DISABLE ROW LEVEL SECURITY;

        -- Optional: helpful view for workspace summaries
        CREATE OR REPLACE VIEW public.workspace_summaries AS
        SELECT w.*
        FROM public.workspaces w;
        """

        cursor.execute(schema_sql)
        conn.commit()

        print("✅ Database schema created successfully!")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"❌ PostgreSQL error: {str(e)}")
        print("💡 Please check your database credentials and connection")
        return False
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False


async def initialize_database():
    """Main database initialization function"""
    print("🚀 Starting database initialization...")

    # Try with direct PostgreSQL connection (more reliable)
    if await initialize_database_with_postgres():
        return True

    # If PostgreSQL connection failed, just print simple message
    print(
        "⚠️  Database schema initialization failed - continuing without database persistence"
    )
    print("💡 App will run in file-only mode. Database features will be unavailable.")

    return False


if __name__ == "__main__":
    # For testing
    asyncio.run(initialize_database())
