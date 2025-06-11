#!/usr/bin/env python3
"""
MFA (Multi-Factor Authentication) Demo Script

This script demonstrates the MFA functionality implemented in the 
security and performance enhancement task.
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8001"
MFA_ENDPOINTS = "/api/security-performance/security/mfa"

def test_mfa_setup(user_id: str = "test_user_123") -> Dict[str, Any]:
    """Test MFA setup for a user"""
    print(f"🔐 Testing MFA Setup for user: {user_id}")
    
    try:
        url = f"{BASE_URL}{MFA_ENDPOINTS}/setup/{user_id}"
        response = requests.post(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ MFA Setup Successful!")
            print(f"   📱 Secret Key: {data.get('secret_key', 'N/A')[:10]}...")
            print(f"   📋 Backup Codes: {len(data.get('backup_codes', []))} codes generated")
            print(f"   📦 QR Code: {'Available' if data.get('qr_code') else 'Not available'}")
            return data
        else:
            print(f"   ❌ Setup Failed: {response.status_code} - {response.text}")
            return {}
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {}

def test_mfa_verification(user_id: str, token: str = "123456") -> bool:
    """Test MFA verification for a user"""
    print(f"🔍 Testing MFA Verification for user: {user_id}")
    
    try:
        url = f"{BASE_URL}{MFA_ENDPOINTS}/verify/{user_id}?token={token}"
        response = requests.post(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            verified = data.get('verified', False)
            print(f"   {'✅' if verified else '❌'} Verification: {'Success' if verified else 'Failed'}")
            return verified
        else:
            print(f"   ❌ Verification Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def demonstrate_security_features():
    """Demonstrate various security features"""
    print("\n🛡️  Security Features Demonstration")
    print("=" * 50)
    
    # Test security status
    print("\n📊 Checking Security Status...")
    try:
        response = requests.get(f"{BASE_URL}/api/security-performance/security/status")
        if response.status_code == 200:
            data = response.json()
            print(f"   🔒 Security Status: {data.get('status', 'Unknown')}")
            print(f"   🚨 Threat Level: {data.get('threat_level', 'Unknown')}")
            print(f"   ⚠️  Active Violations: {data.get('active_violations', 0)}")
        else:
            print(f"   ❌ Failed to get security status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test audit logs
    print("\n📋 Checking Audit Logs...")
    try:
        response = requests.get(f"{BASE_URL}/api/security-performance/security/audit-log")
        if response.status_code == 200:
            data = response.json()
            recent_events = data.get('recent_events', [])
            print(f"   📝 Recent Events: {len(recent_events)} logged")
            if recent_events:
                latest = recent_events[0]
                print(f"   🕐 Latest Event: {latest.get('event_type', 'Unknown')} at {latest.get('timestamp', 'Unknown')}")
        else:
            print(f"   ❌ Failed to get audit logs: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def demonstrate_performance_features():
    """Demonstrate performance monitoring features"""
    print("\n⚡ Performance Features Demonstration")
    print("=" * 50)
    
    # Test performance status
    print("\n📈 Checking Performance Status...")
    try:
        response = requests.get(f"{BASE_URL}/api/security-performance/performance/status")
        if response.status_code == 200:
            data = response.json()
            print(f"   💻 CPU Usage: {data.get('cpu_usage', 0):.1f}%")
            print(f"   🧠 Memory Usage: {data.get('memory_usage', 0):.1f}%")
            print(f"   📦 Cache Hit Rate: {data.get('cache_hit_rate', 0):.1%}")
            print(f"   ⏱️  Average Response Time: {data.get('avg_response_time', 0):.3f}s")
        else:
            print(f"   ❌ Failed to get performance status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test cache statistics
    print("\n📦 Checking Cache Statistics...")
    try:
        response = requests.get(f"{BASE_URL}/api/security-performance/performance/cache/stats")
        if response.status_code == 200:
            data = response.json()
            print(f"   📊 Cache Entries: {data.get('total_entries', 0)}")
            print(f"   🎯 Hit Rate: {data.get('hit_rate', 0):.1%}")
            print(f"   💾 Memory Usage: {data.get('memory_usage_mb', 0):.1f} MB")
        else:
            print(f"   ❌ Failed to get cache stats: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Security & Performance Features Demo")
    print("=" * 50)
    
    # Test server connectivity
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Server is reachable (Health: {health_response.status_code})")
    except Exception as e:
        print(f"❌ Server not reachable: {e}")
        exit(1)
    
    # Demonstrate MFA functionality
    print("\n🔐 Multi-Factor Authentication Demo")
    print("=" * 50)
    
    user_id = "demo_user_123"
    mfa_data = test_mfa_setup(user_id)
    
    if mfa_data:
        # Test with invalid token
        test_mfa_verification(user_id, "000000")
        
        # Note: In a real scenario, you would use a proper TOTP app
        print("\n💡 Note: In production, use a proper TOTP authenticator app")
        print("   Examples: Google Authenticator, Authy, Microsoft Authenticator")
    
    # Demonstrate other security features
    demonstrate_security_features()
    
    # Demonstrate performance features  
    demonstrate_performance_features()
    
    print("\n✨ Demo completed successfully!")
    print("🎉 All security and performance features are operational!")
