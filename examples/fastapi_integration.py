"""
FastAPI Integration Examples for API Schemas

This module demonstrates how to use the API schemas with FastAPI for creating
a complete REST API for the AI Agent 3D Print System.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

# Import our API schemas
from core.api_schemas import (
    # Request models
    CreateWorkflowRequest, UpdateWorkflowRequest, ExecuteStepRequest,
    CancelWorkflowRequest, PaginationParams, WorkflowFilterParams,
    
    # Response models
    WorkflowResponse, WorkflowListResponse, WorkflowStatusResponse,
    AgentStatusResponse, TaskExecutionResponse, SystemHealthResponse,
    
    # Core models
    Workflow, WorkflowStep, AgentInfo, TaskResult,
    
    # Enums
    WorkflowState, WorkflowStepStatus, AgentType, AgentStatus,
    
    # Error models
    ErrorResponse, ValidationErrorResponse,
    
    # WebSocket models
    ProgressUpdate, StatusUpdate,
    
    # Utility functions
    create_error_response, create_validation_error_response
)


# =============================================================================
# FastAPI APP SETUP
# =============================================================================

app = FastAPI(
    title="AI Agent 3D Print System API",
    description="RESTful API for the AI Agent 3D Print System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# In-memory storage for demonstration (replace with actual database)
workflows_db: dict = {}
agents_db: dict = {}


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(ValueError)
async def validation_exception_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content=create_validation_error_response(
            field_errors={"validation": [str(exc)]},
            message="Validation error occurred"
        ).model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_code="HTTP_ERROR",
            message=exc.detail
        ).model_dump()
    )


# =============================================================================
# DEPENDENCY FUNCTIONS
# =============================================================================

async def get_workflow(workflow_id: str) -> Workflow:
    """Get workflow by ID or raise 404."""
    if workflow_id not in workflows_db:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {workflow_id} not found"
        )
    return workflows_db[workflow_id]


async def validate_pagination(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """Validate pagination parameters."""
    return PaginationParams(page=page, page_size=page_size)


# =============================================================================
# WORKFLOW ENDPOINTS
# =============================================================================

@app.post("/workflows", response_model=WorkflowResponse, status_code=201)
async def create_workflow(request: CreateWorkflowRequest, background_tasks: BackgroundTasks):
    """
    Create a new 3D printing workflow.
    
    This endpoint creates a new workflow for generating a 3D object from
    a natural language description.
    """
    try:
        # Create new workflow
        workflow = Workflow(
            user_request=request.user_request,
            user_id=request.user_id,
            metadata=request.metadata
        )
        
        # Store in database
        workflows_db[workflow.workflow_id] = workflow
        
        # Add background task to start processing
        background_tasks.add_task(start_workflow_processing, workflow.workflow_id)
        
        return WorkflowResponse(
            workflow=workflow,
            message="Workflow created successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow: {str(e)}"
        )


@app.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    pagination: PaginationParams = Depends(validate_pagination),
    state: Optional[WorkflowState] = Query(None, description="Filter by workflow state"),
    user_id: Optional[str] = Query(None, description="Filter by user ID")
):
    """
    List workflows with filtering and pagination.
    """
    # Apply filters
    filtered_workflows = list(workflows_db.values())
    
    if state:
        filtered_workflows = [w for w in filtered_workflows if w.state == state]
    
    if user_id:
        filtered_workflows = [w for w in filtered_workflows if w.user_id == user_id]
    
    # Apply pagination
    start = (pagination.page - 1) * pagination.page_size
    end = start + pagination.page_size
    paginated_workflows = filtered_workflows[start:end]
    
    return WorkflowListResponse(
        workflows=paginated_workflows,
        total_count=len(filtered_workflows),
        page=pagination.page,
        page_size=pagination.page_size
    )


@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_details(workflow: Workflow = Depends(get_workflow)):
    """Get detailed information about a specific workflow."""
    return WorkflowResponse(
        workflow=workflow,
        message="Workflow retrieved successfully"
    )


@app.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow: Workflow = Depends(get_workflow)):
    """Get the current status of a workflow."""
    current_step = None
    for step in workflow.steps:
        if step.status == WorkflowStepStatus.RUNNING:
            current_step = step
            break
    
    # Calculate estimated completion (simplified)
    estimated_completion = None
    if workflow.progress_percentage > 0:
        # Simple estimation based on progress
        estimated_completion = datetime.now()
    
    return WorkflowStatusResponse(
        workflow_id=workflow.workflow_id,
        state=workflow.state,
        progress_percentage=workflow.progress_percentage,
        current_step=current_step,
        estimated_completion=estimated_completion
    )


@app.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    request: UpdateWorkflowRequest,
    workflow: Workflow = Depends(get_workflow)
):
    """Update workflow properties."""
    if request.state is not None:
        workflow.state = request.state
    
    if request.error_message is not None:
        workflow.error_message = request.error_message
    
    if request.metadata is not None:
        workflow.metadata.update(request.metadata)
    
    workflow.updated_at = datetime.now()
    
    return WorkflowResponse(
        workflow=workflow,
        message="Workflow updated successfully"
    )


@app.delete("/workflows/{workflow_id}")
async def cancel_workflow(
    request: CancelWorkflowRequest,
    workflow: Workflow = Depends(get_workflow)
):
    """Cancel a workflow."""
    if workflow.state in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel workflow in state: {workflow.state}"
        )
    
    workflow.state = WorkflowState.CANCELLED
    workflow.error_message = request.reason or "Cancelled by user"
    workflow.updated_at = datetime.now()
    
    return {"message": "Workflow cancelled successfully"}


# =============================================================================
# WORKFLOW STEP ENDPOINTS
# =============================================================================

@app.post("/workflows/{workflow_id}/steps/{step_id}/execute", response_model=TaskExecutionResponse)
async def execute_workflow_step(
    step_id: str,
    request: ExecuteStepRequest,
    workflow: Workflow = Depends(get_workflow)
):
    """Execute a specific workflow step."""
    # Find the step
    step = None
    for s in workflow.steps:
        if s.step_id == step_id:
            step = s
            break
    
    if not step:
        raise HTTPException(
            status_code=404,
            detail=f"Step {step_id} not found in workflow"
        )
    
    if step.status != WorkflowStepStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Step is not in pending state: {step.status}"
        )
    
    # Simulate step execution
    step.status = WorkflowStepStatus.RUNNING
    step.start_time = datetime.now()
    step.input_data.update(request.input_data)
    
    # Simulate successful completion
    step.status = WorkflowStepStatus.COMPLETED
    step.end_time = datetime.now()
    step.output_data = {"result": "success", "duration": step.duration_seconds}
    
    # Update workflow progress
    completed_steps = sum(1 for s in workflow.steps if s.status == WorkflowStepStatus.COMPLETED)
    workflow.progress_percentage = (completed_steps / len(workflow.steps)) * 100
    
    result = TaskResult(
        success=True,
        data=step.output_data,
        execution_time=step.duration_seconds
    )
    
    return TaskExecutionResponse(
        task_id=step_id,
        result=result,
        agent_id=step.agent_type.value,
        execution_time=step.duration_seconds or 0.0
    )


# =============================================================================
# AGENT ENDPOINTS
# =============================================================================

@app.get("/agents", response_model=AgentStatusResponse)
async def get_agent_status():
    """Get status of all agents in the system."""
    # Simulate agent data
    agents = [
        AgentInfo(
            agent_id="parent_agent",
            agent_type=AgentType.PARENT,
            status=AgentStatus.RUNNING,
            capabilities=["orchestration", "workflow_management"],
            last_heartbeat=datetime.now()
        ),
        AgentInfo(
            agent_id="research_agent",
            agent_type=AgentType.RESEARCH,
            status=AgentStatus.IDLE,
            capabilities=["requirement_analysis", "feasibility_assessment"]
        ),
        AgentInfo(
            agent_id="cad_agent",
            agent_type=AgentType.CAD,
            status=AgentStatus.IDLE,
            capabilities=["3d_modeling", "parametric_design"]
        ),
        AgentInfo(
            agent_id="slicer_agent",
            agent_type=AgentType.SLICER,
            status=AgentStatus.IDLE,
            capabilities=["gcode_generation", "print_optimization"]
        ),
        AgentInfo(
            agent_id="printer_agent",
            agent_type=AgentType.PRINTER,
            status=AgentStatus.IDLE,
            capabilities=["print_control", "status_monitoring"]
        )
    ]
    
    active_agents = sum(1 for agent in agents if agent.status != AgentStatus.SHUTDOWN)
    
    return AgentStatusResponse(
        agents=agents,
        total_agents=len(agents),
        active_agents=active_agents
    )


# =============================================================================
# SYSTEM ENDPOINTS
# =============================================================================

@app.get("/health", response_model=SystemHealthResponse)
async def health_check():
    """Get system health status."""
    return SystemHealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=3600,  # Mock uptime
        active_workflows=len([w for w in workflows_db.values() 
                            if w.state not in [WorkflowState.COMPLETED, 
                                             WorkflowState.FAILED, 
                                             WorkflowState.CANCELLED]]),
        agent_status={
            "parent": "running",
            "research": "idle", 
            "cad": "idle",
            "slicer": "idle",
            "printer": "idle"
        },
        system_metrics={
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 23.1
        }
    )


# =============================================================================
# AI MODEL MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/ai-models", response_model=dict)
async def get_available_ai_models():
    """Get list of available AI models for intent recognition."""
    try:
        # In a real implementation, this would connect to the research agent
        from agents.research_agent import ResearchAgent
        
        research_agent = ResearchAgent()
        models = research_agent.get_available_ai_models()
        
        return {
            "success": True,
            "models": models,
            "total_models": len(models)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get AI models: {str(e)}"
        )


@app.post("/ai-models/select")
async def select_ai_model(model_name: str = Query(..., description="Name of the AI model to select")):
    """Select the preferred AI model for intent recognition."""
    try:
        from agents.research_agent import ResearchAgent
        
        research_agent = ResearchAgent()
        success = research_agent.set_preferred_ai_model(model_name)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to select AI model: {model_name}"
            )
        
        return {
            "success": True,
            "message": f"AI model '{model_name}' selected successfully",
            "selected_model": model_name
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to select AI model: {str(e)}"
        )


@app.get("/ai-models/status")
async def get_ai_model_status():
    """Get current AI model status and usage statistics."""
    try:
        from agents.research_agent import ResearchAgent
        
        research_agent = ResearchAgent()
        status = research_agent.get_ai_model_status()
        
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get AI model status: {str(e)}"
        )


@app.post("/ai-models/test")
async def test_ai_model(
    model_name: str = Query(..., description="Name of the AI model to test"),
    test_query: str = Query("Create a small gear", description="Test query for the AI model")
):
    """Test a specific AI model with a sample query."""
    try:
        from agents.research_agent import ResearchAgent
        
        research_agent = ResearchAgent()
        
        # Temporarily set the model and test it
        original_model = getattr(research_agent.ai_model_manager, "preferred_model", None)
        research_agent.set_preferred_ai_model(model_name)
        
        # Test the model
        result = research_agent.extract_intent(test_query)
        
        # Restore original model if it existed
        if original_model:
            research_agent.set_preferred_ai_model(original_model)
        
        return {
            "success": True,
            "model_tested": model_name,
            "test_query": test_query,
            "result": result,
            "confidence": result.get("confidence", 0.0)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test AI model: {str(e)}"
        )


# =============================================================================
# WEBSOCKET ENDPOINTS
# =============================================================================

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Connection closed, remove it
                self.active_connections.remove(connection)


manager = ConnectionManager()


@app.websocket("/ws/workflows/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            # Send progress update (simplified)
            if workflow_id in workflows_db:
                workflow = workflows_db[workflow_id]
                update = ProgressUpdate(
                    workflow_id=workflow_id,
                    progress_percentage=workflow.progress_percentage,
                    current_step=f"Current state: {workflow.state.value}",
                    message=f"Workflow is {workflow.state.value}"
                )
                await manager.send_personal_message(update.model_dump(), websocket)
    
    except Exception as e:
        manager.disconnect(websocket)


# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def start_workflow_processing(workflow_id: str):
    """Background task to simulate workflow processing."""
    if workflow_id not in workflows_db:
        return
    
    workflow = workflows_db[workflow_id]
    
    # Create workflow steps
    steps = [
        WorkflowStep(name="Research Phase", agent_type=AgentType.RESEARCH),
        WorkflowStep(name="CAD Generation", agent_type=AgentType.CAD),
        WorkflowStep(name="Slicing", agent_type=AgentType.SLICER),
        WorkflowStep(name="Printing", agent_type=AgentType.PRINTER)
    ]
    
    workflow.steps = steps
    workflow.state = WorkflowState.RESEARCH_PHASE
    
    # Broadcast status update
    status_update = StatusUpdate(
        entity_type="workflow",
        entity_id=workflow_id,
        status=workflow.state.value,
        message="Workflow processing started"
    )
    await manager.broadcast(status_update.model_dump())


# =============================================================================
# MAIN APPLICATION
# =============================================================================

if __name__ == "__main__":
    # Add some sample data for testing
    sample_workflow = Workflow(
        user_request="Create a small gear for a clock mechanism",
        user_id="test_user",
        metadata={"priority": "normal", "material": "PLA"}
    )
    workflows_db[sample_workflow.workflow_id] = sample_workflow
    
    # Run the FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8000)
