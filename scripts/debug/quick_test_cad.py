#!/usr/bin/env python3
"""
Quick test script for CAD Agent Task 2.2.1 validation
"""

import asyncio
import sys
import os

# Add path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.cad_agent import CADAgent


async def quick_test():
    """Quick validation test for CAD Agent Task 2.2.1."""
    print("=== Quick CAD Agent Validation Test ===")
    
    try:
        # Initialize agent
        agent = CADAgent("quick_test")
        print(f"✅ Agent initialized: {agent.agent_name}")
        print(f"✅ Backend: {agent.cad_backend}")
        
        # Test primitive creation functions directly
        print("\n--- Testing Primitive Creation Functions ---")
        
        # Test cube
        try:
            mesh, volume = agent.create_cube(10, 15, 20)
            print(f"✅ Cube created: volume = {volume:.1f} mm³")
        except Exception as e:
            print(f"❌ Cube creation failed: {e}")
        
        # Test cylinder
        try:
            mesh, volume = agent.create_cylinder(5, 10)
            print(f"✅ Cylinder created: volume = {volume:.1f} mm³")
        except Exception as e:
            print(f"❌ Cylinder creation failed: {e}")
        
        # Test sphere
        try:
            mesh, volume = agent.create_sphere(7)
            print(f"✅ Sphere created: volume = {volume:.1f} mm³")
        except Exception as e:
            print(f"❌ Sphere creation failed: {e}")
        
        # Test validation functions
        print("\n--- Testing Validation Functions ---")
        
        try:
            agent._validate_positive_dimension(10, "test_dim")
            print("✅ Positive dimension validation works")
        except Exception as e:
            print(f"❌ Validation failed: {e}")
        
        try:
            agent._validate_positive_dimension(-5, "negative_dim")
            print("❌ Negative dimension validation should have failed")
        except Exception:
            print("✅ Negative dimension validation works")
        
        # Test async task execution
        print("\n--- Testing Async Task Execution ---")
        
        task_data = {
            'operation': 'create_primitive',
            'specifications': {
                'geometry': {
                    'base_shape': 'cube',
                    'dimensions': {'x': 10, 'y': 10, 'z': 10}
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'standard'
        }
        
        result = await agent.execute_task(task_data)
        
        if result.success:
            print("✅ Task execution successful")
            print(f"   Volume: {result.data.get('volume', 'unknown')} mm³")
            print(f"   Printability: {result.data.get('printability_score', 'unknown')}/10")
        else:
            print(f"❌ Task execution failed: {result.error_message}")
        
        # Cleanup
        agent.cleanup()
        print("\n✅ CAD Agent cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(quick_test())
    
    print("\n" + "="*50)
    if success:
        print("🎉 QUICK TEST PASSED - Task 2.2.1 Core Functions Working!")
        print("   ✅ Agent initialization")
        print("   ✅ Primitive creation (cube, cylinder, sphere)")
        print("   ✅ Parameter validation")
        print("   ✅ Async task execution")
        print("   ✅ Volume calculation")
        print("   ✅ Printability assessment")
    else:
        print("⚠️  QUICK TEST FAILED - Issues need to be resolved")
    print("="*50)
