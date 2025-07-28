# gabo

/gabo/
├── main.py                      # Entry point for CLI or dev test
├── config.py                    # Configs (env vars, paths, model settings)
├── requirements.txt             # Python package dependencies
├── README.md

# Ingestion
├── ingestion/
│   ├── __init__.py
│   ├── base_loader.py           # Abstract base class for loaders
│   ├── pdf_loader.py            # PDF ingestion using PyMuPDF or unstructured.io
│   ├── email_loader.py          # Email/EML ingestion
│   ├── utils.py                 # Chunking, cleaning, metadata extraction

# Embeddings
├── embeddings/
│   ├── __init__.py
│   ├── embedder.py              # Interface for embedding (OpenAI, Cohere, Voyage, etc.)
│   ├── models/
│   │   ├── openai_embed.py
│   │   ├── cohere_embed.py
│   │   └── voyage_embed.py

# Storage
├── storage/
│   ├── __init__.py
│   ├── vector_store.py          # PGVector wrapper
│   ├── metadata_store.py        # PostgreSQL insert/update/query functions
│   ├── schemas.py               # Pydantic models for chunks, metadata, etc.

# Tasks (Async job queue)
├── tasks/
│   ├── __init__.py
│   ├── job_runner.py            # Celery/Ray/Prefect task definitions
│   └── scheduler.py             # Schedule retries or background runs

# Interfaces
├── api/
│   ├── __init__.py
│   └── upload_endpoint.py       # Optional: FastAPI for uploading files



## Summary:
A verticalized AI-native platform that unifies structured and unstructured data into a RAG-ready semantic graph. It enables decision-makers to ask complex, high-level questions and receive contextual, sourced answers in natural language.
Key Features:
1. Semantic-Native Architecture
- Built around vector embeddings, not traditional SQL or row-column schemas
- Supports natural language queries with latent-space enriched responses
2. AI-Native Interface
- Every interface is co-piloted with LLMs
- Example: “Ask a question about Q2 supply chain risks” returns a cited, generated answer tied to real-time data
3. Composable AI Agents
- Users can build retrieval-backed agents for tasks like:
- Contract review
- Compliance checks
- Market signal synthesis
- Operational planning
- Agents can run continuously for monitoring and alerting
4. Enterprise Data Connectors
- Integrates with ERP, CRM, cloud drives, BI tools, document management systems, and external data sources
5. Multimodal Indexing Engine
- Converts all data types (text, tables, PDFs, images) into a unified vector space
- Includes metadata tagging, temporal reasoning, and entity/event linking
6. Retrieval-Augmented Workspace
- Context-aware search and Q&A across all indexed data
- Example: “Top five risks flagged in contract negotiations this quarter”
7. Governance & Auditability
- Full access control and source traceability
- Every generated output is linked back to the originating data

## How It Works
- Each query triggers hybrid search (vector, metadata, symbolic)
- Uses task-specific prompt templates (e.g. SWOT analysis, redlining)
- Responses are compositional, blending structured (e.g., CRM) and unstructured (e.g., PDFs) sources
- Entity and event graph is continuously constructed in the background
