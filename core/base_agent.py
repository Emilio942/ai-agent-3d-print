"""
BaseAgent - Abstract Base Class for AI Agent 3D Print System

This module provides the foundation for all agents in the system with standardized
interfaces, error handling, retry mechanisms, and logging integration.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Type
import time
import asyncio
from enum import Enum

try:  # Package-relative imports when available
    from .logger import AgentLogger, get_logger
    from .exceptions import (
        AI3DPrintError, 
        ValidationError, 
        SystemResourceError,
        get_error_handler,
        create_error_response
    )
except ImportError:  # pragma: no cover - legacy fallback for direct module execution
    try:
        from core.logger import AgentLogger, get_logger  # type: ignore
        from core.exceptions import (  # type: ignore
            AI3DPrintError,
            ValidationError,
            SystemResourceError,
            get_error_handler,
            create_error_response
        )
    except ImportError:  # Final fallback when executed from within core package directly
        from logger import AgentLogger, get_logger  # type: ignore
        from exceptions import (  # type: ignore
            AI3DPrintError,
            ValidationError,
            SystemResourceError,
            get_error_handler,
            create_error_response
        )


class TaskStatus(Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the AI 3D Print System.
    
    Provides standardized interfaces for:
    - Task execution with error handling
    - Input validation 
    - Retry mechanisms
    - Logging integration
    - Status tracking
    """
    
    def __init__(self, 
                 agent_name: str,
                 config: Optional[Dict[str, Any]] = None,
                 logger: Optional[AgentLogger] = None):
        """
        Initialize the base agent.
        
        Args:
            agent_name: Unique name for this agent instance
            config: Agent-specific configuration
            logger: Optional custom logger instance
        """
        self.agent_name = agent_name
        self.agent_type = self.__class__.__name__
        self.config = config or {}
        self.logger = logger or get_logger(agent_name)

        # Backward compatibility: expose agent_id attribute used across tests
        self.agent_id = agent_name
        
        # Task execution tracking
        self.current_task_id: Optional[str] = None
        self.current_status = TaskStatus.PENDING
        self.execution_count = 0
        self.error_count = 0
        self.last_error: Optional[Exception] = None
        
        # Configuration from settings
        self.default_timeout = self.config.get('base_timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 2)
        
        self.logger.info(f"{self.agent_type} initialized", 
                        agent_name=agent_name,
                        config_keys=list(self.config.keys()))
    
    @abstractmethod
    def execute_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task with the given details.
        
        This is the main method that each agent must implement with their
        specific business logic.
        
        Args:
            task_details: Dictionary containing task parameters and data
            
        Returns:
            Dictionary containing task results and metadata
            
        Raises:
            AI3DPrintError: For agent-specific errors
            ValidationError: For input validation failures
        """
        pass
    
    def validate_input(self, task_details: Dict[str, Any]) -> bool:
        """
        Validate input parameters for task execution.
        
        Base validation includes:
        - Required fields check
        - Type validation
        - Basic constraint validation
        
        Override in subclasses for agent-specific validation.
        
        Args:
            task_details: Task parameters to validate
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        # Base validation
        if not isinstance(task_details, dict):
            raise ValidationError("task_details must be a dictionary")
        
        # Check for required base fields
        required_fields = ['task_id']
        missing_fields = [field for field in required_fields 
                         if field not in task_details]
        
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {missing_fields}",
                details={"missing_fields": missing_fields}
            )
        
        # Validate task_id
        task_id = task_details.get('task_id')
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValidationError(
                "task_id must be a non-empty string",
                details={"task_id": task_id}
            )
        
        self.logger.debug("Input validation passed",
                         task_id=task_id,
                         field_count=len(task_details))
        
        return True
    
    def handle_error(self, error: Exception, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle errors that occur during task execution.
        
        Provides standardized error handling including:
        - Error logging
        - Error response generation
        - Error statistics tracking
        
        Args:
            error: The exception that occurred
            task_details: Original task details for context
            
        Returns:
            Standardized error response dictionary
        """
        self.error_count += 1
        self.last_error = error
        
        task_id = task_details.get('task_id', 'unknown')
        
        # Log the error with context
        if isinstance(error, AI3DPrintError):
            self.logger.error(f"Agent error in task {task_id}: {error.message}",
                            error_code=error.error_code,
                            error_details=error.details,
                            task_id=task_id,
                            error_count=self.error_count)
        else:
            self.logger.error(f"Unexpected error in task {task_id}: {str(error)}",
                            error_type=type(error).__name__,
                            task_id=task_id,
                            error_count=self.error_count)
        
        # Create standardized error response
        error_response = create_error_response(error, include_details=True)
        error_response.update({
            "task_id": task_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "timestamp": time.time(),
            "error_count": self.error_count
        })
        
        return error_response
    
    def retry_task(self, 
                   task_details: Dict[str, Any], 
                   max_retries: Optional[int] = None,
                   retry_delay: Optional[float] = None) -> Dict[str, Any]:
        """
        Retry task execution with exponential backoff.
        
        Args:
            task_details: Original task details
            max_retries: Maximum number of retry attempts (overrides default)
            retry_delay: Base delay between retries in seconds
            
        Returns:
            Task execution result or error response
        """
        max_retries = max_retries or self.max_retries
        retry_delay = retry_delay or self.retry_delay
        task_id = task_details.get('task_id', 'unknown')
        
        self.logger.info(f"Starting retry sequence for task {task_id}",
                        max_retries=max_retries,
                        retry_delay=retry_delay)
        
        last_error = None
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                if attempt > 0:
                    # Exponential backoff
                    delay = retry_delay * (2 ** (attempt - 1))
                    self.logger.debug(f"Retry attempt {attempt} for task {task_id}",
                                    delay_seconds=delay,
                                    attempt=attempt)
                    time.sleep(delay)
                
                # Execute the task
                result = self._execute_with_status_tracking(task_details)
                
                if attempt > 0:
                    self.logger.info(f"Task {task_id} succeeded on retry attempt {attempt}",
                                   attempt=attempt,
                                   total_attempts=attempt + 1)
                
                return result
                
            except Exception as error:
                last_error = error
                
                if attempt < max_retries:
                    self.logger.warning(f"Task {task_id} failed on attempt {attempt + 1}, retrying",
                                      attempt=attempt + 1,
                                      error=str(error),
                                      remaining_retries=max_retries - attempt)
                else:
                    self.logger.error(f"Task {task_id} failed after {max_retries + 1} attempts",
                                    total_attempts=max_retries + 1,
                                    final_error=str(error))
        
        # All retries exhausted
        if last_error:
            return self.handle_error(last_error, task_details)
        else:
            return self.handle_error(
                AI3DPrintError(f"Task failed after {max_retries + 1} attempts"),
                task_details
            )
    
    def _execute_with_status_tracking(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task with status tracking and timing.
        
        Args:
            task_details: Task parameters
            
        Returns:
            Task execution result
        """
        task_id = task_details.get('task_id', 'unknown')
        self.current_task_id = task_id
        self.current_status = TaskStatus.RUNNING
        
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting task execution: {task_id}",
                           task_id=task_id,
                           agent_type=self.agent_type)
            
            # Validate input
            self.validate_input(task_details)
            
            # Execute the actual task
            result = self.execute_task(task_details)
            
            # Ensure result is a dictionary
            if not isinstance(result, dict):
                result = {"result": result}
            
            # Add metadata
            execution_time = time.time() - start_time
            result.update({
                "task_id": task_id,
                "agent_name": self.agent_name,
                "agent_type": self.agent_type,
                "status": TaskStatus.COMPLETED.value,
                "execution_time": execution_time,
                "timestamp": time.time()
            })
            
            self.current_status = TaskStatus.COMPLETED
            self.execution_count += 1
            
            self.logger.info(f"Task completed successfully: {task_id}",
                           task_id=task_id,
                           execution_time=execution_time,
                           execution_count=self.execution_count)
            
            return result
            
        except Exception as error:
            self.current_status = TaskStatus.FAILED
            raise error
        finally:
            self.current_task_id = None
    
    def execute_with_timeout(self, 
                           task_details: Dict[str, Any],
                           timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute task with timeout protection.
        
        Args:
            task_details: Task parameters
            timeout: Timeout in seconds (overrides default)
            
        Returns:
            Task execution result
            
        Raises:
            SystemResourceError: If task times out
        """
        timeout = timeout or self.default_timeout
        task_id = task_details.get('task_id', 'unknown')
        
        self.logger.debug(f"Executing task with timeout: {task_id}",
                         timeout_seconds=timeout)
        
        start_time = time.time()
        
        try:
            # For now, use simple timeout - can be enhanced with threading/asyncio
            result = self._execute_with_status_tracking(task_details)
            
            execution_time = time.time() - start_time
            if execution_time > timeout:
                self.logger.warning(f"Task {task_id} exceeded timeout but completed",
                                  execution_time=execution_time,
                                  timeout=timeout)
            
            return result
            
        except Exception as error:
            execution_time = time.time() - start_time
            if execution_time >= timeout:
                timeout_error = SystemResourceError(
                    f"Task {task_id} timed out after {timeout} seconds",
                    details={
                        "timeout_seconds": timeout,
                        "execution_time": execution_time,
                        "original_error": str(error) if error else None
                    }
                )
                return self.handle_error(timeout_error, task_details)
            else:
                raise error
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status and statistics.
        
        Returns:
            Dictionary containing agent status information
        """
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "current_status": self.current_status.value,
            "current_task_id": self.current_task_id,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "last_error": str(self.last_error) if self.last_error else None,
            "config": self.config
        }
    
    def reset_statistics(self) -> None:
        """Reset agent statistics counters."""
        self.execution_count = 0
        self.error_count = 0
        self.last_error = None
        
        self.logger.info("Agent statistics reset",
                        agent_name=self.agent_name)
    
    def shutdown(self) -> None:
        """
        Graceful agent shutdown.
        
        Override in subclasses to add cleanup logic.
        """
        self.current_status = TaskStatus.CANCELLED
        self.current_task_id = None
        
        self.logger.info(f"Agent {self.agent_name} shutting down",
                        execution_count=self.execution_count,
                        error_count=self.error_count)
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.agent_type}(name={self.agent_name}, status={self.current_status.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return (f"{self.agent_type}(name='{self.agent_name}', "
                f"status={self.current_status.value}, "
                f"executions={self.execution_count}, "
                f"errors={self.error_count})")


class AgentFactory:
    """
    Factory class for creating agent instances with standardized configuration.
    """
    
    _agent_classes: Dict[str, Type[BaseAgent]] = {}
    
    @classmethod
    def register_agent(cls, agent_type: str, agent_class: Type[BaseAgent]) -> None:
        """
        Register an agent class with the factory.
        
        Args:
            agent_type: String identifier for the agent type
            agent_class: Agent class (must inherit from BaseAgent)
        """
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"Agent class {agent_class} must inherit from BaseAgent")
        
        cls._agent_classes[agent_type] = agent_class
    
    @classmethod
    def create_agent(cls, 
                    agent_type: str, 
                    agent_name: str,
                    config: Optional[Dict[str, Any]] = None) -> BaseAgent:
        """
        Create an agent instance of the specified type.
        
        Args:
            agent_type: Type of agent to create
            agent_name: Unique name for the agent instance
            config: Agent-specific configuration
            
        Returns:
            Configured agent instance
            
        Raises:
            ValueError: If agent type is not registered
        """
        if agent_type not in cls._agent_classes:
            available_types = list(cls._agent_classes.keys())
            raise ValueError(
                f"Unknown agent type '{agent_type}'. "
                f"Available types: {available_types}"
            )
        
        agent_class = cls._agent_classes[agent_type]
        return agent_class(agent_name, config)
    
    @classmethod
    def get_registered_types(cls) -> list[str]:
        """Get list of registered agent types."""
        return list(cls._agent_classes.keys())


# Utility functions for agent testing and validation

def create_test_task(task_id: str, **kwargs) -> Dict[str, Any]:
    """
    Create a test task dictionary with required fields.
    
    Args:
        task_id: Unique task identifier
        **kwargs: Additional task parameters
        
    Returns:
        Task dictionary with required fields
    """
    task = {
        "task_id": task_id,
        "timestamp": time.time(),
        **kwargs
    }
    return task


if __name__ == "__main__":
    # Example implementation for testing
    class TestAgent(BaseAgent):
        """Simple test agent for demonstration."""
        
        def execute_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
            """Test task that simulates work and may fail."""
            task_id = task_details.get('task_id')
            
            # Simulate some work
            import random
            time.sleep(0.1)
            
            # Randomly fail to test error handling
            if random.random() < 0.3:  # 30% failure rate
                raise AI3DPrintError(f"Random test failure for task {task_id}")
            
            return {
                "message": f"Test task {task_id} completed successfully",
                "data": {"processed": True, "result": "success"}
            }
    
    # Test the BaseAgent implementation
    print("Testing BaseAgent implementation...")
    
    # Create test agent
    agent = TestAgent("test_agent", {"max_retries": 2})
    
    # Test successful execution
    task = create_test_task("test_001", test_param="value")
    try:
        result = agent.retry_task(task)
        print(f"✅ Task result: {result.get('message', 'No message')}")
    except Exception as e:
        print(f"❌ Task failed: {e}")
    
    # Test agent status
    status = agent.get_status()
    print(f"Agent status: {status}")
    
    # Test factory
    AgentFactory.register_agent("test", TestAgent)
    factory_agent = AgentFactory.create_agent("test", "factory_test")
    print(f"Factory created agent: {factory_agent}")
    
    print("BaseAgent testing completed!")
