"""
Unit tests for API schemas module.

Tests all Pydantic models for validation, serialization, and business logic.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4
from pydantic import ValidationError

from core.api_schemas import (
    # Enums
    WorkflowState, WorkflowStepStatus, TaskStatus, AgentStatus, 
    MessagePriority, MessageStatus, AgentType,
    
    # Core models
    TaskResult, AgentInfo, Message, WorkflowStep, Workflow,
    
    # Request models
    CreateWorkflowRequest, UpdateWorkflowRequest, ExecuteStepRequest,
    CancelWorkflowRequest,
    
    # Response models
    WorkflowResponse, WorkflowListResponse, WorkflowStatusResponse,
    AgentStatusResponse, TaskExecutionResponse,
    
    # Agent-specific models
    ResearchAgentInput, ResearchAgentOutput, CADAgentInput, CADAgentOutput,
    SlicerAgentInput, SlicerAgentOutput, PrinterAgentInput, PrinterAgentOutput,
    
    # Error models
    ErrorDetail, ErrorResponse, ValidationErrorResponse, SystemHealthResponse,
    
    # WebSocket models
    WebSocketMessage, ProgressUpdate, StatusUpdate,
    
    # Utility functions
    create_error_response, create_validation_error_response,
    get_schema, list_schemas, SCHEMA_REGISTRY
)


class TestEnums:
    """Test enum definitions and values."""
    
    def test_workflow_state_enum(self):
        """Test WorkflowState enum values."""
        assert WorkflowState.PENDING == "pending"
        assert WorkflowState.RESEARCH_PHASE == "research_phase"
        assert WorkflowState.CAD_PHASE == "cad_phase"
        assert WorkflowState.SLICING_PHASE == "slicing_phase"
        assert WorkflowState.PRINTING_PHASE == "printing_phase"
        assert WorkflowState.COMPLETED == "completed"
        assert WorkflowState.FAILED == "failed"
        assert WorkflowState.CANCELLED == "cancelled"
    
    def test_workflow_step_status_enum(self):
        """Test WorkflowStepStatus enum values."""
        assert WorkflowStepStatus.PENDING == "pending"
        assert WorkflowStepStatus.RUNNING == "running"
        assert WorkflowStepStatus.COMPLETED == "completed"
        assert WorkflowStepStatus.FAILED == "failed"
        assert WorkflowStepStatus.SKIPPED == "skipped"
    
    def test_agent_type_enum(self):
        """Test AgentType enum values."""
        assert AgentType.PARENT == "parent"
        assert AgentType.RESEARCH == "research"
        assert AgentType.CAD == "cad"
        assert AgentType.SLICER == "slicer"
        assert AgentType.PRINTER == "printer"


class TestCoreModels:
    """Test core data models."""
    
    def test_task_result_creation(self):
        """Test TaskResult model creation and validation."""
        # Valid task result
        result = TaskResult(
            success=True,
            data={"key": "value"},
            execution_time=1.5
        )
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.execution_time == 1.5
        assert result.error_message is None
        assert result.metadata == {}
    
    def test_task_result_failure(self):
        """Test TaskResult for failed task."""
        result = TaskResult(
            success=False,
            error_message="Task failed",
            metadata={"retry_count": 3}
        )
        assert result.success is False
        assert result.error_message == "Task failed"
        assert result.metadata["retry_count"] == 3
    
    def test_agent_info_creation(self):
        """Test AgentInfo model creation."""
        agent = AgentInfo(
            agent_id="test_agent",
            agent_type=AgentType.RESEARCH,
            status=AgentStatus.RUNNING,
            capabilities=["analyze", "research"],
            version="1.0.0"
        )
        assert agent.agent_id == "test_agent"
        assert agent.agent_type == AgentType.RESEARCH
        assert agent.status == AgentStatus.RUNNING
        assert agent.capabilities == ["analyze", "research"]
        assert agent.version == "1.0.0"
    
    def test_message_creation(self):
        """Test Message model creation with defaults."""
        message = Message(
            sender_id="agent1",
            recipient_id="agent2",
            message_type="task_request",
            payload={"task": "analyze"}
        )
        assert message.sender_id == "agent1"
        assert message.recipient_id == "agent2"
        assert message.message_type == "task_request"
        assert message.priority == MessagePriority.NORMAL
        assert message.status == MessageStatus.PENDING
        assert message.payload == {"task": "analyze"}
        assert message.retry_count == 0
        assert message.max_retries == 3
        # Check that message_id was auto-generated
        assert message.message_id is not None
        assert len(message.message_id) > 0
    
    def test_workflow_step_creation(self):
        """Test WorkflowStep model creation."""
        step = WorkflowStep(
            name="Research Phase",
            agent_type=AgentType.RESEARCH,
            input_data={"request": "analyze requirements"}
        )
        assert step.name == "Research Phase"
        assert step.agent_type == AgentType.RESEARCH
        assert step.status == WorkflowStepStatus.PENDING
        assert step.input_data == {"request": "analyze requirements"}
        assert step.output_data == {}
        assert step.retry_count == 0
        assert step.max_retries == 3
        # Check auto-generated step_id
        assert step.step_id is not None
    
    def test_workflow_step_duration(self):
        """Test WorkflowStep duration calculation."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        step = WorkflowStep(
            name="Test Step",
            agent_type=AgentType.CAD,
            start_time=start_time,
            end_time=end_time
        )
        assert step.duration_seconds == 30.0
    
    def test_workflow_step_duration_incomplete(self):
        """Test WorkflowStep duration when incomplete."""
        step = WorkflowStep(
            name="Test Step",
            agent_type=AgentType.CAD,
            start_time=datetime.now()
            # No end_time
        )
        assert step.duration_seconds is None
    
    def test_workflow_creation(self):
        """Test Workflow model creation."""
        workflow = Workflow(
            user_request="Create a small gear",
            user_id="user123"
        )
        assert workflow.user_request == "Create a small gear"
        assert workflow.state == WorkflowState.PENDING
        assert workflow.progress_percentage == 0.0
        assert workflow.user_id == "user123"
        assert workflow.steps == []
        assert workflow.metadata == {}
        # Check auto-generated workflow_id
        assert workflow.workflow_id is not None
    
    def test_workflow_request_validation(self):
        """Test Workflow user_request validation."""
        # Valid request
        workflow = Workflow(user_request="Valid request")
        assert workflow.user_request == "Valid request"
        
        # Empty request should fail
        with pytest.raises(Exception):  # Pydantic ValidationError
            Workflow(user_request="")
        
        # Whitespace-only request should fail
        with pytest.raises(Exception):  # Pydantic ValidationError
            Workflow(user_request="   ")
        
        # Request with leading/trailing whitespace should be stripped
        workflow = Workflow(user_request="  Request with spaces  ")
        assert workflow.user_request == "Request with spaces"


class TestRequestModels:
    """Test API request models."""
    
    def test_create_workflow_request(self):
        """Test CreateWorkflowRequest validation."""
        request = CreateWorkflowRequest(
            user_request="Create a phone case",
            user_id="user123",
            priority=MessagePriority.HIGH,
            metadata={"urgent": True}
        )
        assert request.user_request == "Create a phone case"
        assert request.user_id == "user123"
        assert request.priority == MessagePriority.HIGH
        assert request.metadata == {"urgent": True}
    
    def test_create_workflow_request_minimal(self):
        """Test CreateWorkflowRequest with minimal data."""
        request = CreateWorkflowRequest(user_request="Simple request")
        assert request.user_request == "Simple request"
        assert request.user_id is None
        assert request.priority == MessagePriority.NORMAL
        assert request.metadata == {}
    
    def test_create_workflow_request_validation_error(self):
        """Test CreateWorkflowRequest validation errors."""
        # Empty request
        with pytest.raises(Exception):  # Pydantic ValidationError
            CreateWorkflowRequest(user_request="")
        
        # Too long request
        long_request = "x" * 1001
        with pytest.raises(Exception):  # Pydantic ValidationError
            CreateWorkflowRequest(user_request=long_request)
    
    def test_update_workflow_request(self):
        """Test UpdateWorkflowRequest."""
        request = UpdateWorkflowRequest(
            state=WorkflowState.COMPLETED,
            metadata={"result": "success"}
        )
        assert request.state == WorkflowState.COMPLETED
        assert request.error_message is None
        assert request.metadata == {"result": "success"}
    
    def test_execute_step_request(self):
        """Test ExecuteStepRequest."""
        request = ExecuteStepRequest(
            step_id="step123",
            input_data={"param": "value"},
            timeout=30.0
        )
        assert request.step_id == "step123"
        assert request.input_data == {"param": "value"}
        assert request.timeout == 30.0
    
    def test_cancel_workflow_request(self):
        """Test CancelWorkflowRequest."""
        request = CancelWorkflowRequest(reason="User requested cancellation")
        assert request.reason == "User requested cancellation"
        
        # Test with no reason
        request = CancelWorkflowRequest()
        assert request.reason is None


class TestResponseModels:
    """Test API response models."""
    
    def test_workflow_response(self):
        """Test WorkflowResponse model."""
        workflow = Workflow(user_request="Test request")
        response = WorkflowResponse(
            workflow=workflow,
            message="Workflow created successfully"
        )
        assert response.workflow == workflow
        assert response.message == "Workflow created successfully"
    
    def test_workflow_list_response(self):
        """Test WorkflowListResponse model."""
        workflows = [
            Workflow(user_request="Request 1"),
            Workflow(user_request="Request 2")
        ]
        response = WorkflowListResponse(
            workflows=workflows,
            total_count=2,
            page=1,
            page_size=10
        )
        assert len(response.workflows) == 2
        assert response.total_count == 2
        assert response.page == 1
        assert response.page_size == 10
    
    def test_workflow_status_response(self):
        """Test WorkflowStatusResponse model."""
        step = WorkflowStep(name="Test Step", agent_type=AgentType.RESEARCH)
        response = WorkflowStatusResponse(
            workflow_id="workflow123",
            state=WorkflowState.RESEARCH_PHASE,
            progress_percentage=25.0,
            current_step=step,
            estimated_completion=datetime.now() + timedelta(minutes=30)
        )
        assert response.workflow_id == "workflow123"
        assert response.state == WorkflowState.RESEARCH_PHASE
        assert response.progress_percentage == 25.0
        assert response.current_step == step


class TestAgentSpecificModels:
    """Test agent-specific input/output models."""
    
    def test_research_agent_input(self):
        """Test ResearchAgentInput model."""
        input_data = ResearchAgentInput(
            user_request="Create a gear",
            context={"material": "PLA"},
            analysis_depth="detailed"
        )
        assert input_data.user_request == "Create a gear"
        assert input_data.context == {"material": "PLA"}
        assert input_data.analysis_depth == "detailed"
    
    def test_research_agent_input_validation(self):
        """Test ResearchAgentInput validation."""
        # Invalid analysis_depth
        with pytest.raises(Exception):  # Pydantic ValidationError
            ResearchAgentInput(
                user_request="Test",
                analysis_depth="invalid"
            )
    
    def test_research_agent_output(self):
        """Test ResearchAgentOutput model."""
        output = ResearchAgentOutput(
            requirements={"size": "small"},
            object_specifications={"diameter": 10},
            material_recommendations=["PLA", "PETG"],
            complexity_score=7.5,
            feasibility_assessment="High feasibility",
            recommendations=["Use supports", "0.2mm layer height"]
        )
        assert output.requirements == {"size": "small"}
        assert output.complexity_score == 7.5
        assert len(output.material_recommendations) == 2
        assert len(output.recommendations) == 2
    
    def test_cad_agent_models(self):
        """Test CAD agent input/output models."""
        input_data = CADAgentInput(
            specifications={"type": "gear"},
            requirements={"diameter": 20},
            format_preference="stl",
            quality_level="high"
        )
        assert input_data.format_preference == "stl"
        assert input_data.quality_level == "high"
        
        output = CADAgentOutput(
            model_file_path="/path/to/model.stl",
            model_format="stl",
            dimensions={"x": 20, "y": 20, "z": 5},
            volume=1570.8,
            surface_area=628.3,
            complexity_metrics={"vertices": 1000},
            generation_time=15.5,
            quality_score=8.5
        )
        assert output.model_file_path == "/path/to/model.stl"
        assert output.dimensions["x"] == 20
        assert output.quality_score == 8.5
    
    def test_slicer_agent_models(self):
        """Test Slicer agent input/output models."""
        input_data = SlicerAgentInput(
            model_file_path="/path/to/model.stl",
            printer_profile="prusa_mk3s",
            material_type="PLA",
            quality_preset="fine",
            infill_percentage=25,
            layer_height=0.15,
            print_speed=40
        )
        assert input_data.infill_percentage == 25
        assert input_data.layer_height == 0.15
        
        output = SlicerAgentOutput(
            gcode_file_path="/path/to/output.gcode",
            estimated_print_time=120,
            material_usage=15.5,
            layer_count=100,
            total_movements=5000,
            slicing_time=3.2
        )
        assert output.estimated_print_time == 120
        assert output.material_usage == 15.5
    
    def test_printer_agent_models(self):
        """Test Printer agent input/output models."""
        input_data = PrinterAgentInput(
            gcode_file_path="/path/to/print.gcode",
            printer_id="printer001",
            start_immediately=True,
            notification_settings={"email": True}
        )
        assert input_data.printer_id == "printer001"
        assert input_data.start_immediately is True
        
        output = PrinterAgentOutput(
            print_job_id="job123",
            status="printing",
            progress_percentage=45.0,
            current_layer=45,
            temperature_bed=60.0,
            temperature_nozzle=210.0,
            estimated_time_remaining=75
        )
        assert output.print_job_id == "job123"
        assert output.progress_percentage == 45.0


class TestErrorModels:
    """Test error and validation models."""
    
    def test_error_detail(self):
        """Test ErrorDetail model."""
        detail = ErrorDetail(
            error_code="FIELD_ERROR",
            error_type="validation",
            message="Invalid value",
            field="user_request",
            value=""
        )
        assert detail.error_code == "FIELD_ERROR"
        assert detail.field == "user_request"
        assert detail.value == ""
    
    def test_error_response(self):
        """Test ErrorResponse model."""
        detail = ErrorDetail(
            error_code="TEST_ERROR",
            error_type="test",
            message="Test error"
        )
        response = ErrorResponse(
            error_code="API_ERROR",
            message="API error occurred",
            details=[detail],
            request_id="req123"
        )
        assert response.success is False
        assert response.error_code == "API_ERROR"
        assert len(response.details) == 1
        assert response.request_id == "req123"
    
    def test_validation_error_response(self):
        """Test ValidationErrorResponse model."""
        response = ValidationErrorResponse(
            message="Validation failed",
            field_errors={"user_request": ["Required field missing"]},
            request_id="req123"
        )
        assert response.error_code == "VALIDATION_ERROR"
        assert response.field_errors["user_request"] == ["Required field missing"]
    
    def test_system_health_response(self):
        """Test SystemHealthResponse model."""
        response = SystemHealthResponse(
            status="healthy",
            version="1.0.0",
            uptime_seconds=3600,
            active_workflows=5,
            agent_status={"parent": "running", "research": "idle"},
            system_metrics={"cpu_usage": 45.2, "memory_usage": 67.8}
        )
        assert response.status == "healthy"
        assert response.uptime_seconds == 3600
        assert response.active_workflows == 5
        assert response.agent_status["parent"] == "running"


class TestWebSocketModels:
    """Test WebSocket communication models."""
    
    def test_websocket_message(self):
        """Test WebSocketMessage model."""
        message = WebSocketMessage(
            message_type="status_update",
            payload={"status": "running"}
        )
        assert message.message_type == "status_update"
        assert message.payload == {"status": "running"}
        assert isinstance(message.timestamp, datetime)
    
    def test_progress_update(self):
        """Test ProgressUpdate model."""
        update = ProgressUpdate(
            workflow_id="workflow123",
            progress_percentage=75.0,
            current_step="CAD Generation",
            message="Generating 3D model"
        )
        assert update.workflow_id == "workflow123"
        assert update.progress_percentage == 75.0
        assert update.current_step == "CAD Generation"
    
    def test_status_update(self):
        """Test StatusUpdate model."""
        update = StatusUpdate(
            entity_type="workflow",
            entity_id="workflow123",
            status="completed",
            message="Workflow completed successfully"
        )
        assert update.entity_type == "workflow"
        assert update.entity_id == "workflow123"
        assert update.status == "completed"


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_error_response(self):
        """Test create_error_response utility function."""
        response = create_error_response(
            error_code="TEST_ERROR",
            message="Test error message",
            request_id="req123"
        )
        assert isinstance(response, ErrorResponse)
        assert response.error_code == "TEST_ERROR"
        assert response.message == "Test error message"
        assert response.request_id == "req123"
        assert response.details == []
    
    def test_create_validation_error_response(self):
        """Test create_validation_error_response utility function."""
        field_errors = {
            "user_request": ["This field is required"],
            "priority": ["Invalid priority level"]
        }
        response = create_validation_error_response(
            field_errors=field_errors,
            message="Custom validation message",
            request_id="req123"
        )
        assert isinstance(response, ValidationErrorResponse)
        assert response.message == "Custom validation message"
        assert response.field_errors == field_errors
        assert len(response.details) == 2
        assert response.request_id == "req123"
    
    def test_schema_registry_functions(self):
        """Test schema registry utility functions."""
        # Test get_schema
        workflow_schema = get_schema("workflow")
        assert workflow_schema == Workflow
        
        # Test non-existent schema
        non_existent = get_schema("non_existent")
        assert non_existent is None
        
        # Test list_schemas
        schema_names = list_schemas()
        assert isinstance(schema_names, list)
        assert "workflow" in schema_names
        assert "workflow_step" in schema_names
        assert len(schema_names) > 0
    
    def test_schema_registry_completeness(self):
        """Test that SCHEMA_REGISTRY contains expected schemas."""
        expected_schemas = [
            "workflow", "workflow_step", "message", "task_result", "agent_info",
            "create_workflow_request", "workflow_response", "error_response",
            "research_input", "cad_input", "slicer_input", "printer_input"
        ]
        
        registry_schemas = list_schemas()
        for expected in expected_schemas:
            assert expected in registry_schemas, f"Schema '{expected}' missing from registry"


class TestValidationConstraints:
    """Test validation constraints and edge cases."""
    
    def test_progress_percentage_constraints(self):
        """Test progress percentage validation."""
        # Valid progress
        workflow = Workflow(user_request="Test", progress_percentage=50.0)
        assert workflow.progress_percentage == 50.0
        
        # Edge cases
        workflow = Workflow(user_request="Test", progress_percentage=0.0)
        assert workflow.progress_percentage == 0.0
        
        workflow = Workflow(user_request="Test", progress_percentage=100.0)
        assert workflow.progress_percentage == 100.0
        
        # Invalid progress (should be handled by Pydantic validation)
        with pytest.raises(Exception):  # Pydantic ValidationError
            Workflow(user_request="Test", progress_percentage=-1.0)
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            Workflow(user_request="Test", progress_percentage=101.0)
    
    def test_string_length_constraints(self):
        """Test string length validation."""
        # Valid lengths
        request = CreateWorkflowRequest(user_request="Valid request")
        assert request.user_request == "Valid request"
        
        # Maximum length
        max_request = "x" * 1000
        request = CreateWorkflowRequest(user_request=max_request)
        assert len(request.user_request) == 1000
        
        # Too long should fail
        with pytest.raises(Exception):  # Pydantic ValidationError
            CreateWorkflowRequest(user_request="x" * 1001)
    
    def test_positive_number_constraints(self):
        """Test positive number validation."""
        # Valid positive numbers
        slicer_input = SlicerAgentInput(
            model_file_path="/test.stl",
            printer_profile="test",
            material_type="PLA",
            layer_height=0.2,
            print_speed=50
        )
        assert slicer_input.layer_height == 0.2
        assert slicer_input.print_speed == 50
        
        # Invalid negative/zero values should fail
        with pytest.raises(Exception):  # Pydantic ValidationError
            SlicerAgentInput(
                model_file_path="/test.stl",
                printer_profile="test",
                material_type="PLA",
                layer_height=0.0  # Should be > 0
            )
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            SlicerAgentInput(
                model_file_path="/test.stl",
                printer_profile="test",
                material_type="PLA",
                print_speed=0  # Should be >= 10
            )


if __name__ == "__main__":
    pytest.main([__file__])
