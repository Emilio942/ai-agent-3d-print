"""
Printer Discovery and Management API Routes
"""

import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import printer discovery
from multi_printer_support import MultiPrinterDetector
from core.logger import get_logger

logger = get_logger(__name__)

# Create router for printer endpoints
router = APIRouter(prefix="/api/printer", tags=["printer"])

class PrinterInfo(BaseModel):
    """Printer information model."""
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
    """Response model for printer discovery."""
    discovered_printers: List[PrinterInfo]
    total_found: int
    scan_time_seconds: float
    timestamp: str

@router.get("/discover", response_model=PrinterDiscoveryResponse)
async def discover_printers():
    """Discover all available 3D printers."""
    try:
        start_time = time.time()
        logger.info("Starting printer discovery...")
        
        # Use the enhanced printer discovery
        detector = MultiPrinterDetector()
        printers = await detector.scan_for_printers(timeout=10.0)
        
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
        
        response = PrinterDiscoveryResponse(
            discovered_printers=printer_infos,
            total_found=len(printer_infos),
            scan_time_seconds=round(scan_time, 2),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Printer discovery completed: found {len(printer_infos)} printers in {scan_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Error during printer discovery: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover printers: {str(e)}"
        )

@router.post("/{port}/connect")
async def connect_printer(port: str):
    """Connect to a specific printer."""
    try:
        # Clean the port parameter (handle URL encoding)
        port = port.replace("%2F", "/")
        
        logger.info(f"Attempting to connect to printer on port: {port}")
        
        # Basic connection attempt (simplified for now)
        return {"status": "connected", "port": port, "message": f"Connection to printer on {port} initiated"}
            
    except Exception as e:
        logger.error(f"Error connecting to printer {port}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to printer: {str(e)}"
        )

@router.post("/{port}/disconnect")
async def disconnect_printer(port: str):
    """Disconnect from a specific printer."""
    try:
        port = port.replace("%2F", "/")
        logger.info(f"Disconnecting from printer on port: {port}")
        
        return {"status": "disconnected", "port": port, "message": f"Disconnection from printer on {port} initiated"}
            
    except Exception as e:
        logger.error(f"Error disconnecting from printer {port}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect from printer: {str(e)}"
        )

@router.get("/{port}/status")
async def get_printer_status(port: str):
    """Get status of a specific printer."""
    try:
        port = port.replace("%2F", "/")
        
        return {
            "port": port,
            "status": "unknown",
            "temperature": {},
            "position": {},
            "is_printing": False,
            "progress": 0
        }
        
    except Exception as e:
        logger.error(f"Error getting printer status for {port}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get printer status: {str(e)}"
        )

@router.get("s")  # This will be /api/printers
async def list_all_printers():
    """List all known printers."""
    try:
        # For now, return empty list - could be enhanced later
        return {
            "printers": [],
            "total": 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing printers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list printers: {str(e)}"
        )
