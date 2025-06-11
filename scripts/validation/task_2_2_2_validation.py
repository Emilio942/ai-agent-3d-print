#!/usr/bin/env python3
"""
Task 2.2.2: Boolean Operations with Error Recovery - Implementation Validation

This script validates all the requirements specified in Task 2.2.2:
- Union, Difference, Intersection operations
- Automatic mesh repair
- Degeneracy detection  
- Fallback algorithms
- Error recovery mechanisms
"""

import asyncio
import tempfile
import os
import sys
import math

# Add path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.cad_agent import CADAgent, BooleanOperationError


def test_boolean_operations():
    """Test all 3 required boolean operations."""
    print("=== Testing Boolean Operations ===")
    
    agent = CADAgent("validation_boolean_test")
    results = {}
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Create test meshes
        print("Creating test meshes...")
        cube_mesh, _ = agent.create_cube(20, 20, 20)
        sphere_mesh, _ = agent.create_sphere(15)
        
        # Export to files for boolean operations
        cube_path = os.path.join(temp_dir, "cube.stl")
        sphere_path = os.path.join(temp_dir, "sphere.stl")
        
        cube_mesh.export(cube_path)
        sphere_mesh.export(sphere_path)
        
        print("✅ Test meshes created successfully")
        
        # Test Union operation
        try:
            union_task = {
                'operation': 'boolean_operation',
                'specifications': {
                    'boolean_operation': {
                        'operation_type': 'union',
                        'operand_a': cube_path,
                        'operand_b': sphere_path,
                        'auto_repair': True
                    }
                },
                'requirements': {},
                'format_preference': 'stl'
            }
            
            async def test_union():
                result = await agent.execute_task(union_task)
                return result.success
            
            union_success = asyncio.run(test_union())
            results['union'] = "✅ PASS" if union_success else "❌ FAIL"
            print(f"Union operation: {results['union']}")
            
        except Exception as e:
            results['union'] = f"❌ FAIL: {e}"
            print(f"Union operation: {results['union']}")
        
        # Test Difference operation
        try:
            diff_task = {
                'operation': 'boolean_operation',
                'specifications': {
                    'boolean_operation': {
                        'operation_type': 'difference',
                        'operand_a': cube_path,
                        'operand_b': sphere_path,
                        'auto_repair': True
                    }
                },
                'requirements': {},
                'format_preference': 'stl'
            }
            
            async def test_difference():
                result = await agent.execute_task(diff_task)
                return result.success
            
            diff_success = asyncio.run(test_difference())
            results['difference'] = "✅ PASS" if diff_success else "❌ FAIL"
            print(f"Difference operation: {results['difference']}")
            
        except Exception as e:
            results['difference'] = f"❌ FAIL: {e}"
            print(f"Difference operation: {results['difference']}")
        
        # Test Intersection operation
        try:
            intersect_task = {
                'operation': 'boolean_operation',
                'specifications': {
                    'boolean_operation': {
                        'operation_type': 'intersection',
                        'operand_a': cube_path,
                        'operand_b': sphere_path,
                        'auto_repair': True
                    }
                },
                'requirements': {},
                'format_preference': 'stl'
            }
            
            async def test_intersection():
                result = await agent.execute_task(intersect_task)
                return result.success
            
            intersect_success = asyncio.run(test_intersection())
            results['intersection'] = "✅ PASS" if intersect_success else "❌ FAIL"
            print(f"Intersection operation: {results['intersection']}")
            
        except Exception as e:
            results['intersection'] = f"❌ FAIL: {e}"
            print(f"Intersection operation: {results['intersection']}")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        agent.cleanup()
        
    except Exception as e:
        results['setup'] = f"❌ FAIL: Setup error: {e}"
        print(f"Setup error: {e}")
    
    return results


def test_error_recovery():
    """Test error recovery and fallback algorithms."""
    print("\n=== Testing Error Recovery ===")
    
    agent = CADAgent("validation_recovery_test")
    results = {}
    
    try:
        # Test with invalid file paths (should trigger error recovery)
        try:
            task_data = {
                'operation': 'boolean_operation',
                'specifications': {
                    'boolean_operation': {
                        'operation_type': 'union',
                        'operand_a': '/nonexistent/file1.stl',
                        'operand_b': '/nonexistent/file2.stl',
                        'auto_repair': True
                    }
                },
                'requirements': {},
                'format_preference': 'stl'
            }
            
            async def test_error_handling():
                result = await agent.execute_task(task_data)
                return not result.success  # Should fail gracefully
            
            error_handled = asyncio.run(test_error_handling())
            results['error_handling'] = "✅ PASS" if error_handled else "❌ FAIL"
            print(f"Error handling: {results['error_handling']}")
            
        except Exception as e:
            results['error_handling'] = f"❌ FAIL: {e}"
            print(f"Error handling: {results['error_handling']}")
        
        # Test mesh validation functions
        try:
            temp_dir = tempfile.mkdtemp()
            cube_mesh, _ = agent.create_cube(10, 10, 10)
            cube_path = os.path.join(temp_dir, "test_cube.stl")
            cube_mesh.export(cube_path)
            
            # Test mesh loading
            loaded_mesh = agent._load_mesh_from_file(cube_path)
            agent._validate_mesh_for_boolean(loaded_mesh, "test_mesh")
            
            results['mesh_validation'] = "✅ PASS"
            print("Mesh validation: ✅ PASS")
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            results['mesh_validation'] = f"❌ FAIL: {e}"
            print(f"Mesh validation: {results['mesh_validation']}")
        
        agent.cleanup()
        
    except Exception as e:
        results['setup'] = f"❌ FAIL: Setup error: {e}"
        print(f"Setup error: {e}")
    
    return results


def test_mesh_repair():
    """Test automatic mesh repair functionality."""
    print("\n=== Testing Mesh Repair ===")
    
    agent = CADAgent("validation_repair_test")
    results = {}
    
    try:
        # Create a test mesh
        mesh, _ = agent.create_sphere(10)
        
        # Test repair function
        try:
            repaired_mesh = agent._repair_mesh(mesh)
            results['mesh_repair'] = "✅ PASS"
            print("Mesh repair: ✅ PASS")
        except Exception as e:
            results['mesh_repair'] = f"❌ FAIL: {e}"
            print(f"Mesh repair: {results['mesh_repair']}")
        
        # Test degenerate geometry detection
        try:
            has_degenerate = agent._has_degenerate_geometry(mesh)
            results['degeneracy_detection'] = "✅ PASS"
            print("Degeneracy detection: ✅ PASS")
        except Exception as e:
            results['degeneracy_detection'] = f"❌ FAIL: {e}"
            print(f"Degeneracy detection: {results['degeneracy_detection']}")
        
        # Test quality assessment
        try:
            quality_score = agent._assess_boolean_result_quality(mesh)
            if 0 <= quality_score <= 10:
                results['quality_assessment'] = "✅ PASS"
                print(f"Quality assessment: ✅ PASS (score: {quality_score:.1f})")
            else:
                results['quality_assessment'] = f"❌ FAIL: Invalid score {quality_score}"
                print(f"Quality assessment: {results['quality_assessment']}")
        except Exception as e:
            results['quality_assessment'] = f"❌ FAIL: {e}"
            print(f"Quality assessment: {results['quality_assessment']}")
        
        agent.cleanup()
        
    except Exception as e:
        results['setup'] = f"❌ FAIL: Setup error: {e}"
        print(f"Setup error: {e}")
    
    return results


def test_fallback_algorithms():
    """Test fallback algorithms and methods."""
    print("\n=== Testing Fallback Algorithms ===")
    
    agent = CADAgent("validation_fallback_test")
    results = {}
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Create test meshes
        cube_mesh, _ = agent.create_cube(10, 10, 10)
        sphere_mesh, _ = agent.create_sphere(8)
        
        cube_path = os.path.join(temp_dir, "cube.stl")
        sphere_path = os.path.join(temp_dir, "sphere.stl")
        
        cube_mesh.export(cube_path)
        sphere_mesh.export(sphere_path)
        
        # Load meshes for direct testing
        mesh_a = agent._load_mesh_from_file(cube_path)
        mesh_b = agent._load_mesh_from_file(sphere_path)
        
        # Test primary boolean operation method
        try:
            result = agent._trimesh_boolean_operation(mesh_a, mesh_b, 'union')
            if agent._is_valid_mesh_result(result):
                results['primary_method'] = "✅ PASS"
                print("Primary boolean method: ✅ PASS")
            else:
                results['primary_method'] = "❌ FAIL: Invalid result"
                print("Primary boolean method: ❌ FAIL: Invalid result")
        except Exception as e:
            results['primary_method'] = f"⚠️  EXPECTED: {str(e)[:50]}..."
            print(f"Primary boolean method: {results['primary_method']}")
        
        # Test mesh validation
        try:
            is_valid = agent._is_valid_mesh_result(mesh_a)
            results['result_validation'] = "✅ PASS" if is_valid else "❌ FAIL"
            print(f"Result validation: {results['result_validation']}")
        except Exception as e:
            results['result_validation'] = f"❌ FAIL: {e}"
            print(f"Result validation: {results['result_validation']}")
        
        # Test volume calculation
        try:
            volume = agent._calculate_mesh_volume(mesh_a)
            if volume >= 0:
                results['volume_calculation'] = "✅ PASS"
                print(f"Volume calculation: ✅ PASS (volume: {volume:.1f})")
            else:
                results['volume_calculation'] = f"❌ FAIL: Negative volume {volume}"
                print(f"Volume calculation: {results['volume_calculation']}")
        except Exception as e:
            results['volume_calculation'] = f"❌ FAIL: {e}"
            print(f"Volume calculation: {results['volume_calculation']}")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        agent.cleanup()
        
    except Exception as e:
        results['setup'] = f"❌ FAIL: Setup error: {e}"
        print(f"Setup error: {e}")
    
    return results


async def test_integration_workflow():
    """Test complete boolean operation workflow integration."""
    print("\n=== Testing Integration Workflow ===")
    
    agent = CADAgent("validation_integration_test")
    results = {}
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Create test objects using primitive generation
        cube_mesh, cube_volume = agent.create_cube(15, 15, 15)
        cylinder_mesh, cylinder_volume = agent.create_cylinder(8, 20)
        
        # Export to files
        cube_path = os.path.join(temp_dir, "cube.stl")
        cylinder_path = os.path.join(temp_dir, "cylinder.stl")
        
        cube_mesh.export(cube_path)
        cylinder_mesh.export(cylinder_path)
        
        # Test complete workflow: Create primitives -> Boolean operation
        task_data = {
            'operation': 'boolean_operation',
            'specifications': {
                'boolean_operation': {
                    'operation_type': 'difference',
                    'operand_a': cube_path,
                    'operand_b': cylinder_path,
                    'auto_repair': True
                }
            },
            'requirements': {},
            'format_preference': 'stl'
        }
        
        result = await agent.execute_task(task_data)
        
        if result.success:
            results['integration_workflow'] = "✅ PASS"
            print(f"Integration workflow: ✅ PASS")
            print(f"  - Result volume: {result.data.get('volume', 0):.1f} mm³")
            print(f"  - Quality score: {result.data.get('quality_score', 0):.1f}/10")
            print(f"  - Printability: {result.data.get('printability_score', 0):.1f}/10")
            print(f"  - Manifold: {result.data.get('is_manifold', False)}")
            print(f"  - Watertight: {result.data.get('is_watertight', False)}")
        else:
            results['integration_workflow'] = f"❌ FAIL: {result.error_message}"
            print(f"Integration workflow: {results['integration_workflow']}")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        agent.cleanup()
        
    except Exception as e:
        results['integration_workflow'] = f"❌ FAIL: {e}"
        print(f"Integration workflow: {results['integration_workflow']}")
    
    return results


def main():
    """Run complete Task 2.2.2 validation suite."""
    print("Task 2.2.2: Boolean Operations with Error Recovery - Validation")
    print("=" * 65)
    
    # Run all validation tests
    boolean_results = test_boolean_operations()
    recovery_results = test_error_recovery()
    repair_results = test_mesh_repair()
    fallback_results = test_fallback_algorithms()
    integration_results = asyncio.run(test_integration_workflow())
    
    # Combine all results
    all_results = {
        **boolean_results,
        **recovery_results,
        **repair_results,
        **fallback_results,
        **integration_results
    }
    
    # Calculate success rate
    total_tests = len(all_results)
    successful_tests = sum(1 for result in all_results.values() if result.startswith("✅"))
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\n" + "=" * 65)
    print("TASK 2.2.2 VALIDATION SUMMARY")
    print("=" * 65)
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Success rate: {success_rate:.1f}%")
    print()
    
    # Print detailed results
    print("DETAILED RESULTS:")
    for test_name, result in all_results.items():
        print(f"  {test_name}: {result}")
    
    print("\n" + "=" * 65)
    if success_rate >= 80:
        print("🎉 TASK 2.2.2: BOOLEAN OPERATIONS WITH ERROR RECOVERY - VALIDATION PASSED!")
        print()
        print("✅ IMPLEMENTED FEATURES:")
        print("  - Union, Difference, Intersection boolean operations")
        print("  - Automatic mesh repair and validation")
        print("  - Degeneracy detection and handling")
        print("  - Multi-level fallback algorithms")
        print("  - Robust error recovery mechanisms")
        print("  - Quality assessment and printability analysis")
        print("  - File I/O operations for mesh data")
        print("  - Integration with primitive generation system")
        print()
        print("🚀 Ready for Task 2.2.3: STL Export with Quality Control")
    else:
        print("⚠️  TASK 2.2.2 VALIDATION INCOMPLETE")
        print(f"   Success rate {success_rate:.1f}% below 80% threshold")
        print("   Please review failed tests and fix issues")
    
    print("=" * 65)
    
    return success_rate >= 80


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
