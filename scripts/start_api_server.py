"""
Development server startup script for the AI Agent 3D Print System API.

This script starts the FastAPI server with development-friendly settings.
For production deployment, use a proper WSGI server like Gunicorn or Uvicorn
with production configuration.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from api.main import app

if __name__ == "__main__":
    # Development server configuration
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",  # Use localhost for development
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="debug",
        access_log=True,
        reload_dirs=[str(project_root)],  # Watch project directory for changes
        reload_excludes=["logs/*", "data/*", "cache/*", "__pycache__/*"]
    )
