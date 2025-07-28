"""
Pydantic models for storage schemas
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """Model for document chunks"""
    content: str = Field(..., description="Text content of the chunk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    source_file: str = Field(..., description="Source file path")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchResult(BaseModel):
    """Model for search results"""
    content: str = Field(..., description="Text content of the result")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Result metadata")
    source_file: str = Field(..., description="Source file path")
    chunk_index: int = Field(..., description="Chunk index in source file")
    similarity: float = Field(..., description="Similarity score")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DocumentMetadata(BaseModel):
    """Model for document metadata"""
    filename: str = Field(..., description="Document filename")
    file_path: str = Field(..., description="Full file path")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_type: Optional[str] = Field(None, description="File type/extension")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    processing_status: str = Field(default="pending", description="Processing status")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProcessingLog(BaseModel):
    """Model for processing logs"""
    document_id: int = Field(..., description="Document ID")
    status: str = Field(..., description="Processing status")
    message: str = Field(default="", description="Status message")
    created_at: Optional[datetime] = Field(None, description="Log timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VectorStoreStats(BaseModel):
    """Model for vector store statistics"""
    total_embeddings: int = Field(0, description="Total number of embeddings")
    unique_sources: int = Field(0, description="Number of unique source files")
    avg_similarity: float = Field(0.0, description="Average similarity score")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MetadataStoreStats(BaseModel):
    """Model for metadata store statistics"""
    total_documents: int = Field(0, description="Total number of documents")
    total_chunks: int = Field(0, description="Total number of chunks")
    status_breakdown: Dict[str, int] = Field(default_factory=dict, description="Documents by status")
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Recent activity")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchQuery(BaseModel):
    """Model for search queries"""
    query: str = Field(..., description="Search query text")
    limit: int = Field(default=10, description="Maximum number of results")
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity score")
    metadata_filter: Optional[Dict[str, Any]] = Field(None, description="Metadata filter")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchResponse(BaseModel):
    """Model for search responses"""
    query: str = Field(..., description="Original query")
    results: List[SearchResult] = Field(default_factory=list, description="Search results")
    total_results: int = Field(0, description="Total number of results")
    search_time_ms: float = Field(0.0, description="Search execution time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EmbeddingInfo(BaseModel):
    """Model for embedding information"""
    provider: str = Field(..., description="Embedding provider")
    model: str = Field(..., description="Model name")
    dimension: int = Field(..., description="Embedding dimension")
    batch_size: int = Field(default=100, description="Batch size for processing")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 