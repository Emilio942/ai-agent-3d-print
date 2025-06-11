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
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4

import uvicorn
from fastapi import (
    BackgroundTasks, Depends, FastAPI, HTTPException, Query, WebSocket,
    WebSocketDisconnect, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import core system components
from core.parent_agent import ParentAgent
from core.logger import get_logger
from core.exceptions import (
    AgentCommunicationError, ValidationError,
    WorkflowError, PrinterAgentError
)
from config.settings import load_config
from core.health_monitor import health_monitor, setup_default_monitoring

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
        await setup_default_monitoring()
        
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
    app.add_middleware(SecurityMiddleware)
    
    # Performance middleware
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(ResourceLimitMiddleware, max_concurrent_requests=100)
    app.add_middleware(CacheControlMiddleware)
    
    # Security headers (should be last to ensure headers are set)
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info("Security and performance middleware loaded successfully")
    
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
        
        # Count active workflows
        active_count = len([w for w in app_state["active_workflows"].values() 
                           if w.state in [WorkflowState.PENDING, WorkflowState.RUNNING]])
        
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
# WEBSOCKET ENDPOINTS
# =============================================================================

@app.websocket("/ws/progress")
async def websocket_progress_endpoint(websocket: WebSocket, job_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time progress updates.
    
    Clients can connect to receive real-time updates about workflow progress.
    If job_id is provided, only updates for that specific job will be sent.
    """
    await websocket.accept()
    
    # Track this connection
    connection_id = str(uuid4())
    logger.info(f"WebSocket connected: {connection_id} for job: {job_id or 'all'}")
    
    try:
        # Add to connections tracking
        if job_id:
            if job_id not in app_state["websocket_connections"]:
                app_state["websocket_connections"][job_id] = set()
            app_state["websocket_connections"][job_id].add(websocket)
        else:
            # Global connection - add to all current workflows
            for workflow_id in app_state["websocket_connections"]:
                app_state["websocket_connections"][workflow_id].add(websocket)
        
        # Send initial status if job_id is specified
        if job_id and job_id in app_state["active_workflows"]:
            workflow = app_state["active_workflows"][job_id]
            initial_status = {
                "type": "status_update",
                "workflow_id": job_id,
                "status": workflow.state,
                "progress_percentage": calculate_workflow_progress(workflow),
                "current_step": get_current_workflow_step(workflow),
                "message": get_current_workflow_step(workflow),
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(initial_status)
        
        # Keep connection alive and handle client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle client messages (ping, subscribe, etc.)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket message handling error: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Remove from all connections
        for workflow_id, connections in app_state["websocket_connections"].items():
            connections.discard(websocket)
        
        logger.info(f"WebSocket disconnected: {connection_id}")

# =============================================================================
# BACKGROUND TASK FUNCTIONS
# =============================================================================

async def process_print_workflow(job_id: str, workflow: Workflow, parent_agent: ParentAgent):
    """
    Background task to process a complete print workflow.
    
    This function orchestrates the entire workflow from research to printing,
    updating the workflow state and notifying WebSocket clients of progress.
    """
    try:
        logger.info(f"Starting workflow processing for job {job_id}")
        
        # Update workflow state
        workflow.state = WorkflowState.RESEARCH_PHASE
        workflow.updated_at = datetime.now()
        
        # Notify WebSocket clients
        await broadcast_workflow_update(job_id, {
            "type": "status_update",
            "workflow_id": job_id,
            "status": "running",
            "message": "Starting workflow processing"
        })
        
        # Define workflow steps
        workflow_steps = [
            ("research", "Research and concept generation"),
            ("cad", "3D model creation"),
            ("slicing", "G-code generation"),
            ("printing", "3D printing")
        ]
        
        total_steps = len(workflow_steps)
        
        # Execute each step
        for step_index, (step_name, step_description) in enumerate(workflow_steps):
            try:
                # Update workflow
                workflow.updated_at = datetime.now()
                
                # Calculate progress (step completion + partial progress within step)
                base_progress = (step_index / total_steps) * 100
                
                # Notify step start
                await broadcast_workflow_update(job_id, {
                    "type": "progress_update",
                    "workflow_id": job_id,
                    "progress_percentage": base_progress,
                    "current_step": step_description,
                    "message": f"Starting {step_description}..."
                })
                
                # Execute the step through ParentAgent
                step_result = await execute_workflow_step(
                    parent_agent, workflow, step_name, 
                    job_id, step_index, total_steps
                )
                
                # Add step to workflow
                workflow_step = WorkflowStep(
                    step_id=f"{step_name}_{step_index}",
                    name=step_description,
                    agent_type=AgentType(step_name) if step_name in [e for e in AgentType] else AgentType.PARENT,
                    status=WorkflowStepStatus.COMPLETED,
                    output_data=step_result.data if step_result.success else {}
                )
                workflow.steps.append(workflow_step)
                
                # Update progress
                step_progress = ((step_index + 1) / total_steps) * 100
                await broadcast_workflow_update(job_id, {
                    "type": "progress_update",
                    "workflow_id": job_id,
                    "progress_percentage": step_progress,
                    "current_step": step_description,
                    "message": f"Completed {step_description}"
                })
                
                logger.info(f"Completed step {step_name} for workflow {job_id}")
                
            except Exception as step_error:
                logger.error(f"Step {step_name} failed for workflow {job_id}: {step_error}")
                
                # Mark step as failed
                workflow_step = WorkflowStep(
                    step_id=f"{step_name}_{step_index}",
                    name=step_description,
                    agent_type=AgentType(step_name) if step_name in [e for e in AgentType] else AgentType.PARENT,
                    status=WorkflowStepStatus.FAILED,
                    error_message=str(step_error),
                    output_data={}
                )
                workflow.steps.append(workflow_step)
                
                # Mark workflow as failed
                workflow.state = WorkflowState.FAILED
                workflow.error_message = f"Failed at step '{step_description}': {str(step_error)}"
                workflow.updated_at = datetime.now()
                
                await broadcast_workflow_update(job_id, {
                    "type": "status_update",
                    "workflow_id": job_id,
                    "status": "failed",
                    "message": workflow.error_message
                })
                
                return
        
        # Mark workflow as completed
        workflow.state = WorkflowState.COMPLETED
        workflow.progress_percentage = 100.0
        workflow.updated_at = datetime.now()
        workflow.completed_at = datetime.now()
        
        await broadcast_workflow_update(job_id, {
            "type": "status_update",
            "workflow_id": job_id,
            "status": "completed",
            "progress_percentage": 100.0,
            "message": "Workflow completed successfully"
        })
        
        logger.info(f"Workflow {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Workflow processing failed for job {job_id}: {e}")
        
        # Mark workflow as failed
        workflow.state = WorkflowState.FAILED
        workflow.error_message = f"Workflow processing error: {str(e)}"
        workflow.updated_at = datetime.now()
        
        await broadcast_workflow_update(job_id, {
            "type": "status_update", 
            "workflow_id": job_id,
            "status": "failed",
            "message": workflow.error_message
        })

async def execute_workflow_step(
    parent_agent: ParentAgent, 
    workflow: Workflow, 
    step_name: str, 
    job_id: str, 
    step_index: int, 
    total_steps: int
) -> TaskResult:
    """Execute a single workflow step through the appropriate agent."""
    
    try:
        # Prepare step input based on previous steps and workflow data
        step_input = {
            "workflow_id": workflow.workflow_id,
            "user_request": workflow.user_request,
            "step_name": step_name,
            "metadata": workflow.metadata
        }
        
        # Add outputs from previous steps
        for prev_step in workflow.steps:
            if prev_step.status == WorkflowStepStatus.COMPLETED and prev_step.output_data:
                step_input[f"{prev_step.agent_type}_output"] = prev_step.output_data
        
        # Create progress callback for real-time updates
        async def progress_callback(progress_data):
            base_progress = (step_index / total_steps) * 100
            step_progress = (progress_data.get("percentage", 0) / 100) * (100 / total_steps)
            total_progress = base_progress + step_progress
            
            await broadcast_workflow_update(job_id, {
                "type": "progress_update",
                "workflow_id": job_id,
                "progress_percentage": min(total_progress, 100.0),
                "current_step": progress_data.get("current_step", f"Processing {step_name}"),
                "message": progress_data.get("message", f"Processing {step_name}...")
            })
        
        # Execute the step through ParentAgent
        if step_name == "research":
            result = await parent_agent.execute_research_workflow(step_input, progress_callback)
        elif step_name == "cad":
            result = await parent_agent.execute_cad_workflow(step_input, progress_callback)
        elif step_name == "slicing":
            result = await parent_agent.execute_slicer_workflow(step_input, progress_callback)
        elif step_name == "printing":
            result = await parent_agent.execute_printer_workflow(step_input, progress_callback)
        else:
            raise ValueError(f"Unknown workflow step: {step_name}")
        
        return result
        
    except Exception as e:
        logger.error(f"Step execution failed: {e}")
        return TaskResult(
            success=False,
            error_message=str(e),
            data={}
        )

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_workflow_progress(workflow: Workflow) -> float:
    """Calculate workflow progress percentage based on state and completed steps."""
    if workflow.state == WorkflowState.PENDING:
        return 0.0
    elif workflow.state == WorkflowState.COMPLETED:
        return 100.0
    elif workflow.state in [WorkflowState.FAILED, WorkflowState.CANCELLED]:
        # Return progress based on completed steps
        if not workflow.steps:
            return 0.0
        completed_steps = len([s for s in workflow.steps if s.status == "completed"])
        return min((completed_steps / 4) * 100, 100.0)  # 4 main steps
    else:  # RUNNING
        if not workflow.steps:
            return 10.0  # Just started
        completed_steps = len([s for s in workflow.steps if s.status == "completed"])
        return min((completed_steps / 4) * 100 + 10, 95.0)  # Max 95% until actually completed

def get_current_workflow_step(workflow: Workflow) -> Optional[str]:
    """Get the current workflow step description."""
    # Map workflow states to step descriptions
    state_descriptions = {
        WorkflowState.PENDING: "Waiting to start",
        WorkflowState.RESEARCH_PHASE: "Research and concept generation",
        WorkflowState.CAD_PHASE: "3D model creation", 
        WorkflowState.SLICING_PHASE: "G-code generation",
        WorkflowState.PRINTING_PHASE: "3D printing",
        WorkflowState.COMPLETED: "Completed",
        WorkflowState.FAILED: "Failed", 
        WorkflowState.CANCELLED: "Cancelled"
    }
    
    return state_descriptions.get(workflow.state, f"Workflow is {workflow.state}")


async def broadcast_workflow_update(workflow_id: str, message: dict):
    """Broadcast an update to all WebSocket clients connected to a workflow."""
    if workflow_id not in app_state["websocket_connections"]:
        return
    
    # Add timestamp
    message["timestamp"] = datetime.now().isoformat()
    
    # Send to all connected clients
    connections = app_state["websocket_connections"][workflow_id].copy()
    for websocket in connections:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
            # Remove failed connection
            app_state["websocket_connections"][workflow_id].discard(websocket)


# =============================================================================
# ROUTER REGISTRATION
# =============================================================================

# Include security and performance monitoring endpoints
try:
    from api.security_performance_endpoints import security_performance_router
    app.include_router(security_performance_router)
    logger.info("Security and performance endpoints registered successfully")
except ImportError as e:
    logger.warning(f"Security and performance endpoints not available: {e}")

# Include 3D print preview endpoints
try:
    from api.preview_routes import router as preview_router
    app.include_router(preview_router)
    logger.info("3D print preview endpoints registered successfully")
except ImportError as e:
    logger.warning(f"3D print preview endpoints not available: {e}")

# Include advanced features endpoints (AI-enhanced design, historical data, etc.)
try:
    from api.advanced_routes import router as advanced_router
    app.include_router(advanced_router)
    logger.info("Advanced features endpoints registered successfully")
except ImportError as e:
    logger.warning(f"Advanced features endpoints not available: {e}")


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
