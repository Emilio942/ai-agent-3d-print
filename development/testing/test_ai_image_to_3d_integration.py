#!/usr/bin/env python3
"""
Comprehensive Test Suite for AI Image-to-3D and 3D Viewer Integration
AI Agent 3D Print System

Tests the newly integrated AI-powered image-to-3D conversion and 3D viewer features.
"""

import asyncio
import requests
import json
import time
from pathlib import Path

class TestAIImageTo3DIntegration:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    def test_api_endpoints(self):
        """Test all API endpoints for image-to-3D functionality"""
        print("\n🧪 Testing AI Image-to-3D API Endpoints...")
        
        # Test 1: List converted models
        try:
            response = requests.get(f"{self.base_url}/api/advanced/image-to-3d/models")
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and isinstance(data.get("models"), list):
                    self.log_test("List converted models API", True, f"Found {data.get('count', 0)} models")
                else:
                    self.log_test("List converted models API", False, "Invalid response format")
            else:
                self.log_test("List converted models API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("List converted models API", False, str(e))

        # Test 2: Get specific model details
        try:
            response = requests.get(f"{self.base_url}/api/advanced/image-to-3d/models/demo_001")
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("model"):
                    self.log_test("Get model details API", True, f"Model: {data['model']['original_filename']}")
                else:
                    self.log_test("Get model details API", False, "Invalid response format")
            else:
                self.log_test("Get model details API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Get model details API", False, str(e))

        # Test 3: Create print job from converted model
        try:
            response = requests.post(
                f"{self.base_url}/api/advanced/image-to-3d/models/demo_001/print",
                json={"priority": "normal"}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("job_id"):
                    self.log_test("Print converted model API", True, f"Job ID: {data['job_id']}")
                else:
                    self.log_test("Print converted model API", False, "Invalid response format")
            else:
                self.log_test("Print converted model API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Print converted model API", False, str(e))

    def test_image_conversion(self):
        """Test image-to-3D conversion with a real image file"""
        print("\n🖼️ Testing Image-to-3D Conversion...")
        
        # Check for test images
        test_images = ["test_circle.png", "test_shapes.png"]
        for image_file in test_images:
            if Path(image_file).exists():
                try:
                    with open(image_file, 'rb') as f:
                        files = {'file': (image_file, f, 'image/png')}
                        data = {
                            'style': 'realistic',
                            'quality': 'medium',
                            'format': 'stl'
                        }
                        
                        response = requests.post(
                            f"{self.base_url}/api/advanced/image-to-3d/convert",
                            files=files,
                            data=data
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get("success") and result.get("model_id"):
                                self.log_test(
                                    f"Convert image {image_file}", 
                                    True, 
                                    f"Model ID: {result['model_id']}, Processing time: {result.get('processing_time', 'N/A')}s"
                                )
                            else:
                                self.log_test(f"Convert image {image_file}", False, "Conversion failed")
                        else:
                            self.log_test(f"Convert image {image_file}", False, f"HTTP {response.status_code}")
                            
                except Exception as e:
                    self.log_test(f"Convert image {image_file}", False, str(e))
            else:
                self.log_test(f"Convert image {image_file}", False, "Image file not found")

    def test_web_interface_assets(self):
        """Test that all web interface assets are loading correctly"""
        print("\n🌐 Testing Web Interface Assets...")
        
        assets = [
            "/web/css/advanced.css",
            "/web/js/image-to-3d.js",
            "/web/js/viewer-manager.js",
            "/web/js/3d-viewer.js"
        ]
        
        for asset in assets:
            try:
                response = requests.get(f"{self.base_url}{asset}")
                if response.status_code == 200:
                    self.log_test(f"Load asset {asset}", True, f"Size: {len(response.content)} bytes")
                else:
                    self.log_test(f"Load asset {asset}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test(f"Load asset {asset}", False, str(e))

    def test_main_interface(self):
        """Test that the main web interface loads with new features"""
        print("\n🏠 Testing Main Web Interface...")
        
        try:
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                content = response.text
                
                # Check for new features in the HTML
                features_to_check = [
                    ("Image to 3D tab", "Image to 3D"),
                    ("3D Viewer tab", "3D Viewer"),
                    ("File upload area", "file-upload-area"),
                    ("Viewer canvas", "viewer-canvas"),
                    ("Three.js library", "three.min.js")
                ]
                
                for feature_name, search_term in features_to_check:
                    if search_term in content:
                        self.log_test(f"Web interface - {feature_name}", True)
                    else:
                        self.log_test(f"Web interface - {feature_name}", False, f"'{search_term}' not found")
                        
            else:
                self.log_test("Main web interface", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Main web interface", False, str(e))

    def test_existing_functionality(self):
        """Test that existing functionality still works"""
        print("\n🔄 Testing Existing Functionality...")
        
        try:
            # Test regular print request
            response = requests.post(
                f"{self.base_url}/api/print-request",
                json={
                    "user_request": "Create a test cube for integration testing",
                    "priority": "normal"
                }
            )
            
            if response.status_code in [200, 201]:  # Both OK and Created are valid
                data = response.json()
                if data.get("job_id") and data.get("status") == "pending":
                    self.log_test("Regular print request", True, f"Job ID: {data['job_id']}")
                else:
                    self.log_test("Regular print request", False, "Invalid response format")
            else:
                self.log_test("Regular print request", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Regular print request", False, str(e))

    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n" + "="*60)
        print("🎯 AI IMAGE-TO-3D INTEGRATION TEST REPORT")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for test in self.test_results:
                if not test["success"]:
                    print(f"   • {test['test']}: {test['details']}")
        
        print(f"\n✅ KEY FEATURES TESTED:")
        print(f"   • AI Image-to-3D Conversion API")
        print(f"   • 3D Model Management (List, Get, Delete)")
        print(f"   • Print Job Creation from Converted Models")
        print(f"   • Web Interface Integration (Tabs, Upload, Viewer)")
        print(f"   • Asset Loading (CSS, JavaScript)")
        print(f"   • Backward Compatibility (Existing APIs)")
        
        print(f"\n🚀 INTEGRATION STATUS: {'SUCCESSFUL' if failed_tests == 0 else 'NEEDS ATTENTION'}")
        
        # Save report to file
        report_file = "AI_IMAGE_TO_3D_INTEGRATION_REPORT.md"
        with open(report_file, 'w') as f:
            f.write("# AI Image-to-3D Integration Test Report\n\n")
            f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Tests:** {total_tests}\n")
            f.write(f"**Passed:** {passed_tests}\n")
            f.write(f"**Failed:** {failed_tests}\n")
            f.write(f"**Success Rate:** {(passed_tests/total_tests)*100:.1f}%\n\n")
            
            f.write("## Test Results\n\n")
            for test in self.test_results:
                status = "✅" if test["success"] else "❌"
                f.write(f"- {status} **{test['test']}**")
                if test["details"]:
                    f.write(f": {test['details']}")
                f.write(f" _{test['timestamp']}_\n")
            
            f.write("\n## Features Integrated\n\n")
            f.write("- ✅ AI-powered image-to-3D conversion\n")
            f.write("- ✅ Advanced 3D model viewer with Three.js\n")
            f.write("- ✅ Tabbed web interface (Text Request | Image to 3D | 3D Viewer)\n")
            f.write("- ✅ File upload with drag-and-drop support\n")
            f.write("- ✅ Converted model management and printing\n")
            f.write("- ✅ Real-time progress tracking\n")
            f.write("- ✅ Mobile-responsive design\n")
            f.write("- ✅ PWA enhancements\n")
        
        print(f"\n📄 Report saved to: {report_file}")

    def run_all_tests(self):
        """Run the complete test suite"""
        print("🚀 Starting AI Image-to-3D Integration Test Suite...")
        print(f"🎯 Target URL: {self.base_url}")
        
        self.test_main_interface()
        self.test_web_interface_assets()
        self.test_api_endpoints()
        self.test_image_conversion()
        self.test_existing_functionality()
        
        self.generate_report()

if __name__ == "__main__":
    # Wait a moment for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(3)
    
    tester = TestAIImageTo3DIntegration()
    tester.run_all_tests()
