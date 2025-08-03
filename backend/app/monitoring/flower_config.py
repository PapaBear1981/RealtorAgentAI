"""
Flower monitoring configuration for Celery tasks.

This module provides configuration for the Flower web-based monitoring
tool for Celery task queues and workers.
"""

import os
from typing import Dict, Any
from ..core.config import get_settings

settings = get_settings()

# Flower configuration
FLOWER_CONFIG = {
    # Basic configuration
    'broker': settings.CELERY_BROKER_URL,
    'port': int(os.environ.get('FLOWER_PORT', 5555)),
    'address': os.environ.get('FLOWER_ADDRESS', '0.0.0.0'),
    
    # Authentication (if enabled)
    'basic_auth': os.environ.get('FLOWER_BASIC_AUTH', None),  # Format: "user:password"
    'oauth2_key': os.environ.get('FLOWER_OAUTH2_KEY', None),
    'oauth2_secret': os.environ.get('FLOWER_OAUTH2_SECRET', None),
    'oauth2_redirect_uri': os.environ.get('FLOWER_OAUTH2_REDIRECT_URI', None),
    
    # Database for persistent storage
    'db': os.environ.get('FLOWER_DB', 'flower.db'),
    
    # URL prefix (if behind reverse proxy)
    'url_prefix': os.environ.get('FLOWER_URL_PREFIX', ''),
    
    # Auto-refresh interval
    'auto_refresh': True,
    'refresh_interval': 30,  # seconds
    
    # Task result backend
    'result_backend': settings.CELERY_RESULT_BACKEND,
    
    # Logging
    'logging': 'INFO',
    
    # Enable/disable features
    'enable_events': True,
    'natural_time': True,
    'tasks_columns': 'name,uuid,state,args,kwargs,result,received,started,runtime,worker',
    
    # Purge offline workers
    'purge_offline_workers': 300,  # seconds
}


def get_flower_config() -> Dict[str, Any]:
    """
    Get Flower configuration dictionary.
    
    Returns:
        Dict: Flower configuration
    """
    return FLOWER_CONFIG.copy()


def start_flower():
    """
    Start Flower monitoring server.
    
    This function can be used to programmatically start Flower
    with the configured settings.
    """
    try:
        from flower.command import FlowerCommand
        
        # Convert config to command line arguments
        args = []
        
        # Basic settings
        args.extend(['--broker', FLOWER_CONFIG['broker']])
        args.extend(['--port', str(FLOWER_CONFIG['port'])])
        args.extend(['--address', FLOWER_CONFIG['address']])
        
        # Authentication
        if FLOWER_CONFIG.get('basic_auth'):
            args.extend(['--basic_auth', FLOWER_CONFIG['basic_auth']])
        
        # Database
        if FLOWER_CONFIG.get('db'):
            args.extend(['--db', FLOWER_CONFIG['db']])
        
        # URL prefix
        if FLOWER_CONFIG.get('url_prefix'):
            args.extend(['--url_prefix', FLOWER_CONFIG['url_prefix']])
        
        # Auto-refresh
        if FLOWER_CONFIG.get('auto_refresh'):
            args.extend(['--auto_refresh', 'True'])
        
        # Logging level
        args.extend(['--logging', FLOWER_CONFIG['logging']])
        
        # Enable events
        if FLOWER_CONFIG.get('enable_events'):
            args.extend(['--enable_events', 'True'])
        
        # Natural time
        if FLOWER_CONFIG.get('natural_time'):
            args.extend(['--natural_time', 'True'])
        
        # Task columns
        if FLOWER_CONFIG.get('tasks_columns'):
            args.extend(['--tasks_columns', FLOWER_CONFIG['tasks_columns']])
        
        # Purge offline workers
        if FLOWER_CONFIG.get('purge_offline_workers'):
            args.extend(['--purge_offline_workers', str(FLOWER_CONFIG['purge_offline_workers'])])
        
        # Start Flower
        flower_command = FlowerCommand()
        flower_command.run_from_argv('flower', args)
        
    except ImportError:
        print("Flower is not installed. Install it with: pip install flower")
        raise
    except Exception as e:
        print(f"Failed to start Flower: {e}")
        raise


if __name__ == '__main__':
    start_flower()
