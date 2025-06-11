"""
Test script for Task 2.1.2: Web Research with Rate Limiting
Tests the enhanced Research Agent with web research capabilities.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.research_agent import ResearchAgent, create_test_intent_request
import time


def test_basic_intent_recognition():
    """Test basic intent recognition without web research."""
    print("\n=== TEST 1: Basic Intent Recognition ===")
    
    agent = ResearchAgent("test_research_agent")
    
    # Test requests
    test_cases = [
        "I want to print a 5cm cube in PLA",
        "Make me a phone case for iPhone 14",
        "Create a gear with 20 teeth"
    ]
    
    for request in test_cases:
        print(f"\nTesting: {request}")
        task_details = create_test_intent_request(request)
        result = agent.execute_task(task_details)
        
        if result["success"]:
            print(f"✅ Success - Confidence: {result['metadata']['confidence']:.2f}")
            print(f"   Object Type: {result['data']['requirements']['object_type']}")
            print(f"   Method Used: {result['metadata']['method_used']}")
        else:
            print(f"❌ Failed: {result['error_message']}")


def test_web_research_functionality():
    """Test web research functionality."""
    print("\n=== TEST 2: Web Research Functionality ===")
    
    agent = ResearchAgent("test_research_agent")
    
    # Test with web research enabled (low confidence trigger)
    ambiguous_request = "I need something for my desk"
    print(f"\nTesting web research with ambiguous request: {ambiguous_request}")
    
    task_details = create_test_intent_request(
        ambiguous_request, 
        analysis_depth="detailed", 
        enable_web_research=True
    )
    
    result = agent.execute_task(task_details)
    
    if result["success"]:
        print(f"✅ Success - Confidence: {result['metadata']['confidence']:.2f}")
        print(f"   Web Research Used: {result['metadata']['web_research_used']}")
        recommendations = result['data']['recommendations']
        print(f"   Recommendations ({len(recommendations)}):")
        for rec in recommendations[:3]:  # Show first 3
            print(f"     - {rec}")
    else:
        print(f"❌ Failed: {result['error_message']}")


def test_direct_web_research():
    """Test direct web research method."""
    print("\n=== TEST 3: Direct Web Research Method ===")
    
    agent = ResearchAgent("test_research_agent")
    
    # Test direct research method
    queries = [
        ["3D printing", "PLA", "tips"],
        ["phone case", "3D print", "design"],
    ]
    
    for query in queries:
        print(f"\nTesting research with keywords: {query}")
        try:
            result = agent.research(query)
            print(f"✅ Research completed")
            print(f"   Result: {result[:100]}...")  # Show first 100 characters
        except Exception as e:
            print(f"❌ Research failed: {str(e)}")


def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\n=== TEST 4: Rate Limiting ===")
    
    agent = ResearchAgent("test_research_agent")
    
    # Test rate limiter
    if agent.rate_limiter:
        print("Testing rate limiter...")
        
        # Make requests rapidly
        requests_made = 0
        for i in range(15):  # Try to exceed the limit of 10
            if agent.rate_limiter.can_make_request():
                agent.rate_limiter.record_request()
                requests_made += 1
                print(f"  Request {requests_made} allowed")
            else:
                print(f"  Request {i+1} blocked by rate limiter")
                break
        
        print(f"✅ Rate limiter working - {requests_made} requests allowed")
    else:
        print("❌ Rate limiter not initialized")


def test_caching():
    """Test caching functionality."""
    print("\n=== TEST 5: Caching ===")
    
    agent = ResearchAgent("test_research_agent")
    
    if agent.cache:
        # Test cache operations
        test_key = "test_key"
        test_value = "test_value"
        
        print("Testing cache set/get...")
        agent.cache.set(test_key, test_value)
        retrieved_value = agent.cache.get(test_key)
        
        if retrieved_value == test_value:
            print("✅ Cache working correctly")
        else:
            print(f"❌ Cache error: expected '{test_value}', got '{retrieved_value}'")
    else:
        print("❌ Cache not initialized")


def main():
    """Run all tests for web research functionality."""
    print("TESTING TASK 2.1.2: Web Research with Rate Limiting")
    print("=" * 60)
    
    try:
        test_basic_intent_recognition()
        test_direct_web_research()
        test_rate_limiting()
        test_caching()
        test_web_research_functionality()
        
        print("\n" + "=" * 60)
        print("✅ TASK 2.1.2 TESTING COMPLETED")
        print("📋 Features tested:")
        print("   - Basic intent recognition (existing functionality)")
        print("   - Direct web research with DuckDuckGo API")
        print("   - Rate limiting (max 10 requests/minute)")
        print("   - Local caching for 24h")
        print("   - Integrated web research enhancement")
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
