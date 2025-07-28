"""
Metadata store for PostgreSQL operations
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
import asyncpg
import json
from datetime import datetime

from config import Config
from .schemas import DocumentChunk

logger = logging.getLogger(__name__)


class MetadataStore:
    """Metadata store for managing document metadata"""
    
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
                
                logger.info("Connected to PostgreSQL for metadata")
                
            except Exception as e:
                logger.error(f"Error connecting to database: {e}")
                raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def initialize_tables(self):
        """Initialize metadata tables"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                # Create documents table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size BIGINT,
                        file_type TEXT,
                        metadata JSONB,
                        processing_status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create chunks table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chunks (
                        id SERIAL PRIMARY KEY,
                        document_id INTEGER REFERENCES documents(id),
                        chunk_index INTEGER,
                        content TEXT,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create processing_logs table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS processing_logs (
                        id SERIAL PRIMARY KEY,
                        document_id INTEGER REFERENCES documents(id),
                        status TEXT,
                        message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents(filename)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(processing_status)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks(document_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS chunks_metadata_idx ON chunks USING GIN(metadata)
                """)
                
                logger.info("Initialized metadata tables")
                
        except Exception as e:
            logger.error(f"Error initializing metadata tables: {e}")
            raise
    
    async def store_metadata(self, chunks: List[DocumentChunk]) -> bool:
        """Store metadata for document chunks"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                # First, create or update document record
                source_file = chunks[0].source_file if chunks else ""
                document_id = await self._get_or_create_document(conn, source_file)
                
                # Store chunk metadata
                for chunk in chunks:
                    await conn.execute("""
                        INSERT INTO chunks (document_id, chunk_index, content, metadata)
                        VALUES ($1, $2, $3, $4)
                    """, document_id, chunk.chunk_index, chunk.content, chunk.metadata)
                
                # Update document status
                await conn.execute("""
                    UPDATE documents 
                    SET processing_status = 'completed', updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, document_id)
                
                logger.info(f"Stored metadata for {len(chunks)} chunks")
                return True
                
        except Exception as e:
            logger.error(f"Error storing metadata: {e}")
            return False
    
    async def _get_or_create_document(self, conn, source_file: str) -> int:
        """Get or create document record"""
        # Check if document exists
        doc_id = await conn.fetchval("""
            SELECT id FROM documents WHERE file_path = $1
        """, source_file)
        
        if doc_id:
            return doc_id
        
        # Create new document record
        doc_id = await conn.fetchval("""
            INSERT INTO documents (filename, file_path, processing_status)
            VALUES ($1, $2, 'processing')
            RETURNING id
        """, source_file.split('/')[-1], source_file)
        
        return doc_id
    
    async def get_document_metadata(self, source_file: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific document"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM documents WHERE file_path = $1
                """, source_file)
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting document metadata: {e}")
            return None
    
    async def get_chunks_for_document(self, source_file: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT c.* FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE d.file_path = $1
                    ORDER BY c.chunk_index
                """, source_file)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting chunks: {e}")
            return []
    
    async def update_processing_status(self, source_file: str, status: str, message: str = ""):
        """Update processing status for a document"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                # Update document status
                await conn.execute("""
                    UPDATE documents 
                    SET processing_status = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE file_path = $1
                """, source_file, status)
                
                # Log the status change
                doc_id = await conn.fetchval("""
                    SELECT id FROM documents WHERE file_path = $1
                """, source_file)
                
                if doc_id:
                    await conn.execute("""
                        INSERT INTO processing_logs (document_id, status, message)
                        VALUES ($1, $2, $3)
                    """, doc_id, status, message)
                
                logger.info(f"Updated status for {source_file}: {status}")
                
        except Exception as e:
            logger.error(f"Error updating processing status: {e}")
    
    async def search_metadata(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search documents by metadata"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                # Build dynamic query based on metadata filters
                conditions = []
                values = []
                param_count = 0
                
                for key, value in query.items():
                    param_count += 1
                    conditions.append(f"metadata->>'{key}' = ${param_count}")
                    values.append(str(value))
                
                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                
                query_sql = f"""
                    SELECT * FROM documents 
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                """
                
                rows = await conn.fetch(query_sql, *values)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error searching metadata: {e}")
            return []
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            await self.connect()
            
            async with self.pool.acquire() as conn:
                # Document counts by status
                status_counts = await conn.fetch("""
                    SELECT processing_status, COUNT(*) as count
                    FROM documents
                    GROUP BY processing_status
                """)
                
                # Total documents
                total_docs = await conn.fetchval("SELECT COUNT(*) FROM documents")
                
                # Total chunks
                total_chunks = await conn.fetchval("SELECT COUNT(*) FROM chunks")
                
                # Recent activity
                recent_activity = await conn.fetch("""
                    SELECT filename, processing_status, updated_at
                    FROM documents
                    ORDER BY updated_at DESC
                    LIMIT 10
                """)
                
                return {
                    "total_documents": total_docs,
                    "total_chunks": total_chunks,
                    "status_breakdown": {row['processing_status']: row['count'] for row in status_counts},
                    "recent_activity": [dict(row) for row in recent_activity]
                }
                
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {} 