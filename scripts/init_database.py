#!/usr/bin/env python3
"""
Database initialization script for gabo platform
"""

import asyncio
import asyncpg
import logging
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize the database with all necessary tables and extensions"""
    
    # Load configuration
    config = Config.from_env()
    db_config = config.database
    
    try:
        # Connect to PostgreSQL
        logger.info("Connecting to PostgreSQL...")
        conn = await asyncpg.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.username,
            password=db_config.password
        )
        
        # Enable PGVector extension
        logger.info("Enabling PGVector extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create embeddings table
        logger.info("Creating embeddings table...")
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
        logger.info("Creating vector index...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS embeddings_vector_idx 
            ON embeddings 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        
        # Create index for metadata queries
        logger.info("Creating metadata index...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS embeddings_metadata_idx 
            ON embeddings USING GIN (metadata)
        """)
        
        # Create documents table
        logger.info("Creating documents table...")
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
        logger.info("Creating chunks table...")
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
        logger.info("Creating processing_logs table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS processing_logs (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id),
                status TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for documents table
        logger.info("Creating document indexes...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents(filename)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(processing_status)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_file_path_idx ON documents(file_path)
        """)
        
        # Create indexes for chunks table
        logger.info("Creating chunk indexes...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks(document_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS chunks_metadata_idx ON chunks USING GIN(metadata)
        """)
        
        # Create indexes for processing_logs table
        logger.info("Creating processing_logs indexes...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS processing_logs_document_idx ON processing_logs(document_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS processing_logs_status_idx ON processing_logs(status)
        """)
        
        # Verify PGVector extension
        logger.info("Verifying PGVector extension...")
        result = await conn.fetchval("SELECT * FROM pg_extension WHERE extname = 'vector'")
        if result:
            logger.info("✅ PGVector extension is enabled")
        else:
            logger.error("❌ PGVector extension is not enabled")
            return False
        
        # Test vector operations
        logger.info("Testing vector operations...")
        await conn.execute("""
            INSERT INTO embeddings (content, embedding, metadata, source_file, chunk_index)
            VALUES ('test content', '[0.1, 0.2, 0.3]'::vector, '{"test": true}', 'test.txt', 0)
        """)
        
        # Clean up test data
        await conn.execute("DELETE FROM embeddings WHERE source_file = 'test.txt'")
        
        logger.info("✅ Vector operations test passed")
        
        await conn.close()
        logger.info("✅ Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


async def test_connection():
    """Test database connection"""
    config = Config.from_env()
    db_config = config.database
    
    try:
        conn = await asyncpg.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.username,
            password=db_config.password
        )
        
        # Test basic connection
        version = await conn.fetchval("SELECT version();")
        logger.info(f"✅ Connected to PostgreSQL: {version.split(',')[0]}")
        
        # Test PGVector
        vector_ext = await conn.fetchval("SELECT * FROM pg_extension WHERE extname = 'vector'")
        if vector_ext:
            logger.info("✅ PGVector extension is available")
        else:
            logger.error("❌ PGVector extension is not available")
            return False
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize gabo database")
    parser.add_argument("--test-only", action="store_true", help="Only test connection")
    parser.add_argument("--init", action="store_true", help="Initialize database tables")
    
    args = parser.parse_args()
    
    if args.test_only:
        success = await test_connection()
        sys.exit(0 if success else 1)
    elif args.init:
        success = await init_database()
        sys.exit(0 if success else 1)
    else:
        # Default: test connection first, then initialize
        logger.info("Testing database connection...")
        if await test_connection():
            logger.info("Initializing database...")
            success = await init_database()
            sys.exit(0 if success else 1)
        else:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 