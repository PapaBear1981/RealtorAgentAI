"""
Celery worker entry point for the RealtorAgentAI platform.

This module provides the main entry point for starting Celery workers
with proper configuration and monitoring.
"""

import os
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Configure Celery worker
if __name__ == '__main__':
    # Set worker configuration
    worker_args = [
        'worker',
        '--loglevel=info',
        '--concurrency=4',  # Adjust based on your system
        '--max-tasks-per-child=1000',
        '--time-limit=3600',  # 1 hour hard limit
        '--soft-time-limit=1800',  # 30 minute soft limit
        '--without-gossip',
        '--without-mingle',
        '--without-heartbeat',
    ]
    
    # Add queue specification if provided
    queues = os.environ.get('CELERY_QUEUES', 'ingest,ocr,llm,export,system')
    if queues:
        worker_args.extend(['--queues', queues])
    
    # Add worker name
    worker_name = os.environ.get('CELERY_WORKER_NAME', f'worker@{os.uname().nodename}')
    worker_args.extend(['--hostname', worker_name])
    
    logger.info(f"Starting Celery worker with args: {' '.join(worker_args)}")
    
    # Start worker
    celery_app.worker_main(worker_args)
