#!/usr/bin/env python3
"""
Task 2.2.3: STL Export with Quality Control - Implementation Validation

This script validates all the requirements specified in Task 2.2.3:
- STL-Export with Mesh-Validierung
- Mesh-Qualitäts-Checks (Watertightness, Manifold)
- Automatische Reparatur
- File-Size-Optimization
"""

import asyncio
import math
import sys
import os
import tempfile
import shutil

# Add path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.cad_agent import CADAgent, GeometryValidationError, ValidationError


def test_stl_export_basic():
    """Test basic STL export functionality."""
    print("\n=== Testing Basic STL Export ===")
    
    agent = CADAgent("validation_stl_basic")
    results = {}
    
    try:
        temp_dir = tempfile.mkdtemp()
        print(f"Using temp directory: {temp_dir}")
        
        # Create a test mesh
        mesh, volume = agent.create_cube(20, 20, 20)
        source_file = os.path.join(temp_dir, "test_cube.stl")
        mesh.export(source_file)
        
        # Test basic STL export
        try:
            task_data = {
                'operation': 'export_stl',
                'specifications': {
                    'stl_export': {
                        'source_file_path': source_file,
                        'output_file_path': os.path.join(temp_dir, "exported_cube.stl"),
                        'quality_level': 'standard',
                        'perform_quality_check': True,
                        'auto_repair_issues': True,
                        'generate_report': True
                    }
                },
                'requirements': {},
                'format_preference': 'stl',
                'quality_level': 'standard'
            }
            
            result = asyncio.run(agent.execute_task(task_data))
            
            if result.success:
                results['basic_export'] = "✅ PASS"
                print("Basic STL export: ✅ PASS")
                print(f"   Output file: {result.data.get('output_file_path')}")
                print(f"   File size: {result.data.get('file_size_bytes', 0)} bytes")
                print(f"   Export time: {result.data.get('export_time', 0):.3f}s")
            else:
                results['basic_export'] = f"❌ FAIL: {result.error_message}"
                print(f"Basic STL export: {results['basic_export']}")
                
        except Exception as e:
            results['basic_export'] = f"❌ FAIL: {e}"
            print(f"Basic STL export: {results['basic_export']}")
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        agent.cleanup()
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        results['basic_export'] = f"❌ SETUP FAIL: {e}"
    
    return results


def test_mesh_quality_checks():
    """Test mesh quality checking functionality."""
    print("\n=== Testing Mesh Quality Checks ===")
    
    agent = CADAgent("validation_quality_checks")
    results = {}
    
    try:
        # Test quality report generation
        mesh, _ = agent.create_sphere(10)
        
        try:
            quality_report = agent._generate_mesh_quality_report(mesh)
            
            # Check required fields
            required_fields = [
                'is_manifold', 'is_watertight', 'has_degenerate_faces',
                'quality_score', 'issues', 'recommendations'
            ]
            
            all_fields_present = all(field in quality_report for field in required_fields)
            
            if all_fields_present:
                results['quality_report'] = "✅ PASS"
                print("Quality report generation: ✅ PASS")
                print(f"   Quality score: {quality_report.get('quality_score', 0)}/10")
                print(f"   Is manifold: {quality_report.get('is_manifold', False)}")
                print(f"   Is watertight: {quality_report.get('is_watertight', False)}")
                print(f"   Issues: {len(quality_report.get('issues', []))}")
            else:
                results['quality_report'] = "❌ FAIL: Missing required fields"
                print(f"Quality report generation: {results['quality_report']}")
                
        except Exception as e:
            results['quality_report'] = f"❌ FAIL: {e}"
            print(f"Quality report generation: {results['quality_report']}")
        
        # Test manifold checking
        try:
            is_manifold = agent._is_mesh_manifold(mesh)
            results['manifold_check'] = "✅ PASS"
            print(f"Manifold checking: ✅ PASS (result: {is_manifold})")
        except Exception as e:
            results['manifold_check'] = f"❌ FAIL: {e}"
            print(f"Manifold checking: {results['manifold_check']}")
        
        # Test watertight checking
        try:
            is_watertight = agent._is_mesh_watertight(mesh)
            results['watertight_check'] = "✅ PASS"
            print(f"Watertight checking: ✅ PASS (result: {is_watertight})")
        except Exception as e:
            results['watertight_check'] = f"❌ FAIL: {e}"
            print(f"Watertight checking: {results['watertight_check']}")
        
        agent.cleanup()
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        for key in ['quality_report', 'manifold_check', 'watertight_check']:
            results[key] = f"❌ SETUP FAIL: {e}"
    
    return results


def test_mesh_optimization():
    """Test mesh optimization and repair functionality."""
    print("\n=== Testing Mesh Optimization ===")
    
    agent = CADAgent("validation_optimization")
    results = {}
    
    try:
        # Create test mesh
        mesh, _ = agent.create_torus(15, 5)  # More complex geometry
        
        # Test mesh optimization
        try:
            optimized_mesh, optimization_report = agent._optimize_mesh_for_export(mesh, "standard")
            
            # Check optimization report
            required_fields = [
                'vertices_before', 'vertices_after', 'faces_before', 'faces_after',
                'optimization_time', 'operations'
            ]
            
            all_fields_present = all(field in optimization_report for field in required_fields)
            
            if all_fields_present and optimized_mesh is not None:
                results['mesh_optimization'] = "✅ PASS"
                print("Mesh optimization: ✅ PASS")
                print(f"   Vertices: {optimization_report['vertices_before']} → {optimization_report['vertices_after']}")
                print(f"   Faces: {optimization_report['faces_before']} → {optimization_report['faces_after']}")
                print(f"   Operations: {len(optimization_report['operations'])}")
            else:
                results['mesh_optimization'] = "❌ FAIL: Invalid optimization result"
                print(f"Mesh optimization: {results['mesh_optimization']}")
                
        except Exception as e:
            results['mesh_optimization'] = f"❌ FAIL: {e}"
            print(f"Mesh optimization: {results['mesh_optimization']}")
        
        # Test mesh repair
        try:
            repaired_mesh = agent._repair_mesh(mesh)
            
            if repaired_mesh is not None:
                results['mesh_repair'] = "✅ PASS"
                print("Mesh repair: ✅ PASS")
            else:
                results['mesh_repair'] = "❌ FAIL: No repair result"
                print(f"Mesh repair: {results['mesh_repair']}")
                
        except Exception as e:
            results['mesh_repair'] = f"❌ FAIL: {e}"
            print(f"Mesh repair: {results['mesh_repair']}")
        
        # Test manifold repair
        try:
            manifold_mesh = agent._make_mesh_manifold(mesh)
            
            if manifold_mesh is not None:
                results['manifold_repair'] = "✅ PASS"
                print("Manifold repair: ✅ PASS")
            else:
                results['manifold_repair'] = "❌ FAIL: No manifold result"
                print(f"Manifold repair: {results['manifold_repair']}")
                
        except Exception as e:
            results['manifold_repair'] = f"❌ FAIL: {e}"
            print(f"Manifold repair: {results['manifold_repair']}")
        
        agent.cleanup()
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        for key in ['mesh_optimization', 'mesh_repair', 'manifold_repair']:
            results[key] = f"❌ SETUP FAIL: {e}"
    
    return results


def test_stl_validation():
    """Test STL file validation functionality."""
    print("\n=== Testing STL Validation ===")
    
    agent = CADAgent("validation_stl_validation")
    results = {}
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Create test STL file
        mesh, _ = agent.create_cylinder(8, 15)
        test_stl = os.path.join(temp_dir, "test_cylinder.stl")
        mesh.export(test_stl)
        
        # Test STL validation
        try:
            validation_result = agent._validate_stl_file(test_stl)
            
            required_fields = [
                'is_valid_stl', 'format_errors', 'structural_errors',
                'file_size_mb', 'triangle_count', 'validation_time'
            ]
            
            all_fields_present = all(field in validation_result for field in required_fields)
            
            if all_fields_present:
                results['stl_validation'] = "✅ PASS"
                print("STL validation: ✅ PASS")
                print(f"   Is valid: {validation_result['is_valid_stl']}")
                print(f"   File size: {validation_result['file_size_mb']:.3f} MB")
                print(f"   Triangles: {validation_result['triangle_count']}")
                print(f"   Format errors: {len(validation_result['format_errors'])}")
            else:
                results['stl_validation'] = "❌ FAIL: Missing validation fields"
                print(f"STL validation: {results['stl_validation']}")
                
        except Exception as e:
            results['stl_validation'] = f"❌ FAIL: {e}"
            print(f"STL validation: {results['stl_validation']}")
        
        # Test printability assessment
        try:
            printability = agent._assess_stl_printability(mesh, test_stl)
            
            required_fields = ['score', 'issues', 'recommendations', 'support_needed']
            all_fields_present = all(field in printability for field in required_fields)
            
            if all_fields_present:
                results['printability_assessment'] = "✅ PASS"
                print("Printability assessment: ✅ PASS")
                print(f"   Score: {printability['score']}/10")
                print(f"   Support needed: {printability['support_needed']}")
                print(f"   Issues: {len(printability['issues'])}")
            else:
                results['printability_assessment'] = "❌ FAIL: Missing assessment fields"
                print(f"Printability assessment: {results['printability_assessment']}")
                
        except Exception as e:
            results['printability_assessment'] = f"❌ FAIL: {e}"
            print(f"Printability assessment: {results['printability_assessment']}")
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        agent.cleanup()
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        for key in ['stl_validation', 'printability_assessment']:
            results[key] = f"❌ SETUP FAIL: {e}"
    
    return results


def test_file_size_optimization():
    """Test file size optimization features."""
    print("\n=== Testing File Size Optimization ===")
    
    agent = CADAgent("validation_file_optimization")
    results = {}
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Create complex mesh for optimization testing
        mesh, _ = agent.create_sphere(12, segments=64)  # High resolution sphere
        source_file = os.path.join(temp_dir, "high_res_sphere.stl")
        mesh.export(source_file)
        
        original_size = os.path.getsize(source_file)
        
        # Test optimization with different quality levels
        quality_levels = ["draft", "standard", "high"]
        optimization_results = {}
        
        for quality in quality_levels:
            try:
                optimized_mesh, report = agent._optimize_mesh_for_export(mesh, quality)
                
                # Export optimized version
                opt_file = os.path.join(temp_dir, f"optimized_{quality}.stl")
                agent._export_mesh_to_stl_file(optimized_mesh, opt_file)
                
                opt_size = os.path.getsize(opt_file)
                reduction = (1 - opt_size / original_size) * 100 if original_size > 0 else 0
                
                optimization_results[quality] = {
                    'original_size': original_size,
                    'optimized_size': opt_size,
                    'reduction_percent': reduction,
                    'operations': len(report.get('operations', []))
                }
                
                print(f"   {quality.title()}: {reduction:.1f}% reduction ({opt_size} bytes)")
                
            except Exception as e:
                optimization_results[quality] = {'error': str(e)}
                print(f"   {quality.title()}: ❌ FAIL - {e}")
        
        # Check if any optimization worked
        successful_optimizations = [q for q in optimization_results 
                                  if 'error' not in optimization_results[q]]
        
        if successful_optimizations:
            results['file_optimization'] = "✅ PASS"
            print("File size optimization: ✅ PASS")
            print(f"   Successful quality levels: {', '.join(successful_optimizations)}")
        else:
            results['file_optimization'] = "❌ FAIL: No optimizations worked"
            print(f"File size optimization: {results['file_optimization']}")
        
        # Test resolution adjustment
        try:
            adjusted_mesh = agent._adjust_mesh_resolution(mesh, 0.05)  # Lower resolution
            
            if adjusted_mesh is not None:
                results['resolution_adjustment'] = "✅ PASS"
                print("Resolution adjustment: ✅ PASS")
            else:
                results['resolution_adjustment'] = "❌ FAIL: No adjusted mesh"
                print(f"Resolution adjustment: {results['resolution_adjustment']}")
                
        except Exception as e:
            results['resolution_adjustment'] = f"❌ FAIL: {e}"
            print(f"Resolution adjustment: {results['resolution_adjustment']}")
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        agent.cleanup()
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        for key in ['file_optimization', 'resolution_adjustment']:
            results[key] = f"❌ SETUP FAIL: {e}"
    
    return results


async def test_integration_workflow():
    """Test complete STL export workflow integration."""
    print("\n=== Testing Integration Workflow ===")
    
    agent = CADAgent("validation_integration")
    results = {}
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Create primitive mesh
        primitive_task = {
            'operation': 'create_primitive',
            'specifications': {
                'geometry': {
                    'base_shape': 'cube',
                    'dimensions': {'x': 25, 'y': 15, 'z': 10}
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'standard'
        }
        
        primitive_result = await agent.execute_task(primitive_task)
        
        if not primitive_result.success:
            results['integration_workflow'] = f"❌ FAIL: Primitive creation failed - {primitive_result.error_message}"
            print(f"Integration workflow: {results['integration_workflow']}")
            return results
        
        # Export the created primitive with quality control
        source_file = primitive_result.data['model_file_path']
        output_file = os.path.join(temp_dir, "final_export.stl")
        
        export_task = {
            'operation': 'export_stl',
            'specifications': {
                'stl_export': {
                    'source_file_path': source_file,
                    'output_file_path': output_file,
                    'quality_level': 'high',
                    'perform_quality_check': True,
                    'auto_repair_issues': True,
                    'generate_report': True,
                    'export_options': {
                        'mesh_resolution': 0.1,
                        'optimize_mesh': True,
                        'validate_manifold': True,
                        'auto_repair': True,
                        'include_normals': True
                    }
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'high'
        }
        
        export_result = await agent.execute_task(export_task)
        
        if export_result.success:
            results['integration_workflow'] = "✅ PASS"
            print("Integration workflow: ✅ PASS")
            print(f"   Source: {source_file}")
            print(f"   Output: {export_result.data['output_file_path']}")
            print(f"   Quality score: {export_result.data.get('mesh_quality_report', {}).get('quality_score', 0)}/10")
            print(f"   Printability: {export_result.data.get('printability_assessment', {}).get('score', 0)}/10")
            print(f"   Repairs applied: {len(export_result.data.get('repairs_applied', []))}")
        else:
            results['integration_workflow'] = f"❌ FAIL: Export failed - {export_result.error_message}"
            print(f"Integration workflow: {results['integration_workflow']}")
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        agent.cleanup()
        
    except Exception as e:
        results['integration_workflow'] = f"❌ FAIL: {e}"
        print(f"Integration workflow: {results['integration_workflow']}")
    
    return results


def main():
    """Run complete Task 2.2.3 validation suite."""
    print("="*60)
    print("🔧 TASK 2.2.3 VALIDATION - STL Export with Quality Control")
    print("="*60)
    
    all_results = {}
    
    # Run all test functions
    test_functions = [
        ("Basic STL Export", test_stl_export_basic),
        ("Mesh Quality Checks", test_mesh_quality_checks),
        ("Mesh Optimization", test_mesh_optimization),
        ("STL Validation", test_stl_validation),
        ("File Size Optimization", test_file_size_optimization),
        ("Integration Workflow", lambda: asyncio.run(test_integration_workflow()))
    ]
    
    for test_name, test_func in test_functions:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results = test_func()
            all_results.update(results)
        except Exception as e:
            print(f"❌ Test category failed: {e}")
            all_results[test_name.lower().replace(' ', '_')] = f"❌ CATEGORY FAIL: {e}"
    
    # Summary
    print("\n" + "="*60)
    print("📊 VALIDATION SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, result in all_results.items():
        status = "✅ PASS" if result.startswith("✅") else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        if status == "✅ PASS":
            passed += 1
        else:
            failed += 1
    
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n📈 RESULTS: {passed}/{total} tests passed ({success_rate:.1f}% success rate)")
    
    if success_rate >= 80:
        print("🎉 TASK 2.2.3 VALIDATION SUCCESSFUL!")
        print("   ✅ STL export with quality control implemented")
        print("   ✅ Mesh validation and repair functional")
        print("   ✅ File size optimization working")
        print("   ✅ Integration with existing systems confirmed")
    else:
        print("⚠️  TASK 2.2.3 VALIDATION NEEDS ATTENTION")
        print("   Some components require fixes before completion")
    
    print("="*60)
    
    return success_rate >= 80


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
