"""
FastAPI upload endpoint for file processing
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile
import shutil

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import Config
from ingestion.pdf_loader import PDFLoader
from ingestion.email_loader import EmailLoader
from embeddings.embedder import Embedder
from storage.vector_store import VectorStore
from storage.metadata_store import MetadataStore
from tasks.job_runner import JobRunner

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="gabo API",
    description="AI-native platform for unified data processing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global configuration and components
config = None
embedder = None
vector_store = None
metadata_store = None
job_runner = None


class UploadResponse(BaseModel):
    """Response model for file upload"""
    filename: str
    status: str
    message: str
    task_id: Optional[str] = None


class SearchRequest(BaseModel):
    """Request model for search"""
    query: str
    limit: int = 10
    similarity_threshold: float = 0.7


class SearchResponse(BaseModel):
    """Response model for search"""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    search_time_ms: float


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: str
    components: Dict[str, str]


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global config, embedder, vector_store, metadata_store, job_runner
    
    try:
        # Load configuration
        config = Config.from_env()
        
        # Initialize components
        embedder = Embedder(config)
        vector_store = VectorStore(config)
        metadata_store = MetadataStore(config)
        job_runner = JobRunner(config)
        
        # Initialize storage
        await vector_store.initialize_tables()
        await metadata_store.initialize_tables()
        
        logger.info("API startup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        if vector_store:
            await vector_store.close()
        if metadata_store:
            await metadata_store.close()
        logger.info("API shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "gabo API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connections
        db_status = "healthy"
        try:
            await vector_store.connect()
        except Exception:
            db_status = "unhealthy"
        
        # Check embedding service
        embedding_status = "healthy"
        try:
            await embedder.embed_text("test")
        except Exception:
            embedding_status = "unhealthy"
        
        return HealthResponse(
            status="healthy" if db_status == "healthy" and embedding_status == "healthy" else "unhealthy",
            timestamp=asyncio.get_event_loop().time(),
            components={
                "database": db_status,
                "embeddings": embedding_status,
                "vector_store": "healthy",
                "metadata_store": "healthy"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload and process a file"""
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.eml', '.msg', '.txt', '.docx']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported types: {allowed_extensions}"
            )
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        # Submit processing task
        task = job_runner.process_document(temp_path, file_ext[1:])
        
        return UploadResponse(
            filename=file.filename,
            status="processing",
            message="File uploaded and processing started",
            task_id=task.id
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/batch", response_model=List[UploadResponse])
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """Upload and process multiple files"""
    try:
        responses = []
        
        for file in files:
            # Validate file type
            allowed_extensions = ['.pdf', '.eml', '.msg', '.txt', '.docx']
            file_ext = Path(file.filename).suffix.lower()
            
            if file_ext not in allowed_extensions:
                responses.append(UploadResponse(
                    filename=file.filename,
                    status="error",
                    message=f"Unsupported file type: {file_ext}",
                    task_id=None
                ))
                continue
            
            # Save uploaded file
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                temp_path = temp_file.name
            
            # Submit processing task
            task = job_runner.process_document(temp_path, file_ext[1:])
            
            responses.append(UploadResponse(
                filename=file.filename,
                status="processing",
                message="File uploaded and processing started",
                task_id=task.id
            ))
        
        return responses
        
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search documents with natural language query"""
    try:
        import time
        start_time = time.time()
        
        # Generate query embedding
        query_embedding = await embedder.embed_query(request.query)
        
        # Search vector store
        results = await vector_store.search(
            query_embedding,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return SearchResponse(
            query=request.query,
            results=[result.dict() for result in results],
            total_results=len(results),
            search_time_ms=search_time
        )
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a processing task"""
    try:
        status = job_runner.get_task_status(task_id)
        return status
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        vector_stats = await vector_store.get_stats()
        metadata_stats = await metadata_store.get_processing_stats()
        
        return {
            "vector_store": vector_stats,
            "metadata_store": metadata_stats,
            "embedding_model": embedder.get_model_info()
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{source_file}")
async def delete_document(source_file: str):
    """Delete a document and its associated data"""
    try:
        # Delete from vector store
        success = await vector_store.delete_by_source(source_file)
        
        if success:
            return {"message": f"Document {source_file} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
            
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 