# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Application
```bash
# Quick start (recommended)
chmod +x run.sh
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Development Setup
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Create .env file with your Anthropic API key (see .env.example for template)
cp .env.example .env
# Then edit .env to add your actual API key
```

### Accessing the Application
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture

This is a **RAG (Retrieval-Augmented Generation) system** for course materials Q&A that uses semantic search and Claude AI. See `query_flow_diagram.md` for a detailed sequence diagram of the query processing flow.

### Core Flow
1. **User Query** → Frontend (`/frontend/script.js`) sends POST to `/api/query`
2. **API Handler** → FastAPI (`/backend/app.py`) routes to RAG system
3. **RAG Orchestration** → `rag_system.py` coordinates the query processing
4. **AI Decision** → Claude (via `ai_generator.py`) decides whether to search or answer directly
5. **Vector Search** → If needed, `search_tools.py` queries ChromaDB via `vector_store.py`
6. **Response Generation** → Claude synthesizes final answer with sources
7. **Display** → Frontend shows formatted response with collapsible sources

### Key Components

**RAG System** (`backend/rag_system.py`): Main orchestrator that coordinates between all components. Manages document loading, query processing, and session history.

**AI Generator** (`backend/ai_generator.py`): Interfaces with Claude API using tool-calling architecture. Claude dynamically decides when to search course content vs. answering from general knowledge.

**Search Tools** (`backend/search_tools.py`): Implements `CourseSearchTool` that Claude can invoke. Provides semantic course name matching and lesson filtering capabilities.

**Vector Store** (`backend/vector_store.py`): Manages ChromaDB collections for course metadata and content. Handles semantic search with embedding-based retrieval.

**Document Processor** (`backend/document_processor.py`): Parses course documents into structured format with course titles, instructors, and lessons. Creates chunks for vector storage.

### Tool-Based Search Architecture

The system uses Claude's tool-calling capability where:
- Claude receives a `search_course_content` tool definition
- For course-specific questions, Claude invokes the search tool with parameters
- The tool executes semantic search in ChromaDB
- Results are formatted and returned to Claude for synthesis

### Configuration (`backend/config.py`)

Key settings:
- **Model**: `claude-sonnet-4-20250514`
- **Embeddings**: `all-MiniLM-L6-v2` (SentenceTransformers)
- **Chunking**: 800 chars with 100 char overlap
- **Storage**: ChromaDB at `./chroma_db`
- **Search Results**: Max 5 results per query
- **Session History**: Maintains last 2 conversation exchanges

### Document Structure

Course documents in `/docs/` should follow this format:
```
Course Title: [Title]
Instructor: [Name]

Lesson [N]: [Topic]
[Content...]
```

The system automatically extracts course metadata and creates searchable chunks.

## Development Notes

- **Python 3.13+** required
- **Windows users** should use Git Bash for commands
- **Hot reload** enabled with `--reload` flag during development
- **No tests or linting** currently configured in the codebase
- Course documents are loaded from `/docs/` on startup (directory created by `run.sh` if missing)
- Frontend is served as static files from `/frontend/`
- The `main.py` file is not used - actual entry point is `backend/app.py`

## API Endpoints

- `POST /api/query`: Process user query with optional session_id
- `GET /api/courses`: Get course statistics and titles
- `GET /docs`: FastAPI automatic API documentation

## Session Management

The system maintains conversation context through session IDs, allowing follow-up questions that reference previous exchanges. Sessions store the last 2 query-response pairs.
- always use uv to run the server do not use pip directly
- use the uv to manage dependencies and run any python file