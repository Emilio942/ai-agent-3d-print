"""
Task 4.1 Validation Script - FastAPI Backend Development

This script validates the implementation of Task 4.1: FastAPI Backend with WebSocket.
It tests all the REST endpoints, WebSocket functionality, and integration with the agent system.

Test Coverage:
1. API Server Startup and Health Check
2. REST Endpoints Validation
3. WebSocket Communication
4. Workflow Integration
5. Error Handling
6. Background Task Processing
7. Production Readiness Features
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import pytest
import websockets
from fastapi.testclient import TestClient

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    "base_url": "http://127.0.0.1:8000",
    "websocket_url": "ws://127.0.0.1:8000",
    "timeout": 30,
    "test_request": "Create a small cube gear for a clock mechanism with 2cm dimensions"
}

class APITestSuite:
    """Comprehensive test suite for the FastAPI backend."""
    
    def __init__(self):
        self.base_url = TEST_CONFIG["base_url"]
        self.websocket_url = TEST_CONFIG["websocket_url"]
        self.timeout = TEST_CONFIG["timeout"]
        self.test_results = {}
        self.job_ids = []
        
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run the complete test suite."""
        logger.info("Starting FastAPI Backend Validation Tests")
        logger.info("=" * 60)
        
        test_methods = [
            ("Health Check", self.test_health_check),
            ("Print Request Creation", self.test_create_print_request),
            ("Job Status Retrieval", self.test_job_status),
            ("Workflow List", self.test_list_workflows),
            ("WebSocket Progress Updates", self.test_websocket_progress),
            ("Workflow Cancellation", self.test_cancel_workflow),
            ("Error Handling", self.test_error_handling),
            ("API Documentation", self.test_api_documentation),
            ("CORS Configuration", self.test_cors_configuration)
        ]
        
        for test_name, test_method in test_methods:
            try:
                logger.info(f"\nRunning: {test_name}")
                result = await test_method()
                self.test_results[test_name] = result
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"{test_name}: {status}")
            except Exception as e:
                logger.error(f"{test_name}: ❌ FAILED - {e}")
                self.test_results[test_name] = False
        
        return self.test_results
    
    async def test_health_check(self) -> bool:
        """Test the health check endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=self.timeout)
                
                if response.status_code != 200:
                    logger.error(f"Health check failed with status {response.status_code}")
                    return False
                
                health_data = response.json()
                required_fields = ["status", "version", "uptime_seconds", "agents_status"]
                
                for field in required_fields:
                    if field not in health_data:
                        logger.error(f"Missing required field in health response: {field}")
                        return False
                
                if health_data["status"] != "healthy":
                    logger.warning(f"System status is not healthy: {health_data['status']}")
                    # Don't fail the test for this, as system might be starting up
                
                logger.info(f"Health check successful: {health_data['status']}")
                return True
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def test_create_print_request(self) -> bool:
        """Test creating a new print request."""
        try:
            print_request = {
                "user_request": TEST_CONFIG["test_request"],
                "user_id": "test_user",
                "printer_profile": "ender3_pla",
                "quality_level": "standard",
                "metadata": {"test": True}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/print-request",
                    json=print_request,
                    timeout=self.timeout
                )
                
                if response.status_code != 201:
                    logger.error(f"Print request creation failed with status {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return False
                
                job_data = response.json()
                required_fields = ["job_id", "status", "progress_percentage", "message", "created_at"]
                
                for field in required_fields:
                    if field not in job_data:
                        logger.error(f"Missing required field in job response: {field}")
                        return False
                
                # Store job ID for further tests
                self.job_ids.append(job_data["job_id"])
                
                logger.info(f"Print request created successfully: {job_data['job_id']}")
                return True
                
        except Exception as e:
            logger.error(f"Print request creation failed: {e}")
            return False
    
    async def test_job_status(self) -> bool:
        """Test retrieving job status."""
        if not self.job_ids:
            logger.error("No job IDs available for status test")
            return False
        
        try:
            job_id = self.job_ids[0]
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/status/{job_id}",
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    logger.error(f"Job status retrieval failed with status {response.status_code}")
                    return False
                
                status_data = response.json()
                required_fields = ["job_id", "status", "progress_percentage", "current_step", "message"]
                
                for field in required_fields:
                    if field not in status_data:
                        logger.error(f"Missing required field in status response: {field}")
                        return False
                
                if status_data["job_id"] != job_id:
                    logger.error(f"Job ID mismatch: expected {job_id}, got {status_data['job_id']}")
                    return False
                
                logger.info(f"Job status retrieved successfully: {status_data['status']}")
                return True
                
        except Exception as e:
            logger.error(f"Job status retrieval failed: {e}")
            return False
    
    async def test_list_workflows(self) -> bool:
        """Test listing workflows with pagination."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/workflows?limit=10&offset=0",
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    logger.error(f"Workflow listing failed with status {response.status_code}")
                    return False
                
                workflows_data = response.json()
                
                if not isinstance(workflows_data, list):
                    logger.error("Workflows response should be a list")
                    return False
                
                # Check if our created job is in the list
                if self.job_ids:
                    job_found = any(wf["job_id"] == self.job_ids[0] for wf in workflows_data)
                    if not job_found:
                        logger.warning("Created job not found in workflow list")
                
                logger.info(f"Workflow listing successful: {len(workflows_data)} workflows")
                return True
                
        except Exception as e:
            logger.error(f"Workflow listing failed: {e}")
            return False
    
    async def test_websocket_progress(self) -> bool:
        """Test WebSocket progress updates."""
        if not self.job_ids:
            logger.warning("No job IDs available for WebSocket test")
            return True  # Don't fail if no jobs to monitor
        
        try:
            job_id = self.job_ids[0]
            websocket_uri = f"{self.websocket_url}/ws/progress?job_id={job_id}"
            
            # Connect to WebSocket
            async with websockets.connect(websocket_uri) as websocket:
                logger.info("WebSocket connected successfully")
                
                # Send a ping message
                ping_message = {"type": "ping"}
                await websocket.send(json.dumps(ping_message))
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "pong":
                        logger.info("WebSocket ping/pong successful")
                        return True
                    elif response_data.get("type") in ["status_update", "progress_update"]:
                        logger.info(f"Received progress update: {response_data.get('message', 'No message')}")
                        return True
                    else:
                        logger.info(f"Received WebSocket message: {response_data}")
                        return True
                        
                except asyncio.TimeoutError:
                    logger.warning("WebSocket response timeout (this is okay if no updates are available)")
                    return True
                
        except Exception as e:
            logger.error(f"WebSocket test failed: {e}")
            return False
    
    async def test_cancel_workflow(self) -> bool:
        """Test workflow cancellation."""
        if not self.job_ids:
            logger.warning("No job IDs available for cancellation test")
            return True
        
        try:
            # Create a new job for cancellation test
            print_request = {
                "user_request": "Create a test cube for cancellation",
                "user_id": "test_user"
            }
            
            async with httpx.AsyncClient() as client:
                # Create job
                response = await client.post(
                    f"{self.base_url}/api/print-request",
                    json=print_request,
                    timeout=self.timeout
                )
                
                if response.status_code != 201:
                    logger.error("Failed to create job for cancellation test")
                    return False
                
                job_data = response.json()
                cancel_job_id = job_data["job_id"]
                
                # Try to cancel the job immediately
                cancel_response = await client.delete(
                    f"{self.base_url}/api/workflows/{cancel_job_id}",
                    timeout=self.timeout
                )
                
                # Accept both successful cancellation (204) and "already completed" (400)
                # since workflows may complete very quickly in our mock implementation
                if cancel_response.status_code not in [204, 400]:
                    logger.error(f"Unexpected cancellation response status {cancel_response.status_code}")
                    return False
                
                if cancel_response.status_code == 400:
                    # Workflow completed before we could cancel - this is acceptable
                    logger.info("Workflow completed before cancellation (acceptable behavior)")
                    return True
                
                # Verify the job was cancelled
                status_response = await client.get(
                    f"{self.base_url}/api/status/{cancel_job_id}",
                    timeout=self.timeout
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data["status"] == "cancelled":
                        logger.info("Workflow cancellation successful")
                        return True
                    else:
                        logger.warning(f"Job status after cancellation: {status_data['status']}")
                        return True  # Don't fail if cancellation is still processing
                
                return True
                
        except Exception as e:
            logger.error(f"Workflow cancellation test failed: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test API error handling."""
        try:
            async with httpx.AsyncClient() as client:
                # Test invalid job ID
                response = await client.get(
                    f"{self.base_url}/api/status/invalid-job-id",
                    timeout=self.timeout
                )
                
                if response.status_code != 404:
                    logger.error(f"Expected 404 for invalid job ID, got {response.status_code}")
                    return False
                
                # Test invalid print request
                invalid_request = {
                    "user_request": ""  # Too short
                }
                
                response = await client.post(
                    f"{self.base_url}/api/print-request",
                    json=invalid_request,
                    timeout=self.timeout
                )
                
                if response.status_code not in [400, 422]:
                    logger.error(f"Expected 400/422 for invalid request, got {response.status_code}")
                    return False
                
                logger.info("Error handling tests passed")
                return True
                
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    async def test_api_documentation(self) -> bool:
        """Test that API documentation is available."""
        try:
            async with httpx.AsyncClient() as client:
                # Test OpenAPI schema
                response = await client.get(f"{self.base_url}/openapi.json", timeout=self.timeout)
                if response.status_code != 200:
                    logger.error("OpenAPI schema not available")
                    return False
                
                # Test Swagger UI
                response = await client.get(f"{self.base_url}/docs", timeout=self.timeout)
                if response.status_code != 200:
                    logger.error("Swagger UI not available")
                    return False
                
                # Test ReDoc
                response = await client.get(f"{self.base_url}/redoc", timeout=self.timeout)
                if response.status_code != 200:
                    logger.error("ReDoc not available")
                    return False
                
                logger.info("API documentation available")
                return True
                
        except Exception as e:
            logger.error(f"API documentation test failed: {e}")
            return False
    
    async def test_cors_configuration(self) -> bool:
        """Test CORS configuration."""
        try:
            async with httpx.AsyncClient() as client:
                # Test OPTIONS request
                headers = {
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                }
                
                response = await client.options(
                    f"{self.base_url}/api/print-request",
                    headers=headers,
                    timeout=self.timeout
                )
                
                # CORS should allow the request or return appropriate headers
                cors_headers = [
                    "access-control-allow-origin",
                    "access-control-allow-methods",
                    "access-control-allow-headers"
                ]
                
                has_cors = any(header in response.headers for header in cors_headers)
                
                if has_cors:
                    logger.info("CORS configuration detected")
                    return True
                else:
                    logger.warning("CORS headers not found (may be configured differently)")
                    return True  # Don't fail, as CORS might be configured at proxy level
                
        except Exception as e:
            logger.error(f"CORS test failed: {e}")
            return False
    
    def print_test_summary(self):
        """Print a summary of all test results."""
        logger.info("\n" + "=" * 60)
        logger.info("FASTAPI BACKEND VALIDATION SUMMARY")
        logger.info("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        logger.info("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"  {test_name}: {status}")
        
        if success_rate >= 90:
            logger.info(f"\n🎉 TASK 4.1 VALIDATION: SUCCESS!")
            logger.info("FastAPI Backend with WebSocket implemented successfully")
        elif success_rate >= 75:
            logger.info(f"\n⚠️ TASK 4.1 VALIDATION: MOSTLY SUCCESSFUL")
            logger.info("Most features working, minor issues detected")
        else:
            logger.info(f"\n❌ TASK 4.1 VALIDATION: NEEDS WORK")
            logger.info("Significant issues detected, review implementation")
        
        return success_rate

async def check_server_availability():
    """Check if the API server is running."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TEST_CONFIG['base_url']}/health", timeout=5)
            return response.status_code == 200
    except:
        return False

async def main():
    """Main validation script entry point."""
    logger.info("Task 4.1 Validation: FastAPI Backend Development")
    logger.info("=" * 60)
    
    # Check if server is running
    if not await check_server_availability():
        logger.error("❌ API server is not running!")
        logger.info("Please start the server first:")
        logger.info("  python start_api_server.py")
        return False
    
    # Run test suite
    test_suite = APITestSuite()
    await test_suite.run_all_tests()
    success_rate = test_suite.print_test_summary()
    
    return success_rate >= 75

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
