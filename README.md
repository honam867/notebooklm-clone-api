# 🤖 RAG API - Intelligent Document Processing System

> **A powerful RAG (Retrieval-Augmented Generation) API built on LightRAG and RAG-Anything for intelligent document processing and question answering.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![LightRAG](https://img.shields.io/badge/LightRAG-Powered-orange.svg)](https://github.com/HKUDS/LightRAG)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

## 🌟 Overview

This project leverages **RAG-Anything** built on **LightRAG** to create a sophisticated document processing and question-answering system. It provides a complete RAG pipeline with support for multiple document formats, advanced parsing capabilities, and external storage backends.

### ✨ Key Features

- 🔍 **Multi-Modal Document Processing** - PDF, images, tables, and equations
- 🧠 **Intelligent Question Answering** - Hybrid search with multiple modes
- 🏢 **Multi-Workspace Support** - Isolated environments for different projects
- 🗄️ **External Storage Integration** - Neo4j, ChromaDB, and PostgreSQL support
- 🔄 **Real-time Processing** - Async document ingestion and querying
- 🏥 **Health Monitoring** - Comprehensive health checks for all services
- 🐳 **Docker Ready** - Easy deployment with Docker Compose
- 🚀 **Production Ready** - Built with FastAPI for high performance

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker & Docker Compose (optional)
- OpenAI API key or compatible LLM endpoint

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd rag-api
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in the project root:

```env
# LLM Configuration
LLM_BINDING_API_KEY=your_openai_api_key
LLM_BINDING_HOST=https://api.openai.com/v1

# External Storage - Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password

# External Storage - PostgreSQL (Supabase)
POSTGRES_HOST=your_project_host
POSTGRES_PORT=5432
POSTGRES_USER=postgres.your_project_ref
POSTGRES_PASSWORD='your_database_password'
POSTGRES_DATABASE=postgres
POSTGRES_MAX_CONNECTIONS=12

# Application Settings
WORKSPACES_DIR=./workspaces
PARSER=mineru
```

#### 📋 Steps to Access Your Supabase Postgres Credentials

1. **Open your Supabase project** in the [Supabase Dashboard](https://app.supabase.com/)

2. **Locate and click the "Connect" button** — typically found at the top of the database overview or project page

3. **In the connection modal**, look under **Connection Parameters** — you'll see fields for:

   - **Host** (e.g., `db.abcdefghijklmnop.supabase.co`)
   - **Port** (usually `5432`)
   - **Database name** (usually `postgres` by default)
   - **User** (format: `postgres.<project-ref>`)
   - **Password** (your project database password set during creation)

4. **Connection String Format**:

   ```
   postgres://postgres.<project-ref>:<PASSWORD>@<host-region>.pooler.supabase.com:5432/postgres
   ```

5. **Map to Environment Variables**:
   ```env
   POSTGRES_HOST=db.abcdefghijklmnop.supabase.co
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres.your_project_ref
   POSTGRES_PASSWORD='your_actual_database_password'
   POSTGRES_DATABASE=postgres
   POSTGRES_MAX_CONNECTIONS=12
   ```

> **💡 Note**: The `postgres` before the dot is the username (standard Supabase format), and `<PASSWORD>` is the actual database password you set during project creation. If you've forgotten it, you can reset it in the Supabase dashboard under Settings → Database.

### 3. Start External Services

You'll need to set up your external services:

**Option A: Use Supabase Cloud + Neo4j Cloud**

- Create a [Supabase project](https://app.supabase.com/) (recommended)
- Create a [Neo4j AuraDB instance](https://neo4j.com/cloud/aura/) or local Neo4j
- Configure your `.env` file with the credentials

**Option B: Local Neo4j with Docker**

```bash
# Start local Neo4j instance
cd ops
docker-compose up -d neo4j

# Or start all services including proxy
docker-compose --profile proxy up -d
```

> **💡 Recommended**: Use Supabase cloud for PostgreSQL as it provides managed vector extensions and better performance for RAG applications.

### 4. Run the Application

```bash
python workspaces.py
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Core Endpoints

#### Workspace Management

```http
POST   /workspaces                    # Create new workspace
GET    /workspaces                    # List all workspaces
GET    /workspaces/{id}               # Get workspace details
DELETE /workspaces/{id}               # Delete workspace
```

#### Document Operations

```http
POST   /workspaces/{id}/documents     # Upload documents
GET    /workspaces/{id}/documents     # List documents
DELETE /workspaces/{id}/documents/{doc_id}  # Delete document
```

#### Chat & Query

```http
POST   /workspaces/{id}/chat          # Ask questions (with optional file upload)
```

#### Health Monitoring

```http
GET    /healthz/                      # Overall system health
GET    /healthz/supabase              # Supabase PostgreSQL status
GET    /healthz/neo4j                 # Neo4j status
GET    /healthz/postgres              # PostgreSQL status (alias)
```

### Example Usage

#### Create a Workspace

```bash
curl -X POST "http://localhost:8000/workspaces" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Research Project",
    "description": "Academic papers and research documents"
  }'
```

#### Upload Documents

```bash
curl -X POST "http://localhost:8000/workspaces/{workspace_id}/documents" \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf"
```

#### Ask Questions

```bash
# JSON request
curl -X POST "http://localhost:8000/workspaces/{workspace_id}/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main findings in the uploaded research papers?",
    "mode": "hybrid"
  }'

# Form request with file upload
curl -X POST "http://localhost:8000/workspaces/{workspace_id}/chat" \
  -F "question=Analyze this new document and compare with existing ones" \
  -F "mode=hybrid" \
  -F "files=@new_document.pdf"
```

## 🔧 Configuration

### Supported Parsers

- **mineru** - Advanced document parsing with layout analysis
- **auto** - Automatic parser selection based on file type

### Query Modes

- **hybrid** - Combines vector similarity and graph traversal
- **local** - Local context search
- **global** - Global knowledge graph search

### Storage Backends

The system supports multiple external storage options:

- **Neo4j** - Graph relationships and entity storage
- **Supabase PostgreSQL** - Vector embeddings, structured data and metadata storage

## 🐳 Docker Deployment

### Development Setup

```bash
cd ops
docker-compose up -d
```

### Production Setup

```bash
cd ops
docker-compose --profile proxy up -d
```

This includes:

- Neo4j graph database (if using Docker)
- Caddy reverse proxy with automatic HTTPS
- Persistent data volumes

## 🏥 Monitoring & Health Checks

The system includes comprehensive health monitoring:

- **Service Health**: Monitor all external storage services
- **Connection Status**: Real-time connectivity checks
- **Performance Metrics**: Response times and availability
- **Automatic Failover**: Graceful degradation when services are unavailable

Visit `/healthz/` for the health dashboard or use individual endpoints for specific services.

## 🔒 Security Features

- **Workspace Isolation**: Each workspace is completely isolated
- **External Storage**: Sensitive data stored in external systems
- **Environment Variables**: Secure configuration management
- **Health Checks**: Monitor for security-related issues

## 📈 Performance

- **Async Processing**: Non-blocking document processing
- **Parallel Operations**: Concurrent health checks and operations
- **Caching**: LLM response caching for improved performance
- **Streaming**: Support for large document processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` endpoint when running
- **Health Status**: Monitor `/healthz/` for system status
- **Issues**: Report bugs and feature requests via GitHub issues

## 🙏 Acknowledgments

- **LightRAG** - Core RAG framework
- **RAG-Anything** - Document processing capabilities
- **FastAPI** - High-performance web framework
- **Supabase** - PostgreSQL database platform
- **Neo4j** - Graph database platform

---

**Built with ❤️ using LightRAG and RAG-Anything**

## 🙏 Acknowledgments

