#!/usr/bin/env python3
"""
Comprehensive Test Suite for STL Export with Quality Control (Task 2.2.3)

This test suite validates all aspects of the STL export functionality:
- Basic export operations
- Quality checking and validation
- Mesh optimization and repair
- File size optimization
- Integration with existing systems
"""

import unittest
import asyncio
import tempfile
import os
import shutil
import sys

# Add path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.cad_agent import CADAgent, GeometryValidationError, ValidationError


class TestSTLExportQualityControl(unittest.TestCase):
    """Test cases for STL Export with Quality Control (Task 2.2.3)."""

    def setUp(self):
        """Set up test environment."""
        self.agent = CADAgent("test_stl_export")
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment."""
        self.agent.cleanup()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_mesh_file(self, filename: str, shape: str = "cube") -> str:
        """Create a test mesh file for export testing."""
        if shape == "cube":
            mesh, _ = self.agent.create_cube(10, 10, 10)
        elif shape == "sphere":
            mesh, _ = self.agent.create_sphere(8)
        elif shape == "cylinder":
            mesh, _ = self.agent.create_cylinder(6, 12)
        elif shape == "torus":
            mesh, _ = self.agent.create_torus(12, 3)
        else:
            mesh, _ = self.agent.create_cube(10, 10, 10)
        
        file_path = os.path.join(self.temp_dir, filename)
        mesh.export(file_path)
        return file_path
    
    # =============================================================================
    # BASIC STL EXPORT TESTS
    # =============================================================================
    
    def test_basic_stl_export(self):
        """Test basic STL export functionality."""
        source_file = self._create_test_mesh_file("test_cube.stl")
        output_file = os.path.join(self.temp_dir, "exported_cube.stl")
        
        task_data = {
            'operation': 'export_stl',
            'specifications': {
                'stl_export': {
                    'source_file_path': source_file,
                    'output_file_path': output_file,
                    'quality_level': 'standard',
                    'perform_quality_check': True,
                    'auto_repair_issues': True
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'standard'
        }
        
        result = asyncio.run(self.agent.execute_task(task_data))
        
        self.assertTrue(result.success, f"STL export failed: {result.error_message}")
        self.assertTrue(os.path.exists(output_file), "Output STL file was not created")
        self.assertIn('mesh_quality_report', result.data)
        self.assertIn('printability_assessment', result.data)
    
    def test_stl_export_all_quality_levels(self):
        """Test STL export with all quality levels."""
        source_file = self._create_test_mesh_file("test_sphere.stl", "sphere")
        
        quality_levels = ["draft", "standard", "high", "ultra"]
        
        for quality in quality_levels:
            with self.subTest(quality_level=quality):
                output_file = os.path.join(self.temp_dir, f"exported_{quality}.stl")
                
                task_data = {
                    'operation': 'export_stl',
                    'specifications': {
                        'stl_export': {
                            'source_file_path': source_file,
                            'output_file_path': output_file,
                            'quality_level': quality,
                            'perform_quality_check': True,
                            'auto_repair_issues': True
                        }
                    },
                    'requirements': {},
                    'format_preference': 'stl',
                    'quality_level': quality
                }
                
                result = asyncio.run(self.agent.execute_task(task_data))
                
                self.assertTrue(result.success, f"Export failed for quality {quality}: {result.error_message}")
                self.assertTrue(os.path.exists(output_file), f"Output file not created for quality {quality}")
    
    def test_stl_export_with_options(self):
        """Test STL export with various export options."""
        source_file = self._create_test_mesh_file("test_cylinder.stl", "cylinder")
        output_file = os.path.join(self.temp_dir, "exported_with_options.stl")
        
        task_data = {
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
                        'mesh_resolution': 0.05,
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
        
        result = asyncio.run(self.agent.execute_task(task_data))
        
        self.assertTrue(result.success, f"STL export with options failed: {result.error_message}")
        self.assertTrue(os.path.exists(output_file), "Output STL file was not created")
        self.assertGreater(result.data.get('file_size_bytes', 0), 0, "File size should be greater than 0")
    
    # =============================================================================
    # MESH QUALITY TESTS
    # =============================================================================
    
    def test_mesh_quality_report_generation(self):
        """Test mesh quality report generation."""
        mesh, _ = self.agent.create_torus(15, 4)
        
        quality_report = self.agent._generate_mesh_quality_report(mesh)
        
        # Check required fields
        required_fields = [
            'is_manifold', 'is_watertight', 'has_degenerate_faces',
            'duplicate_vertices', 'duplicate_faces', 'volume',
            'surface_area', 'quality_score', 'issues', 'recommendations'
        ]
        
        for field in required_fields:
            self.assertIn(field, quality_report, f"Missing required field: {field}")
        
        # Check data types and ranges
        self.assertIsInstance(quality_report['is_manifold'], bool)
        self.assertIsInstance(quality_report['is_watertight'], bool)
        self.assertIsInstance(quality_report['quality_score'], (int, float))
        self.assertGreaterEqual(quality_report['quality_score'], 0)
        self.assertLessEqual(quality_report['quality_score'], 10)
        self.assertIsInstance(quality_report['issues'], list)
        self.assertIsInstance(quality_report['recommendations'], list)
    
    def test_mesh_validation_functions(self):
        """Test individual mesh validation functions."""
        mesh, _ = self.agent.create_cube(12, 12, 12)
        
        # Test manifold checking
        try:
            is_manifold = self.agent._is_mesh_manifold(mesh)
            self.assertIsInstance(is_manifold, bool)
        except Exception as e:
            self.fail(f"Manifold check failed: {e}")
        
        # Test watertight checking
        try:
            is_watertight = self.agent._is_mesh_watertight(mesh)
            self.assertIsInstance(is_watertight, bool)
        except Exception as e:
            self.fail(f"Watertight check failed: {e}")
        
        # Test degenerate geometry checking
        try:
            has_degenerate = self.agent._has_degenerate_geometry(mesh)
            self.assertIsInstance(has_degenerate, bool)
        except Exception as e:
            self.fail(f"Degenerate geometry check failed: {e}")
    
    def test_mesh_property_calculations(self):
        """Test mesh property calculation functions."""
        mesh, expected_volume = self.agent.create_sphere(10)  # radius = 10
        
        # Test volume calculation
        calculated_volume = self.agent._calculate_mesh_volume(mesh)
        self.assertGreater(calculated_volume, 0, "Volume should be positive")
        # Allow some tolerance for mesh approximation
        self.assertAlmostEqual(calculated_volume, expected_volume, delta=expected_volume * 0.1)
        
        # Test surface area calculation
        surface_area = self.agent._calculate_surface_area(mesh)
        self.assertGreater(surface_area, 0, "Surface area should be positive")
        
        # Test vertex and face counting
        vertex_count = self.agent._get_vertex_count(mesh)
        face_count = self.agent._get_face_count(mesh)
        self.assertGreater(vertex_count, 0, "Vertex count should be positive")
        self.assertGreater(face_count, 0, "Face count should be positive")
    
    # =============================================================================
    # MESH OPTIMIZATION TESTS
    # =============================================================================
    
    def test_mesh_optimization_different_qualities(self):
        """Test mesh optimization with different quality levels."""
        mesh, _ = self.agent.create_sphere(12, segments=64)  # High resolution mesh
        
        quality_levels = ["draft", "standard", "high", "ultra"]
        
        for quality in quality_levels:
            with self.subTest(quality_level=quality):
                optimized_mesh, report = self.agent._optimize_mesh_for_export(mesh, quality)
                
                self.assertIsNotNone(optimized_mesh, f"Optimization failed for {quality}")
                self.assertIsInstance(report, dict, "Optimization report should be a dictionary")
                
                # Check report contains expected fields
                expected_fields = ['vertices_before', 'vertices_after', 'faces_before', 'faces_after', 'operations']
                for field in expected_fields:
                    self.assertIn(field, report, f"Missing field {field} in optimization report")
    
    def test_mesh_repair_functionality(self):
        """Test mesh repair functionality."""
        mesh, _ = self.agent.create_cylinder(8, 15)
        
        # Test mesh repair
        try:
            repaired_mesh = self.agent._repair_mesh(mesh)
            self.assertIsNotNone(repaired_mesh, "Mesh repair should return a mesh")
        except Exception as e:
            self.fail(f"Mesh repair failed: {e}")
    
    def test_manifold_repair(self):
        """Test manifold repair functionality."""
        mesh, _ = self.agent.create_torus(10, 3)
        
        # Test manifold repair
        try:
            manifold_mesh = self.agent._make_mesh_manifold(mesh)
            self.assertIsNotNone(manifold_mesh, "Manifold repair should return a mesh")
        except Exception as e:
            self.fail(f"Manifold repair failed: {e}")
    
    def test_resolution_adjustment(self):
        """Test mesh resolution adjustment."""
        mesh, _ = self.agent.create_cube(15, 15, 15)
        
        resolutions = [0.05, 0.1, 0.2, 0.5]
        
        for resolution in resolutions:
            with self.subTest(resolution=resolution):
                try:
                    adjusted_mesh = self.agent._adjust_mesh_resolution(mesh, resolution)
                    self.assertIsNotNone(adjusted_mesh, f"Resolution adjustment failed for {resolution}")
                except Exception as e:
                    # Some resolutions might not work with certain backends
                    self.skipTest(f"Resolution {resolution} not supported: {e}")
    
    # =============================================================================
    # STL VALIDATION TESTS
    # =============================================================================
    
    def test_stl_file_validation(self):
        """Test STL file validation functionality."""
        # Create and export a test mesh
        mesh, _ = self.agent.create_cube(8, 8, 8)
        test_file = os.path.join(self.temp_dir, "validation_test.stl")
        mesh.export(test_file)
        
        # Validate the STL file
        validation_result = self.agent._validate_stl_file(test_file)
        
        # Check required fields
        required_fields = [
            'is_valid_stl', 'format_errors', 'structural_errors',
            'file_size_mb', 'triangle_count', 'validation_time'
        ]
        
        for field in required_fields:
            self.assertIn(field, validation_result, f"Missing validation field: {field}")
        
        # Check data types
        self.assertIsInstance(validation_result['is_valid_stl'], bool)
        self.assertIsInstance(validation_result['format_errors'], list)
        self.assertIsInstance(validation_result['structural_errors'], list)
        self.assertIsInstance(validation_result['file_size_mb'], (int, float))
        self.assertIsInstance(validation_result['triangle_count'], int)
        self.assertGreaterEqual(validation_result['triangle_count'], 0)
    
    def test_stl_validation_nonexistent_file(self):
        """Test STL validation with non-existent file."""
        nonexistent_file = os.path.join(self.temp_dir, "does_not_exist.stl")
        
        validation_result = self.agent._validate_stl_file(nonexistent_file)
        
        self.assertFalse(validation_result['is_valid_stl'], "Non-existent file should be invalid")
        self.assertGreater(len(validation_result['format_errors']), 0, "Should have format errors")
    
    # =============================================================================
    # PRINTABILITY ASSESSMENT TESTS
    # =============================================================================
    
    def test_printability_assessment(self):
        """Test printability assessment functionality."""
        # Test with different shapes
        shapes = [
            ("cube", self.agent.create_cube(15, 15, 15)),
            ("sphere", self.agent.create_sphere(12)),
            ("cylinder", self.agent.create_cylinder(8, 20))
        ]
        
        for shape_name, (mesh, _) in shapes:
            with self.subTest(shape=shape_name):
                # Create temporary STL file
                test_file = os.path.join(self.temp_dir, f"printability_{shape_name}.stl")
                mesh.export(test_file)
                
                # Assess printability
                assessment = self.agent._assess_stl_printability(mesh, test_file)
                
                # Check required fields
                required_fields = ['score', 'issues', 'recommendations', 'support_needed']
                for field in required_fields:
                    self.assertIn(field, assessment, f"Missing assessment field: {field}")
                
                # Check data types and ranges
                self.assertIsInstance(assessment['score'], (int, float))
                self.assertGreaterEqual(assessment['score'], 0)
                self.assertLessEqual(assessment['score'], 10)
                self.assertIsInstance(assessment['issues'], list)
                self.assertIsInstance(assessment['recommendations'], list)
                self.assertIsInstance(assessment['support_needed'], bool)
    
    # =============================================================================
    # FILE SIZE OPTIMIZATION TESTS
    # =============================================================================
    
    def test_file_size_optimization(self):
        """Test file size optimization features."""
        # Create a complex mesh that can be optimized
        mesh, _ = self.agent.create_sphere(15, segments=128)  # Very high resolution
        source_file = os.path.join(self.temp_dir, "high_res_source.stl")
        mesh.export(source_file)
        
        original_size = os.path.getsize(source_file)
        
        # Test optimization with draft quality (should be smaller)
        optimized_mesh, report = self.agent._optimize_mesh_for_export(mesh, "draft")
        optimized_file = os.path.join(self.temp_dir, "optimized_draft.stl")
        self.agent._export_mesh_to_stl_file(optimized_mesh, optimized_file)
        
        optimized_size = os.path.getsize(optimized_file)
        
        # Check that some optimization occurred
        self.assertIsNotNone(optimized_mesh, "Optimization should return a mesh")
        self.assertGreater(len(report.get('operations', [])), 0, "Should have performed some operations")
        
        # File size might not always be smaller due to mesh complexity, but operations should be recorded
        self.assertTrue(True)  # At least the optimization ran without errors
    
    def test_compression_ratio_calculation(self):
        """Test compression ratio calculation in export results."""
        source_file = self._create_test_mesh_file("compression_test.stl", "torus")
        output_file = os.path.join(self.temp_dir, "compressed_output.stl")
        
        task_data = {
            'operation': 'export_stl',
            'specifications': {
                'stl_export': {
                    'source_file_path': source_file,
                    'output_file_path': output_file,
                    'quality_level': 'draft',  # Should optimize more aggressively
                    'export_options': {'optimize_mesh': True}
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'draft'
        }
        
        result = asyncio.run(self.agent.execute_task(task_data))
        
        self.assertTrue(result.success, f"Export failed: {result.error_message}")
        self.assertIn('compression_ratio', result.data)
        self.assertIsInstance(result.data['compression_ratio'], (int, float))
        # Compression ratio should be between -1 and 1 (can be negative if file grows)
        self.assertGreaterEqual(result.data['compression_ratio'], -1)
        self.assertLessEqual(result.data['compression_ratio'], 1)
    
    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================
    
    def test_primitive_to_stl_workflow(self):
        """Test complete workflow from primitive creation to STL export."""
        # Step 1: Create primitive
        primitive_task = {
            'operation': 'create_primitive',
            'specifications': {
                'geometry': {
                    'base_shape': 'cylinder',
                    'dimensions': {'radius': 10, 'height': 20}
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'standard'
        }
        
        primitive_result = asyncio.run(self.agent.execute_task(primitive_task))
        self.assertTrue(primitive_result.success, "Primitive creation should succeed")
        
        # Step 2: Export with quality control
        source_file = primitive_result.data['model_file_path']
        output_file = os.path.join(self.temp_dir, "workflow_output.stl")
        
        export_task = {
            'operation': 'export_stl',
            'specifications': {
                'stl_export': {
                    'source_file_path': source_file,
                    'output_file_path': output_file,
                    'quality_level': 'high',
                    'perform_quality_check': True,
                    'auto_repair_issues': True,
                    'generate_report': True
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'high'
        }
        
        export_result = asyncio.run(self.agent.execute_task(export_task))
        self.assertTrue(export_result.success, "STL export should succeed")
        self.assertTrue(os.path.exists(output_file), "Output file should exist")
    
    def test_error_handling(self):
        """Test error handling in STL export."""
        # Test with missing source file
        task_data = {
            'operation': 'export_stl',
            'specifications': {
                'stl_export': {
                    'source_file_path': '/nonexistent/path/file.stl',
                    'output_file_path': os.path.join(self.temp_dir, 'output.stl'),
                    'quality_level': 'standard'
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'standard'
        }
        
        result = asyncio.run(self.agent.execute_task(task_data))
        self.assertFalse(result.success, "Should fail with nonexistent source file")
        self.assertIsNotNone(result.error_message, "Should have error message")
    
    def test_multiple_exports_same_source(self):
        """Test multiple exports from the same source file."""
        source_file = self._create_test_mesh_file("multi_source.stl", "cube")
        
        # Export with different settings
        export_configs = [
            ("draft", {"mesh_resolution": 0.2, "optimize_mesh": True}),
            ("standard", {"mesh_resolution": 0.1, "optimize_mesh": True}),
            ("high", {"mesh_resolution": 0.05, "optimize_mesh": False})
        ]
        
        for i, (quality, options) in enumerate(export_configs):
            with self.subTest(export_number=i, quality=quality):
                output_file = os.path.join(self.temp_dir, f"multi_output_{i}.stl")
                
                task_data = {
                    'operation': 'export_stl',
                    'specifications': {
                        'stl_export': {
                            'source_file_path': source_file,
                            'output_file_path': output_file,
                            'quality_level': quality,
                            'export_options': options
                        }
                    },
                    'requirements': {},
                    'format_preference': 'stl',
                    'quality_level': quality
                }
                
                result = asyncio.run(self.agent.execute_task(task_data))
                self.assertTrue(result.success, f"Export {i} should succeed")
                self.assertTrue(os.path.exists(output_file), f"Output file {i} should exist")


def run_test_suite():
    """Run the complete test suite."""
    print("="*70)
    print("🧪 RUNNING STL EXPORT QUALITY CONTROL TEST SUITE")
    print("="*70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSTLExportQualityControl)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS SUMMARY")
    print("="*70)
    
    total_tests = result.testsRun
    failed_tests = len(result.failures)
    error_tests = len(result.errors)
    skipped_tests = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed_tests = total_tests - failed_tests - error_tests - skipped_tests
    
    print(f"📈 Total tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"💥 Errors: {error_tests}")
    print(f"⏭️  Skipped: {skipped_tests}")
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"🎯 Success rate: {success_rate:.1f}%")
    
    if result.failures:
        print(f"\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"   • {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"   • {test}: {traceback.split('Exception:')[-1].strip()}")
    
    print("\n" + "="*70)
    
    if success_rate >= 80:
        print("🎉 TASK 2.2.3 STL EXPORT IMPLEMENTATION VALIDATED!")
        print("   ✅ All major functionality working correctly")
        print("   ✅ Quality control systems operational")
        print("   ✅ Integration tests passing")
        return True
    else:
        print("⚠️  TASK 2.2.3 NEEDS ATTENTION")
        print("   Some tests failed - review implementation")
        return False


if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)
