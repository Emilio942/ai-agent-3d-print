# API Schema Documentation

## Overview

The AI Agent 3D Print System uses Pydantic models to define API schemas for type-safe communication between components. This document provides comprehensive documentation for all available schemas, their usage patterns, and validation rules.

## Table of Contents

1. [Core Models](#core-models)
2. [Request Models](#request-models)
3. [Response Models](#response-models)
4. [Agent-Specific Models](#agent-specific-models)
5. [Error Models](#error-models)
6. [WebSocket Models](#websocket-models)
7. [Validation Rules](#validation-rules)
8. [Usage Examples](#usage-examples)

## Core Models

### Workflow

The `Workflow` model represents a complete 3D printing workflow from user request to finished object.

**Schema:**
```python
class Workflow(BaseSchema, TimestampMixin):
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    user_request: str = Field(min_length=1, max_length=1000)
    state: WorkflowState = WorkflowState.PENDING
    completed_at: Optional[datetime] = None
    steps: List[WorkflowStep] = Field(default_factory=list)
    progress_percentage: float = Field(default=0.0, ge=0, le=100)
    error_message: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**States:**
- `PENDING`: Workflow created, ready to start
- `RESEARCH_PHASE`: Analyzing user requirements
- `CAD_PHASE`: Generating 3D model
- `SLICING_PHASE`: Creating G-code
- `PRINTING_PHASE`: 3D printing execution
- `COMPLETED`: Successfully finished
- `FAILED`: Failed permanently
- `CANCELLED`: Cancelled by user

**Example:**
```python
workflow = Workflow(
    user_request="Create a small gear for a clock mechanism",
    user_id="user123",
    metadata={"priority": "high", "material_preference": "PLA"}
)
```

### WorkflowStep

Represents an individual step within a workflow.

**Schema:**
```python
class WorkflowStep(BaseSchema, TimestampMixin):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    agent_type: AgentType
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
```

**Step Statuses:**
- `PENDING`: Ready to execute
- `RUNNING`: Currently executing
- `COMPLETED`: Successfully completed
- `FAILED`: Failed execution
- `SKIPPED`: Skipped (conditional step)

### Message

Inter-agent communication message model.

**Schema:**
```python
class Message(BaseSchema, TimestampMixin):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    sender_id: str
    recipient_id: str
    message_type: str
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    payload: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
```

**Priority Levels:**
- `LOW`: 1
- `NORMAL`: 5
- `HIGH`: 10
- `CRITICAL`: 20

## Request Models

### CreateWorkflowRequest

Request to create a new workflow.

**Schema:**
```python
class CreateWorkflowRequest(BaseSchema):
    user_request: str = Field(min_length=1, max_length=1000)
    user_id: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**Example:**
```python
request = CreateWorkflowRequest(
    user_request="Design a phone case for iPhone 13",
    user_id="user123",
    priority=MessagePriority.HIGH,
    metadata={"material": "TPU", "color": "black"}
)
```

### UpdateWorkflowRequest

Request to update workflow properties.

**Schema:**
```python
class UpdateWorkflowRequest(BaseSchema):
    state: Optional[WorkflowState] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

### ExecuteStepRequest

Request to execute a workflow step.

**Schema:**
```python
class ExecuteStepRequest(BaseSchema):
    step_id: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[PositiveFloat] = None
```

## Response Models

### WorkflowResponse

Standard response containing workflow information.

**Schema:**
```python
class WorkflowResponse(BaseSchema):
    workflow: Workflow
    message: str = "Operation successful"
```

### WorkflowListResponse

Response for list operations with pagination.

**Schema:**
```python
class WorkflowListResponse(BaseSchema):
    workflows: List[Workflow]
    total_count: int
    page: int = 1
    page_size: int = 10
```

### WorkflowStatusResponse

Response for workflow status queries.

**Schema:**
```python
class WorkflowStatusResponse(BaseSchema):
    workflow_id: str
    state: WorkflowState
    progress_percentage: float
    current_step: Optional[WorkflowStep] = None
    estimated_completion: Optional[datetime] = None
    message: str = "Status retrieved successfully"
```

## Agent-Specific Models

### Research Agent

**Input:**
```python
class ResearchAgentInput(BaseSchema):
    user_request: str = Field(min_length=1, max_length=1000)
    context: Dict[str, Any] = Field(default_factory=dict)
    analysis_depth: str = Field(default="standard", pattern="^(basic|standard|detailed)$")
```

**Output:**
```python
class ResearchAgentOutput(BaseSchema):
    requirements: Dict[str, Any]
    object_specifications: Dict[str, Any]
    material_recommendations: List[str]
    complexity_score: float = Field(ge=0, le=10)
    feasibility_assessment: str
    recommendations: List[str]
```

### CAD Agent

**Input:**
```python
class CADAgentInput(BaseSchema):
    specifications: Dict[str, Any]
    requirements: Dict[str, Any]
    format_preference: str = Field(default="stl", pattern="^(stl|obj|ply|step)$")
    quality_level: str = Field(default="standard", pattern="^(draft|standard|high|ultra)$")
```

**Output:**
```python
class CADAgentOutput(BaseSchema):
    model_file_path: str
    model_format: str
    dimensions: Dict[str, float]  # x, y, z dimensions
    volume: float
    surface_area: float
    complexity_metrics: Dict[str, Any]
    generation_time: float
    quality_score: float = Field(ge=0, le=10)
```

### Slicer Agent

**Input:**
```python
class SlicerAgentInput(BaseSchema):
    model_file_path: str
    printer_profile: str
    material_type: str
    quality_preset: str = Field(default="standard", pattern="^(draft|standard|fine|ultra)$")
    infill_percentage: int = Field(default=20, ge=0, le=100)
    layer_height: float = Field(default=0.2, gt=0, le=1.0)
    print_speed: int = Field(default=50, ge=10, le=300)
```

**Output:**
```python
class SlicerAgentOutput(BaseSchema):
    gcode_file_path: str
    estimated_print_time: int  # minutes
    material_usage: float  # grams
    layer_count: int
    total_movements: int
    slicing_time: float
    preview_image_path: Optional[str] = None
```

### Printer Agent

**Input:**
```python
class PrinterAgentInput(BaseSchema):
    gcode_file_path: str
    printer_id: str
    start_immediately: bool = False
    notification_settings: Dict[str, Any] = Field(default_factory=dict)
```

**Output:**
```python
class PrinterAgentOutput(BaseSchema):
    print_job_id: str
    status: str
    progress_percentage: float = Field(ge=0, le=100)
    current_layer: int
    temperature_bed: float
    temperature_nozzle: float
    estimated_time_remaining: int  # minutes
    error_messages: List[str] = Field(default_factory=list)
```

## Error Models

### ErrorResponse

Standard error response for API errors.

**Schema:**
```python
class ErrorResponse(BaseSchema):
    success: bool = False
    error_code: str
    message: str
    details: List[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None
```

### ValidationErrorResponse

Specialized error response for validation failures.

**Schema:**
```python
class ValidationErrorResponse(ErrorResponse):
    error_code: str = "VALIDATION_ERROR"
    field_errors: Dict[str, List[str]] = Field(default_factory=dict)
```

**Example:**
```python
error = ValidationErrorResponse(
    message="Validation failed",
    field_errors={
        "user_request": ["This field is required"],
        "priority": ["Invalid priority level"]
    }
)
```

## WebSocket Models

### ProgressUpdate

Real-time progress updates for workflows.

**Schema:**
```python
class ProgressUpdate(BaseSchema):
    workflow_id: str
    progress_percentage: float = Field(ge=0, le=100)
    current_step: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
```

### StatusUpdate

General status updates for entities.

**Schema:**
```python
class StatusUpdate(BaseSchema):
    entity_type: str  # workflow, agent, system
    entity_id: str
    status: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
```

## Validation Rules

### String Constraints

- **user_request**: 1-1000 characters, cannot be empty or whitespace-only
- **agent_id**: Non-empty string
- **workflow_id**: Auto-generated UUID format
- **file_paths**: Valid file path format

### Numeric Constraints

- **progress_percentage**: 0.0 to 100.0
- **complexity_score**: 0.0 to 10.0
- **layer_height**: > 0.0, ≤ 1.0
- **infill_percentage**: 0 to 100
- **print_speed**: 10 to 300 mm/s

### Enum Constraints

- **quality_preset**: "draft", "standard", "fine", "ultra"
- **analysis_depth**: "basic", "standard", "detailed"
- **format_preference**: "stl", "obj", "ply", "step"

### Date/Time Constraints

- **timestamps**: UTC datetime objects
- **expires_at**: Future datetime (when specified)

## Usage Examples

### Creating a Complete Workflow

```python
from core.api_schemas import CreateWorkflowRequest, Workflow, WorkflowStep, AgentType

# 1. Create workflow request
request = CreateWorkflowRequest(
    user_request="Create a custom phone stand",
    user_id="user123",
    metadata={"material": "PLA", "color": "blue"}
)

# 2. Create workflow from request
workflow = Workflow(
    user_request=request.user_request,
    user_id=request.user_id,
    metadata=request.metadata
)

# 3. Add workflow steps
steps = [
    WorkflowStep(name="Analyze Requirements", agent_type=AgentType.RESEARCH),
    WorkflowStep(name="Generate 3D Model", agent_type=AgentType.CAD),
    WorkflowStep(name="Slice for Printing", agent_type=AgentType.SLICER),
    WorkflowStep(name="3D Print Object", agent_type=AgentType.PRINTER)
]

workflow.steps = steps
```

### Agent Communication

```python
from core.api_schemas import Message, MessagePriority, ResearchAgentInput

# Create message for research agent
message = Message(
    sender_id="parent_agent",
    recipient_id="research_agent",
    message_type="task_request",
    priority=MessagePriority.HIGH,
    payload={
        "task_type": "analyze_requirements",
        "input": ResearchAgentInput(
            user_request="Create a gear",
            analysis_depth="detailed"
        ).model_dump()
    }
)
```

### Error Handling

```python
from core.api_schemas import create_error_response, create_validation_error_response

# Create standard error
error = create_error_response(
    error_code="WORKFLOW_NOT_FOUND",
    message="Workflow with ID 'abc123' not found",
    request_id="req456"
)

# Create validation error
validation_error = create_validation_error_response(
    field_errors={
        "user_request": ["This field is required"],
        "priority": ["Invalid priority level"]
    },
    message="Request validation failed"
)
```

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from core.api_schemas import CreateWorkflowRequest, WorkflowResponse

app = FastAPI()

@app.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(request: CreateWorkflowRequest):
    try:
        workflow = Workflow(
            user_request=request.user_request,
            user_id=request.user_id,
            metadata=request.metadata
        )
        
        return WorkflowResponse(
            workflow=workflow,
            message="Workflow created successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Schema Registry

The module provides a schema registry for dynamic schema access:

```python
from core.api_schemas import get_schema, list_schemas, SCHEMA_REGISTRY

# Get schema by name
WorkflowSchema = get_schema("workflow")
instance = WorkflowSchema(user_request="test")

# List all available schemas
available_schemas = list_schemas()
print(f"Available schemas: {available_schemas}")

# Direct registry access
all_schemas = SCHEMA_REGISTRY
```

## Best Practices

### 1. Validation
- Always validate input data using Pydantic models
- Use custom validators for complex business logic
- Provide clear error messages for validation failures

### 2. Serialization
- Use `.model_dump()` for JSON serialization
- Use `.model_validate()` for object creation from dict
- Handle optional fields gracefully

### 3. Error Handling
- Use standardized error response models
- Include request IDs for traceability
- Provide detailed field-level validation errors

### 4. Performance
- Use field defaults to minimize required input
- Consider using `model_validate_json()` for direct JSON parsing
- Cache schema instances when possible

### 5. Documentation
- Include examples in schema docstrings
- Document validation constraints clearly
- Provide usage examples for complex schemas
