#!/usr/bin/env python3
"""
Simple web server for testing the AI Agent 3D Print System web interface
"""

import os
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from printer_support.multi_printer_support import MultiPrinterDetector
    PRINTER_SUPPORT = True
except ImportError as e:
    print(f"Warning: Printer support not available: {e}")
    PRINTER_SUPPORT = False

# Import additional route modules if available
try:
    from api.advanced_routes import router as advanced_router
    ADVANCED_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Advanced routes not available: {e}")
    ADVANCED_ROUTES_AVAILABLE = False

try:
    from api.preview_routes import router as preview_router
    PREVIEW_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Preview routes not available: {e}")
    PREVIEW_ROUTES_AVAILABLE = False

try:
    from api.analytics_routes import router as analytics_router
    ANALYTICS_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Analytics routes not available: {e}")
    ANALYTICS_ROUTES_AVAILABLE = False

try:
    from api.websocket_routes import router as websocket_router
    WEBSOCKET_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: WebSocket routes not available: {e}")
    WEBSOCKET_ROUTES_AVAILABLE = False

app = FastAPI(
    title="AI Agent 3D Print System",
    description="Web interface for the AI Agent 3D Print System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers if available
if ADVANCED_ROUTES_AVAILABLE:
    app.include_router(advanced_router)
    print("✅ Advanced routes registered")

if PREVIEW_ROUTES_AVAILABLE:
    app.include_router(preview_router)
    print("✅ Preview routes registered")

if ANALYTICS_ROUTES_AVAILABLE:
    app.include_router(analytics_router)
    print("✅ Analytics routes registered")

if WEBSOCKET_ROUTES_AVAILABLE:
    app.include_router(websocket_router)
    print("✅ WebSocket routes registered")

# Mount static files
app.mount("/web", StaticFiles(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")), name="web")

# Models
class PrinterInfo(BaseModel):
    port: str
    name: str
    brand: str
    firmware_type: str
    build_volume: List[int]
    is_connected: bool
    status: str
    temperature: Optional[Dict[str, float]] = None
    profile_name: Optional[str] = None

class PrinterDiscoveryResponse(BaseModel):
    discovered_printers: List[PrinterInfo]
    total_found: int
    scan_time_seconds: float
    timestamp: str

# Global detector instance
printer_detector = None

if PRINTER_SUPPORT:
    try:
        printer_detector = MultiPrinterDetector()
    except Exception as e:
        print(f"Warning: Could not initialize printer detector: {e}")
        PRINTER_SUPPORT = False

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "printer_support": PRINTER_SUPPORT
    }

@app.get("/api/health")
async def api_health_check():
    """Redirect /api/health to /health endpoint."""
    return await health_check()

@app.get("/api/docs")
async def api_docs_redirect():
    """Redirect /api/docs to /docs for API documentation."""
    return RedirectResponse(url="/docs")

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon.ico."""
    try:
        favicon_path = Path(os.path.dirname(os.path.dirname(__file__))) / "web" / "favicon.ico"
        if favicon_path.exists():
            with open(favicon_path, "rb") as f:
                return Response(content=f.read(), media_type="image/x-icon")
        else:
            # Return a simple 404 instead of raising an exception
            raise HTTPException(status_code=404, detail="Favicon not found")
    except Exception:
        raise HTTPException(status_code=404, detail="Favicon not found")

@app.get("/api/printer/discover", response_model=PrinterDiscoveryResponse)
async def discover_printers():
    """Discover all available 3D printers."""
    if not PRINTER_SUPPORT or not printer_detector:
        raise HTTPException(
            status_code=503,
            detail="Printer support not available"
        )
    
    try:
        start_time = time.time()
        
        # Run discovery in thread to avoid blocking
        printers = await printer_detector.scan_for_printers()
        
        # Convert to response format
        printer_infos = []
        for printer in printers:
            info = PrinterInfo(
                port=printer.get("port", "unknown"),
                name=printer.get("name", "Unknown Printer"),
                brand=printer.get("brand", "generic").title(),
                firmware_type=printer.get("firmware_type", "unknown").title(),
                build_volume=list(printer.get("build_volume", (200, 200, 200))),
                is_connected=printer.get("is_connected", False),
                status=printer.get("status", "available"),
                profile_name=printer.get("profile_name")
            )
            printer_infos.append(info)
        
        scan_time = time.time() - start_time
        
        return PrinterDiscoveryResponse(
            discovered_printers=printer_infos,
            total_found=len(printer_infos),
            scan_time_seconds=round(scan_time, 2),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover printers: {str(e)}"
        )

@app.post("/api/printer/{port}/connect")
async def connect_printer(port: str):
    """Connect to a specific printer."""
    if not PRINTER_SUPPORT or not printer_detector:
        raise HTTPException(
            status_code=503,
            detail="Printer support not available"
        )
    
    try:
        # Clean the port parameter
        port = port.replace("%2F", "/")
        
        # Use detector to connect
        success = printer_detector.connect_to_printer(port)
        
        if success:
            return {
                "status": "connected",
                "port": port,
                "message": f"Successfully connected to printer on {port}"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to connect to printer on {port}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to printer: {str(e)}"
        )

@app.post("/api/printer/{port}/disconnect")
async def disconnect_printer(port: str):
    """Disconnect from a specific printer."""
    if not PRINTER_SUPPORT or not printer_detector:
        raise HTTPException(
            status_code=503,
            detail="Printer support not available"
        )
    
    try:
        port = port.replace("%2F", "/")
        
        # Use detector to disconnect
        success = printer_detector.disconnect_printer(port)
        
        return {
            "status": "disconnected" if success else "not_connected",
            "port": port,
            "message": f"{'Successfully disconnected from' if success else 'Printer was not connected on'} {port}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect from printer: {str(e)}"
        )

@app.get("/api/printer/{port}/status")
async def get_printer_status(port: str):
    """Get status of a specific printer."""
    if not PRINTER_SUPPORT or not printer_detector:
        raise HTTPException(
            status_code=503,
            detail="Printer support not available"
        )
    
    try:
        port = port.replace("%2F", "/")
        
        # Get printer status
        status = printer_detector.get_printer_status(port)
        
        return {
            "port": port,
            "status": status.get("status", "unknown"),
            "temperature": status.get("temperature", {}),
            "position": status.get("position", {}),
            "is_printing": status.get("is_printing", False),
            "progress": status.get("progress", 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get printer status: {str(e)}"
        )

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main web interface."""
    try:
        index_path = Path(os.path.dirname(os.path.dirname(__file__))) / "web" / "index.html"
        
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content)
        else:
            return HTMLResponse(
                content="<h1>AI Agent 3D Print System</h1><p>Web interface not found.</p>",
                status_code=404
            )
    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Error</h1><p>Failed to load web interface: {e}</p>",
            status_code=500
        )

# Include the additional routers if available
if ADVANCED_ROUTES_AVAILABLE:
    app.include_router(advanced_router, tags=["advanced"])
    print("✅ Advanced routes included")

if ANALYTICS_ROUTES_AVAILABLE:
    app.include_router(analytics_router, tags=["analytics"])
    print("✅ Analytics routes included")

if WEBSOCKET_ROUTES_AVAILABLE:
    app.include_router(websocket_router, prefix="/api/ws", tags=["websocket"])
    print("✅ WebSocket routes included")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    print("🚀 Starting AI Agent 3D Print System Web Server...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🖨️ Printer support: {'✅ Available' if PRINTER_SUPPORT else '❌ Not available'}")
    print(f"🌐 Web interface: http://localhost:{port}")
    print(f"📚 API docs: http://localhost:{port}/docs")
    
    uvicorn.run(
        "web_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
