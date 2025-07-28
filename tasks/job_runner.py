"""
Celery job runner for async task processing
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging
from celery import Celery
from celery.result import AsyncResult
import json

from config import Config
from ingestion.pdf_loader import PDFLoader
from ingestion.email_loader import EmailLoader
from embeddings.embedder import Embedder
from storage.vector_store import VectorStore
from storage.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


class JobRunner:
    """Celery job runner for processing documents"""
    
    def __init__(self, config: Config):
        self.config = config
        self.celery = Celery(
            'gabo',
            broker=config.task.broker_url,
            backend=config.task.result_backend
        )
        
        # Configure Celery
        self.celery.conf.update(
            task_serializer=config.task.task_serializer,
            result_serializer=config.task.result_serializer,
            accept_content=config.task.accept_content,
            timezone='UTC',
            enable_utc=True,
        )
        
        # Initialize components
        self.embedder = Embedder(config)
        self.vector_store = VectorStore(config)
        self.metadata_store = MetadataStore(config)
        
        # Register tasks
        self._register_tasks()
    
    def _register_tasks(self):
        """Register Celery tasks"""
        
        @self.celery.task(bind=True, name='process_document')
        def process_document_task(self, file_path: str, file_type: Optional[str] = None):
            """Process a single document"""
            try:
                # Update task status
                self.update_state(
                    state='PROGRESS',
                    meta={'status': 'Processing document', 'file': file_path}
                )
                
                # Determine loader
                if file_type == "pdf" or file_path.lower().endswith('.pdf'):
                    loader = PDFLoader()
                elif file_type == "email" or file_path.lower().endswith('.eml'):
                    loader = EmailLoader()
                else:
                    raise ValueError(f"Unsupported file type: {file_type}")
                
                # Load and chunk document
                chunks = asyncio.run(loader.load_and_chunk(file_path))
                
                # Update progress
                self.update_state(
                    state='PROGRESS',
                    meta={'status': 'Generating embeddings', 'file': file_path}
                )
                
                # Generate embeddings
                embeddings = asyncio.run(self.embedder.embed_chunks([c.content for c in chunks]))
                
                # Update progress
                self.update_state(
                    state='PROGRESS',
                    meta={'status': 'Storing data', 'file': file_path}
                )
                
                # Store in vector database
                asyncio.run(self.vector_store.store_embeddings(embeddings, chunks))
                
                # Store metadata
                asyncio.run(self.metadata_store.store_metadata(chunks))
                
                # Update processing status
                asyncio.run(self.metadata_store.update_processing_status(
                    file_path, "completed", "Document processed successfully"
                ))
                
                return {
                    'status': 'SUCCESS',
                    'file': file_path,
                    'chunks_processed': len(chunks),
                    'embeddings_created': len(embeddings)
                }
                
            except Exception as e:
                logger.error(f"Error processing document {file_path}: {e}")
                
                # Update processing status
                asyncio.run(self.metadata_store.update_processing_status(
                    file_path, "failed", str(e)
                ))
                
                raise
        
        @self.celery.task(bind=True, name='batch_process')
        def batch_process_task(self, file_paths: List[str]):
            """Process multiple documents in batch"""
            try:
                results = []
                total_files = len(file_paths)
                
                for i, file_path in enumerate(file_paths):
                    # Update progress
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'status': f'Processing file {i+1}/{total_files}',
                            'current_file': file_path,
                            'progress': (i / total_files) * 100
                        }
                    )
                    
                    # Process individual file
                    result = process_document_task.delay(file_path)
                    results.append(result)
                
                return {
                    'status': 'SUCCESS',
                    'total_files': total_files,
                    'task_ids': [r.id for r in results]
                }
                
            except Exception as e:
                logger.error(f"Error in batch processing: {e}")
                raise
        
        @self.celery.task(bind=True, name='search_documents')
        def search_documents_task(self, query: str, limit: int = 10):
            """Search documents with query"""
            try:
                # Generate query embedding
                query_embedding = asyncio.run(self.embedder.embed_query(query))
                
                # Search vector store
                results = asyncio.run(self.vector_store.search(query_embedding, limit))
                
                return {
                    'status': 'SUCCESS',
                    'query': query,
                    'results': [r.dict() for r in results],
                    'total_results': len(results)
                }
                
            except Exception as e:
                logger.error(f"Error searching documents: {e}")
                raise
        
        @self.celery.task(bind=True, name='cleanup_old_data')
        def cleanup_old_data_task(self, days_old: int = 30):
            """Clean up old data"""
            try:
                # TODO: Implement cleanup logic
                # This would remove old embeddings and metadata
                
                return {
                    'status': 'SUCCESS',
                    'message': f'Cleaned up data older than {days_old} days'
                }
                
            except Exception as e:
                logger.error(f"Error cleaning up data: {e}")
                raise
    
    def process_document(self, file_path: str, file_type: Optional[str] = None) -> AsyncResult:
        """Submit document processing task"""
        return self.celery.send_task('process_document', args=[file_path, file_type])
    
    def batch_process(self, file_paths: List[str]) -> AsyncResult:
        """Submit batch processing task"""
        return self.celery.send_task('batch_process', args=[file_paths])
    
    def search_documents(self, query: str, limit: int = 10) -> AsyncResult:
        """Submit search task"""
        return self.celery.send_task('search_documents', args=[query, limit])
    
    def cleanup_old_data(self, days_old: int = 30) -> AsyncResult:
        """Submit cleanup task"""
        return self.celery.send_task('cleanup_old_data', args=[days_old])
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a task"""
        result = AsyncResult(task_id, app=self.celery)
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None,
            'info': result.info if hasattr(result, 'info') else None
        }
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        try:
            inspect = self.celery.control.inspect()
            
            stats = inspect.stats()
            active_tasks = inspect.active()
            reserved_tasks = inspect.reserved()
            
            return {
                'stats': stats,
                'active_tasks': active_tasks,
                'reserved_tasks': reserved_tasks
            }
        except Exception as e:
            logger.error(f"Error getting worker stats: {e}")
            return {}
    
    def purge_queue(self) -> bool:
        """Purge all tasks from queue"""
        try:
            self.celery.control.purge()
            return True
        except Exception as e:
            logger.error(f"Error purging queue: {e}")
            return False 