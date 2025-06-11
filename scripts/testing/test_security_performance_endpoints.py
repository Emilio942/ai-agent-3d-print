#!/usr/bin/env python3
"""
Test script for security and performance endpoints validation

This script tests the newly implemented security and performance endpoints
to ensure they are working correctly with the running server.
"""

import asyncio
import json
import time
import requests
from typing import Dict, Any

# Server configuration
BASE_URL = "http://localhost:8001"
ENDPOINTS_PREFIX = "/api/security-performance"

def test_endpoint(endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Test a single endpoint and return results"""
    url = f"{BASE_URL}{ENDPOINTS_PREFIX}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "data": response.json() if response.status_code == 200 else None,
            "error": response.text if response.status_code != 200 else None
        }
    except Exception as e:
        return {"error": str(e), "success": False}

def run_endpoint_tests():
    """Run comprehensive endpoint tests"""
    print("🔒 Testing Security & Performance Endpoints")
    print("=" * 60)
    
    # Test endpoints (based on actual implementation)
    endpoints = [
        # Security endpoints
        ("/security/status", "GET"),
        ("/security/audit-log", "GET"),
        
        # Performance endpoints  
        ("/performance/status", "GET"),
        ("/performance/metrics", "GET"),
        ("/performance/cache/stats", "GET"),
        ("/performance/resource-usage", "GET"),
        
        # Combined status
        ("/status", "GET"),
    ]
    
    results = {}
    
    for endpoint, method in endpoints:
        print(f"\n📡 Testing {method} {endpoint}")
        result = test_endpoint(endpoint, method)
        results[endpoint] = result
        
        if result.get("success"):
            print(f"   ✅ SUCCESS (Status: {result['status_code']})")
            if result.get("data"):
                # Print key information from response
                data = result["data"]
                if "status" in data:
                    print(f"   📊 Status: {data['status']}")
                if "threat_level" in data:
                    print(f"   🚨 Threat Level: {data['threat_level']}")
                if "cpu_usage" in data:
                    print(f"   💻 CPU Usage: {data['cpu_usage']:.1f}%")
                if "memory_usage" in data:
                    print(f"   🧠 Memory Usage: {data['memory_usage']:.1f}%")
                if "cache_hit_rate" in data:
                    print(f"   📦 Cache Hit Rate: {data['cache_hit_rate']:.1%}")
        else:
            print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for r in results.values() if r.get("success"))
    total = len(results)
    
    print(f"✅ Successful: {successful}/{total} ({successful/total*100:.1f}%)")
    print(f"❌ Failed: {total-successful}/{total}")
    
    if successful == total:
        print("\n🎉 ALL ENDPOINTS ARE WORKING CORRECTLY!")
    else:
        print(f"\n⚠️  {total-successful} endpoints need attention")
        
        # Show failed endpoints
        failed = [ep for ep, result in results.items() if not result.get("success")]
        for ep in failed:
            print(f"   • {ep}: {results[ep].get('error', 'Unknown error')}")
    
    return results

def test_middleware_functionality():
    """Test middleware functionality"""
    print("\n🛡️  Testing Middleware Functionality")
    print("=" * 60)
    
    # Test rate limiting by making multiple rapid requests
    print("\n📈 Testing Rate Limiting...")
    endpoint = f"{BASE_URL}{ENDPOINTS_PREFIX}/status"
    
    rapid_requests = []
    for i in range(10):
        try:
            start_time = time.time()
            response = requests.get(endpoint, timeout=5)
            end_time = time.time()
            
            rapid_requests.append({
                "request": i + 1,
                "status": response.status_code,
                "time": end_time - start_time
            })
        except Exception as e:
            rapid_requests.append({
                "request": i + 1,
                "error": str(e)
            })
    
    # Analyze results
    successful_requests = [r for r in rapid_requests if r.get("status") == 200]
    rate_limited = [r for r in rapid_requests if r.get("status") == 429]
    
    print(f"   ✅ Successful requests: {len(successful_requests)}")
    print(f"   🚫 Rate limited requests: {len(rate_limited)}")
    print(f"   ⏱️  Average response time: {sum(r.get('time', 0) for r in successful_requests)/len(successful_requests) if successful_requests else 0:.3f}s")
    
    if rate_limited:
        print("   ✅ Rate limiting is working!")
    else:
        print("   ℹ️  No rate limiting detected (may be configured for higher limits)")

if __name__ == "__main__":
    print("🚀 Starting Security & Performance Endpoint Tests")
    print(f"🌐 Server: {BASE_URL}")
    print(f"📍 Base Path: {ENDPOINTS_PREFIX}")
    
    try:
        # Test basic connectivity
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"   ✅ Server is reachable (Health: {health_response.status_code})")
    except Exception as e:
        print(f"   ❌ Server not reachable: {e}")
        exit(1)
    
    # Run endpoint tests
    endpoint_results = run_endpoint_tests()
    
    # Test middleware functionality
    test_middleware_functionality()
    
    print("\n🏁 Testing completed!")
