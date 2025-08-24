# RAG System Query Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Frontend<br/>(script.js)
    participant API as FastAPI<br/>(app.py)
    participant RAG as RAG System<br/>(rag_system.py)
    participant AI as AI Generator<br/>(ai_generator.py)
    participant Tools as Search Tools<br/>(search_tools.py)
    participant Vector as Vector Store<br/>(vector_store.py)
    participant Chroma as ChromaDB
    participant Claude as Claude API

    User->>Frontend: Types query & clicks send
    Note over Frontend: Captures input (line 46)<br/>Shows loading animation
    
    Frontend->>API: POST /api/query<br/>{query, session_id}
    Note over API: Line 56-64<br/>Creates session if needed
    
    API->>RAG: rag_system.query(query, session_id)
    Note over RAG: Line 102-140<br/>Gets conversation history
    
    RAG->>AI: generate_response()<br/>+ tool definitions
    Note over AI: Line 43-78<br/>Prepares Claude call
    
    AI->>Claude: API call with tools
    Claude-->>Claude: Decides: search needed?
    
    alt Course-specific question (needs search)
        Claude-->>AI: Request tool use:<br/>search_course_content
        Note over AI: Line 89-120<br/>Handle tool execution
        
        AI->>Tools: execute_tool("search_course_content")
        Note over Tools: Line 52-86<br/>CourseSearchTool.execute()
        
        Tools->>Vector: search(query, filters)
        Note over Vector: Line 61-100<br/>Resolve course name<br/>Build filters
        
        Vector->>Chroma: query embeddings
        Chroma-->>Vector: matching chunks
        Vector-->>Tools: SearchResults
        
        Tools-->>AI: Formatted results<br/>+ track sources
        AI->>Claude: Send tool results
        Claude-->>AI: Final synthesized answer
    else General knowledge question
        Claude-->>AI: Direct answer<br/>(no search needed)
    end
    
    AI-->>RAG: Response text
    Note over RAG: Line 130-140<br/>Get sources<br/>Update session history
    
    RAG-->>API: (answer, sources)
    API-->>Frontend: JSON Response<br/>{answer, sources, session_id}
    
    Note over Frontend: Line 84-85<br/>Remove loading<br/>Display answer
    Frontend->>User: Shows formatted response<br/>with collapsible sources
```

## Key Components

### 1. **Frontend Layer**
- **script.js**: Handles UI interactions, sends requests, displays responses

### 2. **API Layer** 
- **app.py**: FastAPI server, handles HTTP endpoints, session management

### 3. **RAG Orchestration**
- **rag_system.py**: Coordinates between components, manages conversation flow

### 4. **AI Processing**
- **ai_generator.py**: Interfaces with Claude API, handles tool execution

### 5. **Search System**
- **search_tools.py**: Implements search tool interface for Claude
- **vector_store.py**: Manages ChromaDB vector operations

### 6. **Storage**
- **ChromaDB**: Vector database for semantic search
- **Session Manager**: Maintains conversation history

## Flow Summary

1. **User Input** → Frontend captures query
2. **API Request** → Frontend sends POST to `/api/query`
3. **RAG Processing** → System orchestrates the query
4. **AI Decision** → Claude decides if search is needed
5. **Vector Search** → If needed, semantic search in ChromaDB
6. **Response Generation** → Claude synthesizes final answer
7. **Display** → Frontend shows response with sources

## Key Features

- **Smart Search**: Claude decides when to search vs. answer directly
- **Semantic Matching**: Course names resolved semantically
- **Context Preservation**: Session history maintained
- **Source Attribution**: Tracks and displays content sources
- **Tool-based Architecture**: Extensible tool system for Claude