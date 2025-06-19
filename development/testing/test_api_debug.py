#!/usr/bin/env python3
"""
Debug script to test API startup and identify hanging issues.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_initialization():
    """Test ParentAgent initialization step by step."""
    print("=== API Debug Test ===")
    
    try:
        print("1. Testing ParentAgent import...")
        from core.parent_agent import ParentAgent
        print("✓ ParentAgent imported successfully")
        
        print("2. Creating ParentAgent instance...")
        parent_agent = ParentAgent()
        print("✓ ParentAgent instance created")
        
        print("3. Testing ParentAgent initialization...")
        await parent_agent.initialize()
        print("✓ ParentAgent initialized successfully")
        
        print("4. Testing basic health check...")
        status = parent_agent.get_status()
        print(f"✓ Agent status: {status}")
        
        print("5. Testing agent functionality...")
        # Simple test workflow
        test_result = await parent_agent.execute_research_workflow({
            "user_request": "simple cube",  # Fixed parameter name
            "requirements": "small test object"
        })
        print(f"✓ Test workflow completed: {test_result.success}")
        
        print("6. Cleanup...")
        await parent_agent.shutdown()
        print("✓ Cleanup completed")
        
        print("\n=== All tests passed! ===")
        return True
        
    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_initialization())
    sys.exit(0 if success else 1)
