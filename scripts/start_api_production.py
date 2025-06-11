"""
Production startup script for the AI Agent 3D Print System API.

This script is optimized for production deployment with proper
configuration for scaling and monitoring.
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
    # Production server configuration
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",  # Listen on all interfaces
        port=int(os.getenv("PORT", 8000)),
        workers=int(os.getenv("WORKERS", 1)),  # Single worker for now due to in-memory state
        loop="uvloop",  # Use uvloop for better performance
        log_level=os.getenv("LOG_LEVEL", "info"),
        access_log=True,
        server_header=False,  # Don't reveal server info
        date_header=False,
        # SSL configuration (if certificates are available)
        ssl_keyfile=os.getenv("SSL_KEYFILE"),
        ssl_certfile=os.getenv("SSL_CERTFILE"),
    )
