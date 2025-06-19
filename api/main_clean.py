"""
FastAPI Backend for AI Agent 3D Print System - Clean Version
"""

import asyncio
import json
import logging
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core system components
from core.parent_agent import ParentAgent
from core.logger import get_logger

logger = get_logger(__name__)

# Global application state
app_state = {
    "parent_agent": None,
    "system_health": {
        "status": "starting",
        "agents_initialized": False,
        "last_health_check": None
    },
    "websocket_connections": {},
    "active_workflows": {},
    "startup_time": datetime.now()
}

# System health model
class SystemHealth(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    active_workflows: int
    total_completed: int
    agents_status: dict
    system_metrics: dict

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting AI Agent 3D Print System API...")
    
    try:
        # Initialize ParentAgent with all sub-agents
        parent_agent = ParentAgent()
        app_state["parent_agent"] = parent_agent
        
        # Initialize agents
        logger.info("Initializing agent system...")
        await parent_agent.initialize()
        app_state["system_health"]["agents_initialized"] = True
        
        app_state["system_health"]["status"] = "healthy"
        
        logger.info("API startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        app_state["system_health"]["status"] = "unhealthy"
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Agent 3D Print System API...")
    try:
        if app_state["parent_agent"]:
            await app_state["parent_agent"].shutdown()
        logger.info("API shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="AI Agent 3D Print System API",
    description="FastAPI backend for the AI Agent 3D Print System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health", response_model=SystemHealth)
async def health_check():
    """Get system health status."""
    uptime = (datetime.now() - app_state["startup_time"]).total_seconds()
    
    # Get basic system metrics
    import psutil
    system_metrics = {
        "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
        "memory_usage_percent": psutil.virtual_memory().percent,
        "disk_usage_percent": psutil.disk_usage('/').percent,
        "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0,
        "uptime_seconds": uptime,
        "network_connections": len(psutil.net_connections()),
        "active_threads": len(psutil.Process().threads()),
        "active_connections": len(app_state["websocket_connections"])
    }
    
    agents_status = {"parent": "running"}
    if app_state["parent_agent"]:
        try:
            agents_status.update(await app_state["parent_agent"].get_status())
        except:
            pass
    
    return SystemHealth(
        status=app_state["system_health"]["status"],
        version="1.0.0",
        uptime_seconds=uptime,
        active_workflows=len(app_state["active_workflows"]),
        total_completed=0,
        agents_status=agents_status,
        system_metrics=system_metrics
    )

# Web interface endpoints
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main web interface HTML page."""
    try:
        index_path = Path("web/index.html")
        
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content)
        else:
            return HTMLResponse(
                content="<h1>AI Agent 3D Print System</h1><p>Web interface not found. Please ensure web/index.html exists.</p>",
                status_code=404
            )
    except Exception as e:
        logger.error(f"Error serving main interface: {e}")
        return HTMLResponse(
            content="<h1>Error</h1><p>Failed to load web interface</p>",
            status_code=500
        )

# Mount static files
app.mount("/web", StaticFiles(directory="web"), name="web")

# Include printer routes
try:
    from api.printer_routes import router as printer_router
    app.include_router(printer_router)
    logger.info("Printer discovery endpoints registered successfully")
except ImportError as e:
    logger.warning(f"Printer discovery endpoints not available: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        access_log=True
    )
