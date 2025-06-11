"""
Unit tests for CAD Agent - 3D Primitives Library and STL Export.

Tests cover:
- 3D primitive generation (cube, cylinder, sphere, torus, cone)
- Boolean operations (union, difference, intersection)
- STL export with quality control
- Parameter validation and error handling
- Printability checks and material calculations
- File generation and export functionality
"""

import pytest
import asyncio
import tempfile
import os
import shutil
import math
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.cad_agent import (
    CADAgent, GeometryValidationError, PrintabilityError,
    BooleanOperationError, MeshRepairError
)
from core.api_schemas import CADAgentInput, CADAgentOutput, TaskResult
from core.exceptions import ValidationError, AI3DPrintError


class TestCADAgent:
    """Test cases for CAD Agent 3D primitives library."""
    
    @pytest.fixture
    def cad_agent(self):
        """Create a CAD Agent instance for testing."""
        return CADAgent("test_cad_agent")
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_input(self):
        """Sample input for testing."""
        return CADAgentInput(
            specifications={
                "primitive_creation": {
                    "shape": "cube",
                    "dimensions": {"x": 10, "y": 15, "z": 20}
                }
            },
            requirements={},
            format_preference="stl",
            quality_level="standard"
        )
    
    def test_agent_initialization(self, cad_agent):
        """Test CAD Agent initialization."""
        assert cad_agent.agent_name == "test_cad_agent"
        assert cad_agent.agent_type == "CADAgent"
        assert cad_agent.cad_backend in ["freecad", "trimesh"]
        assert cad_agent.min_dimension == 0.1
        assert cad_agent.max_dimension == 300.0
        assert cad_agent.material_density > 0
    
    def test_create_cube_valid_dimensions(self, cad_agent):
        """Test cube creation with valid dimensions."""
        mesh, volume = cad_agent.create_cube(10, 15, 20)
        
        assert mesh is not None
        assert abs(volume - 3000.0) < 0.1  # 10*15*20 = 3000
    
    def test_create_cube_centered(self, cad_agent):
        """Test cube creation centered at origin."""
        mesh, volume = cad_agent.create_cube(10, 10, 10, center=True)
        
        assert mesh is not None
        assert abs(volume - 1000.0) < 0.1
    
    def test_create_cylinder_valid_parameters(self, cad_agent):
        """Test cylinder creation with valid parameters."""
        mesh, volume = cad_agent.create_cylinder(radius=5, height=10)
        
        expected_volume = math.pi * 5 * 5 * 10  # π*r²*h
        assert mesh is not None
        assert abs(volume - expected_volume) < expected_volume * 0.1
    
    def test_create_sphere_valid_radius(self, cad_agent):
        """Test sphere creation with valid radius."""
        mesh, volume = cad_agent.create_sphere(radius=5)
        
        expected_volume = (4.0 / 3.0) * math.pi * 5 * 5 * 5  # (4/3)*π*r³
        assert mesh is not None
        assert abs(volume - expected_volume) < expected_volume * 0.1
    
    def test_create_torus_valid_radii(self, cad_agent):
        """Test torus creation with valid radii."""
        mesh, volume = cad_agent.create_torus(major_radius=10, minor_radius=3)
        
        expected_volume = 2 * math.pi * math.pi * 10 * 3 * 3  # 2*π²*R*r²
        assert mesh is not None
        assert abs(volume - expected_volume) < expected_volume * 0.1
    
    def test_create_cone_complete(self, cad_agent):
        """Test complete cone creation."""
        mesh, volume = cad_agent.create_cone(base_radius=6, top_radius=0, height=12)
        
        expected_volume = (1.0 / 3.0) * math.pi * 6 * 6 * 12  # (1/3)*π*r²*h
        assert mesh is not None
        assert abs(volume - expected_volume) < expected_volume * 0.1
    
    def test_create_cone_truncated(self, cad_agent):
        """Test truncated cone creation."""
        mesh, volume = cad_agent.create_cone(base_radius=8, top_radius=4, height=10)
        
        # Truncated cone: (1/3)*π*h*(r1² + r1*r2 + r2²)
        expected_volume = (1.0 / 3.0) * math.pi * 10 * (8*8 + 8*4 + 4*4)
        assert mesh is not None
        assert abs(volume - expected_volume) < expected_volume * 0.1
    
    def test_validation_negative_dimensions(self, cad_agent):
        """Test validation catches negative dimensions."""
        with pytest.raises(GeometryValidationError):
            cad_agent.create_cube(-5, 10, 10)
        
        with pytest.raises(GeometryValidationError):
            cad_agent.create_cylinder(-3, 10)
        
        with pytest.raises(GeometryValidationError):
            cad_agent.create_sphere(-2)
    
    def test_validation_zero_dimensions(self, cad_agent):
        """Test validation catches zero dimensions."""
        with pytest.raises(GeometryValidationError):
            cad_agent.create_cube(0, 10, 10)
        
        with pytest.raises(GeometryValidationError):
            cad_agent.create_cylinder(5, 0)
    
    def test_validation_too_small_dimensions(self, cad_agent):
        """Test validation catches dimensions below minimum."""
        with pytest.raises(GeometryValidationError):
            cad_agent.create_cube(0.05, 10, 10)  # Below 0.1mm minimum
    
    def test_validation_too_large_dimensions(self, cad_agent):
        """Test validation catches dimensions above maximum."""
        with pytest.raises(GeometryValidationError):
            cad_agent.create_cube(350, 10, 10)  # Above 300mm maximum
    
    def test_validation_invalid_segments(self, cad_agent):
        """Test validation catches invalid segment counts."""
        with pytest.raises(GeometryValidationError):
            cad_agent.create_cylinder(5, 10, segments=2)  # Too few segments
        
        with pytest.raises(GeometryValidationError):
            cad_agent.create_sphere(5, segments=300)  # Too many segments
    
    def test_validation_torus_radii(self, cad_agent):
        """Test validation for torus radii relationship."""
        with pytest.raises(GeometryValidationError):
            cad_agent.create_torus(5, 8)  # Minor radius >= major radius
    
    def test_printability_assessment_cube(self, cad_agent):
        """Test printability assessment for cube."""
        dimensions = {"x": 20, "y": 15, "z": 10}
        mesh, _ = cad_agent.create_cube(**dimensions)
        
        score = cad_agent._check_printability(mesh, "cube", dimensions)
        assert 0 <= score <= 10
        assert score > 8  # Cube should have high printability
    
    def test_printability_assessment_sphere(self, cad_agent):
        """Test printability assessment for sphere."""
        dimensions = {"radius": 10}
        mesh, _ = cad_agent.create_sphere(**dimensions)
        
        score = cad_agent._check_printability(mesh, "sphere", dimensions)
        assert 0 <= score <= 10
        assert score < 10  # Sphere needs support, lower score
    
    def test_material_calculation(self, cad_agent):
        """Test material volume and weight calculation."""
        mesh, volume = cad_agent.create_cube(10, 10, 10)
        
        # Volume should be 1000 mm³ = 1 cm³
        volume_cm3 = volume / 1000
        weight_g = volume_cm3 * cad_agent.material_density
        
        assert abs(volume_cm3 - 1.0) < 0.001
        assert abs(weight_g - 1.24) < 0.02  # PLA density ~1.24 g/cm³


class TestCADAgentBooleanOperations:
    """Test cases for CAD Agent Boolean Operations."""
    
    @pytest.fixture
    def cad_agent(self):
        """Create a CAD Agent instance for testing."""
        return CADAgent("test_boolean_agent")
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_meshes(self, cad_agent, temp_dir):
        """Create sample mesh files for boolean operations."""
        # Create two overlapping cubes
        mesh_a, _ = cad_agent.create_cube(20, 20, 20, center=True)
        mesh_b, _ = cad_agent.create_cube(20, 20, 20, center=True)
        
        # Save to temporary files
        mesh_a_path = os.path.join(temp_dir, "mesh_a.stl")
        mesh_b_path = os.path.join(temp_dir, "mesh_b.stl")
        
        cad_agent._export_mesh_to_file(mesh_a, mesh_a_path)
        cad_agent._export_mesh_to_file(mesh_b, mesh_b_path)
        
        return mesh_a_path, mesh_b_path
    
    def test_boolean_union_operation(self, cad_agent, sample_meshes, temp_dir):
        """Test boolean union operation."""
        mesh_a_path, mesh_b_path = sample_meshes
        output_path = os.path.join(temp_dir, "union_result.stl")
        
        result = cad_agent.perform_boolean_operation(
            mesh_a_path, mesh_b_path, "union", output_path
        )
        
        assert result["success"] is True
        assert os.path.exists(output_path)
        assert result["operation"] == "union"
        assert result["quality_score"] > 0
    
    def test_boolean_difference_operation(self, cad_agent, sample_meshes, temp_dir):
        """Test boolean difference operation."""
        mesh_a_path, mesh_b_path = sample_meshes
        output_path = os.path.join(temp_dir, "difference_result.stl")
        
        result = cad_agent.perform_boolean_operation(
            mesh_a_path, mesh_b_path, "difference", output_path
        )
        
        assert result["success"] is True
        assert os.path.exists(output_path)
        assert result["operation"] == "difference"
    
    def test_boolean_intersection_operation(self, cad_agent, sample_meshes, temp_dir):
        """Test boolean intersection operation."""
        mesh_a_path, mesh_b_path = sample_meshes
        output_path = os.path.join(temp_dir, "intersection_result.stl")
        
        result = cad_agent.perform_boolean_operation(
            mesh_a_path, mesh_b_path, "intersection", output_path
        )
        
        assert result["success"] is True
        assert os.path.exists(output_path)
        assert result["operation"] == "intersection"
    
    def test_boolean_operation_invalid_input(self, cad_agent, temp_dir):
        """Test boolean operation with invalid input."""
        nonexistent_path = os.path.join(temp_dir, "nonexistent.stl")
        output_path = os.path.join(temp_dir, "result.stl")
        
        with pytest.raises(ValidationError):
            cad_agent.perform_boolean_operation(
                nonexistent_path, nonexistent_path, "union", output_path
            )
    
    def test_boolean_operation_invalid_operation(self, cad_agent, sample_meshes, temp_dir):
        """Test boolean operation with invalid operation type."""
        mesh_a_path, mesh_b_path = sample_meshes
        output_path = os.path.join(temp_dir, "result.stl")
        
        with pytest.raises(ValidationError):
            cad_agent.perform_boolean_operation(
                mesh_a_path, mesh_b_path, "invalid_operation", output_path
            )
    
    def test_mesh_quality_assessment(self, cad_agent, sample_meshes):
        """Test mesh quality assessment functions."""
        mesh_a_path, _ = sample_meshes
        mesh = cad_agent._load_mesh_from_file(mesh_a_path)
        
        # Test quality assessment
        quality_score = cad_agent._assess_boolean_result_quality(mesh)
        assert 0 <= quality_score <= 10
        
        # Test manifold check
        is_manifold = cad_agent._is_mesh_manifold(mesh)
        assert isinstance(is_manifold, bool)
        
        # Test watertight check
        is_watertight = cad_agent._is_mesh_watertight(mesh)
        assert isinstance(is_watertight, bool)
    
    def test_mesh_repair_functionality(self, cad_agent, sample_meshes):
        """Test mesh repair functionality."""
        mesh_a_path, _ = sample_meshes
        mesh = cad_agent._load_mesh_from_file(mesh_a_path)
        
        # Attempt mesh repair
        repaired_mesh = cad_agent._repair_mesh(mesh)
        
        assert repaired_mesh is not None
        # Repaired mesh should ideally be manifold and watertight
        # (though this depends on the input mesh quality)


class TestCADAgentSTLExport:
    """Test cases for CAD Agent STL Export with Quality Control."""
    
    @pytest.fixture
    def cad_agent(self):
        """Create a CAD Agent instance for testing."""
        return CADAgent("test_stl_export_agent")
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_basic_stl_export(self, cad_agent, temp_dir):
        """Test basic STL export functionality."""
        # Create a simple cube
        mesh, _ = cad_agent.create_cube(10, 10, 10)
        output_file = os.path.join(temp_dir, "test_cube.stl")
        
        # Export to STL
        result = cad_agent.export_to_stl(
            mesh=mesh,
            output_file_path=output_file,
            quality_level="standard"
        )
        
        assert result["success"] is True
        assert os.path.exists(output_file)
        assert result["file_size_bytes"] > 0
        assert result["quality_level"] == "standard"
    
    def test_stl_export_all_quality_levels(self, cad_agent, temp_dir):
        """Test STL export with all quality levels."""
        quality_levels = ["draft", "standard", "high", "ultra"]
        
        for quality in quality_levels:
            mesh, _ = cad_agent.create_sphere(10)
            output_file = os.path.join(temp_dir, f"sphere_{quality}.stl")
            
            result = cad_agent.export_to_stl(
                mesh=mesh,
                output_file_path=output_file,
                quality_level=quality
            )
            
            assert result["success"] is True
            assert os.path.exists(output_file)
            assert result["quality_level"] == quality
    
    def test_stl_export_with_optimization(self, cad_agent, temp_dir):
        """Test STL export with mesh optimization."""
        mesh, _ = cad_agent.create_cylinder(5, 10, segments=64)
        output_file = os.path.join(temp_dir, "optimized_cylinder.stl")
        
        result = cad_agent.export_to_stl(
            mesh=mesh,
            output_file_path=output_file,
            quality_level="high",
            optimize_mesh=True
        )
        
        assert result["success"] is True
        assert os.path.exists(output_file)
        assert "optimization_applied" in result
    
    def test_stl_validation_and_repair(self, cad_agent, temp_dir):
        """Test STL validation and automatic repair."""
        mesh, _ = cad_agent.create_torus(10, 3)
        output_file = os.path.join(temp_dir, "torus_repaired.stl")
        
        result = cad_agent.export_to_stl(
            mesh=mesh,
            output_file_path=output_file,
            quality_level="standard",
            auto_repair=True
        )
        
        assert result["success"] is True
        assert "quality_report" in result
        quality_report = result["quality_report"]
        assert "is_manifold" in quality_report
        assert "is_watertight" in quality_report
    
    def test_mesh_property_calculations(self, cad_agent):
        """Test mesh property calculation functions."""
        mesh, expected_volume = cad_agent.create_sphere(10)  # radius = 10
        
        # Test volume calculation
        calculated_volume = cad_agent._calculate_mesh_volume(mesh)
        assert calculated_volume > 0
        # Allow some tolerance for mesh approximation
        assert abs(calculated_volume - expected_volume) < expected_volume * 0.1
        
        # Test surface area calculation
        surface_area = cad_agent._calculate_surface_area(mesh)
        assert surface_area > 0
        
        # Test vertex and face counting
        vertex_count = cad_agent._get_vertex_count(mesh)
        face_count = cad_agent._get_face_count(mesh)
        assert vertex_count > 0
        assert face_count > 0
    
    def test_printability_assessment_stl(self, cad_agent, temp_dir):
        """Test printability assessment for exported STL."""
        mesh, _ = cad_agent.create_cube(20, 20, 20)
        output_file = os.path.join(temp_dir, "printability_test.stl")
        
        # Export first
        cad_agent._export_mesh_to_file(mesh, output_file)
        
        # Assess printability
        assessment = cad_agent._assess_stl_printability(mesh, output_file)
        
        assert isinstance(assessment, dict)
        assert "score" in assessment
        assert "issues" in assessment
        assert "recommendations" in assessment
        assert "support_needed" in assessment
        assert 0 <= assessment["score"] <= 10


class TestCADAgentAsyncTasks:
    """Test async task execution for CAD Agent."""
    
    @pytest.fixture
    def cad_agent(self):
        """Create a CAD Agent instance for testing."""
        return CADAgent("test_async_agent")
    
    @pytest.mark.asyncio
    async def test_execute_task_primitive_creation(self, cad_agent):
        """Test async task execution for primitive creation."""
        task_data = {
            "task_id": "test_001",
            "operation": "create_primitive",
            "specifications": {
                "primitive_creation": {
                    "shape": "cube",
                    "dimensions": {"x": 10, "y": 15, "z": 20}
                }
            },
            "requirements": {},
            "format_preference": "stl",
            "quality_level": "standard"
        }
        
        result = await cad_agent.execute_task(task_data)
        
        assert isinstance(result, TaskResult)
        assert result.success is True
        assert "model_file_path" in result.data
        assert result.data["model_format"] == "stl"
    
    @pytest.mark.asyncio
    async def test_execute_task_boolean_operation(self, cad_agent):
        """Test async task execution for boolean operations."""
        # First create two meshes
        mesh_a, _ = cad_agent.create_cube(10, 10, 10)
        mesh_b, _ = cad_agent.create_cube(10, 10, 10)
        
        # Save to temporary files
        temp_dir = tempfile.mkdtemp()
        try:
            mesh_a_path = os.path.join(temp_dir, "mesh_a.stl")
            mesh_b_path = os.path.join(temp_dir, "mesh_b.stl")
            
            cad_agent._export_mesh_to_file(mesh_a, mesh_a_path)
            cad_agent._export_mesh_to_file(mesh_b, mesh_b_path)
            
            task_data = {
                "task_id": "test_002",
                "operation": "boolean_operation",
                "specifications": {
                    "boolean_operation": {
                        "mesh_a_path": mesh_a_path,
                        "mesh_b_path": mesh_b_path,
                        "operation": "union"
                    }
                },
                "requirements": {},
                "format_preference": "stl",
                "quality_level": "standard"
            }
            
            result = await cad_agent.execute_task(task_data)
            
            assert isinstance(result, TaskResult)
            assert result.success is True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_execute_task_stl_export(self, cad_agent):
        """Test async task execution for STL export."""
        # First create a mesh
        mesh, _ = cad_agent.create_sphere(10)
        temp_dir = tempfile.mkdtemp()
        
        try:
            source_file = os.path.join(temp_dir, "source.stl")
            cad_agent._export_mesh_to_file(mesh, source_file)
            
            task_data = {
                "task_id": "test_003",
                "operation": "export_stl",
                "specifications": {
                    "stl_export": {
                        "source_file_path": source_file,
                        "quality_level": "high",
                        "perform_quality_check": True,
                        "auto_repair_issues": True
                    }
                },
                "requirements": {},
                "format_preference": "stl",
                "quality_level": "high"
            }
            
            result = await cad_agent.execute_task(task_data)
            
            assert isinstance(result, TaskResult)
            assert result.success is True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_execute_task_validation_error(self, cad_agent):
        """Test task execution with validation errors."""
        # Missing required fields
        task_data = {
            "task_id": "test_004",
            "operation": "create_primitive"
            # Missing specifications
        }
        
        result = await cad_agent.execute_task(task_data)
        assert isinstance(result, TaskResult)
        assert result.success is False
        assert "error_message" in result.__dict__
    
    @pytest.mark.asyncio
    async def test_execute_task_invalid_operation(self, cad_agent):
        """Test task execution with invalid operation."""
        task_data = {
            "task_id": "test_005",
            "operation": "invalid_operation",
            "specifications": {},
            "requirements": {},
            "format_preference": "stl",
            "quality_level": "standard"
        }
        
        result = await cad_agent.execute_task(task_data)
        
        assert isinstance(result, TaskResult)
        assert result.success is False
        assert "unknown" in result.error_message.lower() or "invalid" in result.error_message.lower()


class TestCADAgentDimensionValidation:
    """Test dimension validation for different shapes."""
    
    @pytest.fixture
    def cad_agent(self):
        """Create a CAD Agent instance for testing."""
        return CADAgent("test_validation_agent")
    
    def test_cube_dimension_validation(self, cad_agent):
        """Test cube dimension validation."""
        # Valid dimensions
        mesh, volume = cad_agent.create_cube(10, 20, 30)
        assert mesh is not None
        assert volume > 0
        
        # Edge case: minimum dimensions
        mesh, volume = cad_agent.create_cube(0.1, 0.1, 0.1)
        assert mesh is not None
        
        # Edge case: maximum dimensions
        mesh, volume = cad_agent.create_cube(300, 300, 300)
        assert mesh is not None
    
    def test_cylinder_dimension_validation(self, cad_agent):
        """Test cylinder dimension validation."""
        # Valid dimensions
        mesh, volume = cad_agent.create_cylinder(5, 10)
        assert mesh is not None
        assert volume > 0
        
        # Test segment validation
        mesh, volume = cad_agent.create_cylinder(5, 10, segments=16)
        assert mesh is not None
    
    def test_sphere_dimension_validation(self, cad_agent):
        """Test sphere dimension validation."""
        # Valid radius
        mesh, volume = cad_agent.create_sphere(10)
        assert mesh is not None
        assert volume > 0
        
        # Test segment validation
        mesh, volume = cad_agent.create_sphere(10, segments=32)
        assert mesh is not None
    
    def test_torus_dimension_validation(self, cad_agent):
        """Test torus dimension validation."""
        # Valid radii
        mesh, volume = cad_agent.create_torus(15, 5)
        assert mesh is not None
        assert volume > 0
    
    def test_cone_dimension_validation(self, cad_agent):
        """Test cone dimension validation."""
        # Complete cone
        mesh, volume = cad_agent.create_cone(10, 0, 15)
        assert mesh is not None
        assert volume > 0
        
        # Truncated cone
        mesh, volume = cad_agent.create_cone(10, 5, 15)
        assert mesh is not None
        assert volume > 0


class TestCADAgentIntegration:
    """Integration tests for CAD Agent."""
    
    @pytest.fixture
    def cad_agent(self):
        """Create a CAD Agent instance for integration testing."""
        return CADAgent("integration_test_agent")
    
    @pytest.mark.asyncio
    async def test_full_cad_workflow(self, cad_agent):
        """Test full CAD workflow from primitive to STL."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create primitive
            task_data = {
                "task_id": "integration_001",
                "operation": "create_primitive",
                "specifications": {
                    "primitive_creation": {
                        "shape": "torus",
                        "dimensions": {"major_radius": 15, "minor_radius": 5}
                    }
                },
                "requirements": {"material": "PLA"},
                "format_preference": "stl",
                "quality_level": "high"
            }
            
            result = await cad_agent.execute_task(task_data)
            
            assert result.success is True
            assert os.path.exists(result.data["model_file_path"])
            assert result.data["quality_score"] > 5
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_agent_status_tracking(self, cad_agent):
        """Test agent status tracking."""
        status = cad_agent.get_status()
        
        assert isinstance(status, dict)
        assert "agent_name" in status
        assert "agent_type" in status
        assert "current_status" in status
        assert status["agent_name"] == "integration_test_agent"
        assert status["agent_type"] == "CADAgent"
    
    def test_cleanup(self, cad_agent):
        """Test agent cleanup."""
        cad_agent.cleanup()
        
        # Verify cleanup completed without errors
        status = cad_agent.get_status()
        assert isinstance(status, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
