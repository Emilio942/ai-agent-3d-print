#!/usr/bin/env python3
"""
Minimal API server test for new endpoints
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only what we need for testing
from core.voice_control import VoiceControlManager
from core.analytics_dashboard import AnalyticsDashboard  
from core.template_library import TemplateLibrary

app = FastAPI(title="AI Agent 3D Print - New Features Test")

# Initialize systems
voice_control = VoiceControlManager()
analytics_dashboard = AnalyticsDashboard()
template_library = TemplateLibrary()

@app.get("/")
async def root():
    return {"message": "AI Agent 3D Print - New Features Test API"}

# Voice Control Test Endpoints
@app.get("/voice/status")
async def get_voice_control_status():
    try:
        status = await voice_control.get_status()
        return JSONResponse({"success": True, "status": status})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/voice/command/test")
async def test_voice_command():
    try:
        command = await voice_control.process_text_command("print a small gear")
        return JSONResponse({
            "success": True,
            "command": {
                "intent": command.intent,
                "parameters": command.parameters,
                "confidence": command.confidence,
                "recognized_text": command.command
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

# Analytics Test Endpoints
@app.get("/analytics/overview")
async def get_analytics_overview():
    try:
        overview = await analytics_dashboard.get_overview()
        return JSONResponse({"success": True, "overview": overview})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/analytics/health")
async def get_system_health():
    try:
        health = await analytics_dashboard.get_system_health()
        return JSONResponse({"success": True, "health": health})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

# Template Library Test Endpoints
@app.get("/templates")
async def list_templates():
    try:
        templates = await template_library.list_templates()
        return JSONResponse({"success": True, "templates": templates})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/templates/categories")
async def get_template_categories():
    try:
        categories = await template_library.get_categories()
        return JSONResponse({"success": True, "categories": categories})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/templates/search")
async def search_templates():
    try:
        templates = await template_library.search_templates(category="mechanical")
        return JSONResponse({"success": True, "templates": templates})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

if __name__ == "__main__":
    print("🚀 Starting minimal API test server...")
    print("📋 Available endpoints:")
    print("   - GET  /voice/status")
    print("   - POST /voice/command/test")
    print("   - GET  /analytics/overview")
    print("   - GET  /analytics/health")
    print("   - GET  /templates")
    print("   - GET  /templates/categories")
    print("   - POST /templates/search")
    print()
    print("🌐 Server will be available at: http://localhost:8002")
    
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
