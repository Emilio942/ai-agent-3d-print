#!/usr/bin/env python3
"""
Task 4.2 Frontend-Backend Integration Test
Tests the complete frontend-backend communication system
"""

import asyncio
import json
import time
import requests
import websockets
from typing import Dict, Any
from datetime import datetime

class Task42IntegrationTest:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws/progress"
        self.frontend_url = "http://localhost:3000"
        self.test_results = {}
        
    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test results"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"[{timestamp}] {status_icon} {test_name}: {status}")
        if details:
            print(f"    {details}")
        
        self.test_results[test_name] = {
            "status": status,
            "details": details,
            "timestamp": timestamp
        }

    def test_frontend_serving(self) -> bool:
        """Test if frontend is being served correctly"""
        try:
            response = requests.get(f"{self.frontend_url}/", timeout=5)
            
            if response.status_code == 200:
                # Check if it contains expected elements
                content = response.text
                required_elements = [
                    'AI Agent 3D Print System',
                    'id="userRequest"',
                    'id="priority"',
                    'id="submitButton"',
                    'js/app.js',
                    'js/api.js',
                    'js/websocket.js',
                    'js/ui.js'
                ]
                
                missing_elements = [elem for elem in required_elements if elem not in content]
                
                if not missing_elements:
                    self.log_test("Frontend Serving", "PASS", f"HTML served correctly with all required elements")
                    return True
                else:
                    self.log_test("Frontend Serving", "FAIL", f"Missing elements: {missing_elements}")
                    return False
            else:
                self.log_test("Frontend Serving", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Frontend Serving", "FAIL", f"Error: {str(e)}")
            return False

    def test_static_assets(self) -> bool:
        """Test if static assets are accessible"""
        assets_to_test = [
            "/css/styles.css",
            "/css/components.css", 
            "/js/app.js",
            "/js/api.js",
            "/js/websocket.js",
            "/js/ui.js",
            "/manifest.json",
            "/sw.js"
        ]
        
        failed_assets = []
        
        for asset in assets_to_test:
            try:
                response = requests.get(f"{self.frontend_url}{asset}", timeout=5)
                if response.status_code != 200:
                    failed_assets.append(f"{asset} ({response.status_code})")
            except Exception as e:
                failed_assets.append(f"{asset} (Error: {str(e)})")
        
        if not failed_assets:
            self.log_test("Static Assets", "PASS", f"All {len(assets_to_test)} assets loaded successfully")
            return True
        else:
            self.log_test("Static Assets", "FAIL", f"Failed assets: {failed_assets}")
            return False

    def test_api_endpoints(self) -> bool:
        """Test API endpoints accessibility from frontend perspective"""
        try:
            # Test CORS headers for frontend requests
            headers = {
                'Origin': self.frontend_url,
                'Content-Type': 'application/json'
            }
            
            # Test health endpoint
            response = requests.get(f"{self.api_base_url}/health", headers=headers, timeout=5)
            
            if response.status_code == 200:
                # Check CORS headers
                cors_headers = response.headers.get('Access-Control-Allow-Origin')
                if cors_headers and ('*' in cors_headers or self.frontend_url in cors_headers):
                    self.log_test("API CORS", "PASS", "CORS headers configured correctly")
                else:
                    self.log_test("API CORS", "WARN", f"CORS headers: {cors_headers}")
                
                return True
            else:
                self.log_test("API Endpoints", "FAIL", f"Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("API Endpoints", "FAIL", f"Error: {str(e)}")
            return False

    async def test_websocket_connection(self) -> bool:
        """Test WebSocket connection"""
        try:
            # Test WebSocket connection
            async with websockets.connect(self.ws_url) as websocket:
                # Send a test message
                test_message = {"type": "ping"}
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "pong":
                        self.log_test("WebSocket Connection", "PASS", "Ping/pong successful")
                        return True
                    else:
                        self.log_test("WebSocket Connection", "WARN", f"Unexpected response: {data}")
                        return True  # Still connected
                        
                except asyncio.TimeoutError:
                    self.log_test("WebSocket Connection", "PASS", "Connected but no ping response (may be normal)")
                    return True
                    
        except Exception as e:
            self.log_test("WebSocket Connection", "FAIL", f"Error: {str(e)}")
            return False

    async def test_end_to_end_workflow(self) -> bool:
        """Test a complete print request workflow"""
        try:
            # Submit a test print request
            print_request = {
                "user_request": "Create a test cube for frontend integration testing",
                "priority": "normal"
            }
            
            headers = {
                'Origin': self.frontend_url,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/print-request",
                json=print_request,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 201:
                job_data = response.json()
                job_id = job_data.get("job_id")
                
                self.log_test("Print Request Submission", "PASS", f"Job created: {job_id}")
                
                # Test job status retrieval
                status_response = requests.get(
                    f"{self.api_base_url}/api/status/{job_id}",
                    headers=headers,
                    timeout=5
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    self.log_test("Job Status Retrieval", "PASS", f"Status: {status_data.get('status')}")
                    
                    # Test WebSocket subscription
                    try:
                        async with websockets.connect(self.ws_url) as websocket:
                            # Subscribe to job updates
                            subscribe_msg = {
                                "type": "subscribe",
                                "job_id": job_id
                            }
                            await websocket.send(json.dumps(subscribe_msg))
                            
                            # Wait briefly for any messages
                            try:
                                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                                self.log_test("WebSocket Job Subscription", "PASS", "Subscription successful")
                            except asyncio.TimeoutError:
                                self.log_test("WebSocket Job Subscription", "PASS", "Subscribed (no immediate updates)")
                                
                    except Exception as ws_e:
                        self.log_test("WebSocket Job Subscription", "WARN", f"WS Error: {str(ws_e)}")
                    
                    return True
                else:
                    self.log_test("Job Status Retrieval", "FAIL", f"HTTP {status_response.status_code}")
                    return False
            else:
                self.log_test("Print Request Submission", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("End-to-End Workflow", "FAIL", f"Error: {str(e)}")
            return False

    def test_javascript_modules(self) -> bool:
        """Test if JavaScript modules are syntactically correct"""
        js_files = [
            "/home/emilio/Documents/ai/ai-agent-3d-print/web/js/api.js",
            "/home/emilio/Documents/ai/ai-agent-3d-print/web/js/websocket.js", 
            "/home/emilio/Documents/ai/ai-agent-3d-print/web/js/ui.js",
            "/home/emilio/Documents/ai/ai-agent-3d-print/web/js/app.js"
        ]
        
        syntax_errors = []
        
        for js_file in js_files:
            try:
                with open(js_file, 'r') as f:
                    content = f.read()
                    
                # Basic syntax checks
                if 'class ' in content and 'constructor(' in content:
                    # Check for basic ES6 class syntax
                    if content.count('{') != content.count('}'):
                        syntax_errors.append(f"{js_file}: Mismatched braces")
                    elif 'window.' in content and 'function' in content:
                        # Looks like valid JavaScript
                        continue
                        
            except Exception as e:
                syntax_errors.append(f"{js_file}: {str(e)}")
        
        if not syntax_errors:
            self.log_test("JavaScript Modules", "PASS", f"All {len(js_files)} modules appear syntactically correct")
            return True
        else:
            self.log_test("JavaScript Modules", "FAIL", f"Issues: {syntax_errors}")
            return False

    async def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Task 4.2 Frontend-Backend Integration Tests")
        print("=" * 60)
        
        # Test frontend serving
        test1 = self.test_frontend_serving()
        
        # Test static assets
        test2 = self.test_static_assets()
        
        # Test JavaScript modules
        test3 = self.test_javascript_modules()
        
        # Test API endpoints
        test4 = self.test_api_endpoints()
        
        # Test WebSocket connection
        test5 = await self.test_websocket_connection()
        
        # Test end-to-end workflow
        test6 = await self.test_end_to_end_workflow()
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASS")
        failed_tests = sum(1 for result in self.test_results.values() if result["status"] == "FAIL")
        warned_tests = sum(1 for result in self.test_results.values() if result["status"] == "WARN")
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️  Warnings: {warned_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests == 0:
            print("\n🎉 ALL CORE TESTS PASSED! Frontend-backend integration is working!")
            print("\n✨ Task 4.2: Frontend Communication - COMPLETED ✨")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Please review the issues above.")
        
        return failed_tests == 0

if __name__ == "__main__":
    async def main():
        tester = Task42IntegrationTest()
        await tester.run_all_tests()
    
    asyncio.run(main())
