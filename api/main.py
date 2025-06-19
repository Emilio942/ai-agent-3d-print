"""
FastAPI Backend for AI Agent 3D Print System

This is the production FastAPI backend that provides REST API endpoints
and WebSocket communication for the AI Agent 3D Print System. It integrates
all the agents (Research, CAD, Slicer/Printer) through the ParentAgent
orchestration system.

Key Features:
- REST API endpoints for print requests and status
- WebSocket for real-time progress updates
- Integration with all agent systems
- Comprehensive error handling and logging
- Background task processing for workflows
- Production-ready configuration

Required endpoints:
- POST /api/print-request - Start a new print workflow
- GET /api/status/{job_id} - Get job status and progress
- WebSocket /ws/progress - Real-time progress updates
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
from typing import Dict, List, Optional, Set, Any
from uuid import uuid4

import uvicorn
from fastapi import (
    BackgroundTasks, Depends, FastAPI, HTTPException, Query, WebSocket,
    WebSocketDisconnect, status, File, UploadFile, Form
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core system components
from core.parent_agent import ParentAgent
from core.logger import get_logger
from core.exceptions import (
    AgentCommunicationError, ValidationError,
    WorkflowError, PrinterAgentError
)
from config.settings import load_config
from core.health_monitor import health_monitor, setup_default_monitoring
from agents.image_processing_agent import ImageProcessingAgent

# Import printer discovery (optional)
try:
    from printer_support.multi_printer_support import MultiPrinterDetector
    from printer_support.enhanced_printer_agent import EnhancedPrinterAgent
    PRINTER_SUPPORT_AVAILABLE = True
    # Create alias for compatibility
    PrinterDiscovery = MultiPrinterDetector
except ImportError:
    PRINTER_SUPPORT_AVAILABLE = False
    print("Warning: Printer support modules not available")
    # Create dummy class
    class PrinterDiscovery:
        def scan_serial_ports(self):
            return []
        def detect_printer_type(self, port):
            return {"type": "unknown", "brand": "generic"}

# Import API schemas
from core.api_schemas import (
    CreateWorkflowRequest, WorkflowResponse, WorkflowStatusResponse,
    SystemHealthResponse, ErrorResponse, ProgressUpdate, StatusUpdate,
    Workflow, WorkflowState, WorkflowStep, WorkflowStepStatus, TaskResult, AgentType
)

# =============================================================================
# CONFIGURATION AND SETUP
# =============================================================================

# Load system configuration
config = load_config()
logger = get_logger(__name__)

# Import API routers (after logger is defined)
try:
    from api.advanced_routes import router as advanced_router
    ADVANCED_ROUTES_AVAILABLE = True
except ImportError as e:
    ADVANCED_ROUTES_AVAILABLE = False
    logger.warning(f"Advanced routes not available: {e}")

try:
    from api.analytics_routes import router as analytics_router
    ANALYTICS_ROUTES_AVAILABLE = True
except ImportError as e:
    ANALYTICS_ROUTES_AVAILABLE = False
    logger.warning(f"Analytics routes not available: {e}")

try:
    from api.websocket_routes import router as websocket_router
    WEBSOCKET_ROUTES_AVAILABLE = True
except ImportError as e:
    WEBSOCKET_ROUTES_AVAILABLE = False
    logger.warning(f"WebSocket routes not available: {e}")

try:
    from api.security_performance_endpoints import router as security_router
    SECURITY_ROUTES_AVAILABLE = True
except ImportError as e:
    SECURITY_ROUTES_AVAILABLE = False
    logger.warning(f"Security routes not available: {e}")

# Application state
app_state = {
    "parent_agent": None,
    "active_workflows": {},
    "websocket_connections": {},
    "startup_time": None,
    "system_health": {
        "status": "starting",
        "agents_initialized": False,
        "last_health_check": None
    }
}

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    try:
        logger.info("Starting AI Agent 3D Print System API...")
        app_state["startup_time"] = datetime.now()
        
        # Initialize ParentAgent with all sub-agents
        parent_agent = ParentAgent()
        app_state["parent_agent"] = parent_agent
        
        # Initialize agents
        logger.info("Initializing agent system...")
        await parent_agent.initialize()
        app_state["system_health"]["agents_initialized"] = True
        
        # Initialize health monitoring
        logger.info("Setting up health monitoring...")
        # Temporarily disabled due to timeout issues
        # await setup_default_monitoring()
        
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
        # Stop health monitoring
        health_monitor.stop_monitoring()
        
        if app_state["parent_agent"]:
            await app_state["parent_agent"].shutdown()
        
        # Close all WebSocket connections
        for workflow_id, connections in app_state["websocket_connections"].items():
            for websocket in connections.copy():
                try:
                    await websocket.close()
                except:
                    pass
        
        logger.info("API shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="AI Agent 3D Print System API",
    description="Production FastAPI backend for the AI Agent 3D Print System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Mount static files for web interface
app.mount("/web", StaticFiles(directory="web"), name="web")

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security and performance middleware
try:
    from api.middleware.security_middleware import SecurityMiddleware, SecurityHeadersMiddleware
    from api.middleware.performance_middleware import (
        PerformanceMiddleware, ResourceLimitMiddleware, CacheControlMiddleware
    )
    
    # Security middleware (should be first for security checks)
    # Temporarily disabled for mass testing
    # app.add_middleware(SecurityMiddleware)
    
    # Performance middleware
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(ResourceLimitMiddleware, max_concurrent_requests=100)
    app.add_middleware(CacheControlMiddleware)
    
    # Security headers (should be last to ensure headers are set)
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info("Security and performance middleware loaded successfully (SecurityMiddleware disabled for testing)")
    
except ImportError as e:
    logger.warning(f"Middleware import failed: {e}. Running without enhanced security/performance features.")
    
    # Fallback to basic security headers only
    from starlette.middleware.base import BaseHTTPMiddleware
    
    class BasicSecurityMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response
    
    app.add_middleware(BasicSecurityMiddleware)
    logger.info("Basic security headers middleware loaded as fallback")

# =============================================================================
# API ROUTER REGISTRATION
# =============================================================================

# Include API routers
if ADVANCED_ROUTES_AVAILABLE:
    app.include_router(advanced_router)
    logger.info("Advanced routes registered")

if ANALYTICS_ROUTES_AVAILABLE:
    app.include_router(analytics_router)
    logger.info("Analytics routes registered")

if WEBSOCKET_ROUTES_AVAILABLE:
    app.include_router(websocket_router)
    logger.info("WebSocket routes registered")

if SECURITY_ROUTES_AVAILABLE:
    app.include_router(security_router)
    logger.info("Security routes registered")

# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "message": str(exc),
            "details": getattr(exc, 'details', None)
        }
    )

@app.exception_handler(AgentCommunicationError)
async def agent_execution_exception_handler(request, exc: AgentCommunicationError):
    """Handle agent execution errors."""
    logger.error(f"Agent execution error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "agent_execution_error",
            "message": str(exc),
            "agent_type": getattr(exc, 'agent_type', None)
        }
    )

@app.exception_handler(WorkflowError)
async def workflow_exception_handler(request, exc: WorkflowError):
    """Handle workflow errors."""
    logger.error(f"Workflow error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "workflow_error",
            "message": str(exc),
            "workflow_id": getattr(exc, 'workflow_id', None)
        }
    )

@app.exception_handler(PrinterAgentError)
async def printer_exception_handler(request, exc: PrinterAgentError):
    """Handle printer errors."""
    logger.error(f"Printer error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "printer_error",
            "message": str(exc),
            "printer_status": getattr(exc, 'printer_status', None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle all other exceptions."""
    logger.error(f"Unexpected error: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred"
        }
    )

# =============================================================================
# DEPENDENCY FUNCTIONS
# =============================================================================

async def get_parent_agent() -> ParentAgent:
    """Get the ParentAgent instance."""
    parent_agent = app_state.get("parent_agent")
    if not parent_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent system not initialized"
        )
    return parent_agent

async def get_workflow(job_id: str) -> Workflow:
    """Get workflow by ID or raise 404."""
    workflow = app_state["active_workflows"].get(job_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {job_id} not found"
        )
    return workflow

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_workflow_progress(workflow: Dict[str, Any]) -> float:
    """Calculate workflow progress percentage."""
    try:
        if workflow.get("status") == "completed":
            return 100.0
        elif workflow.get("status") == "failed":
            return 0.0
        elif workflow.get("status") == "cancelled":
            return workflow.get("progress", 0.0)
        
        # Calculate based on completed steps
        steps = workflow.get("steps", [])
        if not steps:
            return 0.0
        
        completed_steps = sum(1 for step in steps if step.get("status") == "completed")
        return (completed_steps / len(steps)) * 100.0
    except Exception:
        return 0.0

def get_current_workflow_step(workflow: Dict[str, Any]) -> str:
    """Get the current workflow step description."""
    try:
        status = workflow.get("status", "unknown")
        if status == "completed":
            return "Workflow completed successfully"
        elif status == "failed":
            return f"Workflow failed: {workflow.get('error', 'Unknown error')}"
        elif status == "cancelled":
            return "Workflow cancelled"
        
        # Find current step
        steps = workflow.get("steps", [])
        for step in steps:
            if step.get("status") == "running":
                return f"Running: {step.get('name', 'Unknown step')}"
        
        # If no running step, find next pending step
        for step in steps:
            if step.get("status") == "pending":
                return f"Next: {step.get('name', 'Unknown step')}"
        
        return "Initializing workflow"
    except Exception:
        return "Status unknown"

async def broadcast_workflow_update(job_id: str, update_data: Dict[str, Any]):
    """Broadcast workflow updates to WebSocket connections."""
    try:
        connections = app_state["websocket_connections"].get(job_id, set())
        if connections:
            message = json.dumps(update_data)
            for websocket in connections.copy():
                try:
                    await websocket.send_text(message)
                except Exception:
                    # Remove disconnected websocket
                    connections.discard(websocket)
        
        # Update workflow in app state
        if job_id in app_state["active_workflows"]:
            app_state["active_workflows"][job_id].update(update_data)
    except Exception as e:
        logger.error(f"Error broadcasting workflow update: {e}")

async def process_print_workflow(job_id: str, workflow: Dict[str, Any], parent_agent: ParentAgent):
    """Process a print workflow in the background."""
    try:
        logger.info(f"Starting print workflow {job_id}")
        
        # Update workflow status
        workflow["status"] = "running"
        workflow["steps"] = [
            {"name": "Research", "status": "pending"},
            {"name": "CAD Generation", "status": "pending"},
            {"name": "Slicing", "status": "pending"},
            {"name": "Printing", "status": "pending"}
        ]
        
        await broadcast_workflow_update(job_id, {"status": "running", "steps": workflow["steps"]})
        
        # Execute workflow steps
        user_request = workflow.get("user_request", "")
        
        # Step 1: Research
        workflow["steps"][0]["status"] = "running"
        await broadcast_workflow_update(job_id, {"steps": workflow["steps"]})
        
        research_result = await parent_agent.research_agent.process_request(user_request)
        
        workflow["steps"][0]["status"] = "completed"
        workflow["steps"][1]["status"] = "running"
        await broadcast_workflow_update(job_id, {"steps": workflow["steps"]})
        
        # Step 2: CAD Generation
        cad_result = await parent_agent.cad_agent.generate_cad(research_result)
        
        workflow["steps"][1]["status"] = "completed"
        workflow["steps"][2]["status"] = "running"
        await broadcast_workflow_update(job_id, {"steps": workflow["steps"]})
        
        # Step 3: Slicing
        slicer_result = await parent_agent.slicer_agent.slice_model(cad_result)
        
        workflow["steps"][2]["status"] = "completed"
        workflow["steps"][3]["status"] = "running"
        await broadcast_workflow_update(job_id, {"steps": workflow["steps"]})
        
        # Step 4: Printing (simulation)
        await asyncio.sleep(2)  # Simulate printing process
        
        workflow["steps"][3]["status"] = "completed"
        workflow["status"] = "completed"
        
        await broadcast_workflow_update(job_id, {
            "status": "completed",
            "steps": workflow["steps"],
            "output_files": {
                "stl_file": f"/output/{job_id}.stl",
                "gcode_file": f"/output/{job_id}.gcode"
            }
        })
        
        logger.info(f"Print workflow {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in print workflow {job_id}: {e}")
        workflow["status"] = "failed"
        workflow["error"] = str(e)
        await broadcast_workflow_update(job_id, {"status": "failed", "error": str(e)})

async def process_image_workflow(job_id: str, workflow: Dict[str, Any], parent_agent: ParentAgent):
    """Process an image-to-3D workflow in the background."""
    try:
        logger.info(f"Starting image workflow {job_id}")
        
        # Update workflow status
        workflow["status"] = "running"
        workflow["steps"] = [
            {"name": "Image Processing", "status": "pending"},
            {"name": "3D Model Generation", "status": "pending"},
            {"name": "Slicing", "status": "pending"},
            {"name": "Printing", "status": "pending"}
        ]
        
        await broadcast_workflow_update(job_id, {"status": "running", "steps": workflow["steps"]})
        
        # Execute workflow steps similar to process_print_workflow
        # This is a simplified version - actual implementation would use image processing
        
        for i, step in enumerate(workflow["steps"]):
            step["status"] = "running"
            await broadcast_workflow_update(job_id, {"steps": workflow["steps"]})
            
            # Simulate processing time
            await asyncio.sleep(1)
            
            step["status"] = "completed"
        
        workflow["status"] = "completed"
        await broadcast_workflow_update(job_id, {
            "status": "completed",
            "steps": workflow["steps"],
            "output_files": {
                "stl_file": f"/output/{job_id}.stl",
                "gcode_file": f"/output/{job_id}.gcode"
            }
        })
        
        logger.info(f"Image workflow {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in image workflow {job_id}: {e}")
        workflow["status"] = "failed"
        workflow["error"] = str(e)
        await broadcast_workflow_update(job_id, {"status": "failed", "error": str(e)})

# =============================================================================
# PYDANTIC MODELS FOR API
# =============================================================================

class PrintRequest(BaseModel):
    """Request model for starting a new print job."""
    user_request: str = Field(..., min_length=10, max_length=1000,
                             description="Natural language description of the object to print")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    printer_profile: Optional[str] = Field("ender3_pla", 
                                          description="Printer and material profile")
    quality_level: Optional[str] = Field("standard", 
                                        description="Print quality: draft, standard, fine, ultra")
    metadata: Optional[Dict] = Field(default_factory=dict, 
                                   description="Additional metadata")

class PrintStatus(BaseModel):
    """Response model for print job status."""
    job_id: str
    status: str
    progress_percentage: float = Field(ge=0, le=100)
    current_step: Optional[str] = None
    message: str
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    output_files: Optional[Dict[str, str]] = None

class SystemHealth(BaseModel):
    """System health status."""
    status: str
    version: str
    uptime_seconds: float
    active_workflows: int
    total_completed: int
    agents_status: Dict[str, str]
    system_metrics: Dict[str, float]

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

# =============================================================================
# REST API ENDPOINTS
# =============================================================================

@app.post("/api/print-request", response_model=PrintStatus, status_code=status.HTTP_201_CREATED)
async def create_print_request(
    request: PrintRequest,
    background_tasks: BackgroundTasks,
    parent_agent: ParentAgent = Depends(get_parent_agent)
):
    """
    Start a new 3D print workflow.
    
    This endpoint accepts a natural language description of an object to print
    and starts the complete workflow: Research → CAD → Slicing → Printing
    """
    try:
        # Generate unique job ID
        job_id = str(uuid4())
        
        # Create workflow
        workflow = Workflow(
            workflow_id=job_id,
            user_request=request.user_request,
            user_id=request.user_id or "anonymous",
            state=WorkflowState.PENDING,
            metadata={
                **request.metadata,
                "printer_profile": request.printer_profile,
                "quality_level": request.quality_level,
                "api_endpoint": "print-request"
            }
        )
        
        # Store workflow
        app_state["active_workflows"][job_id] = workflow
        app_state["websocket_connections"][job_id] = set()
        
        logger.info(f"Created print request {job_id}: {request.user_request[:50]}...")
        
        # Start workflow processing in background
        background_tasks.add_task(process_print_workflow, job_id, workflow, parent_agent)
        
        # Return initial status
        return PrintStatus(
            job_id=job_id,
            status=workflow.state,
            progress_percentage=0.0,
            current_step="Initializing workflow",
            message="Print request received and queued for processing",
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except Exception as e:
        logger.error(f"Failed to create print request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create print request: {str(e)}"
        )

@app.post("/api/image-print-request", response_model=PrintStatus, status_code=status.HTTP_201_CREATED)
async def create_image_print_request(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="Image file to convert to 3D model"),
    priority: str = Form("normal", description="Priority level: low, normal, high, urgent"),
    extrusion_height: float = Form(5.0, description="Height to extrude the image (mm)"),
    base_thickness: float = Form(1.0, description="Thickness of the base plate (mm)"),
    user_id: Optional[str] = Form(None, description="Optional user identifier"),
    parent_agent: ParentAgent = Depends(get_parent_agent)
):
    """Start a new 3D print workflow from an uploaded image."""
    try:
        # Validate image file
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Please upload an image file"
            )
        
        # Validate parameters
        if extrusion_height <= 0 or extrusion_height > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extrusion height must be between 0.1 and 50 mm"
            )
        
        if base_thickness <= 0 or base_thickness > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Base thickness must be between 0.1 and 10 mm"
            )
        
        # Generate unique job ID
        job_id = str(uuid4())
        
        logger.info(f"Starting image→3D workflow: {job_id} for '{image.filename}'")
        
        # Create workflow with image processing
        workflow = Workflow(
            workflow_id=job_id,
            user_request=f"Convert uploaded image '{image.filename}' to 3D model",
            user_id=user_id or "anonymous",
            state=WorkflowState.PENDING,
            metadata={
                "input_type": "image",
                "image_filename": image.filename,
                "image_content_type": image.content_type,
                "extrusion_height": extrusion_height,
                "base_thickness": base_thickness,
                "priority": priority,
                "api_endpoint": "image-print-request"
            }
        )
        
        # Store workflow
        app_state["active_workflows"][job_id] = workflow
        app_state["websocket_connections"][job_id] = set()
        
        # Store image data for processing
        image_data = await image.read()
        workflow.metadata["image_data"] = image_data
        
        logger.info(f"Created image print workflow {job_id}: {image.filename}")
        
        # Start workflow processing in background
        background_tasks.add_task(process_image_workflow, job_id, workflow, parent_agent)
        
        # Return initial status
        return PrintStatus(
            job_id=job_id,
            status=workflow.state,
            progress_percentage=0.0,
            current_step="Initializing image processing",
            message=f"Image '{image.filename}' received and queued for processing",
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process image upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image upload: {str(e)}"
        )

@app.get("/api/status/{job_id}", response_model=PrintStatus)
async def get_job_status(
    job_id: str,
    workflow: Workflow = Depends(get_workflow)
):
    """
    Get the current status and progress of a print job.
    
    Returns detailed information about the workflow state, progress,
    current step, and any output files generated.
    """
    try:
        # Calculate progress based on workflow state and steps
        progress_percentage = calculate_workflow_progress(workflow)
        
        # Get current step
        current_step = get_current_workflow_step(workflow)
        
        # Prepare output files info
        output_files = {}
        if workflow.steps:
            for step in workflow.steps:
                if step.status == WorkflowStepStatus.COMPLETED and step.output_data:
                    if "stl_file" in step.output_data:
                        output_files["stl"] = step.output_data["stl_file"]
                    if "gcode_file" in step.output_data:
                        output_files["gcode"] = step.output_data["gcode_file"]
        
        return PrintStatus(
            job_id=job_id,
            status=workflow.state,
            progress_percentage=progress_percentage,
            current_step=current_step,
            message=get_current_workflow_step(workflow),
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            estimated_completion=None,
            error_message=workflow.error_message,
            output_files=output_files if output_files else None
        )
        
    except Exception as e:
        logger.error(f"Failed to get status for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )

@app.get("/api/workflows", response_model=List[PrintStatus])
async def list_workflows(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None)
):
    """List all workflows with optional filtering and pagination."""
    try:
        workflows = list(app_state["active_workflows"].values())
        
        # Filter by status if provided
        if status_filter:
            workflows = [w for w in workflows if w.state == status_filter]
        
        # Sort by creation time (newest first)
        workflows.sort(key=lambda w: w.created_at, reverse=True)
        
        # Apply pagination
        paginated_workflows = workflows[offset:offset + limit]
        
        # Convert to response format
        result = []
        for workflow in paginated_workflows:
            progress = calculate_workflow_progress(workflow)
            current_step = get_current_workflow_step(workflow)
            
            result.append(PrintStatus(
                job_id=workflow.workflow_id,
                status=workflow.state,
                progress_percentage=progress,
                current_step=current_step,
                message=get_current_workflow_step(workflow),
                created_at=workflow.created_at,
                updated_at=workflow.updated_at,
                estimated_completion=None,
                error_message=workflow.error_message
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )

@app.delete("/api/workflows/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_workflow(
    job_id: str,
    workflow: Workflow = Depends(get_workflow),
    parent_agent: ParentAgent = Depends(get_parent_agent)
):
    """Cancel a running workflow."""
    try:
        if workflow.state in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel workflow in state: {workflow.state}"
            )
        
        # Cancel the workflow
        await parent_agent.cancel_workflow(job_id)
        
        # Update workflow state
        workflow.state = WorkflowState.CANCELLED
        workflow.updated_at = datetime.now()
        workflow.error_message = "Workflow cancelled by user"
        
        # Notify WebSocket clients
        await broadcast_workflow_update(job_id, {
            "type": "status_update",
            "workflow_id": job_id,
            "status": "cancelled",
            "message": "Workflow cancelled by user"
        })
        
        logger.info(f"Cancelled workflow {job_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel workflow: {str(e)}"
        )

@app.get("/health", response_model=SystemHealth)
async def health_check():
    """Get system health status and metrics using comprehensive health monitoring."""
    try:
        # Get comprehensive health report
        health_report = await health_monitor.get_overall_health()
        
        startup_time = app_state.get("startup_time")
        uptime_seconds = (datetime.now() - startup_time).total_seconds() if startup_time else 0
        
        # Count active workflows (any state that's not completed, failed, or cancelled)
        active_count = len([w for w in app_state["active_workflows"].values() 
                           if w.state in [WorkflowState.PENDING, WorkflowState.RESEARCH_PHASE, 
                                          WorkflowState.CAD_PHASE, WorkflowState.SLICING_PHASE, 
                                          WorkflowState.PRINTING_PHASE]])
        
        completed_count = len([w for w in app_state["active_workflows"].values() 
                              if w.state == WorkflowState.COMPLETED])
        
        # Map component health to agent status
        agents_status = {}
        for component_name, component_health in health_report["components"].items():
            if component_name.endswith("_agent"):
                agent_name = component_name.replace("_agent", "")
                agents_status[agent_name] = component_health["status"]
        
        # Add parent agent status
        agents_status["parent"] = "running" if app_state["parent_agent"] else "stopped"
        
        # Use real system metrics from health monitor
        system_metrics = health_report["system_metrics"]
        system_metrics["active_connections"] = sum(len(conns) for conns in app_state["websocket_connections"].values())
        
        return SystemHealth(
            status=health_report["overall_status"],
            version="1.0.0",
            uptime_seconds=uptime_seconds,
            active_workflows=active_count,
            total_completed=completed_count,
            agents_status=agents_status,
            system_metrics=system_metrics
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return SystemHealth(
            status="unhealthy",
            version="1.0.0",
            uptime_seconds=0,
            active_workflows=0,
            total_completed=0,
            agents_status={},
            system_metrics={}
        )


@app.get("/health/detailed")
async def detailed_health_check():
    """Get detailed health information for all system components."""
    try:
        health_report = await health_monitor.get_overall_health()
        return health_report
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "overall_status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "components": {},
            "system_metrics": {}
        }


@app.get("/health/components/{component_name}")
async def component_health_check(component_name: str):
    """Get health status for a specific component."""
    try:
        component_health = await health_monitor.check_component_health(component_name)
        return {
            "component": component_name,
            "status": component_health.status,
            "last_check": component_health.last_check.isoformat(),
            "response_time_ms": component_health.response_time_ms,
            "error_message": component_health.error_message,
            "metrics": component_health.metrics
        }
        
    except Exception as e:
        logger.error(f"Component health check failed for {component_name}: {e}")
        return {
            "component": component_name,
            "status": "unhealthy",
            "error": str(e)
        }

# =============================================================================
# API REDIRECTION ENDPOINTS
# =============================================================================

@app.get("/api/health", response_model=SystemHealth)
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
        favicon_path = Path("web/favicon.ico")
        if favicon_path.exists():
            with open(favicon_path, "rb") as f:
                return Response(content=f.read(), media_type="image/x-icon")
        else:
            # Return a simple 404 instead of raising an exception
            raise HTTPException(status_code=404, detail="Favicon not found")
    except Exception:
        raise HTTPException(status_code=404, detail="Favicon not found")

# =============================================================================
# PRINTER DISCOVERY AND MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/api/printer/discover", response_model=PrinterDiscoveryResponse)
async def discover_printers():
    """Discover all available 3D printers."""
    try:
        start_time = time.time()
        logger.info("Starting printer discovery...")
        
        # Use the enhanced printer discovery
        discovery = PrinterDiscovery()
        printers = await asyncio.to_thread(discovery.discover_all_printers)
        
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

@app.post("/api/printer/{port}/connect")
async def connect_printer(port: str):
    """Connect to a specific printer."""
    try:
        # Clean the port parameter (handle URL encoding)
        port = port.replace("%2F", "/")
        
        logger.info(f"Attempting to connect to printer on port: {port}")
        
        # Get parent agent's printer agent
        parent_agent = app_state.get("parent_agent")
        if not parent_agent:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        printer_agent = parent_agent.printer_agent
        if not hasattr(printer_agent, 'connect_specific_printer'):
            # Use discovery to get printer info and connect
            discovery = PrinterDiscovery()
            success = discovery.connect_to_printer(port)
            
            if success:
                return {"status": "connected", "port": port, "message": f"Successfully connected to printer on {port}"}
            else:
                raise HTTPException(status_code=400, detail=f"Failed to connect to printer on {port}")
        else:
            # Use enhanced printer agent
            result = await printer_agent.connect_specific_printer(port)
            return result
            
    except Exception as e:
        logger.error(f"Error connecting to printer {port}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to printer: {str(e)}"
        )

@app.post("/api/printer/{port}/disconnect")
async def disconnect_printer(port: str):
    """Disconnect from a specific printer."""
    try:
        port = port.replace("%2F", "/")
        logger.info(f"Disconnecting from printer on port: {port}")
        
        # Implementation for disconnection
        discovery = PrinterDiscovery()
        success = discovery.disconnect_printer(port)
        
        if success:
            return {"status": "disconnected", "port": port, "message": f"Successfully disconnected from printer on {port}"}
        else:
            return {"status": "not_connected", "port": port, "message": f"Printer on {port} was not connected"}
            
    except Exception as e:
        logger.error(f"Error disconnecting from printer {port}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect from printer: {str(e)}"
        )

@app.get("/api/printer/{port}/status")
async def get_printer_status(port: str):
    """Get status of a specific printer."""
    try:
        port = port.replace("%2F", "/")
        
        # Get printer status
        discovery = PrinterDiscovery()
        status = discovery.get_printer_status(port)
        
        return {
            "port": port,
            "status": status.get("status", "unknown"),
            "temperature": status.get("temperature", {}),
            "position": status.get("position", {}),
            "is_printing": status.get("is_printing", False),
            "progress": status.get("progress", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting printer status for {port}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get printer status: {str(e)}"
        )

@app.get("/api/printers")
async def list_all_printers():
    """List all known printers."""
    try:
        discovery = PrinterDiscovery()
        printers = discovery.get_all_known_printers()
        
        return {
            "printers": printers,
            "total": len(printers),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing printers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list printers: {str(e)}"
        )


# =============================================================================
# ANALYTICS DASHBOARD
# =============================================================================

@app.get("/analytics-dashboard", response_class=HTMLResponse)
async def analytics_dashboard():
    """Serve the analytics dashboard HTML page."""
    try:
        dashboard_path = Path("templates/analytics_dashboard.html")
        
        if dashboard_path.exists():
            with open(dashboard_path, "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content)
        else:
            return HTMLResponse(
                content="<h1>Analytics Dashboard</h1><p>Dashboard template not found</p>",
                status_code=404
            )
    except Exception as e:
        logger.error(f"Error serving analytics dashboard: {e}")
        return HTMLResponse(
            content="<h1>Error</h1><p>Failed to load analytics dashboard</p>",
            status_code=500
        )


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


# =============================================================================
# MAIN APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Production configuration
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level="info",
        access_log=True
    )
