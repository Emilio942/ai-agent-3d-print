"""
Custom Exception Classes for AI Agent 3D Print System

This module defines custom exception classes for different types of errors
that can occur in the system, organized by agent type and functionality.
"""

from typing import Any, Dict, Optional


class AI3DPrintError(Exception):
    """Base exception class for all AI 3D Print System errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize base exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }
    
    def __str__(self) -> str:
        """String representation of the exception."""
        if self.details:
            details_str = ", ".join([f"{k}={v}" for k, v in self.details.items()])
            return f"{self.message} [{self.error_code}] Details: {details_str}"
        return f"{self.message} [{self.error_code}]"


# =============================================================================
# Configuration and System Errors
# =============================================================================

class ConfigurationError(AI3DPrintError):
    """Raised when there's an error in system configuration."""
    pass


class ValidationError(AI3DPrintError):
    """Raised when input validation fails."""
    pass


class SystemResourceError(AI3DPrintError):
    """Raised when system resources are unavailable or exhausted."""
    pass


# =============================================================================
# Research Agent Errors
# =============================================================================

class ResearchAgentError(AI3DPrintError):
    """Base exception for Research Agent errors."""
    pass


class IntentRecognitionError(ResearchAgentError):
    """Raised when intent recognition fails or has low confidence."""
    
    def __init__(self, message: str, confidence: float = 0.0, user_input: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "confidence": confidence,
            "user_input": user_input
        })


class WebResearchError(ResearchAgentError):
    """Raised when web research operations fail."""
    
    def __init__(self, message: str, search_terms: Optional[list] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "search_terms": search_terms or []
        })


class ContentSummarizationError(ResearchAgentError):
    """Raised when content summarization fails."""
    pass


class NLPModelError(ResearchAgentError):
    """Raised when NLP model operations fail."""
    
    def __init__(self, message: str, model_name: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "model_name": model_name
        })


class DesignSpecificationError(ResearchAgentError):
    """Raised when design specification generation fails."""
    
    def __init__(self, message: str, intent_data: Optional[Dict] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "intent_data": intent_data or {}
        })


# =============================================================================
# CAD Agent Errors
# =============================================================================

class CADAgentError(AI3DPrintError):
    """Base exception for CAD Agent errors."""
    pass


class GeometryError(CADAgentError):
    """Raised when geometry operations fail."""
    
    def __init__(self, message: str, operation: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "operation": operation
        })


class PrimitiveCreationError(CADAgentError):
    """Raised when creating geometric primitives fails."""
    
    def __init__(self, message: str, shape_type: str = "", dimensions: Optional[Dict] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "shape_type": shape_type,
            "dimensions": dimensions or {}
        })


class BooleanOperationError(CADAgentError):
    """Raised when boolean operations fail."""
    
    def __init__(self, message: str, operation: str = "", objects: Optional[list] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "boolean_operation": operation,
            "object_count": len(objects) if objects else 0
        })


class MeshValidationError(CADAgentError):
    """Raised when mesh validation fails."""
    
    def __init__(self, message: str, validation_type: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "validation_type": validation_type
        })


class STLExportError(CADAgentError):
    """Raised when STL export operations fail."""
    
    def __init__(self, message: str, file_path: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "file_path": file_path
        })


class PrintabilityError(CADAgentError):
    """Raised when object fails printability checks."""
    
    def __init__(self, message: str, check_type: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "check_type": check_type
        })


class FreeCADError(CADAgentError):
    """Raised when FreeCAD operations fail."""
    
    def __init__(self, message: str, freecad_error: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "freecad_error": freecad_error
        })


# =============================================================================
# Slicer Agent Errors
# =============================================================================

class SlicerAgentError(AI3DPrintError):
    """Base exception for Slicer Agent errors."""
    pass


class SlicerConfigurationError(SlicerAgentError):
    """Raised when slicer configuration is invalid."""
    
    def __init__(self, message: str, profile_name: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "profile_name": profile_name
        })


class SlicerExecutionError(SlicerAgentError):
    """Raised when slicer execution fails."""
    
    def __init__(self, message: str, slicer_command: str = "", exit_code: int = 0, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "slicer_command": slicer_command,
            "exit_code": exit_code
        })


class GCodeGenerationError(SlicerAgentError):
    """Raised when G-code generation fails."""
    
    def __init__(self, message: str, stl_file: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "stl_file": stl_file
        })


class SlicerProfileError(SlicerAgentError):
    """Raised when there are issues with slicer profiles."""
    
    def __init__(self, message: str, profile_name: str = "", available_profiles: Optional[list] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "profile_name": profile_name,
            "available_profiles": available_profiles or []
        })


# =============================================================================
# Printer Agent Errors
# =============================================================================

class PrinterAgentError(AI3DPrintError):
    """Base exception for Printer Agent errors."""
    pass


class PrinterConnectionError(PrinterAgentError):
    """Raised when printer connection fails."""
    
    def __init__(self, message: str, port: str = "", baudrate: int = 0, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "port": port,
            "baudrate": baudrate
        })


class PrinterNotConnectedError(PrinterAgentError):
    """Raised when attempting operations on a disconnected printer."""
    
    def __init__(self, message: str, operation: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "operation": operation
        })


class SerialCommunicationError(PrinterAgentError):
    """Raised when serial communication fails."""
    
    def __init__(self, message: str, command: str = "", response: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "command": command,
            "response": response
        })


class GCodeStreamingError(PrinterAgentError):
    """Raised when G-code streaming fails."""
    
    def __init__(self, message: str, line_number: int = 0, gcode_line: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "line_number": line_number,
            "gcode_line": gcode_line
        })


class PrinterTimeoutError(PrinterAgentError):
    """Raised when printer operations timeout."""
    
    def __init__(self, message: str, timeout_seconds: float = 0.0, operation: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "timeout_seconds": timeout_seconds,
            "operation": operation
        })


class PrinterSafetyError(PrinterAgentError):
    """Raised when printer safety checks fail."""
    
    def __init__(self, message: str, safety_check: str = "", current_value: Any = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "safety_check": safety_check,
            "current_value": current_value
        })


class EmergencyStopError(PrinterAgentError):
    """Raised when emergency stop is triggered."""
    
    def __init__(self, message: str, trigger_reason: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "trigger_reason": trigger_reason
        })


# =============================================================================
# Parent Agent and Orchestration Errors
# =============================================================================

class ParentAgentError(AI3DPrintError):
    """Base exception for Parent Agent errors."""
    pass


class WorkflowError(ParentAgentError):
    """Raised when workflow execution fails."""
    
    def __init__(self, message: str, workflow_step: str = "", agent_name: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "workflow_step": workflow_step,
            "agent_name": agent_name
        })


class AgentCommunicationError(ParentAgentError):
    """Raised when agent communication fails."""
    
    def __init__(self, message: str, source_agent: str = "", target_agent: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "source_agent": source_agent,
            "target_agent": target_agent
        })


class AgentTimeoutError(ParentAgentError):
    """Raised when agent operations timeout."""
    
    def __init__(self, message: str, timeout_duration: float = 0.0, agent_name: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "timeout_duration": timeout_duration,
            "agent_name": agent_name
        })


class RollbackError(ParentAgentError):
    """Raised when workflow rollback fails."""
    
    def __init__(self, message: str, rollback_step: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "rollback_step": rollback_step
        })


class JobQueueError(ParentAgentError):
    """Raised when job queue operations fail."""
    
    def __init__(self, message: str, job_id: str = "", queue_operation: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "job_id": job_id,
            "queue_operation": queue_operation
        })


# =============================================================================
# API and Communication Errors
# =============================================================================

class APIError(AI3DPrintError):
    """Base exception for API errors."""
    pass


class AuthenticationError(APIError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(APIError):
    """Raised when authorization fails."""
    pass


class RateLimitError(APIError):
    """Raised when rate limiting is triggered."""
    
    def __init__(self, message: str, limit: int = 0, window_seconds: int = 0, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "rate_limit": limit,
            "window_seconds": window_seconds
        })


class WebSocketError(APIError):
    """Raised when WebSocket operations fail."""
    
    def __init__(self, message: str, connection_id: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "connection_id": connection_id
        })


# =============================================================================
# File and Storage Errors
# =============================================================================

class FileOperationError(AI3DPrintError):
    """Base exception for file operation errors."""
    pass


class FileValidationError(FileOperationError):
    """Raised when file validation fails."""
    
    def __init__(self, message: str, file_path: str = "", file_type: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "file_path": file_path,
            "file_type": file_type
        })


class StorageError(FileOperationError):
    """Raised when storage operations fail."""
    
    def __init__(self, message: str, storage_path: str = "", operation: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "storage_path": storage_path,
            "operation": operation
        })


class FileSizeError(FileOperationError):
    """Raised when files exceed size limits."""
    
    def __init__(self, message: str, file_size: int = 0, max_size: int = 0, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "file_size": file_size,
            "max_size": max_size
        })


# =============================================================================
# Message Queue Errors
# =============================================================================

class MessageQueueError(AI3DPrintError):
    """Base exception for Message Queue errors."""
    pass


class MessageNotFoundError(MessageQueueError):
    """Raised when a message is not found in the queue."""
    
    def __init__(self, message: str, message_id: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "message_id": message_id
        })


class QueueFullError(MessageQueueError):
    """Raised when attempting to add to a full queue."""
    
    def __init__(self, message: str, max_size: int = 0, current_size: int = 0, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "max_size": max_size,
            "current_size": current_size
        })


class MessageExpiredError(MessageQueueError):
    """Raised when a message has expired."""
    
    def __init__(self, message: str, message_id: str = "", expires_at: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "message_id": message_id,
            "expires_at": expires_at
        })


class InvalidMessageError(MessageQueueError):
    """Raised when a message format is invalid."""
    
    def __init__(self, message: str, message_id: str = "", validation_error: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "message_id": message_id,
            "validation_error": validation_error
        })


# =============================================================================
# Security and Performance Errors
# =============================================================================

class SecurityViolationError(AI3DPrintError):
    """Raised when security violations are detected."""
    
    def __init__(self, message: str, violation_type: str = "", threat_level: str = "MEDIUM", **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "violation_type": violation_type,
            "threat_level": threat_level
        })


class RateLimitExceededError(APIError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, limit_type: str = "", retry_after: int = 60, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "limit_type": limit_type,
            "retry_after": retry_after
        })


class PerformanceError(AI3DPrintError):
    """Raised when performance thresholds are exceeded."""
    
    def __init__(self, message: str, metric_type: str = "", current_value: float = 0.0, threshold: float = 0.0, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "metric_type": metric_type,
            "current_value": current_value,
            "threshold": threshold
        })


class ResourceExhaustedException(SystemResourceError):
    """Raised when system resources are exhausted."""
    
    def __init__(self, message: str, resource_type: str = "", current_usage: float = 0.0, **kwargs):
        super().__init__(message, **kwargs)
        self.details.update({
            "resource_type": resource_type,
            "current_usage": current_usage
        })


# =============================================================================
# Utility Functions
# =============================================================================

def get_error_handler(agent_name: str):
    """
    Get a context manager for handling errors in agent operations.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Context manager for error handling
    """
    from contextlib import contextmanager
    # Note: AgentLogger import would be needed for actual usage
    
    @contextmanager
    def error_handler():
        try:
            yield
        except AI3DPrintError as e:
            # logger = get_logger(agent_name)
            # logger.error(f"Agent error: {e.message}", 
            #             error_code=e.error_code,
            #             error_details=e.details)
            raise
        except Exception as e:
            # logger = get_logger(agent_name)
            # logger.error(f"Unexpected error: {str(e)}", error_type=type(e).__name__)
            # Convert to our custom exception type
            raise AI3DPrintError(f"Unexpected error in {agent_name}: {str(e)}") from e
    
    return error_handler


def create_error_response(error: Exception, include_details: bool = False) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.
    
    Args:
        error: The exception that occurred
        include_details: Whether to include detailed error information
        
    Returns:
        Standardized error response dictionary
    """
    if isinstance(error, AI3DPrintError):
        response = {
            "error": True,
            "error_type": error.__class__.__name__,
            "error_code": error.error_code,
            "message": error.message
        }
        
        if include_details:
            response["details"] = error.details
    else:
        response = {
            "error": True,
            "error_type": type(error).__name__,
            "error_code": "UNKNOWN_ERROR",
            "message": str(error)
        }
    
    return response


# Error code mappings for quick reference
ERROR_CODES = {
    # Research Agent
    "INTENT_LOW_CONFIDENCE": IntentRecognitionError,
    "WEB_RESEARCH_FAILED": WebResearchError,
    "NLP_MODEL_ERROR": NLPModelError,
    
    # CAD Agent
    "GEOMETRY_INVALID": GeometryError,
    "BOOLEAN_OP_FAILED": BooleanOperationError,
    "STL_EXPORT_FAILED": STLExportError,
    "NOT_PRINTABLE": PrintabilityError,
    
    # Slicer Agent
    "SLICER_EXECUTION_FAILED": SlicerExecutionError,
    "GCODE_GENERATION_FAILED": GCodeGenerationError,
    "PROFILE_NOT_FOUND": SlicerProfileError,
    
    # Printer Agent
    "PRINTER_CONNECTION_FAILED": PrinterConnectionError,
    "GCODE_STREAMING_FAILED": GCodeStreamingError,
    "PRINTER_TIMEOUT": PrinterTimeoutError,
    "SAFETY_CHECK_FAILED": PrinterSafetyError,
    
    # System
    "CONFIGURATION_ERROR": ConfigurationError,
    "VALIDATION_ERROR": ValidationError,
    "WORKFLOW_ERROR": WorkflowError,
}


if __name__ == "__main__":
    # Example usage and testing
    print("Testing AI Agent 3D Print Exception System")
    
    # Test different exception types
    try:
        raise IntentRecognitionError(
            "Failed to recognize user intent",
            confidence=0.25,
            user_input="make something cool"
        )
    except AI3DPrintError as e:
        print(f"Caught exception: {e}")
        print(f"Exception dict: {e.to_dict()}")
    
    try:
        raise CADAgentError("CAD operation failed", 
                           error_code="GEOMETRY_INVALID",
                           details={"operation": "boolean_union", "objects": 2})
    except AI3DPrintError as e:
        print(f"Caught exception: {e}")
        
        # Test error response creation
        response = create_error_response(e, include_details=True)
        print(f"Error response: {response}")
    
    print("Exception testing completed.")
