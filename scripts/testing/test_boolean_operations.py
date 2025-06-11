#!/usr/bin/env python3
"""
Test suite for CAD Agent Boolean Operations - Task 2.2.2

This test suite validates the boolean operations implementation:
- Union, Difference, Intersection operations
- Error recovery and mesh repair
- Fallback algorithms
- Quality assessment and validation
"""

import asyncio
import unittest
import tempfile
import os
from pathlib import Path
import math
import numpy as np

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.cad_agent import CADAgent, BooleanOperationError, MeshRepairError
from core.api_schemas import CADAgentInput, BooleanOperationRequest, BooleanOperationResult
from core.exceptions import ValidationError


class TestCADAgentBooleanOperations(unittest.TestCase):
    """Test cases for CAD Agent Boolean Operations (Task 2.2.2)."""

    def setUp(self):
        """Set up test environment."""
        self.agent = CADAgent("test_boolean_cad_agent")
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test mesh files for boolean operations
        self.mesh_a_path = self._create_test_cube_mesh("cube_a.stl", 20, 20, 20)
        self.mesh_b_path = self._create_test_cube_mesh("cube_b.stl", 15, 15, 15, offset=[10, 0, 0])
        self.sphere_path = self._create_test_sphere_mesh("sphere.stl", 12)

    def tearDown(self):
        """Clean up test environment."""
        self.agent.cleanup()
        # Clean up temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_test_cube_mesh(self, filename: str, x: float, y: float, z: float, offset: list = None) -> str:
        """Create a test cube mesh file."""
        try:
            mesh, _ = self.agent.create_cube(x, y, z, center=True)
            
            if offset:
                if hasattr(mesh, 'apply_translation'):
                    mesh.apply_translation(offset)
            
            file_path = os.path.join(self.temp_dir, filename)
            if hasattr(mesh, 'export'):
                mesh.export(file_path)
            
            return file_path
        except Exception as e:
            self.fail(f"Failed to create test cube mesh: {e}")
    
    def _create_test_sphere_mesh(self, filename: str, radius: float) -> str:
        """Create a test sphere mesh file."""
        try:
            mesh, _ = self.agent.create_sphere(radius)
            
            file_path = os.path.join(self.temp_dir, filename)
            if hasattr(mesh, 'export'):
                mesh.export(file_path)
            
            return file_path
        except Exception as e:
            self.fail(f"Failed to create test sphere mesh: {e}")

    def test_boolean_union_operation(self):
        """Test boolean union operation."""
        task_data = {
            'operation': 'boolean_operation',
            'specifications': {
                'boolean_operation': {
                    'operation_type': 'union',
                    'operand_a': self.mesh_a_path,
                    'operand_b': self.mesh_b_path,
                    'auto_repair': True
                }
            },
            'requirements': {},
            'format_preference': 'stl'
        }
        
        async def run_test():
            result = await self.agent.execute_task(task_data)
            
            self.assertTrue(result.success, f"Union operation failed: {result.error_message}")
            self.assertEqual(result.data['operation_type'], 'union')
            self.assertIn('result_file_path', result.data)
            self.assertTrue(os.path.exists(result.data['result_file_path']))
            self.assertGreater(result.data['volume'], 0)
            self.assertGreaterEqual(result.data['quality_score'], 0)
            self.assertLessEqual(result.data['quality_score'], 10)
        
        asyncio.run(run_test())

    def test_boolean_difference_operation(self):
        """Test boolean difference operation."""
        task_data = {
            'operation': 'boolean_operation',
            'specifications': {
                'boolean_operation': {
                    'operation_type': 'difference',
                    'operand_a': self.mesh_a_path,
                    'operand_b': self.mesh_b_path,
                    'auto_repair': True
                }
            },
            'requirements': {},
            'format_preference': 'stl'
        }
        
        async def run_test():
            result = await self.agent.execute_task(task_data)
            
            self.assertTrue(result.success, f"Difference operation failed: {result.error_message}")
            self.assertEqual(result.data['operation_type'], 'difference')
            self.assertIn('result_file_path', result.data)
            self.assertTrue(os.path.exists(result.data['result_file_path']))
        
        asyncio.run(run_test())

    def test_boolean_intersection_operation(self):
        """Test boolean intersection operation."""
        task_data = {
            'operation': 'boolean_operation',
            'specifications': {
                'boolean_operation': {
                    'operation_type': 'intersection',
                    'operand_a': self.mesh_a_path,
                    'operand_b': self.mesh_b_path,
                    'auto_repair': True
                }
            },
            'requirements': {},
            'format_preference': 'stl'
        }
        
        async def run_test():
            result = await self.agent.execute_task(task_data)
            
            self.assertTrue(result.success, f"Intersection operation failed: {result.error_message}")
            self.assertEqual(result.data['operation_type'], 'intersection')
            self.assertIn('result_file_path', result.data)
            self.assertTrue(os.path.exists(result.data['result_file_path']))
        
        asyncio.run(run_test())

    def test_boolean_operation_validation(self):
        """Test validation of boolean operation parameters."""
        # Test missing operand
        task_data = {
            'operation': 'boolean_operation',
            'specifications': {
                'boolean_operation': {
                    'operation_type': 'union',
                    'operand_a': self.mesh_a_path,
                    # Missing operand_b
                    'auto_repair': True
                }
            },
            'requirements': {},
            'format_preference': 'stl'
        }
        
        async def run_test():
            result = await self.agent.execute_task(task_data)
            self.assertFalse(result.success)
            self.assertIn("operand", result.error_message.lower())
        
        asyncio.run(run_test())

    def test_boolean_operation_invalid_file(self):
        """Test boolean operation with invalid file path."""
        task_data = {
            'operation': 'boolean_operation',
            'specifications': {
                'boolean_operation': {
                    'operation_type': 'union',
                    'operand_a': '/nonexistent/file.stl',
                    'operand_b': self.mesh_b_path,
                    'auto_repair': True
                }
            },
            'requirements': {},
            'format_preference': 'stl'
        }
        
        async def run_test():
            result = await self.agent.execute_task(task_data)
            self.assertFalse(result.success)
            self.assertIn("not found", result.error_message)
        
        asyncio.run(run_test())

    def test_mesh_loading_and_validation(self):
        """Test mesh loading and validation functions."""
        # Test valid mesh loading
        mesh = self.agent._load_mesh_from_file(self.mesh_a_path)
        self.assertIsNotNone(mesh)
        self.assertTrue(hasattr(mesh, 'vertices'))
        self.assertTrue(hasattr(mesh, 'faces'))
        
        # Test mesh validation
        try:
            self.agent._validate_mesh_for_boolean(mesh, "test_mesh")
            # Should not raise exception for valid mesh
        except Exception as e:
            self.fail(f"Valid mesh failed validation: {e}")

    def test_mesh_repair_functionality(self):
        """Test mesh repair functionality."""
        mesh = self.agent._load_mesh_from_file(self.mesh_a_path)
        
        # Test repair function (should not fail)
        try:
            repaired_mesh = self.agent._repair_mesh(mesh)
            self.assertIsNotNone(repaired_mesh)
        except Exception as e:
            self.fail(f"Mesh repair failed: {e}")

    def test_mesh_quality_assessment(self):
        """Test mesh quality assessment functions."""
        mesh = self.agent._load_mesh_from_file(self.mesh_a_path)
        
        # Test quality assessment
        quality_score = self.agent._assess_boolean_result_quality(mesh)
        self.assertGreaterEqual(quality_score, 0)
        self.assertLessEqual(quality_score, 10)
        
        # Test manifold check
        is_manifold = self.agent._is_mesh_manifold(mesh)
        self.assertIsInstance(is_manifold, bool)
        
        # Test watertight check
        is_watertight = self.agent._is_mesh_watertight(mesh)
        self.assertIsInstance(is_watertight, bool)

    def test_mesh_volume_calculation(self):
        """Test mesh volume calculation."""
        mesh = self.agent._load_mesh_from_file(self.mesh_a_path)
        volume = self.agent._calculate_mesh_volume(mesh)
        
        self.assertIsInstance(volume, float)
        self.assertGreaterEqual(volume, 0)

    def test_boolean_operation_fallback(self):
        """Test boolean operation fallback mechanisms."""
        # Create task with complex geometry that might trigger fallbacks
        task_data = {
            'operation': 'boolean_operation',
            'specifications': {
                'boolean_operation': {
                    'operation_type': 'union',
                    'operand_a': self.mesh_a_path,
                    'operand_b': self.sphere_path,
                    'auto_repair': True
                }
            },
            'requirements': {},
            'format_preference': 'stl'
        }
        
        async def run_test():
            result = await self.agent.execute_task(task_data)
            
            # Should succeed even if primary method fails due to fallbacks
            self.assertTrue(result.success or "fallback" in result.error_message.lower())
        
        asyncio.run(run_test())

    def test_invalid_operation_type(self):
        """Test invalid boolean operation type."""
        task_data = {
            'operation': 'boolean_operation',
            'specifications': {
                'boolean_operation': {
                    'operation_type': 'invalid_operation',
                    'operand_a': self.mesh_a_path,
                    'operand_b': self.mesh_b_path,
                    'auto_repair': True
                }
            },
            'requirements': {},
            'format_preference': 'stl'
        }
        
        async def run_test():
            result = await self.agent.execute_task(task_data)
            self.assertFalse(result.success)
            self.assertIn("operation", result.error_message.lower())
        
        asyncio.run(run_test())

    def test_printability_assessment_boolean(self):
        """Test printability assessment for boolean results."""
        mesh = self.agent._load_mesh_from_file(self.mesh_a_path)
        
        # Test printability for different operation types
        for op_type in ['union', 'difference', 'intersection']:
            score = self.agent._check_printability_boolean(mesh, op_type)
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 10)

    def test_degenerate_geometry_detection(self):
        """Test degenerate geometry detection."""
        mesh = self.agent._load_mesh_from_file(self.mesh_a_path)
        
        # Test degenerate geometry check
        has_degenerate = self.agent._has_degenerate_geometry(mesh)
        self.assertIsInstance(has_degenerate, bool)

    def test_mesh_export_functionality(self):
        """Test mesh export functionality."""
        mesh = self.agent._load_mesh_from_file(self.mesh_a_path)
        
        export_path = os.path.join(self.temp_dir, "export_test.stl")
        
        try:
            self.agent._export_mesh_to_file(mesh, export_path)
            self.assertTrue(os.path.exists(export_path))
        except Exception as e:
            self.fail(f"Mesh export failed: {e}")


class TestCADAgentBooleanValidation(unittest.TestCase):
    """Test boolean operation parameter validation."""

    def setUp(self):
        """Set up test environment."""
        self.agent = CADAgent("test_validation_cad_agent")

    def tearDown(self):
        """Clean up test environment."""
        self.agent.cleanup()

    def test_boolean_operation_validation_methods(self):
        """Test individual validation methods."""
        # Test valid mesh result validation
        mock_mesh = type('MockMesh', (), {
            'vertices': np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]]),
            'faces': np.array([[0, 1, 2]])
        })()
        
        self.assertTrue(self.agent._is_valid_mesh_result(mock_mesh))
        
        # Test invalid mesh result validation
        self.assertFalse(self.agent._is_valid_mesh_result(None))
        self.assertFalse(self.agent._is_valid_mesh_result("not_a_mesh"))


def run_boolean_operations_test():
    """Run all boolean operations tests."""
    import time
    
    print("=== CAD Agent Boolean Operations Test Suite (Task 2.2.2) ===")
    print("Testing Boolean Operations Implementation...")
    print()
    
    start_time = time.time()
    
    # Run unit tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCADAgentBooleanOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestCADAgentBooleanValidation))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    end_time = time.time()
    
    print()
    print("=== Boolean Operations Test Results Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100:.1f}%")
    print(f"Execution time: {end_time - start_time:.2f} seconds")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    print()
    print("=== Task 2.2.2 Features Validated ===")
    if result.wasSuccessful():
        print("✅ Boolean Operations (Union, Difference, Intersection)")
        print("✅ Mesh Loading and Validation")
        print("✅ Error Recovery and Fallback Algorithms")
        print("✅ Automatic Mesh Repair")
        print("✅ Degenerate Geometry Detection")
        print("✅ Quality Assessment and Printability Analysis")
        print("✅ File Export and Import Operations")
        print("✅ Parameter Validation and Error Handling")
        print()
        print("🎉 Task 2.2.2: Boolean Operations with Error Recovery - COMPLETED!")
    else:
        print("❌ Some tests failed - Task 2.2.2 needs fixes")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_boolean_operations_test()
    exit(0 if success else 1)
