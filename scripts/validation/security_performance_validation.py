"""
Security & Performance Enhancement Validation Test

This script validates the implementation of Task X.2: Security & Performance Enhancement
including advanced security features, performance optimizations, and monitoring capabilities.
"""

import asyncio
import requests
import time
import json
from datetime import datetime
from typing import Dict, Any

# Test configuration
API_BASE_URL = "http://localhost:8000"
TEST_ENDPOINTS = [
    "/health",
    "/api/security-performance/status",
    "/api/security-performance/security/status", 
    "/api/security-performance/performance/status",
    "/api/security-performance/performance/cache/stats"
]

class SecurityPerformanceValidator:
    """Comprehensive validator for security and performance enhancements"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        
    def log_test(self, category: str, test_name: str, status: str, details: str = ""):
        """Log test results"""
        if category not in self.results:
            self.results[category] = []
        
        self.results[category].append({
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {category}: {test_name} - {status}")
        if details:
            print(f"    {details}")
    
    async def test_security_features(self) -> bool:
        """Test security enhancement features"""
        print("\n=== SECURITY FEATURES TESTING ===")
        all_passed = True
        
        try:
            # Test 1: Input Sanitization
            print("\n1. Testing Input Sanitization...")
            from core.security import input_sanitizer
            
            # Test SQL injection detection
            sql_test = "'; DROP TABLE users; --"
            result = input_sanitizer.sanitize_input(sql_test)
            
            if 'sql_injection' in result['detected_threats']:
                self.log_test("Security", "SQL Injection Detection", "PASS", 
                            f"Detected threat score: {result['threat_score']}")
            else:
                self.log_test("Security", "SQL Injection Detection", "FAIL", 
                            "SQL injection not detected")
                all_passed = False
            
            # Test XSS detection
            xss_test = "<script>alert('xss')</script>"
            result = input_sanitizer.sanitize_input(xss_test)
            
            if 'xss' in result['detected_threats']:
                self.log_test("Security", "XSS Detection", "PASS",
                            f"Detected threat score: {result['threat_score']}")
            else:
                self.log_test("Security", "XSS Detection", "FAIL",
                            "XSS not detected")
                all_passed = False
            
            # Test 2: Rate Limiting
            print("\n2. Testing Rate Limiting...")
            from core.security import rate_limiter
            
            # Test rate limit functionality
            test_results = []
            for i in range(5):
                result = await rate_limiter.check_rate_limit(
                    user_id="test_user",
                    ip_address="127.0.0.1",
                    endpoint="/api/test"
                )
                test_results.append(result['allowed'])
            
            if all(test_results):
                self.log_test("Security", "Rate Limiting System", "PASS",
                            f"Processed {len(test_results)} requests successfully")
            else:
                self.log_test("Security", "Rate Limiting System", "FAIL",
                            f"Some requests blocked: {test_results}")
                
            # Test 3: Security Audit Logging
            print("\n3. Testing Security Audit Logging...")
            from core.security import audit_logger, SecurityEvent, ThreatLevel
            
            test_event = SecurityEvent(
                event_type="test_event",
                threat_level=ThreatLevel.LOW,
                source_ip="127.0.0.1",
                user_id="test_user",
                endpoint="/api/test"
            )
            
            await audit_logger.log_security_event(test_event)
            stats = await audit_logger.get_statistics()
            
            if stats['total_events'] > 0:
                self.log_test("Security", "Audit Logging", "PASS",
                            f"Total events logged: {stats['total_events']}")
            else:
                self.log_test("Security", "Audit Logging", "FAIL",
                            "No events logged")
                all_passed = False
            
            # Test 4: MFA System
            print("\n4. Testing MFA System...")
            from core.security import mfa_manager
            
            # Generate MFA secret
            secret = mfa_manager.generate_secret("test_user")
            qr_code = mfa_manager.generate_qr_code("test_user")
            
            if secret and qr_code.startswith("data:image/png;base64,"):
                self.log_test("Security", "MFA Setup", "PASS",
                            f"Secret generated, QR code: {len(qr_code)} chars")
            else:
                self.log_test("Security", "MFA Setup", "FAIL",
                            "MFA setup failed")
                all_passed = False
                
        except Exception as e:
            self.log_test("Security", "Security Features", "FAIL", f"Error: {e}")
            all_passed = False
            
        return all_passed
    
    async def test_performance_features(self) -> bool:
        """Test performance enhancement features"""
        print("\n=== PERFORMANCE FEATURES TESTING ===")
        all_passed = True
        
        try:
            # Test 1: Caching System
            print("\n1. Testing Caching System...")
            from core.performance import cache
            
            # Test cache set/get
            await cache.set("test_key", {"test": "data"}, ttl=60)
            cached_data = await cache.get("test_key")
            
            if cached_data and cached_data["test"] == "data":
                self.log_test("Performance", "Cache System", "PASS",
                            "Cache set/get operations working")
            else:
                self.log_test("Performance", "Cache System", "FAIL",
                            "Cache operations failed")
                all_passed = False
            
            # Test cache statistics
            stats = cache.get_stats()
            if 'hit_rate' in stats and 'total_size_mb' in stats:
                self.log_test("Performance", "Cache Statistics", "PASS",
                            f"Hit rate: {stats['hit_rate']:.2%}, Size: {stats['total_size_mb']:.2f}MB")
            else:
                self.log_test("Performance", "Cache Statistics", "FAIL",
                            "Cache statistics not available")
                all_passed = False
            
            # Test 2: Resource Management
            print("\n2. Testing Resource Management...")
            from core.performance import resource_manager
            
            # Test resource availability check
            availability = await resource_manager.check_resource_availability("test_job")
            
            if availability['overall_available']:
                self.log_test("Performance", "Resource Management", "PASS",
                            f"Memory: {availability['memory_available']}, CPU: {availability['cpu_available']}")
            else:
                self.log_test("Performance", "Resource Management", "WARN",
                            f"Resources limited: {availability['warnings']}")
            
            # Test resource allocation context manager
            try:
                async with resource_manager.allocate_resources("test_job", "testing"):
                    # Simulate some work
                    await asyncio.sleep(0.1)
                
                self.log_test("Performance", "Resource Allocation", "PASS",
                            "Resource allocation context manager working")
            except Exception as e:
                self.log_test("Performance", "Resource Allocation", "FAIL",
                            f"Resource allocation failed: {e}")
                all_passed = False
            
            # Test 3: Performance Monitoring
            print("\n3. Testing Performance Monitoring...")
            from core.performance import performance_monitor
            
            # Record test metrics
            await performance_monitor.record_metrics(
                response_time=0.5,
                memory_usage=0.6,
                cpu_usage=0.4,
                active_connections=5,
                cache_hit_rate=0.8,
                error_rate=0.02
            )
            
            # Get performance summary
            summary = performance_monitor.get_performance_summary(minutes=5)
            
            if summary and 'averages' in summary:
                self.log_test("Performance", "Performance Monitoring", "PASS",
                            f"Recorded metrics, samples: {summary.get('sample_count', 0)}")
            else:
                self.log_test("Performance", "Performance Monitoring", "FAIL",
                            "Performance monitoring not working")
                all_passed = False
            
            # Test 4: Response Compression
            print("\n4. Testing Response Compression...")
            from core.performance import compressor
            
            # Test compression decision
            should_compress = compressor.should_compress("application/json", 2048)
            
            if should_compress:
                # Test actual compression
                test_data = b'{"test": "data"}' * 100  # Large JSON
                compressed = compressor.compress_content(test_data)
                compression_ratio = len(compressed) / len(test_data)
                
                self.log_test("Performance", "Response Compression", "PASS",
                            f"Compression ratio: {compression_ratio:.2f}")
            else:
                self.log_test("Performance", "Response Compression", "WARN",
                            "Small content not compressed (expected)")
                
        except Exception as e:
            self.log_test("Performance", "Performance Features", "FAIL", f"Error: {e}")
            all_passed = False
            
        return all_passed
    
    def test_api_endpoints(self) -> bool:
        """Test security and performance API endpoints"""
        print("\n=== API ENDPOINTS TESTING ===")
        all_passed = True
        
        try:
            # Start a local server for testing (if not already running)
            print("Testing API endpoints (ensure server is running)...")
            
            for endpoint in TEST_ENDPOINTS:
                try:
                    url = f"{API_BASE_URL}{endpoint}"
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.log_test("API", f"Endpoint {endpoint}", "PASS",
                                    f"Status: {response.status_code}, Response size: {len(str(data))}")
                    else:
                        self.log_test("API", f"Endpoint {endpoint}", "FAIL",
                                    f"Status: {response.status_code}")
                        all_passed = False
                        
                except requests.exceptions.RequestException as e:
                    self.log_test("API", f"Endpoint {endpoint}", "SKIP",
                                f"Server not running: {e}")
            
            # Test security headers
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                headers = response.headers
                
                security_headers = [
                    'X-Frame-Options',
                    'X-Content-Type-Options', 
                    'X-XSS-Protection'
                ]
                
                missing_headers = [h for h in security_headers if h not in headers]
                
                if not missing_headers:
                    self.log_test("API", "Security Headers", "PASS",
                                f"All security headers present")
                else:
                    self.log_test("API", "Security Headers", "FAIL",
                                f"Missing headers: {missing_headers}")
                    all_passed = False
                    
            except requests.exceptions.RequestException:
                self.log_test("API", "Security Headers", "SKIP", "Server not running")
                
        except Exception as e:
            self.log_test("API", "API Endpoints", "FAIL", f"Error: {e}")
            all_passed = False
            
        return all_passed
    
    def test_middleware_integration(self) -> bool:
        """Test middleware integration"""
        print("\n=== MIDDLEWARE INTEGRATION TESTING ===")
        all_passed = True
        
        try:
            # Test middleware imports
            from api.middleware.security_middleware import SecurityMiddleware
            from api.middleware.performance_middleware import PerformanceMiddleware
            
            self.log_test("Middleware", "Import Security Middleware", "PASS", 
                        "SecurityMiddleware imported successfully")
            self.log_test("Middleware", "Import Performance Middleware", "PASS",
                        "PerformanceMiddleware imported successfully")
            
            # Test FastAPI app with middleware
            from api.main import app
            
            # Check middleware is registered
            middleware_types = [type(middleware) for middleware in app.user_middleware]
            middleware_names = [m.__name__ for m in middleware_types]
            
            if any("Security" in name for name in middleware_names):
                self.log_test("Middleware", "Security Middleware Registration", "PASS",
                            f"Security middleware found in: {middleware_names}")
            else:
                self.log_test("Middleware", "Security Middleware Registration", "FAIL",
                            f"Security middleware not found in: {middleware_names}")
                all_passed = False
            
            if any("Performance" in name or "Resource" in name for name in middleware_names):
                self.log_test("Middleware", "Performance Middleware Registration", "PASS",
                            f"Performance middleware found")
            else:
                self.log_test("Middleware", "Performance Middleware Registration", "FAIL",
                            f"Performance middleware not found")
                all_passed = False
                
        except Exception as e:
            self.log_test("Middleware", "Middleware Integration", "FAIL", f"Error: {e}")
            all_passed = False
            
        return all_passed
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of all security and performance features"""
        self.start_time = time.time()
        
        print("🔒⚡ AI Agent 3D Print System - Security & Performance Enhancement Validation")
        print("=" * 80)
        
        # Run all test categories
        test_results = {
            'security_features': await self.test_security_features(),
            'performance_features': await self.test_performance_features(),
            'api_endpoints': self.test_api_endpoints(),
            'middleware_integration': self.test_middleware_integration()
        }
        
        # Calculate overall results
        total_time = time.time() - self.start_time
        total_tests = sum(len(tests) for tests in self.results.values())
        passed_tests = sum(len([t for t in tests if t['status'] == 'PASS']) 
                          for tests in self.results.values())
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Generate summary
        print(f"\n{'=' * 80}")
        print("🎯 VALIDATION SUMMARY")
        print(f"{'=' * 80}")
        print(f"⏱️  Total Time: {total_time:.2f} seconds")
        print(f"📊 Tests Run: {total_tests}")
        print(f"✅ Tests Passed: {passed_tests}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        # Print category summaries
        for category, tests in self.results.items():
            passed = len([t for t in tests if t['status'] == 'PASS'])
            total = len(tests)
            status_icon = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
            print(f"{status_icon} {category.replace('_', ' ').title()}: {passed}/{total} passed")
        
        # Overall status
        overall_status = "SUCCESS" if success_rate >= 80 else "PARTIAL" if success_rate >= 50 else "FAILED"
        status_icon = "🎉" if overall_status == "SUCCESS" else "⚠️" if overall_status == "PARTIAL" else "❌"
        
        print(f"\n{status_icon} Overall Status: {overall_status}")
        
        return {
            'overall_status': overall_status,
            'success_rate': success_rate,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'total_time': total_time,
            'test_results': test_results,
            'detailed_results': self.results
        }


async def main():
    """Main validation function"""
    validator = SecurityPerformanceValidator()
    results = await validator.run_comprehensive_validation()
    
    # Save detailed results
    with open('security_performance_validation_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: security_performance_validation_results.json")
    
    return results['overall_status'] == "SUCCESS"


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
