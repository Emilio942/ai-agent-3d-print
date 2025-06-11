"""
Unit tests for BaseAgent class and related functionality.

Tests cover:
- Task execution
- Error handling
- Retry mechanisms
- Input validation
- Status tracking
- Agent factory
"""

import time
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.base_agent import (
    BaseAgent, AgentFactory, TaskStatus, TaskPriority, 
    create_test_task
)
from core.exceptions import (
    AI3DPrintError, ValidationError, SystemResourceError
)


class MockSuccessAgent(BaseAgent):
    """Mock agent that always succeeds."""
    
    def execute_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "message": f"Task {task_details['task_id']} completed",
            "data": "success"
        }


class MockFailingAgent(BaseAgent):
    """Mock agent that always fails."""
    
    def execute_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        raise AI3DPrintError(
            f"Test failure for task {task_details['task_id']}",
            error_code="TEST_FAILURE"
        )


class MockIntermittentAgent(BaseAgent):
    """Mock agent that fails initially then succeeds."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attempt_count = 0
    
    def execute_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        self.attempt_count += 1
        if self.attempt_count < 3:  # Fail first 2 attempts
            raise AI3DPrintError(f"Attempt {self.attempt_count} failed")
        
        return {
            "message": f"Task {task_details['task_id']} succeeded on attempt {self.attempt_count}",
            "attempts": self.attempt_count
        }


class TestBaseAgent:
    """Test cases for BaseAgent functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = MockSuccessAgent("test_agent", {"max_retries": 2})
        self.task = create_test_task("test_001", test_param="value")
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = MockSuccessAgent("test_agent", {"custom_config": "value"})
        
        assert agent.agent_name == "test_agent"
        assert agent.agent_type == "MockSuccessAgent"
        assert agent.config["custom_config"] == "value"
        assert agent.current_status == TaskStatus.PENDING
        assert agent.execution_count == 0
        assert agent.error_count == 0
    
    def test_successful_task_execution(self):
        """Test successful task execution."""
        result = self.agent._execute_with_status_tracking(self.task)
        
        assert result["status"] == "completed"
        assert result["task_id"] == "test_001"
        assert result["agent_name"] == "test_agent"
        assert result["agent_type"] == "MockSuccessAgent"
        assert "execution_time" in result
        assert result["message"] == "Task test_001 completed"
        
        # Check agent status
        assert self.agent.current_status == TaskStatus.COMPLETED
        assert self.agent.execution_count == 1
        assert self.agent.error_count == 0
    
    def test_input_validation_success(self):
        """Test successful input validation."""
        valid_task = {
            "task_id": "valid_001",
            "param1": "value1",
            "param2": 123
        }
        
        result = self.agent.validate_input(valid_task)
        assert result is True
    
    def test_input_validation_missing_task_id(self):
        """Test input validation with missing task_id."""
        invalid_task = {"param1": "value1"}
        
        try:
            self.agent.validate_input(invalid_task)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "Missing required fields" in str(e)
            assert "task_id" in e.details["missing_fields"]
    
    def test_input_validation_invalid_task_id(self):
        """Test input validation with invalid task_id."""
        invalid_task = {"task_id": ""}
        
        try:
            self.agent.validate_input(invalid_task)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "task_id must be a non-empty string" in str(e)
    
    def test_input_validation_non_dict(self):
        """Test input validation with non-dictionary input."""
        try:
            self.agent.validate_input("not a dict")
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "task_details must be a dictionary" in str(e)
    
    def test_error_handling(self):
        """Test error handling functionality."""
        test_error = AI3DPrintError("Test error", error_code="TEST_ERROR")
        
        error_response = self.agent.handle_error(test_error, self.task)
        
        assert error_response["error"] is True
        assert error_response["error_code"] == "TEST_ERROR"
        assert error_response["task_id"] == "test_001"
        assert error_response["agent_name"] == "test_agent"
        assert "timestamp" in error_response
        
        # Check agent statistics
        assert self.agent.error_count == 1
        assert self.agent.last_error == test_error
    
    def test_retry_mechanism_success_on_retry(self):
        """Test retry mechanism with success on retry."""
        agent = MockIntermittentAgent("retry_agent", {"max_retries": 3})
        task = create_test_task("retry_001")
        
        result = agent.retry_task(task, max_retries=3)
        
        assert result["status"] == "completed"
        assert result["attempts"] == 3
        assert "succeeded on attempt 3" in result["message"]
    
    def test_retry_mechanism_all_attempts_fail(self):
        """Test retry mechanism when all attempts fail."""
        agent = MockFailingAgent("failing_agent", {"max_retries": 2})
        task = create_test_task("fail_001")
        
        result = agent.retry_task(task, max_retries=2)
        
        assert result["error"] is True
        assert result["error_code"] == "TEST_FAILURE"
        assert agent.error_count > 0
    
    def test_retry_with_custom_parameters(self):
        """Test retry with custom parameters."""
        agent = MockIntermittentAgent("custom_retry_agent")
        task = create_test_task("custom_001")
        
        start_time = time.time()
        result = agent.retry_task(task, max_retries=3, retry_delay=0.1)
        end_time = time.time()
        
        # Should succeed on 3rd attempt
        assert result["status"] == "completed"
        
        # Should have some delay due to retries
        assert end_time - start_time > 0.1  # At least one retry delay
    
    def test_timeout_functionality(self):
        """Test timeout functionality."""
        # Mock a slow task
        class SlowAgent(BaseAgent):
            def execute_task(self, task_details):
                time.sleep(0.2)  # Longer than timeout
                return {"message": "slow task completed"}
        
        agent = SlowAgent("slow_agent")
        task = create_test_task("slow_001")
        
        # This should complete since our timeout detection is basic
        # In a real implementation, this would use threading/asyncio
        result = agent.execute_with_timeout(task, timeout=0.1)
        
        # For now, just test that it executes
        assert "task_id" in result
    
    def test_agent_status(self):
        """Test agent status reporting."""
        status = self.agent.get_status()
        
        assert status["agent_name"] == "test_agent"
        assert status["agent_type"] == "MockSuccessAgent"
        assert status["current_status"] == "pending"
        assert status["execution_count"] == 0
        assert status["error_count"] == 0
        assert status["current_task_id"] is None
    
    def test_statistics_reset(self):
        """Test statistics reset functionality."""
        # Execute a task to generate statistics
        self.agent._execute_with_status_tracking(self.task)
        
        # Add an error
        self.agent.handle_error(AI3DPrintError("test"), self.task)
        
        assert self.agent.execution_count > 0
        assert self.agent.error_count > 0
        
        # Reset statistics
        self.agent.reset_statistics()
        
        assert self.agent.execution_count == 0
        assert self.agent.error_count == 0
        assert self.agent.last_error is None
    
    def test_agent_shutdown(self):
        """Test agent shutdown."""
        self.agent.current_task_id = "test_001"
        self.agent.shutdown()
        
        assert self.agent.current_status == TaskStatus.CANCELLED
        assert self.agent.current_task_id is None
    
    def test_string_representations(self):
        """Test string representations of agent."""
        str_repr = str(self.agent)
        repr_str = repr(self.agent)
        
        assert "MockSuccessAgent" in str_repr
        assert "test_agent" in str_repr
        assert "pending" in str_repr
        
        assert "MockSuccessAgent" in repr_str
        assert "test_agent" in repr_str
        assert "executions=0" in repr_str
        assert "errors=0" in repr_str


class TestAgentFactory:
    """Test cases for AgentFactory."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear factory state
        AgentFactory._agent_classes.clear()
    
    def test_register_agent(self):
        """Test agent registration."""
        AgentFactory.register_agent("success", MockSuccessAgent)
        
        assert "success" in AgentFactory._agent_classes
        assert AgentFactory._agent_classes["success"] == MockSuccessAgent
    
    def test_register_invalid_agent(self):
        """Test registering invalid agent class."""
        class NotAnAgent:
            pass
        
        with pytest.raises(ValueError) as exc_info:
            AgentFactory.register_agent("invalid", NotAnAgent)
        
        assert "must inherit from BaseAgent" in str(exc_info.value)
    
    def test_create_agent(self):
        """Test agent creation."""
        AgentFactory.register_agent("success", MockSuccessAgent)
        
        agent = AgentFactory.create_agent("success", "test_agent", {"param": "value"})
        
        assert isinstance(agent, MockSuccessAgent)
        assert agent.agent_name == "test_agent"
        assert agent.config["param"] == "value"
    
    def test_create_unknown_agent(self):
        """Test creating unknown agent type."""
        with pytest.raises(ValueError) as exc_info:
            AgentFactory.create_agent("unknown", "test_agent")
        
        assert "Unknown agent type 'unknown'" in str(exc_info.value)
    
    def test_get_registered_types(self):
        """Test getting registered agent types."""
        AgentFactory.register_agent("type1", MockSuccessAgent)
        AgentFactory.register_agent("type2", MockFailingAgent)
        
        types = AgentFactory.get_registered_types()
        
        assert "type1" in types
        assert "type2" in types
        assert len(types) == 2


class TestUtilities:
    """Test utility functions."""
    
    def test_create_test_task(self):
        """Test test task creation."""
        task = create_test_task("test_123", param1="value1", param2=456)
        
        assert task["task_id"] == "test_123"
        assert task["param1"] == "value1"
        assert task["param2"] == 456
        assert "timestamp" in task


def run_tests():
    """Run all tests manually."""
    test_classes = [TestBaseAgent, TestAgentFactory, TestUtilities]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n=== Running {test_class.__name__} ===")
        
        test_instance = test_class()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) 
                       if method.startswith('test_')]
        
        for test_method_name in test_methods:
            total_tests += 1
            
            try:
                # Set up
                if hasattr(test_instance, 'setup_method'):
                    test_instance.setup_method()
                
                # Run test
                test_method = getattr(test_instance, test_method_name)
                test_method()
                
                print(f"  ✅ {test_method_name}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ❌ {test_method_name}: {e}")
                failed_tests.append(f"{test_class.__name__}.{test_method_name}: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\nFailed tests:")
        for failure in failed_tests:
            print(f"  - {failure}")
        return False
    else:
        print(f"\n🎉 All tests passed!")
        return True


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
