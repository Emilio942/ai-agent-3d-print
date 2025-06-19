#!/usr/bin/env python3
"""
Simplified API startup script for debugging.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
from core.parent_agent import ParentAgent

# Create FastAPI app
app = FastAPI(title="AI Agent 3D Print System API - Debug")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
app_state = {
    "parent_agent": None,
    "system_health": {"status": "initializing"}
}

@app.on_event("startup")
async def startup_event():
    """Startup event."""
    try:
        print("Starting simplified API...")
        
        # Initialize ParentAgent
        print("Initializing ParentAgent...")
        parent_agent = ParentAgent()
        await parent_agent.initialize()
        app_state["parent_agent"] = parent_agent
        app_state["system_health"]["status"] = "healthy"
        
        print("✓ API started successfully")
        
    except Exception as e:
        print(f"✗ API startup failed: {e}")
        app_state["system_health"]["status"] = "unhealthy"
        raise

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": app_state["system_health"]["status"], "timestamp": "2025-06-18T17:06:00Z"}

@app.get("/api/status")
async def api_status():
    """API status endpoint."""
    return {
        "api_version": "1.0.0-debug",
        "status": app_state["system_health"]["status"],
        "parent_agent_status": app_state["parent_agent"].get_status() if app_state["parent_agent"] else None
    }

@app.post("/api/print-request")
async def create_print_request(data: dict):
    """Simple print request endpoint."""
    try:
        if not app_state["parent_agent"]:
            raise HTTPException(status_code=503, detail="System not ready")
        
        # Simple test workflow
        result = await app_state["parent_agent"].execute_research_workflow({
            "user_request": data.get("description", "test object"),
            "requirements": "debug test"
        })
        
        return {
            "job_id": "debug-123",
            "status": "completed" if result.success else "failed",
            "message": "Debug test completed",
            "result": result.success
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting debug API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
