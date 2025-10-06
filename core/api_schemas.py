"""
API Schema Definition - Pydantic models for API communication

This module defines all Pydantic models used for API communication in the
AI Agent 3D Print System, including request/response models, validation schemas,
and data transfer objects for inter-agent communication.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, field_validator, AliasChoices
from pydantic.types import PositiveInt, PositiveFloat


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class WorkflowState(str, Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RESEARCH_PHASE = "research_phase"
    CAD_PHASE = "cad_phase"
    SLICING_PHASE = "slicing_phase"
    PRINTING_PHASE = "printing_phase"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepStatus(str, Enum):
    """Individual step status within a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskStatus(str, Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class AgentStatus(str, Enum):
    """Agent operational status."""
    IDLE = "idle"
    RUNNING = "running"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"
    SHUTDOWN = "shutdown"


class MessagePriority(int, Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class MessageStatus(str, Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class AgentType(str, Enum):
    """Available agent types in the system."""
    PARENT = "parent"
    RESEARCH = "research"
    CAD = "cad"
    SLICER = "slicer"
    PRINTER = "printer"


# =============================================================================
# BASE MODELS
# =============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
        protected_namespaces=()
    )


class TimestampMixin(BaseModel):
    """Mixin for models that need timestamps."""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# CORE DATA MODELS
# =============================================================================

class TaskResult(BaseSchema):
    """Result of task execution."""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        """Ensure task_id is mirrored into metadata for legacy consumers."""
        if self.task_id and 'task_id' not in self.metadata:
            self.metadata['task_id'] = self.task_id

    def __getitem__(self, item: str) -> Any:
        """Provide dict-style access for legacy callers and tests."""
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)


class AgentInfo(BaseSchema):
    """Agent information model."""
    agent_id: str
    agent_type: AgentType
    status: AgentStatus
    capabilities: List[str] = Field(default_factory=list)
    version: str = "1.0.0"
    last_heartbeat: Optional[datetime] = None


class Message(BaseSchema, TimestampMixin):
    """Inter-agent communication message."""
    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        validation_alias=AliasChoices("message_id", "id")
    )
    sender_id: str = Field(validation_alias=AliasChoices("sender_id", "sender"))
    recipient_id: str = Field(validation_alias=AliasChoices("recipient_id", "receiver"))
    message_type: str
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    payload: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

    @property
    def sender(self) -> str:
        """Backward-compatible sender accessor."""
        return self.sender_id

    @property
    def receiver(self) -> str:
        """Backward-compatible receiver accessor."""
        return self.recipient_id


class WorkflowStep(BaseSchema, TimestampMixin):
    """Individual step in a workflow."""
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

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate step execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class Workflow(BaseSchema, TimestampMixin):
    """Complete workflow for 3D object creation."""
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    user_request: str = Field(min_length=1, max_length=1000)
    state: WorkflowState = WorkflowState.PENDING
    completed_at: Optional[datetime] = None
    steps: List[WorkflowStep] = Field(default_factory=list)
    progress_percentage: float = Field(default=0.0, ge=0, le=100)
    error_message: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('user_request')
    @classmethod
    def validate_user_request(cls, v: str) -> str:
        """Validate user request is not empty and reasonable length."""
        if not v.strip():
            raise ValueError("User request cannot be empty")
        return v.strip()


# =============================================================================
# API REQUEST MODELS
# =============================================================================

class CreateWorkflowRequest(BaseSchema):
    """Request to create a new workflow."""
    user_request: str = Field(
        min_length=1, 
        max_length=1000,
        description="Natural language description of the 3D object to create"
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user identifier"
    )
    priority: MessagePriority = Field(
        MessagePriority.NORMAL,
        description="Workflow execution priority"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the workflow"
    )


class UpdateWorkflowRequest(BaseSchema):
    """Request to update workflow properties."""
    state: Optional[WorkflowState] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ExecuteStepRequest(BaseSchema):
    """Request to execute a workflow step."""
    step_id: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[PositiveFloat] = None


class CancelWorkflowRequest(BaseSchema):
    """Request to cancel a workflow."""
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional reason for cancellation"
    )


# =============================================================================
# API RESPONSE MODELS  
# =============================================================================

class WorkflowResponse(BaseSchema):
    """Response containing workflow information."""
    workflow: Workflow
    message: str = "Operation successful"


class WorkflowListResponse(BaseSchema):
    """Response containing multiple workflows."""
    workflows: List[Workflow]
    total_count: int
    page: int = 1
    page_size: int = 10


class WorkflowStatusResponse(BaseSchema):
    """Response for workflow status queries."""
    workflow_id: str
    state: WorkflowState
    progress_percentage: float
    current_step: Optional[WorkflowStep] = None
    estimated_completion: Optional[datetime] = None
    message: str = "Status retrieved successfully"


class AgentStatusResponse(BaseSchema):
    """Response for agent status queries."""
    agents: List[AgentInfo]
    total_agents: int
    active_agents: int
    message: str = "Agent status retrieved successfully"


class TaskExecutionResponse(BaseSchema):
    """Response for task execution."""
    task_id: str
    result: TaskResult
    agent_id: str
    execution_time: float
    message: str = "Task executed successfully"


# =============================================================================
# AGENT-SPECIFIC SCHEMAS
# =============================================================================

class ResearchAgentInput(BaseSchema):
    """Input for research agent analysis."""
    user_request: str = Field(min_length=1, max_length=1000)
    context: Dict[str, Any] = Field(default_factory=dict)
    analysis_depth: str = Field(
        default="standard",
        pattern="^(basic|standard|detailed)$"
    )


class ResearchAgentOutput(BaseSchema):
    """Output from research agent analysis."""
    requirements: Dict[str, Any]
    object_specifications: Dict[str, Any]
    material_recommendations: List[str]
    complexity_score: float = Field(ge=0, le=10)
    feasibility_assessment: str
    recommendations: List[str]


class CADAgentInput(BaseSchema):
    """Input for CAD generation."""
    specifications: Dict[str, Any]
    requirements: Dict[str, Any]
    format_preference: str = Field(
        default="stl",
        pattern="^(stl|obj|ply|step)$"
    )
    quality_level: str = Field(
        default="standard",
        pattern="^(draft|standard|high|ultra)$"
    )


class CADAgentOutput(BaseSchema):
    """Output from CAD generation."""
    model_file_path: str
    model_format: str
    dimensions: Dict[str, float]  # x, y, z dimensions
    volume: float
    surface_area: float
    complexity_metrics: Dict[str, Any]
    generation_time: float
    quality_score: float = Field(ge=0, le=10)


class GeometryDimensions(BaseSchema):
    """Geometry dimensions for 3D primitives."""
    x: Optional[float] = Field(None, gt=0, description="Width in mm")
    y: Optional[float] = Field(None, gt=0, description="Depth in mm") 
    z: Optional[float] = Field(None, gt=0, description="Height in mm")
    radius: Optional[float] = Field(None, gt=0, description="Radius in mm")
    height: Optional[float] = Field(None, gt=0, description="Height in mm")
    major_radius: Optional[float] = Field(None, gt=0, description="Major radius for torus in mm")
    minor_radius: Optional[float] = Field(None, gt=0, description="Minor radius for torus in mm")
    base_radius: Optional[float] = Field(None, gt=0, description="Base radius for cone in mm")
    top_radius: Optional[float] = Field(None, ge=0, description="Top radius for cone in mm")


class PrimitiveGeometry(BaseSchema):
    """3D primitive geometry specification."""
    shape_type: str = Field(
        description="Type of primitive shape",
        pattern="^(cube|cylinder|sphere|torus|cone)$"
    )
    dimensions: GeometryDimensions
    segments: int = Field(default=32, ge=3, le=256, description="Number of segments for curved surfaces")
    center: bool = Field(default=True, description="Whether to center the shape at origin")


class PrintabilityAssessment(BaseSchema):
    """Printability analysis results."""
    score: float = Field(ge=0, le=10, description="Printability score (0-10)")
    issues: List[str] = Field(default_factory=list, description="List of potential printing issues")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    support_needed: bool = Field(description="Whether support material is needed")
    estimated_print_time: Optional[int] = Field(None, description="Estimated print time in minutes")


class MaterialCalculation(BaseSchema):
    """Material usage calculation."""
    volume_mm3: float = Field(gt=0, description="Volume in cubic millimeters")
    volume_cm3: float = Field(gt=0, description="Volume in cubic centimeters")
    weight_grams: float = Field(gt=0, description="Estimated weight in grams")
    material_type: str = Field(default="PLA", description="Material type used for calculation")
    density: float = Field(default=1.24, gt=0, description="Material density in g/cm³")


class GeometryValidationResult(BaseSchema):
    """Result of geometry validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    corrected_dimensions: Optional[GeometryDimensions] = None


class CADPrimitiveRequest(BaseSchema):
    """Request for creating a 3D primitive."""
    operation: str = Field(default="create_primitive", description="CAD operation type")
    geometry: PrimitiveGeometry
    quality_level: str = Field(
        default="standard",
        pattern="^(draft|standard|high|ultra)$"
    )
    validate_printability: bool = Field(default=True, description="Whether to perform printability checks")
    material_type: str = Field(default="PLA", description="Material type for calculations")


class CADPrimitiveResponse(BaseSchema):
    """Response from primitive creation."""
    success: bool
    model_file_path: Optional[str] = None
    geometry_info: Dict[str, Any] = Field(default_factory=dict)
    material_calculation: Optional[MaterialCalculation] = None
    printability_assessment: Optional[PrintabilityAssessment] = None
    validation_result: Optional[GeometryValidationResult] = None
    generation_time: float = Field(ge=0, description="Generation time in seconds")
    error_message: Optional[str] = None


class BooleanOperation(BaseSchema):
    """Boolean operation specification (for Task 2.2.2)."""
    operation_type: str = Field(
        description="Type of boolean operation",
        pattern="^(union|difference|intersection)$"
    )
    operand_a: str = Field(description="Path to first operand file")
    operand_b: str = Field(description="Path to second operand file")
    auto_repair: bool = Field(default=True, description="Automatically repair mesh after operation")


class STLExportOptions(BaseModel):
    """STL export configuration (for Task 2.2.3)."""
    mesh_resolution: float = Field(default=0.1, gt=0, le=1.0, description="Mesh resolution/tolerance")
    optimize_mesh: bool = Field(default=True, description="Optimize mesh for file size")
    validate_manifold: bool = Field(default=True, description="Ensure manifold mesh")
    auto_repair: bool = Field(default=True, description="Automatically repair mesh issues")
    include_normals: bool = Field(default=True, description="Include vertex normals in STL")


class SlicerAgentInput(BaseSchema):
    """Input for slicing operation."""
    model_file_path: str
    printer_profile: str
    material_type: str
    quality_preset: str = Field(
        default="standard",
        pattern="^(draft|standard|fine|ultra)$"
    )
    infill_percentage: int = Field(default=20, ge=0, le=100)
    layer_height: float = Field(default=0.2, gt=0, le=1.0)
    print_speed: int = Field(default=50, ge=10, le=300)


class SlicerAgentOutput(BaseSchema):
    """Output from slicing operation."""
    gcode_file_path: str
    estimated_print_time: int  # minutes
    material_usage: float  # grams
    layer_count: int
    total_movements: int
    slicing_time: float
    preview_image_path: Optional[str] = None


class PrinterAgentInput(BaseSchema):
    """Input for printer operation."""
    gcode_file_path: str
    printer_id: str
    start_immediately: bool = False
    notification_settings: Dict[str, Any] = Field(default_factory=dict)


class PrinterAgentOutput(BaseSchema):
    """Output from printer operation."""
    print_job_id: str
    status: str
    progress_percentage: float = Field(ge=0, le=100)
    current_layer: int
    temperature_bed: float
    temperature_nozzle: float
    estimated_time_remaining: int  # minutes
    error_messages: List[str] = Field(default_factory=list)


# =============================================================================
# ERROR AND VALIDATION SCHEMAS
# =============================================================================

class ErrorDetail(BaseSchema):
    """Detailed error information."""
    error_code: str
    error_type: str
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None


class ErrorResponse(BaseSchema):
    """Standard error response model."""
    success: bool = False
    error_code: str
    message: str
    details: List[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None


class ValidationErrorResponse(ErrorResponse):
    """Validation error response."""
    error_code: str = "VALIDATION_ERROR"
    field_errors: Dict[str, List[str]] = Field(default_factory=dict)


class SystemHealthResponse(BaseSchema):
    """System health check response."""
    status: str = Field(pattern="^(healthy|degraded|unhealthy)$")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str
    uptime_seconds: int
    active_workflows: int
    agent_status: Dict[str, str]
    system_metrics: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# PAGINATION AND FILTERING
# =============================================================================

class PaginationParams(BaseSchema):
    """Pagination parameters for list endpoints."""
    page: PositiveInt = Field(default=1, description="Page number")
    page_size: PositiveInt = Field(
        default=10, 
        le=100, 
        description="Items per page (max 100)"
    )


class WorkflowFilterParams(BaseSchema):
    """Filter parameters for workflow queries."""
    state: Optional[WorkflowState] = None
    user_id: Optional[str] = None
    agent_type: Optional[AgentType] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class SortParams(BaseSchema):
    """Sorting parameters."""
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$"
    )


# =============================================================================
# WEBSOCKET MODELS
# =============================================================================

class WebSocketMessage(BaseSchema):
    """WebSocket message model."""
    message_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ProgressUpdate(BaseSchema):
    """Progress update message."""
    workflow_id: str
    progress_percentage: float = Field(ge=0, le=100)
    current_step: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class StatusUpdate(BaseSchema):
    """Status update message."""
    entity_type: str  # workflow, agent, system
    entity_id: str
    status: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_error_response(
    error_code: str,
    message: str,
    details: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Create a standardized error response."""
    return ErrorResponse(
        error_code=error_code,
        message=message,
        details=details or [],
        request_id=request_id
    )


def create_validation_error_response(
    field_errors: Dict[str, List[str]],
    message: str = "Validation failed",
    request_id: Optional[str] = None
) -> ValidationErrorResponse:
    """Create a validation error response."""
    details = [
        ErrorDetail(
            error_code="FIELD_VALIDATION_ERROR",
            error_type="validation",
            message=f"Field '{field}': {'; '.join(errors)}",
            field=field
        )
        for field, errors in field_errors.items()
    ]
    
    return ValidationErrorResponse(
        message=message,
        details=details,
        field_errors=field_errors,
        request_id=request_id
    )


# =============================================================================
# SCHEMA REGISTRY - Moved to end of file to have access to all schemas
# =============================================================================

def get_schema(schema_name: str) -> Optional[type[BaseSchema]]:
    """Get a schema class by name."""
    return SCHEMA_REGISTRY.get(schema_name)


def list_schemas() -> List[str]:
    """List all available schema names."""
    return list(SCHEMA_REGISTRY.keys())

class BooleanOperationRequest(BaseSchema):
    """Request for boolean operations (Task 2.2.2)."""
    operation_type: str = Field(
        description="Type of boolean operation",
        pattern="^(union|difference|intersection)$"
    )
    operand_a: str = Field(description="Path to first operand mesh file")
    operand_b: str = Field(description="Path to second operand mesh file")
    auto_repair: bool = Field(default=True, description="Automatically repair meshes before/after operation")
    quality_level: str = Field(
        default="standard",
        pattern="^(draft|standard|high|ultra)$",
        description="Quality level for boolean operations"
    )
    fallback_enabled: bool = Field(default=True, description="Enable fallback algorithms if primary fails")


class BooleanOperationResult(BaseSchema):
    """Result from boolean operations."""
    operation_type: str
    result_file_path: str
    volume: float = Field(ge=0, description="Volume of result mesh in mm³")
    surface_area: float = Field(ge=0, description="Surface area in mm²")
    quality_score: float = Field(ge=0, le=10, description="Quality score (0-10)")
    printability_score: float = Field(ge=0, le=10, description="Printability score (0-10)")
    vertex_count: int = Field(ge=0, description="Number of vertices in result")
    face_count: int = Field(ge=0, description="Number of faces in result")
    is_manifold: bool = Field(description="Whether result mesh is manifold")
    is_watertight: bool = Field(description="Whether result mesh is watertight")
    auto_repaired: bool = Field(description="Whether automatic repair was applied")
    generation_time: float = Field(ge=0, description="Operation time in seconds")
    fallback_used: Optional[str] = Field(default=None, description="Fallback method used if any")
    repair_operations: List[str] = Field(default_factory=list, description="List of repair operations performed")


class MeshQualityReport(BaseSchema):
    """Detailed mesh quality assessment."""
    is_manifold: bool
    is_watertight: bool
    has_degenerate_faces: bool
    duplicate_vertices: int
    duplicate_faces: int
    boundary_edges: int
    non_manifold_edges: int
    volume: float
    surface_area: float
    bounds: Dict[str, List[float]]  # {"min": [x,y,z], "max": [x,y,z]}
    quality_score: float = Field(ge=0, le=10)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# =============================================================================
# STL EXPORT SCHEMAS (TASK 2.2.3)
# =============================================================================

class STLExportRequest(BaseSchema):
    """Request for STL export with quality control (Task 2.2.3)."""
    source_file_path: str = Field(description="Path to source mesh file (STL, OBJ, PLY, etc.)")
    output_file_path: str = Field(description="Desired output STL file path")
    export_options: STLExportOptions = Field(default_factory=STLExportOptions)
    quality_level: str = Field(
        default="standard",
        pattern="^(draft|standard|high|ultra)$",
        description="Quality level for export process"
    )
    perform_quality_check: bool = Field(default=True, description="Perform comprehensive quality checks")
    auto_repair_issues: bool = Field(default=True, description="Automatically repair detected issues")
    generate_report: bool = Field(default=True, description="Generate detailed quality report")


class STLExportResult(BaseSchema):
    """Result from STL export with quality control."""
    success: bool
    output_file_path: str
    file_size_bytes: int = Field(ge=0, description="Size of exported STL file")
    original_file_size: Optional[int] = Field(None, description="Original file size for comparison")
    compression_ratio: Optional[float] = Field(None, description="File size reduction ratio")
    mesh_quality_report: MeshQualityReport
    printability_assessment: PrintabilityAssessment
    export_time: float = Field(ge=0, description="Export process time in seconds")
    repairs_applied: List[str] = Field(default_factory=list, description="List of repairs applied")
    warnings: List[str] = Field(default_factory=list, description="Export warnings")
    error_message: Optional[str] = None


class MeshOptimizationReport(BaseSchema):
    """Report on mesh optimization performed during export."""
    vertices_before: int = Field(ge=0, description="Vertex count before optimization")
    vertices_after: int = Field(ge=0, description="Vertex count after optimization")
    faces_before: int = Field(ge=0, description="Face count before optimization")
    faces_after: int = Field(ge=0, description="Face count after optimization")
    duplicate_vertices_removed: int = Field(ge=0)
    duplicate_faces_removed: int = Field(ge=0)
    degenerate_faces_removed: int = Field(ge=0)
    holes_filled: int = Field(ge=0)
    optimization_time: float = Field(ge=0, description="Time spent on optimization in seconds")
    size_reduction_percent: float = Field(description="Percentage reduction in file size")


class STLValidationResult(BaseSchema):
    """STL file validation results."""
    is_valid_stl: bool
    format_errors: List[str] = Field(default_factory=list)
    structural_errors: List[str] = Field(default_factory=list)
    printability_issues: List[str] = Field(default_factory=list)
    file_size_mb: float = Field(ge=0, description="File size in megabytes")
    triangle_count: int = Field(ge=0, description="Number of triangles in STL")
    is_ascii_format: bool = Field(description="Whether STL is in ASCII format")
    validation_time: float = Field(ge=0, description="Validation time in seconds")


# Registry for quick schema lookup - Defined at end to have access to all schemas
SCHEMA_REGISTRY = {
    # Core models
    "workflow": Workflow,
    "workflow_step": WorkflowStep,
    "message": Message,
    "task_result": TaskResult,
    "agent_info": AgentInfo,
    
    # Request models
    "create_workflow_request": CreateWorkflowRequest,
    "update_workflow_request": UpdateWorkflowRequest,
    "execute_step_request": ExecuteStepRequest,
    "cancel_workflow_request": CancelWorkflowRequest,
    
    # Response models
    "workflow_response": WorkflowResponse,
    "workflow_list_response": WorkflowListResponse,
    "workflow_status_response": WorkflowStatusResponse,
    "agent_status_response": AgentStatusResponse,
    "task_execution_response": TaskExecutionResponse,
    
    # Agent-specific models
    "research_input": ResearchAgentInput,
    "research_output": ResearchAgentOutput,
    "cad_input": CADAgentInput,
    "cad_output": CADAgentOutput,
    "slicer_input": SlicerAgentInput,
    "slicer_output": SlicerAgentOutput,
    "printer_input": PrinterAgentInput,
    "printer_output": PrinterAgentOutput,
    
    # Error models
    "error_response": ErrorResponse,
    "validation_error_response": ValidationErrorResponse,
    "system_health_response": SystemHealthResponse,
    
    # WebSocket models
    "websocket_message": WebSocketMessage,
    "progress_update": ProgressUpdate,
    "status_update": StatusUpdate,
    
    # CAD-specific models
    "cad_primitive_request": CADPrimitiveRequest,
    "cad_primitive_response": CADPrimitiveResponse,
    "geometry_validation_result": GeometryValidationResult,
    "printability_assessment": PrintabilityAssessment,
    "material_calculation": MaterialCalculation,
    "boolean_operation": BooleanOperation,
    "stl_export_options": STLExportOptions,
    
    # Boolean Operations (Task 2.2.2)
    "boolean_operation_request": BooleanOperationRequest,
    "boolean_operation_result": BooleanOperationResult,
    "mesh_quality_report": MeshQualityReport,
    
    # STL Export (Task 2.2.3)
    "stl_export_request": STLExportRequest,
    "stl_export_result": STLExportResult,
    "mesh_optimization_report": MeshOptimizationReport,
    "stl_validation_result": STLValidationResult,
}
