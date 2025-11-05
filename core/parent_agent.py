"""
ParentAgent - Orchestration and workflow management for the 3D printing system.

This module implements the main orchestration agent that coordinates the complete
workflow for creating 3D objects from natural language descriptions.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable, Awaitable
from contextlib import asynccontextmanager

try:  # Prefer package-relative imports but fall back for legacy direct usage
    from .base_agent import BaseAgent
    from .api_schemas import AgentStatus, TaskResult
    from .message_queue import MessageQueue, Message, MessagePriority, MessageStatus, create_message_queue
    from .exceptions import (
        WorkflowError,
        AgentCommunicationError,
        AgentTimeoutError,
        ValidationError
    )
    from .logger import AgentLogger
except ImportError:  # pragma: no cover - legacy fallback for direct module execution
    try:
        from core.base_agent import BaseAgent  # type: ignore
        from core.api_schemas import AgentStatus, TaskResult  # type: ignore
        from core.message_queue import MessageQueue, Message, MessagePriority, MessageStatus, create_message_queue  # type: ignore
        from core.exceptions import (  # type: ignore
            WorkflowError,
            AgentCommunicationError,
            AgentTimeoutError,
            ValidationError
        )
        from core.logger import AgentLogger  # type: ignore
    except ImportError:
        from base_agent import BaseAgent  # type: ignore
        from api_schemas import AgentStatus, TaskResult  # type: ignore
        from message_queue import MessageQueue, Message, MessagePriority, MessageStatus, create_message_queue  # type: ignore
        from exceptions import (  # type: ignore
            WorkflowError,
            AgentCommunicationError,
            AgentTimeoutError,
            ValidationError
        )
        from logger import AgentLogger  # type: ignore


class WorkflowState(Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RESEARCH_PHASE = "research_phase"
    CAD_PHASE = "cad_phase"
    SLICING_PHASE = "slicing_phase"
    PRINTING_PHASE = "printing_phase"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepStatus(Enum):
    """Individual step status within a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Individual step in the workflow."""
    step_id: str
    name: str
    agent_type: str
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate step execution duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if step is completed successfully."""
        return self.status == WorkflowStepStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if step has failed."""
        return self.status == WorkflowStepStatus.FAILED
    
    @property
    def can_retry(self) -> bool:
        """Check if step can be retried."""
        if self.retry_count >= self.max_retries:
            return False
        if self.status == WorkflowStepStatus.COMPLETED:
            return False
        return True


@dataclass
class Workflow:
    """Complete workflow for 3D object creation."""
    workflow_id: str
    user_request: str
    state: WorkflowState = WorkflowState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    steps: List[WorkflowStep] = field(default_factory=list)
    progress_percentage: float = 0.0
    error_message: Optional[str] = None
    
    # Progress tracking callbacks
    progress_callbacks: List[Callable[[Dict[str, Any]], Awaitable[None]]] = field(
        default_factory=list, init=False
    )
    
    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow."""
        self.steps.append(step)
        self.updated_at = datetime.now()
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get step by ID."""
        return next((step for step in self.steps if step.step_id == step_id), None)
    
    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the currently executing step."""
        return next(
            (step for step in self.steps if step.status == WorkflowStepStatus.RUNNING),
            None
        )
    
    def get_failed_steps(self) -> List[WorkflowStep]:
        """Get all failed steps."""
        return [step for step in self.steps if step.is_failed]
    
    def calculate_progress(self) -> float:
        """Calculate overall workflow progress."""
        if not self.steps:
            return 0.0
        
        completed_steps = sum(1 for step in self.steps if step.is_completed)
        self.progress_percentage = (completed_steps / len(self.steps)) * 100.0
        return self.progress_percentage
    
    async def notify_progress(self, event_data: Dict[str, Any]) -> None:
        """Notify progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                await callback(event_data)
            except Exception as e:
                # Don't let callback errors affect workflow
                pass


class ParentAgent(BaseAgent):
    """
    Main orchestration agent for the 3D printing workflow.
    
    Coordinates between ResearchAgent, CADAgent, SlicerAgent, and PrinterAgent
    to complete the full workflow from natural language to 3D printed object.
    """
    
    def __init__(
        self,
        agent_id: str = "parent_agent",
        message_queue: Optional[MessageQueue] = None,
        timeout: float = 300.0,  # 5 minutes default timeout
        max_concurrent_workflows: int = 5
    ):
        """
        Initialize ParentAgent.
        
        Args:
            agent_id: Unique identifier for this agent
            message_queue: Message queue for inter-agent communication
            timeout: Default timeout for agent operations
            max_concurrent_workflows: Maximum concurrent workflows
        """
        super().__init__(agent_id)
        self.logger = AgentLogger("parent_agent")
        self.message_queue = message_queue or create_message_queue()
        self.timeout = timeout
        self.max_concurrent_workflows = max_concurrent_workflows
        
        # Workflow management
        self.active_workflows: Dict[str, Workflow] = {}
        self.workflow_lock = asyncio.Lock()
        
        # Agent registry for communication
        self.registered_agents: Set[str] = set()
        self.agent_responses: Dict[str, Dict[str, Any]] = {}
        
        # Agent status tracking
        self.status = AgentStatus.IDLE
        
        # Task execution state
        self._shutdown = False
        self._background_tasks: Set[asyncio.Task] = set()
    
    async def startup(self) -> None:
        """Start the ParentAgent and begin processing messages."""
        self.logger.info("Starting ParentAgent")
        self.status = AgentStatus.RUNNING
        
        # Start background message processing
        task = asyncio.create_task(self._process_messages())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    async def shutdown(self) -> None:
        """Shutdown the ParentAgent gracefully."""
        self.logger.info("Shutting down ParentAgent")
        self._shutdown = True
        self.status = AgentStatus.STOPPED
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
    
    def register_agent(self, agent_id: str) -> None:
        """Register a sub-agent for communication."""
        self.registered_agents.add(agent_id)
        self.logger.info(f"Registered agent: {agent_id}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister a sub-agent."""
        self.registered_agents.discard(agent_id)
        self.logger.info(f"Unregistered agent: {agent_id}")
    
    async def create_workflow(
        self,
        user_request: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> str:
        """
        Create a new workflow for processing a user request.
        
        Args:
            user_request: Natural language description of desired 3D object
            progress_callback: Optional callback for progress updates
            
        Returns:
            Workflow ID
            
        Raises:
            WorkflowError: If workflow creation fails
        """
        async with self.workflow_lock:
            if len(self.active_workflows) >= self.max_concurrent_workflows:
                raise WorkflowError(
                    "Maximum concurrent workflows reached",
                    error_code="MAX_WORKFLOWS_EXCEEDED"
                )
            
            workflow_id = str(uuid.uuid4())
            workflow = Workflow(
                workflow_id=workflow_id,
                user_request=user_request
            )
            
            if progress_callback:
                workflow.progress_callbacks.append(progress_callback)
            
            # Define workflow steps
            steps = [
                WorkflowStep(
                    step_id=f"{workflow_id}_research",
                    name="Requirements Analysis",
                    agent_type="research_agent"
                ),
                WorkflowStep(
                    step_id=f"{workflow_id}_cad",
                    name="3D Model Generation",
                    agent_type="cad_agent"
                ),
                WorkflowStep(
                    step_id=f"{workflow_id}_slicer",
                    name="G-code Generation",
                    agent_type="slicer_agent"
                ),
                WorkflowStep(
                    step_id=f"{workflow_id}_printer",
                    name="3D Printing",
                    agent_type="printer_agent"
                )
            ]
            
            for step in steps:
                workflow.add_step(step)
            
            self.active_workflows[workflow_id] = workflow
            
            self.logger.info(
                "Created workflow",
                extra={
                    "workflow_id": workflow_id,
                    "user_request": user_request,
                    "steps_count": len(steps)
                }
            )
            
            return workflow_id
    
    async def execute_workflow(self, workflow_id: str) -> TaskResult:
        """
        Execute a complete workflow.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            TaskResult with execution status and results
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise WorkflowError(
                f"Workflow {workflow_id} not found",
                error_code="WORKFLOW_NOT_FOUND"
            )
        
        try:
            self.logger.info(f"Starting workflow execution: {workflow_id}")
            workflow.state = WorkflowState.RESEARCH_PHASE
            
            # Execute steps in sequence
            for step in workflow.steps:
                try:
                    await self._execute_workflow_step(workflow, step)
                    
                    if step.is_failed and not step.can_retry:
                        workflow.state = WorkflowState.FAILED
                        workflow.error_message = step.error_message
                        break
                    
                except Exception as e:
                    step.status = WorkflowStepStatus.FAILED
                    step.error_message = str(e)
                    step.end_time = datetime.now()
                    
                    self.logger.error(
                        f"Step execution failed: {step.step_id}",
                        extra={"error": str(e), "workflow_id": workflow_id}
                    )
                    
                    if not step.can_retry:
                        workflow.state = WorkflowState.FAILED
                        workflow.error_message = str(e)
                        break
            
            # Check final state
            if workflow.state != WorkflowState.FAILED:
                if all(step.is_completed for step in workflow.steps):
                    workflow.state = WorkflowState.COMPLETED
                    workflow.completed_at = datetime.now()
                    
                    self.logger.info(f"Workflow completed successfully: {workflow_id}")
                    return TaskResult(
                        task_id=workflow_id,
                        success=True,
                        data={
                            "workflow_id": workflow_id,
                            "state": workflow.state.value,
                            "progress": workflow.calculate_progress(),
                            "steps": [
                                {
                                    "step_id": step.step_id,
                                    "name": step.name,
                                    "status": step.status.value,
                                    "duration": str(step.duration) if step.duration else None
                                }
                                for step in workflow.steps
                            ]
                        }
                    )
            
            # Handle failure case
            self.logger.error(f"Workflow failed: {workflow_id}")
            return TaskResult(
                task_id=workflow_id,
                success=False,
                error=workflow.error_message or "Workflow execution failed",
                data={
                    "workflow_id": workflow_id,
                    "state": workflow.state.value,
                    "failed_steps": [
                        {
                            "step_id": step.step_id,
                            "error": step.error_message
                        }
                        for step in workflow.get_failed_steps()
                    ]
                }
            )
            
        except Exception as e:
            workflow.state = WorkflowState.FAILED
            workflow.error_message = str(e)
            
            self.logger.error(
                f"Workflow execution error: {workflow_id}",
                extra={"error": str(e)}
            )
            
            raise WorkflowError(
                f"Workflow execution failed: {str(e)}",
                error_code="WORKFLOW_EXECUTION_FAILED"
            )
        
        finally:
            # Update workflow progress
            workflow.calculate_progress()
            workflow.updated_at = datetime.now()
            
            # Notify progress callbacks
            await workflow.notify_progress({
                "workflow_id": workflow_id,
                "state": workflow.state.value,
                "progress": workflow.progress_percentage,
                "completed": workflow.state in [WorkflowState.COMPLETED, WorkflowState.FAILED]
            })
    
    async def _execute_workflow_step(
        self,
        workflow: Workflow,
        step: WorkflowStep
    ) -> None:
        """Execute a single workflow step."""
        step.status = WorkflowStepStatus.RUNNING
        step.start_time = datetime.now()
        
        # Update workflow state based on step
        if step.agent_type == "research_agent":
            workflow.state = WorkflowState.RESEARCH_PHASE
            step.input_data = {"user_request": workflow.user_request}
        elif step.agent_type == "cad_agent":
            workflow.state = WorkflowState.CAD_PHASE
            # Build CAD task data based on research output
            import re
            research_step = workflow.get_step(f"{workflow.workflow_id}_research")
            research_data = research_step.output_data if research_step else {}
            user_req = workflow.user_request
            # Detect image-to-3D request
            image_match = re.search(r"(\S+\.(?:png|jpg|jpeg|gif))", user_req)
            if image_match:
                step.input_data = {
                    'task_id': step.step_id,
                    'operation': 'create_from_image',
                    'image_path': image_match.group(1),
                    'height_scale': research_data.get('height_scale', 5.0),
                    'base_thickness': research_data.get('base_thickness', 2.0)
                }
            else:
                # Fallback to primitive creation
                spec = research_data.get('design_specification', {})
                geometry = spec.get('object_specifications', {}).get('geometry', {})
                step.input_data = {
                    'task_id': step.step_id,
                    'operation': 'create_primitive',
                    'specifications': {'geometry': geometry},
                    'requirements': {'format_preference': research_data.get('format_preference', 'stl')}
                }
        elif step.agent_type == "slicer_agent":
            workflow.state = WorkflowState.SLICING_PHASE
            # Get CAD results from previous step
            cad_step = workflow.get_step(f"{workflow.workflow_id}_cad")
            step.input_data = {
                "model_file": cad_step.output_data.get("model_file") if cad_step else None
            }
        elif step.agent_type == "printer_agent":
            workflow.state = WorkflowState.PRINTING_PHASE
            # Get slicer results from previous step
            slicer_step = workflow.get_step(f"{workflow.workflow_id}_slicer")
            step.input_data = {
                "gcode_file": slicer_step.output_data.get("gcode_file") if slicer_step else None
            }
        
        try:
            # Send message to target agent
            response = await self._send_agent_message(
                step.agent_type,
                step.step_id,
                step.input_data
            )
            
            if response.get("success", False):
                step.status = WorkflowStepStatus.COMPLETED
                step.output_data = response.get("data", {})
                step.end_time = datetime.now()
                
                self.logger.info(
                    f"Step completed: {step.step_id}",
                    extra={
                        "workflow_id": workflow.workflow_id,
                        "duration": str(step.duration)
                    }
                )
            else:
                raise AgentCommunicationError(
                    response.get("error", "Agent execution failed"),
                    error_code="AGENT_EXECUTION_FAILED"
                )
                
        except Exception as e:
            step.status = WorkflowStepStatus.FAILED
            step.error_message = str(e)
            step.end_time = datetime.now()
            step.retry_count += 1
            
            if step.can_retry:
                self.logger.warning(
                    f"Step failed, retrying: {step.step_id}",
                    extra={
                        "retry_count": step.retry_count,
                        "max_retries": step.max_retries,
                        "error": str(e)
                    }
                )
                
                # Retry after a short delay
                await asyncio.sleep(2 ** step.retry_count)  # Exponential backoff
                await self._execute_workflow_step(workflow, step)
            else:
                self.logger.error(
                    f"Step failed permanently: {step.step_id}",
                    extra={"error": str(e)}
                )
                raise
    
    async def _send_agent_message(
        self,
        agent_type: str,
        task_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a message to a specific agent and wait for response."""
        if agent_type not in self.registered_agents:
            raise AgentCommunicationError(
                f"Agent {agent_type} not registered",
                error_code="AGENT_NOT_REGISTERED"
            )
        
        # Create message
        message = Message(
            sender=self.agent_id,
            receiver=agent_type,
            message_type="task_request",
            payload={
                "task_id": task_id,
                "data": data,
                "timeout": self.timeout
            },
            priority=MessagePriority.HIGH
        )
        
        # Send message
        await self.message_queue.send(message)
        
        self.logger.info(
            f"Sent task to {agent_type}",
            extra={"task_id": task_id, "message_id": message.id}
        )
        
        # Wait for response
        response_timeout = self.timeout
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < response_timeout:
            response_key = f"{agent_type}_{task_id}"
            if response_key in self.agent_responses:
                response = self.agent_responses.pop(response_key)
                return response
            
            await asyncio.sleep(0.1)  # Check every 100ms
        
        raise AgentTimeoutError(
            f"Timeout waiting for response from {agent_type}",
            error_code="AGENT_RESPONSE_TIMEOUT"
        )
    
    async def _process_messages(self) -> None:
        """Background task to process incoming messages."""
        while not self._shutdown:
            try:
                message = await self.message_queue.receive_message(timeout=1.0)
                if message:
                    await self._handle_message(message)
                    await self.message_queue.acknowledge_message(message.id)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Message processing error: {str(e)}")
                # Skip acknowledgment on error for now
                continue
    
    async def _handle_message(self, message: Message) -> None:
        """Handle incoming messages from other agents."""
        if message.message_type == "task_response":
            # Store agent response
            task_id = message.payload.get("task_id")
            if task_id:
                response_key = f"{message.sender}_{task_id}"
                self.agent_responses[response_key] = message.payload
                
                self.logger.info(
                    f"Received response from {message.sender}",
                    extra={"task_id": task_id, "message_id": message.id}
                )
        elif message.message_type == "status_update":
            # Handle status updates from agents
            self.logger.info(
                f"Status update from {message.sender}",
                extra={"status": message.payload}
            )
        else:
            self.logger.warning(
                f"Unknown message type: {message.message_type}",
                extra={"sender": message.sender}
            )
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current status of a workflow."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise WorkflowError(
                f"Workflow {workflow_id} not found",
                error_code="WORKFLOW_NOT_FOUND"
            )
        
        return {
            "workflow_id": workflow_id,
            "state": workflow.state.value,
            "progress": workflow.calculate_progress(),
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "steps": [
                {
                    "step_id": step.step_id,
                    "name": step.name,
                    "agent_type": step.agent_type,
                    "status": step.status.value,
                    "start_time": step.start_time.isoformat() if step.start_time else None,
                    "end_time": step.end_time.isoformat() if step.end_time else None,
                    "duration": str(step.duration) if step.duration else None,
                    "retry_count": step.retry_count,
                    "error_message": step.error_message
                }
                for step in workflow.steps
            ],
            "error_message": workflow.error_message
        }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False
        
        if workflow.state in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
            return False
        
        workflow.state = WorkflowState.CANCELLED
        workflow.updated_at = datetime.now()
        
        # Cancel any running steps
        current_step = workflow.get_current_step()
        if current_step:
            current_step.status = WorkflowStepStatus.FAILED
            current_step.error_message = "Workflow cancelled by user"
            current_step.end_time = datetime.now()
        
        self.logger.info(f"Workflow cancelled: {workflow_id}")
        return True
    
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows."""
        return [
            {
                "workflow_id": wf.workflow_id,
                "state": wf.state.value,
                "progress": wf.calculate_progress(),
                "created_at": wf.created_at.isoformat(),
                "user_request": wf.user_request[:100] + "..." if len(wf.user_request) > 100 else wf.user_request
            }
            for wf in self.active_workflows.values()
        ]
    
    async def execute_task(self, task_data: Dict[str, Any]) -> TaskResult:
        """
        Execute a task (implements BaseAgent interface).
        
        For ParentAgent, this primarily handles workflow creation and execution.
        """
        task_id = task_data.get("task_id")
        task_type = task_data.get("type", "create_workflow")
        
        if task_type == "create_workflow":
            user_request = task_data.get("user_request")
            if not user_request:
                raise ValidationError("user_request is required for workflow creation")
            
            workflow_id = await self.create_workflow(user_request)
            result = await self.execute_workflow(workflow_id)
            return result
            
        elif task_type == "get_workflow_status":
            workflow_id = task_data.get("workflow_id")
            if not workflow_id:
                raise ValidationError("workflow_id is required")
            
            status = await self.get_workflow_status(workflow_id)
            return TaskResult(
                task_id=task_id,
                success=True,
                data=status
            )
            
        elif task_type == "cancel_workflow":
            workflow_id = task_data.get("workflow_id")
            if not workflow_id:
                raise ValidationError("workflow_id is required")
            
            cancelled = await self.cancel_workflow(workflow_id)
            return TaskResult(
                task_id=task_id,
                success=cancelled,
                data={"cancelled": cancelled}
            )
            
        elif task_type == "list_workflows":
            workflows = await self.list_workflows()
            return TaskResult(
                task_id=task_id,
                success=True,
                data={"workflows": workflows}
            )
        
        else:
            raise ValidationError(f"Unknown task type: {task_type}")
    
    @asynccontextmanager
    async def workflow_context(self, workflow_id: str):
        """Context manager for workflow operations."""
        try:
            yield self.active_workflows[workflow_id]
        finally:
            # Cleanup if needed
            pass
    
    def __str__(self) -> str:
        """String representation of ParentAgent."""
        return f"ParentAgent(id={self.agent_id}, active_workflows={len(self.active_workflows)})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"ParentAgent(agent_id='{self.agent_id}', "
            f"status={self.status.value}, "
            f"active_workflows={len(self.active_workflows)}, "
            f"registered_agents={self.registered_agents})"
        )
    
    # =============================================================================
    # WORKFLOW-SPECIFIC EXECUTION METHODS FOR API INTEGRATION
    # =============================================================================
    
    async def initialize(self) -> None:
        """Initialize the ParentAgent and all sub-agents."""
        try:
            self.logger.info("Initializing ParentAgent and sub-agents")
            
            # Import and initialize agents
            from agents.research_agent import ResearchAgent
            from agents.cad_agent import CADAgent
            from agents.slicer_agent import SlicerAgent
            from agents.printer_agent import PrinterAgent
            
            # Initialize sub-agents
            self._research_agent = ResearchAgent()
            self._cad_agent = CADAgent()
            self._slicer_agent = SlicerAgent()
            self._slicer_agent.set_mock_mode(True)  # Enable mock mode for testing
            self.logger.info(f"Set slicer mock mode to: {self._slicer_agent.mock_mode}")
            self._printer_agent = PrinterAgent()
            
            # Register agents
            self.register_agent("research_agent")
            self.register_agent("cad_agent") 
            self.register_agent("slicer_agent")
            self.register_agent("printer_agent")
            
            self.status = AgentStatus.RUNNING
            self.logger.info("ParentAgent initialization completed")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ParentAgent: {e}")
            self.status = AgentStatus.ERROR
            raise
    
    async def execute_research_workflow(
        self, 
        input_data: Dict[str, Any], 
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> TaskResult:
        """Execute the research phase of the workflow."""
        try:
            self.logger.info("Starting research workflow phase")
            
            if progress_callback:
                await progress_callback({
                    "percentage": 10,
                    "current_step": "Analyzing user request",
                    "message": "Starting research and concept generation"
                })
            
            # Handle both string and dict input
            if isinstance(input_data, str):
                user_request = input_data
                workflow_id = 'unknown'
                metadata = {}
            else:
                user_request = input_data.get("user_request", input_data)
                workflow_id = input_data.get('workflow_id', 'unknown')
                metadata = input_data.get("metadata", {})
            
            # Execute research agent
            research_result = await self._research_agent.execute_task({
                "task_id": f"research_{workflow_id}",
                "operation": "analyze_and_research",
                "user_request": user_request,
                "metadata": metadata
            })
            
            if progress_callback:
                await progress_callback({
                    "percentage": 90,
                    "current_step": "Research completed",
                    "message": "Research and concept generation completed"
                })
            
            return TaskResult(
                success=research_result.success,
                data={
                    "design_specification": research_result.data,
                    "user_request": user_request
                },
                error_message=research_result.error_message
            )
            
        except Exception as e:
            self.logger.error(f"Research workflow failed: {e}")
            return TaskResult(
                success=False,
                error_message=f"Research phase failed: {str(e)}",
                data={}
            )
    
    async def execute_cad_workflow(
        self, 
        input_data: Dict[str, Any], 
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> TaskResult:
        """Execute the CAD generation phase of the workflow."""
        try:
            self.logger.info("Starting CAD workflow phase")

            if progress_callback:
                await progress_callback({
                    "percentage": 10,
                    "current_step": "Processing design specification",
                    "message": "Starting 3D model generation"
                })

            # Get research output and extract user_request
            if hasattr(input_data, 'data'):
                research_output = input_data.data
                user_request = research_output.get('user_request', '')
                metadata = research_output.get('metadata', {})
                workflow_id = research_output.get('workflow_id', 'unknown')
            else:
                research_output = input_data
                user_request = research_output.get('user_request', '') if isinstance(research_output, dict) else str(research_output)
                metadata = research_output.get('metadata', {}) if isinstance(research_output, dict) else {}
                workflow_id = research_output.get('workflow_id', 'unknown') if isinstance(research_output, dict) else 'unknown'

            # Early image-to-3D conversion handling
            import re
            image_match = re.search(r"(\S+\.(?:png|jpg|jpeg|gif))", user_request)
            if image_match:
                image_path = image_match.group(1)
                cad_input_data = {
                    'operation': 'create_from_image',
                    'image_path': image_path,
                    'height_scale': metadata.get('height_scale', 5.0),
                    'base_thickness': metadata.get('base_thickness', 2.0)
                }
                cad_result = await self._cad_agent.execute_task(cad_input_data)
                if not cad_result.success:
                    raise WorkflowError(f"CAD phase failed: {cad_result.error_message}")
                stl_file = cad_result.data.get('model_file') or cad_result.data.get('stl_file')
                return TaskResult(
                    success=True,
                    data={
                        'stl_file': stl_file,
                        'cad_output': cad_result.data,
                        'workflow_id': workflow_id,
                        'metadata': metadata
                    }
                )

            # Get CAD specifications from research output
            design_spec = research_output.get("design_specification", {})
            
            # Extract and format specifications for CAD agent
            object_specs = design_spec.get("object_specifications", {})
            geometry = object_specs.get("geometry", {})
            primitives = object_specs.get("primitives", [])
            
            # Convert dimensions to the format CAD agent expects
            cad_dimensions = {}
            
            # First check for dimensions in geometry section
            if "dimensions" in geometry:
                dims = geometry["dimensions"] 
                # Handle both formats: {x,y,z} or {length,width,height}
                if "x" in dims and "y" in dims and "z" in dims:
                    cad_dimensions = {"x": dims["x"], "y": dims["y"], "z": dims["z"]}
                elif "length" in dims and "width" in dims and "height" in dims:
                    cad_dimensions = {"x": dims["length"], "y": dims["width"], "z": dims["height"]}
            
            # If no dimensions found, check primitives section
            if not cad_dimensions and primitives:
                for primitive in primitives:
                    if primitive.get("type") == "box":
                        dims = primitive.get("dimensions", {})
                        if "length" in dims and "width" in dims and "height" in dims:
                            cad_dimensions = {"x": dims["length"], "y": dims["width"], "z": dims["height"]}
                            break
                    
            # Fallback to default dimensions for cube if still empty
            if not cad_dimensions:
                cad_dimensions = {"x": 20, "y": 20, "z": 20}  # 2cm cube default
            # Determine the shape type
            shape_type = geometry.get("primitive_type", "cube")
            if not shape_type and primitives:
                for primitive in primitives:
                    if primitive.get("type") == "box":
                        shape_type = "cube"
                        break
                        
            cad_specifications = {
                "geometry": {
                    "type": geometry.get("type", "primitive"),
                    "base_shape": shape_type,
                    "dimensions": cad_dimensions
                }
            }
            
            # Determine CAD task data
            import re
            image_match = re.search(r"(\S+\.(?:png|jpg|jpeg|gif))", user_request or "")
            if image_match:
                cad_input_data = {
                    'operation': 'create_from_image',
                    'image_path': image_match.group(1),
                    'height_scale': metadata.get('height_scale', 5.0),
                    'base_thickness': metadata.get('base_thickness', 2.0)
                }
            else:
                cad_input_data = {
                    'operation': 'create_primitive',
                    'specifications': cad_specifications,
                    'requirements': {'format_preference': metadata.get('format_preference', 'stl')}
                }

            # Execute CAD agent task
            cad_result = await self._cad_agent.execute_task(cad_input_data)
            if progress_callback:
                await progress_callback({
                    'percentage': 90,
                    'current_step': '3D model generated',
                    'message': '3D model generation completed'
                })

            # Process CAD result
            if not cad_result.success:
                raise WorkflowError(f"CAD phase failed: {cad_result.error_message}")

            # Prepare output for slicing
            # Extract stl_file from result
            stl_file = cad_result.data.get('model_file') or cad_result.data.get('stl_file')

            return TaskResult(
                success=True,
                data={
                    'stl_file': stl_file,
                    'cad_output': cad_result.data,
                    'workflow_id': workflow_id,
                    'metadata': metadata
                }
            )
            
        except Exception as e:
            self.logger.error(f"CAD workflow failed: {e}")
            return TaskResult(
                success=False,
                error_message=f"CAD phase failed: {str(e)}",
                data={}
            )
    
    async def execute_slicer_workflow(
        self, 
        input_data: Dict[str, Any], 
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> TaskResult:
        """Execute the slicing phase of the workflow."""
        try:
            self.logger.info("Starting slicer workflow phase")
            
            if progress_callback:
                await progress_callback({
                    "percentage": 10,
                    "current_step": "Loading STL file",
                    "message": "Starting G-code generation"
                })
            
            # Get CAD output - handle TaskResult object
            if hasattr(input_data, 'data'):
                # input_data is a TaskResult object
                cad_output = input_data.data
                workflow_id = 'unknown'
                metadata = {}
            elif isinstance(input_data, dict):
                cad_output = input_data.get("cad_output", input_data)
                workflow_id = input_data.get('workflow_id', 'unknown')
                metadata = input_data.get("metadata", {})
            else:
                # Fallback
                cad_output = {}
                workflow_id = 'unknown'
                metadata = {}
                
            stl_file = cad_output.get("stl_file")
            
            if not stl_file:
                raise ValueError("No STL file available from CAD phase")
            
            # Get printer profile from metadata
            printer_profile = metadata.get("printer_profile", "ender3_pla")
            quality_level = metadata.get("quality_level", "standard")
            material_type = metadata.get("material_type", "PLA")
            
            # Execute slicer agent - map to SlicerAgentInput schema format
            slicer_result = await self._slicer_agent.execute_task({
                "task_type": "slice_stl",
                "model_file_path": stl_file,          # Map stl_file -> model_file_path
                "printer_profile": printer_profile,
                "material_type": material_type,      # Required field
                "quality_preset": quality_level,     # Map quality_level -> quality_preset
                "infill_percentage": metadata.get("infill_percentage", 20),
                "layer_height": metadata.get("layer_height", 0.2),
                "print_speed": metadata.get("print_speed", 50)
            })
            
            if progress_callback:
                await progress_callback({
                    "percentage": 90,
                    "current_step": "G-code generated",
                    "message": "G-code generation completed"
                })
            
            return TaskResult(
                success=slicer_result.success,
                data={
                    "gcode_file": slicer_result.data.get("gcode_file_path"),
                    "slice_info": {
                        "estimated_print_time": slicer_result.data.get("estimated_print_time"),
                        "material_usage": slicer_result.data.get("material_usage"),
                        "layer_count": slicer_result.data.get("layer_count"),
                        "slicing_time": slicer_result.data.get("slicing_time")
                    },
                    "stl_file": stl_file
                },
                error_message=slicer_result.error_message
            )
            
        except Exception as e:
            self.logger.error(f"Slicer workflow failed: {e}")
            return TaskResult(
                success=False,
                error_message=f"Slicing phase failed: {str(e)}",
                data={}
            )
    
    async def execute_printer_workflow(
        self, 
        input_data: Dict[str, Any], 
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> TaskResult:
        """Execute the printing phase of the workflow."""
        try:
            self.logger.info("Starting printer workflow phase")
            
            if progress_callback:
                await progress_callback({
                    "percentage": 10,
                    "current_step": "Connecting to printer",
                    "message": "Starting 3D printing"
                })
            
            # Get slicer output - handle TaskResult object
            if hasattr(input_data, 'data'):
                # input_data is a TaskResult object
                slicing_output = input_data.data
                workflow_id = 'unknown'
                metadata = {}
            elif isinstance(input_data, dict):
                slicing_output = input_data.get("slicing_output", input_data)
                workflow_id = input_data.get('workflow_id', 'unknown')
                metadata = input_data.get("metadata", {})
            else:
                # Fallback
                slicing_output = {}
                workflow_id = 'unknown'
                metadata = {}
                
            gcode_file = None
            if hasattr(slicing_output, 'get'):
                # slicing_output is a dict
                gcode_file = slicing_output.get("gcode_file")
            elif hasattr(slicing_output, 'data'):
                # slicing_output is a TaskResult object
                gcode_file = slicing_output.data.get("gcode_file_path") if hasattr(slicing_output.data, 'get') else None
            else:
                # Try to extract from object attributes
                gcode_file = getattr(slicing_output, 'gcode_file', None) or getattr(slicing_output, 'gcode_file_path', None)
            
            if not gcode_file:
                raise ValueError("No G-code file available from slicing phase")
            
            # Setup progress callback for streaming
            async def streaming_progress_callback(progress_data):
                if progress_callback:
                    await progress_callback({
                        "percentage": 10 + (progress_data.get("progress_percentage", 0) * 0.8),
                        "current_step": f"Printing: {progress_data.get('current_command', 'Processing')}",
                        "message": f"Printing progress: {progress_data.get('progress_percentage', 0):.1f}%"
                    })
            
            # Execute printing
            print_result = await self._printer_agent.execute_task({
                "task_id": f"print_{workflow_id}",
                "operation": "stream_gcode",
                "specifications": {
                    "gcode_file": gcode_file,
                    "progress_callback": streaming_progress_callback
                },
                "metadata": metadata
            })
            
            if progress_callback:
                await progress_callback({
                    "percentage": 100,
                    "current_step": "Printing completed",
                    "message": "3D printing completed successfully"
                })
            
            return TaskResult(
                success=print_result.success if hasattr(print_result, 'success') else print_result.get("success", False),
                data={
                    "print_result": print_result.data if hasattr(print_result, 'data') else print_result,
                    "gcode_file": gcode_file
                },
                error_message=(print_result.error_message if hasattr(print_result, 'error_message') else None)
            )
            
        except Exception as e:
            self.logger.error(f"Printer workflow failed: {e}")
            return TaskResult(
                success=False,
                error_message=f"Printing phase failed: {str(e)}",
                data={}
            )
