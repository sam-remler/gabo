#!/usr/bin/env python3
"""
Main entry point for gabo - AI-native platform for unified data processing
"""

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Optional

from config import Config
from ingestion.base_loader import BaseLoader
from ingestion.pdf_loader import PDFLoader
from ingestion.email_loader import EmailLoader
from embeddings.embedder import Embedder
from storage.vector_store import VectorStore
from storage.metadata_store import MetadataStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GaboApp:
    """Main application class for gabo platform"""
    
    def __init__(self, config: Config):
        self.config = config
        self.embedder = Embedder(config)
        self.vector_store = VectorStore(config)
        self.metadata_store = MetadataStore(config)
        
    async def process_file(self, file_path: str, file_type: Optional[str] = None) -> bool:
        """Process a single file through the ingestion pipeline"""
        try:
            # Determine loader based on file type
            if file_type == "pdf" or file_path.lower().endswith('.pdf'):
                loader = PDFLoader()
            elif file_type == "email" or file_path.lower().endswith('.eml'):
                loader = EmailLoader()
            else:
                # Try to auto-detect
                loader = self._get_loader_for_file(file_path)
            
            # Load and chunk the document
            chunks = await loader.load_and_chunk(file_path)
            
            # Generate embeddings
            embeddings = await self.embedder.embed_chunks(chunks)
            
            # Store in vector database
            await self.vector_store.store_embeddings(embeddings, chunks)
            
            # Store metadata
            await self.metadata_store.store_metadata(chunks)
            
            logger.info(f"Successfully processed {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return False
    
    def _get_loader_for_file(self, file_path: str) -> BaseLoader:
        """Auto-detect appropriate loader for file type"""
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            return PDFLoader()
        elif ext in ['.eml', '.msg']:
            return EmailLoader()
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    async def query(self, question: str) -> str:
        """Query the system with a natural language question"""
        try:
            # Generate query embedding
            query_embedding = await self.embedder.embed_text(question)
            
            # Search for relevant chunks
            results = await self.vector_store.search(query_embedding, limit=5)
            
            # TODO: Implement LLM-based answer generation
            # For now, return the top results
            return f"Query: {question}\n\nTop results:\n" + "\n".join(
                [f"- {result.content[:200]}..." for result in results]
            )
            
        except Exception as e:
            logger.error(f"Error querying: {e}")
            return f"Error processing query: {e}"


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="gabo - AI-native data platform")
    parser.add_argument("--config", default="config.yaml", help="Configuration file")
    parser.add_argument("--file", help="Process a single file")
    parser.add_argument("--query", help="Query the system")
    parser.add_argument("--dev", action="store_true", help="Run in development mode")
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config.from_file(args.config)
    
    # Initialize app
    app = GaboApp(config)
    
    if args.file:
        # Process a single file
        success = await app.process_file(args.file)
        print(f"File processing {'successful' if success else 'failed'}")
        
    elif args.query:
        # Query the system
        result = await app.query(args.query)
        print(result)
        
    elif args.dev:
        # Development mode - run some tests
        print("Running in development mode...")
        # TODO: Add development tests
        
    else:
        print("gabo - AI-native data platform")
        print("Use --file to process a file or --query to ask a question")


if __name__ == "__main__":
    asyncio.run(main()) 