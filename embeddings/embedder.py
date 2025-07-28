"""
Main embedder interface for gabo platform
"""

from typing import List, Dict, Any, Optional
import asyncio
import logging

from config import Config
from .models.openai_embed import OpenAIEmbedder
from .models.cohere_embed import CohereEmbedder
from .models.voyage_embed import VoyageEmbedder

logger = logging.getLogger(__name__)


class Embedder:
    """Main embedder class that manages different embedding providers"""
    
    def __init__(self, config: Config):
        self.config = config
        self.provider = config.embedding.provider
        self.model = config.embedding.model
        self.batch_size = config.embedding.batch_size
        self.max_retries = config.embedding.max_retries
        
        # Initialize the appropriate embedder
        self._embedder = self._create_embedder()
    
    def _create_embedder(self):
        """Create the appropriate embedder based on configuration"""
        if self.provider == "openai":
            return OpenAIEmbedder(self.config)
        elif self.provider == "cohere":
            return CohereEmbedder(self.config)
        elif self.provider == "voyage":
            return VoyageEmbedder(self.config)
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")
    
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string"""
        try:
            return await self._embedder.embed_text(text)
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            raise
    
    async def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        """Embed multiple text chunks in batches"""
        try:
            embeddings = []
            
            # Process in batches
            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                batch_embeddings = await self._embedder.embed_batch(batch)
                embeddings.extend(batch_embeddings)
                
                # Add small delay between batches to avoid rate limits
                if i + self.batch_size < len(chunks):
                    await asyncio.sleep(0.1)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error embedding chunks: {e}")
            raise
    
    async def embed_query(self, query: str) -> List[float]:
        """Embed a query for search (may use different model)"""
        try:
            return await self._embedder.embed_query(query)
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self._embedder.get_embedding_dimension()
    
    async def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            return self._embedder.similarity(embedding1, embedding2)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            raise
    
    async def batch_similarity(self, query_embedding: List[float], 
                             embeddings: List[List[float]]) -> List[float]:
        """Calculate similarities between query and multiple embeddings"""
        try:
            return self._embedder.batch_similarity(query_embedding, embeddings)
        except Exception as e:
            logger.error(f"Error calculating batch similarity: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current embedding model"""
        return {
            "provider": self.provider,
            "model": self.model,
            "dimension": self.get_embedding_dimension(),
            "batch_size": self.batch_size,
            "max_retries": self.max_retries
        } 