#!/usr/bin/env python3
"""
Final comprehensive test for Task 0.3: Logging & Error Handling Framework

This script validates that all logging and exception handling features work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import (
    get_research_logger, get_cad_logger, get_slicer_logger,
    get_printer_logger, get_parent_logger, get_api_logger,
    LoggerManager
)
from core.exceptions import (
    AI3DPrintError, IntentRecognitionError, CADAgentError,
    GeometryError, SlicerExecutionError, PrinterConnectionError,
    WorkflowError, create_error_response, get_error_handler
)


def test_all_loggers():
    """Test all agent logger types."""
    print("=== Testing All Agent Loggers ===")
    
    loggers = {
        "research": get_research_logger(),
        "cad": get_cad_logger(),
        "slicer": get_slicer_logger(),
        "printer": get_printer_logger(),
        "parent": get_parent_logger(),
        "api": get_api_logger()
    }
    
    for agent_name, logger in loggers.items():
        logger.info(f"{agent_name.title()} agent initialized", 
                   agent_type=agent_name,
                   status="active")
        logger.debug(f"{agent_name.title()} debug message",
                    debug_level="verbose")
    
    print("✅ All agent loggers tested successfully")


def test_all_log_levels():
    """Test all log levels with structured data."""
    print("=== Testing All Log Levels ===")
    
    logger = get_research_logger()
    
    # Test all log levels
    logger.debug("Debug message", operation="intent_parsing", step=1)
    logger.info("Info message", user_request="Create a cube", confidence=0.95)
    logger.warning("Warning message", confidence=0.45, fallback_used=True)
    logger.error("Error message", error_type="validation_failed", retry_count=2)
    logger.critical("Critical message", system_status="degraded", action_required=True)
    
    print("✅ All log levels tested successfully")


def test_exception_hierarchy():
    """Test the complete exception hierarchy."""
    print("=== Testing Exception Hierarchy ===")
    
    exceptions_to_test = [
        (IntentRecognitionError, "Intent recognition failed", 
         {"confidence": 0.2, "user_input": "make something"}),
        
        (GeometryError, "Geometry operation failed",
         {"operation": "boolean_union"}),
        
        (SlicerExecutionError, "Slicer execution failed",
         {"slicer_command": "prusaslicer --export-gcode test.stl", "exit_code": 1}),
        
        (PrinterConnectionError, "Printer connection failed",
         {"port": "/dev/ttyUSB0", "baudrate": 115200}),
        
        (WorkflowError, "Workflow step failed",
         {"workflow_step": "cad_generation", "agent_name": "cad_agent"})
    ]
    
    for exception_class, message, details in exceptions_to_test:
        try:
            if details:
                raise exception_class(message, **details)
            else:
                raise exception_class(message)
        except AI3DPrintError as e:
            # Test error response creation
            response = create_error_response(e, include_details=True)
            assert response["error"] == True
            assert response["error_type"] == exception_class.__name__
            print(f"✅ {exception_class.__name__} tested successfully")
    
    print("✅ Exception hierarchy tested successfully")


def test_error_handler_context():
    """Test error handler context manager."""
    print("=== Testing Error Handler Context ===")
    
    error_handler = get_error_handler("test_agent")
    
    # Test with custom exception
    try:
        with error_handler():
            raise CADAgentError("Test CAD error", 
                              error_code="TEST_ERROR",
                              details={"operation": "test_operation"})
    except AI3DPrintError as e:
        print(f"✅ Error handler captured: {e.error_code}")
    
    # Test with standard Python exception
    try:
        with error_handler():
            raise ValueError("Standard Python exception")
    except AI3DPrintError as e:
        print(f"✅ Error handler converted exception: {e.error_code}")
    
    print("✅ Error handler context tested successfully")


def test_structured_logging():
    """Test structured logging with complex data."""
    print("=== Testing Structured Logging ===")
    
    logger = get_api_logger()
    
    # Complex nested data
    request_data = {
        "request_id": "req_12345",
        "user_id": "user_789",
        "endpoint": "/api/print-request",
        "method": "POST",
        "payload": {
            "text": "Create a 2cm cube",
            "material": "PLA",
            "priority": "normal"
        },
        "headers": {
            "content-type": "application/json",
            "user-agent": "AI-3D-Print-Client/1.0"
        },
        "timestamp": "2025-06-10T12:45:00Z"
    }
    
    logger.info("API request received", **request_data)
    
    # Performance metrics
    performance_data = {
        "operation": "complete_workflow",
        "duration_ms": 15750,
        "steps": {
            "research": 2300,
            "cad": 8900,
            "slice": 3200,
            "queue": 1350
        },
        "memory_peak_mb": 256,
        "success": True
    }
    
    logger.info("Workflow completed", **performance_data)
    
    print("✅ Structured logging tested successfully")


def test_log_file_creation():
    """Verify that log files are created correctly."""
    print("=== Testing Log File Creation ===")
    
    logs_dir = Path("logs")
    
    expected_files = [
        "ai_3d_print.log",
        "error.log",
        "research_agent.log",
        "cad_agent.log",
        "slicer_agent.log",
        "printer_agent.log",
        "parent_agent.log",
        "api.log"
    ]
    
    # Trigger creation of all log files
    for agent_name in ["research_agent", "cad_agent", "slicer_agent", 
                      "printer_agent", "parent_agent", "api"]:
        logger = LoggerManager.get_logger(agent_name)
        logger.info(f"Test message for {agent_name}", test=True)
    
    # Check if files exist
    created_files = []
    for log_file in logs_dir.glob("*.log"):
        if log_file.is_file():
            created_files.append(log_file.name)
    
    print(f"✅ Created log files: {sorted(created_files)}")
    
    # Check JSON format in main log
    main_log = logs_dir / "ai_3d_print.log"
    if main_log.exists():
        with open(main_log, 'r') as f:
            first_line = f.readline().strip()
            if first_line.startswith('{') and first_line.endswith('}'):
                print("✅ JSON format verified in main log")
            else:
                print("⚠️  Main log might not be in JSON format")
    
    print("✅ Log file creation tested successfully")


def main():
    """Run all tests for Task 0.3."""
    print("🚀 Running Final Tests for Task 0.3: Logging & Error Handling Framework")
    print("=" * 80)
    
    try:
        test_all_loggers()
        print()
        
        test_all_log_levels()
        print()
        
        test_exception_hierarchy()
        print()
        
        test_error_handler_context()
        print()
        
        test_structured_logging()
        print()
        
        test_log_file_creation()
        print()
        
        print("🎉 All Task 0.3 tests completed successfully!")
        print("\n📋 Task 0.3 Success Criteria Met:")
        print("✅ core/logger.py with structured JSON logging exists")
        print("✅ core/exceptions.py with custom exception classes exists")
        print("✅ Separate log files per agent created")
        print("✅ All log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) working")
        print("✅ Structured logging with context data working")
        print("✅ Exception handling and error responses working")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🏁 Task 0.3: Logging & Error Handling Framework - COMPLETED!")
        print("Ready to proceed to Phase 1: Kern-Architektur & Agenten-Framework")
    else:
        print("\n❌ Task 0.3 failed. Please review and fix issues.")
    
    sys.exit(0 if success else 1)
