"""
OpenAI embedding implementation
"""

import asyncio
import numpy as np
from typing import List, Dict, Any
import logging
from openai import AsyncOpenAI

from config import Config

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """OpenAI embedding model implementation"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.embedding.api_key
        self.model = config.embedding.model
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # Model dimension mapping
        self.dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072
        }
    
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string"""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error embedding text with OpenAI: {e}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts"""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error embedding batch with OpenAI: {e}")
            raise
    
    async def embed_query(self, query: str) -> List[float]:
        """Embed a query (same as embed_text for OpenAI)"""
        return await self.embed_text(query)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self.dimensions.get(self.model, 1536)
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Normalize vectors
            vec1_norm = vec1 / np.linalg.norm(vec1)
            vec2_norm = vec2 / np.linalg.norm(vec2)
            
            # Calculate cosine similarity
            similarity = np.dot(vec1_norm, vec2_norm)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            raise
    
    def batch_similarity(self, query_embedding: List[float], 
                        embeddings: List[List[float]]) -> List[float]:
        """Calculate similarities between query and multiple embeddings"""
        try:
            query_vec = np.array(query_embedding)
            query_norm = query_vec / np.linalg.norm(query_vec)
            
            similarities = []
            for embedding in embeddings:
                vec = np.array(embedding)
                vec_norm = vec / np.linalg.norm(vec)
                similarity = np.dot(query_norm, vec_norm)
                similarities.append(float(similarity))
            
            return similarities
        except Exception as e:
            logger.error(f"Error calculating batch similarity: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the OpenAI model"""
        return {
            "provider": "openai",
            "model": self.model,
            "dimension": self.get_embedding_dimension(),
            "api_key_configured": bool(self.api_key)
        } 