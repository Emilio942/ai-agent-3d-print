"""
Unit tests for ParentAgent - Orchestration and workflow management.

Tests cover workflow creation, execution, agent communication,
error handling, and progress tracking.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Add the core directory to the path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from parent_agent import (
    ParentAgent, WorkflowState, WorkflowStepStatus, 
    Workflow, WorkflowStep
)
from core.api_schemas import TaskResult, AgentStatus
from core.message_queue import Message, MessagePriority, create_message_queue
from core.exceptions import WorkflowError, AgentCommunicationError, ValidationError


@pytest.fixture
def mock_message_queue():
    """Create a mock message queue."""
    queue = Mock()
    queue.send = AsyncMock()
    queue.receive = AsyncMock()
    queue.ack = AsyncMock()
    queue.nack = AsyncMock()
    return queue


@pytest.fixture
def parent_agent(mock_message_queue):
    """Create a ParentAgent instance for testing."""
    agent = ParentAgent(
        agent_id="test_parent_agent",
        message_queue=mock_message_queue,
        timeout=10.0,
        max_concurrent_workflows=3
    )
    agent.register_agent("research_agent")
    agent.register_agent("cad_agent")
    agent.register_agent("slicer_agent")
    agent.register_agent("printer_agent")
    return agent


class TestParentAgent:
    """Test cases for ParentAgent."""
    
    def test_agent_initialization(self, parent_agent):
        """Test ParentAgent initialization."""
        assert parent_agent.agent_id == "test_parent_agent"
        assert parent_agent.timeout == 10.0
        assert parent_agent.max_concurrent_workflows == 3
        assert len(parent_agent.active_workflows) == 0
        assert "research_agent" in parent_agent.registered_agents
        assert "cad_agent" in parent_agent.registered_agents
        assert "slicer_agent" in parent_agent.registered_agents
        assert "printer_agent" in parent_agent.registered_agents
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, parent_agent):
        """Test workflow creation."""
        user_request = "Create a simple cube"
        
        workflow_id = await parent_agent.create_workflow(user_request)
        
        assert workflow_id in parent_agent.active_workflows
        workflow = parent_agent.active_workflows[workflow_id]
        
        assert workflow.workflow_id == workflow_id
        assert workflow.user_request == user_request
        assert workflow.state == WorkflowState.PENDING
        assert len(workflow.steps) == 4  # research, cad, slicer, printer
        
        # Check step configuration
        step_names = [step.name for step in workflow.steps]
        assert "Requirements Analysis" in step_names
        assert "3D Model Generation" in step_names
        assert "G-code Generation" in step_names
        assert "3D Printing" in step_names
    
    @pytest.mark.asyncio
    async def test_workflow_max_limit(self, parent_agent):
        """Test maximum concurrent workflow limit."""
        # Create maximum allowed workflows
        for i in range(parent_agent.max_concurrent_workflows):
            await parent_agent.create_workflow(f"Request {i}")
        
        # Try to create one more - should raise error
        with pytest.raises(WorkflowError) as exc_info:
            await parent_agent.create_workflow("Exceeding limit")
        
        assert "Maximum concurrent workflows reached" in str(exc_info.value)
        assert exc_info.value.error_code == "MAX_WORKFLOWS_EXCEEDED"
    
    @pytest.mark.asyncio
    async def test_workflow_progress_calculation(self, parent_agent):
        """Test workflow progress calculation."""
        workflow_id = await parent_agent.create_workflow("Test request")
        workflow = parent_agent.active_workflows[workflow_id]
        
        # Initially no progress
        assert workflow.calculate_progress() == 0.0
        
        # Complete first step
        workflow.steps[0].status = WorkflowStepStatus.COMPLETED
        assert workflow.calculate_progress() == 25.0
        
        # Complete second step
        workflow.steps[1].status = WorkflowStepStatus.COMPLETED
        assert workflow.calculate_progress() == 50.0
        
        # Complete all steps
        for step in workflow.steps:
            step.status = WorkflowStepStatus.COMPLETED
        assert workflow.calculate_progress() == 100.0
    
    @pytest.mark.asyncio
    async def test_workflow_step_retry_logic(self, parent_agent):
        """Test workflow step retry logic."""
        workflow_id = await parent_agent.create_workflow("Test request")
        workflow = parent_agent.active_workflows[workflow_id]
        
        step = workflow.steps[0]
        step.max_retries = 2
        
        # Initially can retry
        assert step.can_retry is True
        
        # After first failure
        step.status = WorkflowStepStatus.FAILED
        step.retry_count = 1
        assert step.can_retry is True
        
        # After max retries
        step.retry_count = 2
        assert step.can_retry is False
    
    @pytest.mark.asyncio
    async def test_get_workflow_status(self, parent_agent):
        """Test workflow status retrieval."""
        workflow_id = await parent_agent.create_workflow("Test request")
        
        status = await parent_agent.get_workflow_status(workflow_id)
        
        assert status["workflow_id"] == workflow_id
        assert status["state"] == WorkflowState.PENDING.value
        assert status["progress"] == 0.0
        assert len(status["steps"]) == 4
        assert status["error_message"] is None
    
    @pytest.mark.asyncio
    async def test_get_workflow_status_not_found(self, parent_agent):
        """Test workflow status for non-existent workflow."""
        with pytest.raises(WorkflowError) as exc_info:
            await parent_agent.get_workflow_status("non-existent-id")
        
        assert "Workflow non-existent-id not found" in str(exc_info.value)
        assert exc_info.value.error_code == "WORKFLOW_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_cancel_workflow(self, parent_agent):
        """Test workflow cancellation."""
        workflow_id = await parent_agent.create_workflow("Test request")
        
        # Cancel the workflow
        result = await parent_agent.cancel_workflow(workflow_id)
        assert result is True
        
        workflow = parent_agent.active_workflows[workflow_id]
        assert workflow.state == WorkflowState.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_workflow(self, parent_agent):
        """Test cancelling non-existent workflow."""
        result = await parent_agent.cancel_workflow("non-existent-id")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_workflows(self, parent_agent):
        """Test listing workflows."""
        # Create some workflows
        id1 = await parent_agent.create_workflow("Request 1")
        id2 = await parent_agent.create_workflow("Request 2")
        
        workflows = await parent_agent.list_workflows()
        
        assert len(workflows) == 2
        workflow_ids = [wf["workflow_id"] for wf in workflows]
        assert id1 in workflow_ids
        assert id2 in workflow_ids
    
    @pytest.mark.asyncio
    async def test_agent_registration(self, parent_agent):
        """Test agent registration and unregistration."""
        # Register a new agent
        parent_agent.register_agent("test_agent")
        assert "test_agent" in parent_agent.registered_agents
        
        # Unregister agent
        parent_agent.unregister_agent("test_agent")
        assert "test_agent" not in parent_agent.registered_agents
    
    @pytest.mark.asyncio
    async def test_execute_task_create_workflow(self, parent_agent):
        """Test executing workflow creation task."""
        with patch.object(parent_agent, 'execute_workflow') as mock_execute:
            mock_execute.return_value = TaskResult(
                task_id="test",
                success=True,
                data={"workflow_id": "test-id"}
            )
            
            task_data = {
                "task_id": "test",
                "type": "create_workflow",
                "user_request": "Create a cube"
            }
            
            result = await parent_agent.execute_task(task_data)
            
            assert result.success is True
            assert len(parent_agent.active_workflows) == 1
    
    @pytest.mark.asyncio
    async def test_execute_task_get_status(self, parent_agent):
        """Test executing get workflow status task."""
        workflow_id = await parent_agent.create_workflow("Test request")
        
        task_data = {
            "task_id": "test",
            "type": "get_workflow_status",
            "workflow_id": workflow_id
        }
        
        result = await parent_agent.execute_task(task_data)
        
        assert result.success is True
        assert result.data["workflow_id"] == workflow_id
    
    @pytest.mark.asyncio
    async def test_execute_task_cancel_workflow(self, parent_agent):
        """Test executing cancel workflow task."""
        workflow_id = await parent_agent.create_workflow("Test request")
        
        task_data = {
            "task_id": "test",
            "type": "cancel_workflow",
            "workflow_id": workflow_id
        }
        
        result = await parent_agent.execute_task(task_data)
        
        assert result.success is True
        assert result.data["cancelled"] is True
    
    @pytest.mark.asyncio
    async def test_execute_task_list_workflows(self, parent_agent):
        """Test executing list workflows task."""
        await parent_agent.create_workflow("Test request")
        
        task_data = {
            "task_id": "test",
            "type": "list_workflows"
        }
        
        result = await parent_agent.execute_task(task_data)
        
        assert result.success is True
        assert len(result.data["workflows"]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_task_validation_error(self, parent_agent):
        """Test task execution with validation errors."""
        # Missing user_request
        task_data = {
            "task_id": "test",
            "type": "create_workflow"
        }
        
        with pytest.raises(ValidationError):
            await parent_agent.execute_task(task_data)
        
        # Unknown task type
        task_data = {
            "task_id": "test",
            "type": "unknown_type"
        }
        
        with pytest.raises(ValidationError):
            await parent_agent.execute_task(task_data)
    
    @pytest.mark.asyncio
    async def test_message_handling(self, parent_agent):
        """Test message handling."""
        # Test task response handling
        message = Message(
            sender="research_agent",
            receiver=parent_agent.agent_id,
            message_type="task_response",
            payload={
                "task_id": "test_task",
                "success": True,
                "data": {"result": "analysis complete"}
            }
        )
        
        await parent_agent._handle_message(message)
        
        # Check that response was stored
        response_key = "research_agent_test_task"
        assert response_key in parent_agent.agent_responses
        assert parent_agent.agent_responses[response_key]["success"] is True
    
    @pytest.mark.asyncio
    async def test_workflow_step_execution_input_data(self, parent_agent):
        """Test workflow step input data preparation."""
        workflow_id = await parent_agent.create_workflow("Create a cube")
        workflow = parent_agent.active_workflows[workflow_id]
        
        # Test research step input
        research_step = workflow.steps[0]
        assert research_step.agent_type == "research_agent"
        
        # Test CAD step input (should get research results)
        cad_step = workflow.steps[1]
        assert cad_step.agent_type == "cad_agent"
        
        # Test slicer step input (should get CAD results)
        slicer_step = workflow.steps[2]
        assert slicer_step.agent_type == "slicer_agent"
        
        # Test printer step input (should get slicer results)
        printer_step = workflow.steps[3]
        assert printer_step.agent_type == "printer_agent"
    
    def test_string_representations(self, parent_agent):
        """Test string representations of ParentAgent."""
        str_repr = str(parent_agent)
        assert "ParentAgent" in str_repr
        assert "test_parent_agent" in str_repr
        
        repr_str = repr(parent_agent)
        assert "ParentAgent" in repr_str
        assert "test_parent_agent" in repr_str
        assert "registered_agents" in repr_str


class TestWorkflow:
    """Test cases for Workflow class."""
    
    def test_workflow_creation(self):
        """Test workflow creation."""
        workflow_id = str(uuid.uuid4())
        workflow = Workflow(
            workflow_id=workflow_id,
            user_request="Create a sphere"
        )
        
        assert workflow.workflow_id == workflow_id
        assert workflow.user_request == "Create a sphere"
        assert workflow.state == WorkflowState.PENDING
        assert len(workflow.steps) == 0
        assert workflow.progress_percentage == 0.0
    
    def test_workflow_step_management(self):
        """Test workflow step addition and retrieval."""
        workflow = Workflow(
            workflow_id="test",
            user_request="test"
        )
        
        step = WorkflowStep(
            step_id="step1",
            name="Test Step",
            agent_type="test_agent"
        )
        
        workflow.add_step(step)
        
        assert len(workflow.steps) == 1
        assert workflow.get_step("step1") == step
        assert workflow.get_step("nonexistent") is None
    
    def test_workflow_failed_steps(self):
        """Test getting failed steps."""
        workflow = Workflow(
            workflow_id="test",
            user_request="test"
        )
        
        step1 = WorkflowStep(
            step_id="step1",
            name="Step 1",
            agent_type="agent1",
            status=WorkflowStepStatus.COMPLETED
        )
        
        step2 = WorkflowStep(
            step_id="step2",
            name="Step 2",
            agent_type="agent2",
            status=WorkflowStepStatus.FAILED
        )
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        
        failed_steps = workflow.get_failed_steps()
        assert len(failed_steps) == 1
        assert failed_steps[0] == step2


class TestWorkflowStep:
    """Test cases for WorkflowStep class."""
    
    def test_step_creation(self):
        """Test workflow step creation."""
        step = WorkflowStep(
            step_id="test_step",
            name="Test Step",
            agent_type="test_agent"
        )
        
        assert step.step_id == "test_step"
        assert step.name == "Test Step"
        assert step.agent_type == "test_agent"
        assert step.status == WorkflowStepStatus.PENDING
        assert step.retry_count == 0
        assert step.max_retries == 3
    
    def test_step_duration_calculation(self):
        """Test step duration calculation."""
        step = WorkflowStep(
            step_id="test",
            name="Test",
            agent_type="test"
        )
        
        # No duration without times
        assert step.duration is None
        
        # Set start time
        start_time = datetime.now()
        step.start_time = start_time
        assert step.duration is None  # Still no end time
        
        # Set end time
        end_time = start_time + timedelta(seconds=5)
        step.end_time = end_time
        
        duration = step.duration
        assert duration is not None
        assert duration.total_seconds() == 5.0
    
    def test_step_status_properties(self):
        """Test step status properties."""
        step = WorkflowStep(
            step_id="test",
            name="Test",
            agent_type="test"
        )
        
        # Initially pending
        assert not step.is_completed
        assert not step.is_failed
        
        # Completed status
        step.status = WorkflowStepStatus.COMPLETED
        assert step.is_completed
        assert not step.is_failed
        
        # Failed status
        step.status = WorkflowStepStatus.FAILED
        assert not step.is_completed
        assert step.is_failed
    
    def test_step_retry_logic(self):
        """Test step retry logic."""
        step = WorkflowStep(
            step_id="test",
            name="Test",
            agent_type="test",
            max_retries=2
        )
        
        # Initially can retry
        step.status = WorkflowStepStatus.FAILED
        assert step.can_retry
        
        # After first retry
        step.retry_count = 1
        assert step.can_retry
        
        # After max retries
        step.retry_count = 2
        assert not step.can_retry
        
        # Completed steps can't retry
        step.status = WorkflowStepStatus.COMPLETED
        step.retry_count = 0
        assert not step.can_retry


# Utility functions for testing
def create_test_workflow(workflow_id: str = None, user_request: str = "Test request") -> Workflow:
    """Create a test workflow with default steps."""
    if workflow_id is None:
        workflow_id = str(uuid.uuid4())
    
    workflow = Workflow(
        workflow_id=workflow_id,
        user_request=user_request
    )
    
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
    
    return workflow


def create_test_step(
    step_id: str = "test_step",
    name: str = "Test Step",
    agent_type: str = "test_agent",
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
) -> WorkflowStep:
    """Create a test workflow step."""
    return WorkflowStep(
        step_id=step_id,
        name=name,
        agent_type=agent_type,
        status=status
    )


if __name__ == "__main__":
    print("Running ParentAgent tests...")
    pytest.main([__file__, "-v"])
