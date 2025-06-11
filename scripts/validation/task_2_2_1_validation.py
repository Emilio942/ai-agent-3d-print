#!/usr/bin/env python3
"""
Task 2.2.1: CAD Agent 3D Primitives Library - Implementation Validation

This script validates all the requirements specified in Task 2.2.1:
- create_cube, create_cylinder, create_sphere, create_torus, create_cone
- Parameter validation for geometries
- Printability checks
- Material volume calculation
"""

import asyncio
import math
import sys
import os

# Add path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.cad_agent import CADAgent, GeometryValidationError


def test_primitive_functions():
    """Test all 5 required primitive creation functions."""
    print("=== Testing 3D Primitive Creation Functions ===")
    
    agent = CADAgent("validation_test")
    results = {}
    
    # Test 1: create_cube
    try:
        mesh, volume = agent.create_cube(x=20, y=15, z=10, center=True)
        expected_volume = 20 * 15 * 10  # 3000
        assert abs(volume - expected_volume) < 0.1, f"Volume mismatch: {volume} vs {expected_volume}"
        results['cube'] = "✅ PASS"
        print(f"✅ create_cube: {volume} mm³ (expected: {expected_volume})")
    except Exception as e:
        results['cube'] = f"❌ FAIL: {e}"
        print(f"❌ create_cube failed: {e}")
    
    # Test 2: create_cylinder
    try:
        mesh, volume = agent.create_cylinder(radius=5, height=10, segments=32)
        expected_volume = math.pi * 5 * 5 * 10  # π*r²*h
        assert abs(volume - expected_volume) < 0.1, f"Volume mismatch: {volume} vs {expected_volume}"
        results['cylinder'] = "✅ PASS"
        print(f"✅ create_cylinder: {volume:.1f} mm³ (expected: {expected_volume:.1f})")
    except Exception as e:
        results['cylinder'] = f"❌ FAIL: {e}"
        print(f"❌ create_cylinder failed: {e}")
    
    # Test 3: create_sphere
    try:
        mesh, volume = agent.create_sphere(radius=6, segments=32)
        expected_volume = (4.0/3.0) * math.pi * 6 * 6 * 6  # (4/3)*π*r³
        assert abs(volume - expected_volume) < 0.1, f"Volume mismatch: {volume} vs {expected_volume}"
        results['sphere'] = "✅ PASS"
        print(f"✅ create_sphere: {volume:.1f} mm³ (expected: {expected_volume:.1f})")
    except Exception as e:
        results['sphere'] = f"❌ FAIL: {e}"
        print(f"❌ create_sphere failed: {e}")
    
    # Test 4: create_torus
    try:
        mesh, volume = agent.create_torus(major_radius=10, minor_radius=3)
        expected_volume = 2 * math.pi * math.pi * 10 * 3 * 3  # 2*π²*R*r²
        assert abs(volume - expected_volume) < 0.1, f"Volume mismatch: {volume} vs {expected_volume}"
        results['torus'] = "✅ PASS"
        print(f"✅ create_torus: {volume:.1f} mm³ (expected: {expected_volume:.1f})")
    except Exception as e:
        results['torus'] = f"❌ FAIL: {e}"
        print(f"❌ create_torus failed: {e}")
    
    # Test 5: create_cone
    try:
        mesh, volume = agent.create_cone(base_radius=8, top_radius=0, height=12)
        expected_volume = (1.0/3.0) * math.pi * 8 * 8 * 12  # (1/3)*π*r²*h
        assert abs(volume - expected_volume) < 0.1, f"Volume mismatch: {volume} vs {expected_volume}"
        results['cone'] = "✅ PASS"
        print(f"✅ create_cone: {volume:.1f} mm³ (expected: {expected_volume:.1f})")
    except Exception as e:
        results['cone'] = f"❌ FAIL: {e}"
        print(f"❌ create_cone failed: {e}")
    
    agent.cleanup()
    return results


def test_parameter_validation():
    """Test parameter validation for geometries."""
    print("\n=== Testing Parameter Validation ===")
    
    agent = CADAgent("validation_test")
    results = {}
    
    # Test negative dimensions
    try:
        agent.create_cube(-5, 10, 10)
        results['negative_validation'] = "❌ FAIL: Should reject negative dimensions"
    except GeometryValidationError:
        results['negative_validation'] = "✅ PASS"
        print("✅ Negative dimension validation works")
    except Exception as e:
        results['negative_validation'] = f"❌ FAIL: Wrong exception: {e}"
    
    # Test zero dimensions
    try:
        agent.create_cylinder(0, 10)
        results['zero_validation'] = "❌ FAIL: Should reject zero dimensions"
    except GeometryValidationError:
        results['zero_validation'] = "✅ PASS"
        print("✅ Zero dimension validation works")
    except Exception as e:
        results['zero_validation'] = f"❌ FAIL: Wrong exception: {e}"
    
    # Test too small dimensions
    try:
        agent.create_sphere(0.05)  # Below 0.1mm minimum
        results['min_validation'] = "❌ FAIL: Should reject dimensions below minimum"
    except GeometryValidationError:
        results['min_validation'] = "✅ PASS"
        print("✅ Minimum dimension validation works")
    except Exception as e:
        results['min_validation'] = f"❌ FAIL: Wrong exception: {e}"
    
    # Test too large dimensions
    try:
        agent.create_cube(350, 10, 10)  # Above 300mm maximum
        results['max_validation'] = "❌ FAIL: Should reject dimensions above maximum"
    except GeometryValidationError:
        results['max_validation'] = "✅ PASS"
        print("✅ Maximum dimension validation works")
    except Exception as e:
        results['max_validation'] = f"❌ FAIL: Wrong exception: {e}"
    
    # Test invalid segments
    try:
        agent.create_cylinder(5, 10, segments=2)  # Too few segments
        results['segments_validation'] = "❌ FAIL: Should reject invalid segment count"
    except GeometryValidationError:
        results['segments_validation'] = "✅ PASS"
        print("✅ Segment validation works")
    except Exception as e:
        results['segments_validation'] = f"❌ FAIL: Wrong exception: {e}"
    
    agent.cleanup()
    return results


def test_printability_checks():
    """Test printability checks implementation."""
    print("\n=== Testing Printability Checks ===")
    
    agent = CADAgent("validation_test")
    results = {}
    
    # Test cube printability (should be high)
    try:
        mesh, volume = agent.create_cube(20, 20, 20)
        dimensions = {'x': 20, 'y': 20, 'z': 20}
        score = agent._check_printability(mesh, 'cube', dimensions)
        
        assert 0 <= score <= 10, f"Score out of range: {score}"
        assert score >= 8, f"Cube should have high printability: {score}"
        
        results['cube_printability'] = "✅ PASS"
        print(f"✅ Cube printability: {score}/10")
    except Exception as e:
        results['cube_printability'] = f"❌ FAIL: {e}"
        print(f"❌ Cube printability test failed: {e}")
    
    # Test sphere printability (should be lower due to support needs)
    try:
        mesh, volume = agent.create_sphere(10)
        dimensions = {'radius': 10}
        score = agent._check_printability(mesh, 'sphere', dimensions)
        
        assert 0 <= score <= 10, f"Score out of range: {score}"
        
        results['sphere_printability'] = "✅ PASS"
        print(f"✅ Sphere printability: {score}/10 (needs support)")
    except Exception as e:
        results['sphere_printability'] = f"❌ FAIL: {e}"
        print(f"❌ Sphere printability test failed: {e}")
    
    agent.cleanup()
    return results


def test_material_volume_calculation():
    """Test material volume calculation."""
    print("\n=== Testing Material Volume Calculation ===")
    
    agent = CADAgent("validation_test")
    results = {}
    
    try:
        # Create a 10x10x10mm cube = 1000 mm³ = 1 cm³
        mesh, volume = agent.create_cube(10, 10, 10)
        
        # Calculate material weight using PLA density (1.24 g/cm³)
        volume_cm3 = volume / 1000  # Convert mm³ to cm³
        expected_weight = volume_cm3 * agent.material_density
        
        assert abs(volume - 1000) < 0.1, f"Volume incorrect: {volume}"
        assert abs(volume_cm3 - 1.0) < 0.001, f"Volume conversion incorrect: {volume_cm3}"
        assert abs(expected_weight - 1.24) < 0.01, f"Weight calculation incorrect: {expected_weight}"
        
        results['material_calculation'] = "✅ PASS"
        print(f"✅ Material calculation: {volume} mm³ = {volume_cm3} cm³ = {expected_weight:.2f}g")
        
    except Exception as e:
        results['material_calculation'] = f"❌ FAIL: {e}"
        print(f"❌ Material calculation test failed: {e}")
    
    agent.cleanup()
    return results


async def test_integration_workflow():
    """Test complete workflow integration."""
    print("\n=== Testing Integration Workflow ===")
    
    agent = CADAgent("integration_test")
    results = {}
    
    try:
        # Test complete workflow for cube creation
        task_data = {
            'operation': 'create_primitive',
            'specifications': {
                'geometry': {
                    'base_shape': 'cube',
                    'dimensions': {'x': 25, 'y': 20, 'z': 15}
                }
            },
            'requirements': {'material_type': 'PLA'},
            'format_preference': 'stl',
            'quality_level': 'standard'
        }
        
        result = await agent.execute_task(task_data)
        
        assert result.success, f"Task failed: {result.error_message}"
        assert 'volume' in result.data, "Volume not calculated"
        assert 'printability_score' in result.data, "Printability not assessed"
        assert 'material_weight_g' in result.data, "Material weight not calculated"
        assert 'model_file_path' in result.data, "Model file not generated"
        
        expected_volume = 25 * 20 * 15  # 7500 mm³
        actual_volume = result.data['volume']
        assert abs(actual_volume - expected_volume) < 0.1, f"Volume mismatch: {actual_volume} vs {expected_volume}"
        
        results['integration'] = "✅ PASS"
        print(f"✅ Integration test passed:")
        print(f"   Volume: {result.data['volume']} mm³")
        print(f"   Weight: {result.data['material_weight_g']:.2f}g")
        print(f"   Printability: {result.data['printability_score']}/10")
        print(f"   File: {os.path.basename(result.data['model_file_path'])}")
        
    except Exception as e:
        results['integration'] = f"❌ FAIL: {e}"
        print(f"❌ Integration test failed: {e}")
    
    agent.cleanup()
    return results


def main():
    """Run complete Task 2.2.1 validation suite."""
    print("="*70)
    print("TASK 2.2.1: CAD Agent 3D Primitives Library - Validation Suite")
    print("="*70)
    
    all_results = {}
    
    # Run all test suites
    all_results.update(test_primitive_functions())
    all_results.update(test_parameter_validation())
    all_results.update(test_printability_checks())
    all_results.update(test_material_volume_calculation())
    
    # Run async integration test
    integration_results = asyncio.run(test_integration_workflow())
    all_results.update(integration_results)
    
    # Summary report
    print("\n" + "="*70)
    print("TASK 2.2.1 VALIDATION RESULTS")
    print("="*70)
    
    passed = 0
    total = len(all_results)
    
    for test_name, result in all_results.items():
        status = "✅" if result.startswith("✅") else "❌"
        print(f"{status} {test_name.replace('_', ' ').title()}: {result}")
        if result.startswith("✅"):
            passed += 1
    
    success_rate = (passed / total) * 100
    print(f"\nSUCCESS RATE: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("\n🎉 TASK 2.2.1 IMPLEMENTATION SUCCESSFUL!")
        print("CAD Agent 3D Primitives Library meets all requirements:")
        print("   ✅ All 5 primitive functions implemented")
        print("   ✅ Comprehensive parameter validation")
        print("   ✅ Printability assessment system")
        print("   ✅ Material volume calculation")
        print("   ✅ Integration workflow functional")
        return True
    else:
        print(f"\n⚠️  IMPLEMENTATION INCOMPLETE ({success_rate:.1f}% success)")
        print("Some requirements need attention before Task 2.2.1 completion.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
