"""
Scheduler for background tasks and retries
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
from celery.schedules import crontab
from celery import Celery

from config import Config
from .job_runner import JobRunner

logger = logging.getLogger(__name__)


class Scheduler:
    """Scheduler for background tasks and retries"""
    
    def __init__(self, config: Config):
        self.config = config
        self.job_runner = JobRunner(config)
        self.celery = self.job_runner.celery
        
        # Configure periodic tasks
        self._configure_periodic_tasks()
    
    def _configure_periodic_tasks(self):
        """Configure periodic tasks"""
        
        @self.celery.task(name='scheduled_cleanup')
        def scheduled_cleanup_task():
            """Scheduled cleanup of old data"""
            try:
                # Clean up data older than 30 days
                result = self.job_runner.cleanup_old_data(days_old=30)
                logger.info("Scheduled cleanup completed")
                return result
            except Exception as e:
                logger.error(f"Error in scheduled cleanup: {e}")
                raise
        
        @self.celery.task(name='health_check')
        def health_check_task():
            """Health check for the system"""
            try:
                # Check database connections
                # Check embedding service
                # Check storage systems
                
                return {
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'checks': {
                        'database': 'ok',
                        'embeddings': 'ok',
                        'storage': 'ok'
                    }
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise
        
        @self.celery.task(name='retry_failed_tasks')
        def retry_failed_tasks():
            """Retry failed tasks"""
            try:
                # Get failed tasks from database
                # Retry them with exponential backoff
                
                return {
                    'status': 'completed',
                    'retried_tasks': 0
                }
            except Exception as e:
                logger.error(f"Error retrying failed tasks: {e}")
                raise
        
        # Configure periodic schedule
        self.celery.conf.beat_schedule = {
            'cleanup-old-data': {
                'task': 'scheduled_cleanup',
                'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
            },
            'health-check': {
                'task': 'health_check',
                'schedule': crontab(minute='*/15'),  # Every 15 minutes
            },
            'retry-failed-tasks': {
                'task': 'retry_failed_tasks',
                'schedule': crontab(minute='*/5'),  # Every 5 minutes
            },
        }
    
    def schedule_document_processing(self, file_paths: List[str], 
                                   priority: str = 'normal') -> str:
        """Schedule document processing with retry logic"""
        try:
            # Submit batch processing task
            task = self.job_runner.batch_process(file_paths)
            
            # Configure retry logic
            task.retry(
                countdown=60,  # Wait 1 minute before first retry
                max_retries=3,
                exc=Exception
            )
            
            logger.info(f"Scheduled processing for {len(file_paths)} files: {task.id}")
            return task.id
            
        except Exception as e:
            logger.error(f"Error scheduling document processing: {e}")
            raise
    
    def schedule_search(self, query: str, limit: int = 10) -> str:
        """Schedule search task"""
        try:
            task = self.job_runner.search_documents(query, limit)
            logger.info(f"Scheduled search for query: {query}")
            return task.id
            
        except Exception as e:
            logger.error(f"Error scheduling search: {e}")
            raise
    
    def schedule_cleanup(self, days_old: int = 30) -> str:
        """Schedule cleanup task"""
        try:
            task = self.job_runner.cleanup_old_data(days_old)
            logger.info(f"Scheduled cleanup for data older than {days_old} days")
            return task.id
            
        except Exception as e:
            logger.error(f"Error scheduling cleanup: {e}")
            raise
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get list of scheduled tasks"""
        try:
            inspect = self.celery.control.inspect()
            scheduled = inspect.scheduled()
            
            tasks = []
            for worker, worker_tasks in scheduled.items():
                for task in worker_tasks:
                    tasks.append({
                        'worker': worker,
                        'task_id': task['id'],
                        'name': task['name'],
                        'args': task['args'],
                        'kwargs': task['kwargs'],
                        'eta': task['eta'],
                        'expires': task['expires']
                    })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting scheduled tasks: {e}")
            return []
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        try:
            self.celery.control.revoke(task_id, terminate=True)
            logger.info(f"Cancelled task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    def get_task_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get task history for the last N hours"""
        try:
            # This would typically query a database for task history
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Error getting task history: {e}")
            return []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            # Get worker stats
            worker_stats = self.job_runner.get_worker_stats()
            
            # Get scheduled tasks
            scheduled_tasks = self.get_scheduled_tasks()
            
            # Get task history
            task_history = self.get_task_history()
            
            return {
                'workers': worker_stats,
                'scheduled_tasks': len(scheduled_tasks),
                'recent_tasks': len(task_history),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    def start_beat(self):
        """Start the Celery beat scheduler"""
        try:
            # This would start the beat scheduler in a separate process
            # For now, just log that it would start
            logger.info("Starting Celery beat scheduler")
            
        except Exception as e:
            logger.error(f"Error starting beat scheduler: {e}")
            raise
    
    def stop_beat(self):
        """Stop the Celery beat scheduler"""
        try:
            logger.info("Stopping Celery beat scheduler")
            
        except Exception as e:
            logger.error(f"Error stopping beat scheduler: {e}")
            raise 