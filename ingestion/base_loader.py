"""
Abstract base class for document loaders
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
import logging

from .utils import chunk_text, clean_text, extract_metadata
from ..storage.schemas import DocumentChunk

logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """Abstract base class for document loaders"""
    
    def __init__(self):
        self.supported_extensions = []
        self.max_chunk_size = 1000
        self.chunk_overlap = 200
    
    @abstractmethod
    async def load_document(self, file_path: str) -> Dict[str, Any]:
        """Load document content and metadata"""
        pass
    
    @abstractmethod
    def extract_text(self, content: Dict[str, Any]) -> str:
        """Extract text content from loaded document"""
        pass
    
    async def load_and_chunk(self, file_path: str) -> List[DocumentChunk]:
        """Load document and return chunked content"""
        try:
            # Load the document
            content = await self.load_document(file_path)
            
            # Extract text
            text = self.extract_text(content)
            
            # Clean text
            cleaned_text = clean_text(text)
            
            # Chunk the text
            chunks = chunk_text(cleaned_text, self.max_chunk_size, self.chunk_overlap)
            
            # Create DocumentChunk objects
            document_chunks = []
            for i, chunk in enumerate(chunks):
                metadata = extract_metadata(content, chunk, i)
                document_chunk = DocumentChunk(
                    content=chunk,
                    metadata=metadata,
                    chunk_index=i,
                    source_file=file_path
                )
                document_chunks.append(document_chunk)
            
            logger.info(f"Created {len(document_chunks)} chunks from {file_path}")
            return document_chunks
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            raise
    
    def can_handle(self, file_path: str) -> bool:
        """Check if this loader can handle the given file"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions
    
    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get basic file metadata"""
        path = Path(file_path)
        return {
            "filename": path.name,
            "file_size": path.stat().st_size,
            "file_extension": path.suffix.lower(),
            "file_path": str(path.absolute())
        } 