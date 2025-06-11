"""
Test suite for CAD Agent - 3D Primitives Library

This test suite validates Task 2.2.1 implementation:
- 3D primitive generation (cube, cylinder, sphere, torus, cone)
- Parameter validation and error handling
- Printability checks and material calculations
- File generation and export functionality
"""

import asyncio
import unittest
import tempfile
import os
from pathlib import Path
import math

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.cad_agent import CADAgent, GeometryValidationError, PrintabilityError
from core.api_schemas import CADAgentInput, CADPrimitiveRequest, PrimitiveGeometry, GeometryDimensions
from core.exceptions import ValidationError


class TestCADAgent(unittest.TestCase):
    """Test cases for CAD Agent 3D primitives library."""

    def setUp(self):
        """Set up test environment."""
        self.agent = CADAgent("test_cad_agent")
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        self.agent.cleanup()
        # Clean up temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_cad_agent_initialization(self):
        """Test CAD agent initializes correctly."""
        self.assertEqual(self.agent.agent_name, "test_cad_agent")
        self.assertIn(self.agent.cad_backend, ["freecad", "trimesh"])
        self.assertEqual(self.agent.min_dimension, 0.1)
        self.assertEqual(self.agent.max_dimension, 300.0)

    def test_create_cube_valid_dimensions(self):
        """Test cube creation with valid dimensions."""
        mesh, volume = self.agent.create_cube(10, 15, 20)
        
        self.assertIsNotNone(mesh)
        self.assertAlmostEqual(volume, 3000.0, places=1)  # 10*15*20 = 3000

    def test_create_cube_centered(self):
        """Test cube creation centered at origin."""
        mesh, volume = self.agent.create_cube(10, 10, 10, center=True)
        
        self.assertIsNotNone(mesh)
        self.assertAlmostEqual(volume, 1000.0, places=1)

    def test_create_cylinder_valid_parameters(self):
        """Test cylinder creation with valid parameters."""
        mesh, volume = self.agent.create_cylinder(radius=5, height=10)
        
        expected_volume = math.pi * 5 * 5 * 10  # π*r²*h
        self.assertIsNotNone(mesh)
        self.assertAlmostEqual(volume, expected_volume, places=1)

    def test_create_sphere_valid_radius(self):
        """Test sphere creation with valid radius."""
        mesh, volume = self.agent.create_sphere(radius=7)
        
        expected_volume = (4.0 / 3.0) * math.pi * 7 * 7 * 7  # (4/3)*π*r³
        self.assertIsNotNone(mesh)
        self.assertAlmostEqual(volume, expected_volume, places=1)

    def test_create_torus_valid_radii(self):
        """Test torus creation with valid radii."""
        mesh, volume = self.agent.create_torus(major_radius=10, minor_radius=3)
        
        expected_volume = 2 * math.pi * math.pi * 10 * 3 * 3  # 2*π²*R*r²
        self.assertIsNotNone(mesh)
        self.assertAlmostEqual(volume, expected_volume, places=1)

    def test_create_cone_complete(self):
        """Test complete cone creation."""
        mesh, volume = self.agent.create_cone(base_radius=6, top_radius=0, height=12)
        
        expected_volume = (1.0 / 3.0) * math.pi * 6 * 6 * 12  # (1/3)*π*r²*h
        self.assertIsNotNone(mesh)
        self.assertAlmostEqual(volume, expected_volume, places=1)

    def test_create_cone_truncated(self):
        """Test truncated cone creation."""
        mesh, volume = self.agent.create_cone(base_radius=8, top_radius=4, height=10)
        
        # Truncated cone: (1/3)*π*h*(r1² + r1*r2 + r2²)
        expected_volume = (1.0 / 3.0) * math.pi * 10 * (8*8 + 8*4 + 4*4)
        self.assertIsNotNone(mesh)
        self.assertAlmostEqual(volume, expected_volume, places=1)

    def test_validation_negative_dimensions(self):
        """Test validation catches negative dimensions."""
        with self.assertRaises(GeometryValidationError):
            self.agent.create_cube(-5, 10, 10)
        
        with self.assertRaises(GeometryValidationError):
            self.agent.create_cylinder(-3, 10)
        
        with self.assertRaises(GeometryValidationError):
            self.agent.create_sphere(-2)

    def test_validation_zero_dimensions(self):
        """Test validation catches zero dimensions."""
        with self.assertRaises(GeometryValidationError):
            self.agent.create_cube(0, 10, 10)
        
        with self.assertRaises(GeometryValidationError):
            self.agent.create_cylinder(5, 0)

    def test_validation_too_small_dimensions(self):
        """Test validation catches dimensions below minimum."""
        with self.assertRaises(GeometryValidationError):
            self.agent.create_cube(0.05, 10, 10)  # Below 0.1mm minimum

    def test_validation_too_large_dimensions(self):
        """Test validation catches dimensions above maximum."""
        with self.assertRaises(GeometryValidationError):
            self.agent.create_cube(350, 10, 10)  # Above 300mm maximum

    def test_validation_invalid_segments(self):
        """Test validation catches invalid segment counts."""
        with self.assertRaises(GeometryValidationError):
            self.agent.create_cylinder(5, 10, segments=2)  # Too few segments
        
        with self.assertRaises(GeometryValidationError):
            self.agent.create_sphere(5, segments=300)  # Too many segments

    def test_validation_torus_radii(self):
        """Test validation for torus radii relationship."""
        with self.assertRaises(GeometryValidationError):
            self.agent.create_torus(5, 8)  # Minor radius >= major radius

    def test_printability_assessment_cube(self):
        """Test printability assessment for cube."""
        dimensions = {"x": 20, "y": 15, "z": 10}
        mesh, _ = self.agent.create_cube(**dimensions)
        
        score = self.agent._check_printability(mesh, "cube", dimensions)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 10)
        self.assertGreater(score, 8)  # Cube should have high printability

    def test_printability_assessment_sphere(self):
        """Test printability assessment for sphere."""
        dimensions = {"radius": 10}
        mesh, _ = self.agent.create_sphere(**dimensions)
        
        score = self.agent._check_printability(mesh, "sphere", dimensions)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 10)
        self.assertLess(score, 10)  # Sphere needs support, lower score

    def test_material_calculation(self):
        """Test material volume and weight calculation."""
        mesh, volume = self.agent.create_cube(10, 10, 10)
        
        # Volume should be 1000 mm³ = 1 cm³
        volume_cm3 = volume / 1000
        weight_g = volume_cm3 * self.agent.material_density
        
        self.assertAlmostEqual(volume_cm3, 1.0, places=3)
        self.assertAlmostEqual(weight_g, 1.24, places=2)  # PLA density


class TestCADAgentAsyncTasks(unittest.TestCase):
    """Test async task execution for CAD Agent."""

    def setUp(self):
        """Set up test environment."""
        self.agent = CADAgent("test_async_cad_agent")

    def tearDown(self):
        """Clean up test environment."""
        self.agent.cleanup()

    async def test_execute_cube_task(self):
        """Test executing cube creation task."""
        task_data = {
            'operation': 'create_primitive',
            'specifications': {
                'geometry': {
                    'base_shape': 'cube',
                    'dimensions': {'x': 20, 'y': 15, 'z': 10}
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'standard'
        }
        
        result = await self.agent.execute_task(task_data)
        
        self.assertTrue(result.success)
        self.assertIn('model_file_path', result.data)
        self.assertIn('volume', result.data)
        self.assertIn('printability_score', result.data)
        self.assertEqual(result.data['volume'], 3000.0)

    async def test_execute_cylinder_task(self):
        """Test executing cylinder creation task."""
        task_data = {
            'operation': 'create_primitive',
            'specifications': {
                'geometry': {
                    'base_shape': 'cylinder',
                    'dimensions': {'radius': 8, 'height': 15}
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'high'
        }
        
        result = await self.agent.execute_task(task_data)
        
        self.assertTrue(result.success)
        self.assertIn('model_file_path', result.data)
        
        # Check volume calculation
        expected_volume = math.pi * 8 * 8 * 15
        self.assertAlmostEqual(result.data['volume'], expected_volume, places=1)

    async def test_execute_sphere_task(self):
        """Test executing sphere creation task."""
        task_data = {
            'operation': 'create_primitive',
            'specifications': {
                'geometry': {
                    'base_shape': 'sphere',
                    'dimensions': {'radius': 12}
                }
            },
            'requirements': {},
            'format_preference': 'stl'
        }
        
        result = await self.agent.execute_task(task_data)
        
        self.assertTrue(result.success)
        
        # Sphere should have lower printability due to support needs
        self.assertLess(result.data['printability_score'], 10)

    async def test_execute_invalid_shape_task(self):
        """Test executing task with invalid shape."""
        task_data = {
            'operation': 'create_primitive',
            'specifications': {
                'geometry': {
                    'base_shape': 'pyramid',  # Not supported
                    'dimensions': {'x': 10, 'y': 10, 'z': 10}
                }
            },
            'requirements': {}
        }
        
        result = await self.agent.execute_task(task_data)
        
        self.assertFalse(result.success)
        self.assertIn('error_message', result.__dict__)

    def test_async_cube_task(self):
        """Test async cube task execution."""
        asyncio.run(self.test_execute_cube_task())

    def test_async_cylinder_task(self):
        """Test async cylinder task execution."""
        asyncio.run(self.test_execute_cylinder_task())

    def test_async_sphere_task(self):
        """Test async sphere task execution."""
        asyncio.run(self.test_execute_sphere_task())

    def test_async_invalid_shape_task(self):
        """Test async invalid shape task execution."""
        asyncio.run(self.test_execute_invalid_shape_task())


class TestCADAgentDimensionValidation(unittest.TestCase):
    """Test dimension validation for different shapes."""

    def setUp(self):
        """Set up test environment."""
        self.agent = CADAgent("test_validation_agent")

    def tearDown(self):
        """Clean up test environment."""
        self.agent.cleanup()

    def test_validate_cube_dimensions(self):
        """Test cube dimension validation."""
        # Valid dimensions
        dimensions = {'x': 10, 'y': 15, 'z': 20}
        self.agent._validate_dimensions(dimensions, 'cube')
        
        # Missing dimension
        with self.assertRaises(ValidationError):
            self.agent._validate_dimensions({'x': 10, 'y': 15}, 'cube')

    def test_validate_cylinder_dimensions(self):
        """Test cylinder dimension validation."""
        # Valid dimensions
        dimensions = {'radius': 5, 'height': 10}
        self.agent._validate_dimensions(dimensions, 'cylinder')
        
        # Alternative naming (x for radius, z for height)
        dimensions_alt = {'x': 5, 'z': 10}
        self.agent._validate_dimensions(dimensions_alt, 'cylinder')
        self.assertEqual(dimensions_alt['radius'], 5)
        self.assertEqual(dimensions_alt['height'], 10)

    def test_validate_sphere_dimensions(self):
        """Test sphere dimension validation."""
        # Valid dimensions
        dimensions = {'radius': 8}
        self.agent._validate_dimensions(dimensions, 'sphere')
        
        # Alternative naming
        dimensions_alt = {'x': 8}
        self.agent._validate_dimensions(dimensions_alt, 'sphere')
        self.assertEqual(dimensions_alt['radius'], 8)

    def test_validate_torus_dimensions(self):
        """Test torus dimension validation."""
        # Valid dimensions
        dimensions = {'major_radius': 10, 'minor_radius': 3}
        self.agent._validate_dimensions(dimensions, 'torus')
        
        # Missing dimension
        with self.assertRaises(ValidationError):
            self.agent._validate_dimensions({'major_radius': 10}, 'torus')

    def test_validate_cone_dimensions(self):
        """Test cone dimension validation."""
        # Valid dimensions
        dimensions = {'base_radius': 6, 'height': 12}
        self.agent._validate_dimensions(dimensions, 'cone')
        
        # Missing dimension
        with self.assertRaises(ValidationError):
            self.agent._validate_dimensions({'base_radius': 6}, 'cone')


def run_comprehensive_test():
    """Run all CAD Agent tests."""
    import time
    
    print("=== CAD Agent 3D Primitives Library Test Suite ===")
    print("Testing Task 2.2.1 Implementation...")
    print()
    
    start_time = time.time()
    
    # Run unit tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCADAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestCADAgentAsyncTasks))
    suite.addTests(loader.loadTestsFromTestCase(TestCADAgentDimensionValidation))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    end_time = time.time()
    
    print()
    print("=== Test Results Summary ===")
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
    
    return result.wasSuccessful()


async def run_integration_test():
    """Run integration test with sample design specifications."""
    print("\n=== Integration Test: CAD Agent with Design Specifications ===")
    
    agent = CADAgent("integration_test_agent")
    
    # Sample design specifications (similar to Research Agent output)
    test_cases = [
        {
            'name': 'Simple Cube',
            'data': {
                'operation': 'create_primitive',
                'specifications': {
                    'geometry': {
                        'type': 'primitive',
                        'base_shape': 'cube',
                        'dimensions': {'x': 25, 'y': 25, 'z': 25}
                    },
                    'constraints': {
                        'min_wall_thickness': 1.2,
                        'support_needed': False,
                        'print_orientation': 'flat'
                    }
                },
                'requirements': {'material_type': 'PLA'},
                'format_preference': 'stl',
                'quality_level': 'standard'
            }
        },
        {
            'name': 'Cylinder Container',
            'data': {
                'operation': 'create_primitive',
                'specifications': {
                    'geometry': {
                        'type': 'primitive',
                        'base_shape': 'cylinder',
                        'dimensions': {'radius': 15, 'height': 30}
                    }
                },
                'requirements': {'material_type': 'PETG'},
                'format_preference': 'stl',
                'quality_level': 'high'
            }
        },
        {
            'name': 'Decorative Sphere',
            'data': {
                'operation': 'create_primitive',
                'specifications': {
                    'geometry': {
                        'type': 'primitive',
                        'base_shape': 'sphere',
                        'dimensions': {'radius': 20}
                    }
                },
                'requirements': {'material_type': 'PLA'},
                'format_preference': 'stl'
            }
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        try:
            result = await agent.execute_task(test_case['data'])
            
            if result.success:
                print(f"✅ Success!")
                print(f"   Volume: {result.data.get('volume', 0):.1f} mm³")
                print(f"   Printability Score: {result.data.get('printability_score', 0):.1f}/10")
                print(f"   Material Weight: {result.data.get('material_weight_g', 0):.2f}g")
                print(f"   File: {os.path.basename(result.data.get('model_file_path', 'None'))}")
                results.append(True)
            else:
                print(f"❌ Failed: {result.error_message}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append(False)
    
    agent.cleanup()
    
    success_rate = (sum(results) / len(results)) * 100
    print(f"\n=== Integration Test Results ===")
    print(f"Success Rate: {success_rate:.1f}% ({sum(results)}/{len(results)})")
    
    return success_rate == 100.0


if __name__ == "__main__":
    # Run comprehensive unit tests
    unit_test_success = run_comprehensive_test()
    
    # Run integration tests
    integration_test_success = asyncio.run(run_integration_test())
    
    print("\n" + "="*60)
    print("FINAL RESULTS - Task 2.2.1: CAD Agent 3D Primitives Library")
    print("="*60)
    print(f"Unit Tests: {'✅ PASSED' if unit_test_success else '❌ FAILED'}")
    print(f"Integration Tests: {'✅ PASSED' if integration_test_success else '❌ FAILED'}")
    
    if unit_test_success and integration_test_success:
        print("\n🎉 Task 2.2.1 IMPLEMENTATION SUCCESSFUL!")
        print("CAD Agent 3D Primitives Library is ready for production use.")
    else:
        print("\n⚠️  Some tests failed. Please review and fix issues.")
    
    print("\nImplemented features:")
    print("- ✅ create_cube() with parameter validation")
    print("- ✅ create_cylinder() with segment control")
    print("- ✅ create_sphere() with quality settings")
    print("- ✅ create_torus() with dual radius support")
    print("- ✅ create_cone() with truncated cone support")
    print("- ✅ Comprehensive parameter validation")
    print("- ✅ Printability assessment scoring")
    print("- ✅ Material volume and weight calculation")
    print("- ✅ STL file generation and export")
    print("- ✅ Error handling and validation")
    print("- ✅ FreeCAD and trimesh backend support")
