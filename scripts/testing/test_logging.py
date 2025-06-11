#!/usr/bin/env python3
"""
Test script for the AI Agent 3D Print logging and exception system.

This script tests the logging infrastructure and exception handling
to ensure everything works correctly before proceeding with agent development.
"""

import sys
import traceback
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from core.logger import (
        get_logger, 
        get_research_logger, 
        get_cad_logger, 
        get_slicer_logger,
        get_printer_logger,
        get_parent_logger,
        get_api_logger,
        LoggerManager
    )
    from core.exceptions import (
        AI3DPrintError,
        IntentRecognitionError,
        CADAgentError,
        SlicerExecutionError,
        PrinterConnectionError,
        WorkflowError,
        create_error_response,
        get_error_handler
    )
    print("✅ Successfully imported logging and exception modules")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    sys.exit(1)


def test_basic_logging():
    """Test basic logging functionality."""
    print("\n=== Testing Basic Logging ===")
    
    # Test different logger types
    research_logger = get_research_logger()
    cad_logger = get_cad_logger()
    api_logger = get_api_logger()
    
    # Test different log levels
    research_logger.debug("Debug message from research agent", operation="intent_analysis")
    research_logger.info("Processing user input", user_input="Create a 2cm cube", timestamp="2025-06-10T14:30:22Z")
    research_logger.warning("Low confidence in recognition", confidence=0.45, fallback="regex_patterns")
    
    cad_logger.info("Starting CAD generation", shape="cube", dimensions={"x": 20, "y": 20, "z": 20})
    cad_logger.error("Boolean operation failed", operation="union", error_type="geometry_invalid")
    
    api_logger.info("API request received", endpoint="/api/print-request", method="POST")
    api_logger.critical("System overload detected", cpu_usage=98, memory_usage=95)
    
    print("✅ Basic logging test completed")


def test_exception_handling():
    """Test exception handling and error responses."""
    print("\n=== Testing Exception Handling ===")
    
    # Test different exception types
    try:
        raise IntentRecognitionError(
            "Failed to parse user intent",
            confidence=0.25,
            user_input="make something cool",
            error_code="INTENT_LOW_CONFIDENCE"
        )
    except AI3DPrintError as e:
        print(f"✅ Caught IntentRecognitionError: {e}")
        response = create_error_response(e, include_details=True)
        print(f"   Error response: {response}")
    
    try:
        raise CADAgentError(
            "Geometry validation failed",
            error_code="GEOMETRY_INVALID",
            details={"operation": "boolean_union", "mesh_errors": ["non_manifold", "self_intersecting"]}
        )
    except AI3DPrintError as e:
        print(f"✅ Caught CADAgentError: {e}")
    
    try:
        raise PrinterConnectionError(
            "Failed to connect to printer",
            port="/dev/ttyUSB0",
            baudrate=115200,
            error_code="CONNECTION_TIMEOUT"
        )
    except AI3DPrintError as e:
        print(f"✅ Caught PrinterConnectionError: {e}")
    
    print("✅ Exception handling test completed")


def test_error_handler_context():
    """Test the error handler context manager."""
    print("\n=== Testing Error Handler Context ===")
    
    error_handler = get_error_handler("test_agent")
    
    # Test with custom exception
    try:
        with error_handler():
            raise SlicerExecutionError("Slicer failed to process STL", 
                                     slicer_command="prusaslicer --export-gcode test.stl",
                                     exit_code=1)
    except AI3DPrintError as e:
        print(f"✅ Context manager handled SlicerExecutionError: {e.error_code}")
    
    # Test with standard Python exception
    try:
        with error_handler():
            raise ValueError("Standard Python exception")
    except AI3DPrintError as e:
        print(f"✅ Context manager converted ValueError to AI3DPrintError: {e.error_code}")
    
    print("✅ Error handler context test completed")


def test_structured_logging():
    """Test structured logging with complex data."""
    print("\n=== Testing Structured Logging ===")
    
    logger = get_logger("test_structured")
    
    # Complex data structures
    workflow_data = {
        "workflow_id": "wf_12345",
        "steps": ["research", "cad", "slice", "print"],
        "current_step": "cad",
        "progress": 0.5,
        "estimated_completion": "2025-06-10T15:45:00Z"
    }
    
    logger.info("Workflow progress update", **workflow_data)
    
    # Performance metrics
    performance_data = {
        "operation": "stl_export",
        "execution_time_ms": 1250,
        "memory_usage_mb": 128,
        "cpu_usage_percent": 45,
        "success": True
    }
    
    logger.debug("Performance metrics recorded", **performance_data)
    
    # Error with context
    error_context = {
        "user_id": "user_789",
        "session_id": "sess_abc123",
        "request_id": "req_xyz789",
        "timestamp": "2025-06-10T14:30:22.123Z",
        "stack_trace": "Traceback (most recent call last)..."
    }
    
    logger.error("Request processing failed", **error_context)
    
    print("✅ Structured logging test completed")


def test_logger_manager():
    """Test the logger manager functionality."""
    print("\n=== Testing Logger Manager ===")
    
    # Test getting multiple loggers
    logger1 = LoggerManager.get_logger("agent_1")
    logger2 = LoggerManager.get_logger("agent_2")
    logger1_again = LoggerManager.get_logger("agent_1")
    
    # Verify singleton behavior
    assert logger1 is logger1_again, "Logger manager should return same instance"
    print("✅ Logger singleton behavior verified")
    
    # Test agent names tracking
    agent_names = LoggerManager.get_agent_names()
    print(f"✅ Registered agents: {agent_names}")
    
    # Test configuration
    custom_config = {
        "level": "DEBUG",
        "format": "json",
        "console_enabled": True,
        "file_enabled": False  # Disable file logging for test
    }
    
    LoggerManager.configure(custom_config)
    print("✅ Logger configuration updated")
    
    print("✅ Logger manager test completed")


def main():
    """Run all tests."""
    print("🚀 Starting AI Agent 3D Print Logging System Tests")
    
    try:
        test_basic_logging()
        test_exception_handling()
        test_error_handler_context()
        test_structured_logging()
        test_logger_manager()
        
        print("\n🎉 All tests completed successfully!")
        print("\nLog files should be created in the logs/ directory:")
        
        # Check if log directory exists
        logs_dir = Path("logs")
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            for log_file in log_files:
                print(f"  📄 {log_file}")
        else:
            print("  ⚠️  logs/ directory not found - logs may be disabled in configuration")
            
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
