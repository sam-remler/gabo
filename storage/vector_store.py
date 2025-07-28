"""
PGVector wrapper for vector storage
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
import asyncpg
import numpy as np
from pgvector.asyncpg import register_vector

from config import Config
from .schemas import SearchResult

logger = logging.getLogger(__name__)


class VectorStore:
    """PGVector wrapper for storing and searching embeddings"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_config = config.database
        self.pool = None
    
    async def connect(self):
        """Establish database connection pool"""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    host=self.db_config.host,
                    port=self.db_config.port,
                    database=self.db_config.database,
                    user=self.db_config.username,
                    password=self.db_config.password
                )
                
                # Register vector type
                async with self.pool.acquire() as conn:
                    await register_vector(conn)
                
                logger.info("Connected to PostgreSQL with PGVector")
                
            except Exception as e:
                logger.error(f"Error connecting to database: {e}")
                raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def initialize_tables(self):
        """Initialize vector and metadata tables"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                # Create vector table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector(1536),
                        metadata JSONB,
                        source_file TEXT,
                        chunk_index INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create index for vector similarity search
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_vector_idx 
                    ON embeddings 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)
                
                # Create index for metadata queries
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_metadata_idx 
                    ON embeddings USING GIN (metadata)
                """)
                
                logger.info("Initialized vector storage tables")
                
        except Exception as e:
            logger.error(f"Error initializing tables: {e}")
            raise
    
    async def store_embeddings(self, embeddings: List[List[float]], 
                              chunks: List[Dict[str, Any]]) -> bool:
        """Store embeddings and their associated chunks"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                # Prepare batch insert
                values = []
                for i, (embedding, chunk) in enumerate(zip(embeddings, chunks)):
                    values.append((
                        chunk.get('content', ''),
                        embedding,
                        chunk.get('metadata', {}),
                        chunk.get('source_file', ''),
                        chunk.get('chunk_index', i)
                    ))
                
                # Batch insert
                await conn.executemany("""
                    INSERT INTO embeddings (content, embedding, metadata, source_file, chunk_index)
                    VALUES ($1, $2, $3, $4, $5)
                """, values)
                
                logger.info(f"Stored {len(embeddings)} embeddings")
                return True
                
        except Exception as e:
            logger.error(f"Error storing embeddings: {e}")
            return False
    
    async def search(self, query_embedding: List[float], 
                    limit: int = 10, 
                    similarity_threshold: float = 0.7) -> List[SearchResult]:
        """Search for similar embeddings"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                # Perform similarity search
                rows = await conn.fetch("""
                    SELECT content, metadata, source_file, chunk_index,
                           1 - (embedding <=> $1) as similarity
                    FROM embeddings
                    WHERE 1 - (embedding <=> $1) > $2
                    ORDER BY embedding <=> $1
                    LIMIT $3
                """, query_embedding, similarity_threshold, limit)
                
                results = []
                for row in rows:
                    result = SearchResult(
                        content=row['content'],
                        metadata=row['metadata'],
                        source_file=row['source_file'],
                        chunk_index=row['chunk_index'],
                        similarity=row['similarity']
                    )
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            return []
    
    async def search_with_metadata(self, query_embedding: List[float],
                                 metadata_filter: Dict[str, Any],
                                 limit: int = 10) -> List[SearchResult]:
        """Search with metadata filtering"""
        try:
            await self.connect()
            
            # Build metadata filter query
            filter_conditions = []
            filter_values = [query_embedding]
            param_count = 1
            
            for key, value in metadata_filter.items():
                filter_conditions.append(f"metadata->>'{key}' = ${param_count + 1}")
                filter_values.append(str(value))
                param_count += 1
            
            filter_clause = " AND ".join(filter_conditions) if filter_conditions else "TRUE"
            
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT content, metadata, source_file, chunk_index,
                           1 - (embedding <=> $1) as similarity
                    FROM embeddings
                    WHERE {filter_clause}
                    ORDER BY embedding <=> $1
                    LIMIT ${param_count + 1}
                """
                filter_values.append(limit)
                
                rows = await conn.fetch(query, *filter_values)
                
                results = []
                for row in rows:
                    result = SearchResult(
                        content=row['content'],
                        metadata=row['metadata'],
                        source_file=row['source_file'],
                        chunk_index=row['chunk_index'],
                        similarity=row['similarity']
                    )
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching with metadata: {e}")
            return []
    
    async def delete_by_source(self, source_file: str) -> bool:
        """Delete all embeddings for a specific source file"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM embeddings WHERE source_file = $1
                """, source_file)
                
                logger.info(f"Deleted embeddings for {source_file}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting embeddings: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                # Total embeddings
                total_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
                
                # Unique source files
                source_count = await conn.fetchval("""
                    SELECT COUNT(DISTINCT source_file) FROM embeddings
                """)
                
                # Average similarity score
                avg_similarity = await conn.fetchval("""
                    SELECT AVG(1 - (embedding <=> embedding)) FROM embeddings
                """)
                
                return {
                    "total_embeddings": total_count,
                    "unique_sources": source_count,
                    "avg_similarity": float(avg_similarity) if avg_similarity else 0.0
                }
                
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {} 