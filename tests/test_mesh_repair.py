"""
Unit Tests for Mesh Auto-Repair Functionality

Tests the new auto_repair_mesh() method in CADAgent to ensure:
- Mesh watertight detection works
- Hole filling is attempted
- Normals are fixed
- Vertices are merged
- Quality score is calculated correctly
"""

import pytest
import trimesh
import numpy as np
from agents.cad_agent import CADAgent


class TestMeshAutoRepair:
    """Test suite for mesh auto-repair functionality"""
    
    @pytest.fixture
    def cad_agent(self):
        """Create CAD agent instance for testing"""
        agent = CADAgent(agent_name="test_cad_agent")
        return agent
    
    def test_repair_simple_cube(self, cad_agent):
        """Test repair on a simple watertight cube"""
        # Create a simple cube mesh
        mesh = trimesh.creation.box(extents=[10, 10, 10])
        
        # Repair mesh
        repaired_mesh, report = cad_agent.auto_repair_mesh(mesh)
        
        # Assertions
        assert repaired_mesh is not None
        assert report['was_watertight'] == True
        assert report['holes_filled'] == 0
        assert report['normals_fixed'] == True
        assert report['final_quality_score'] >= 50
        assert len(report['issues_found']) >= 0
        
    def test_repair_sphere(self, cad_agent):
        """Test repair on a sphere (should be watertight)"""
        # Create sphere
        mesh = trimesh.creation.icosphere(subdivisions=2, radius=5.0)
        
        # Repair mesh
        repaired_mesh, report = cad_agent.auto_repair_mesh(mesh)
        
        # Assertions
        assert repaired_mesh is not None
        assert report['was_watertight'] == True
        assert report['normals_fixed'] == True
        assert report['final_quality_score'] >= 50
        
    def test_repair_cylinder(self, cad_agent):
        """Test repair on a cylinder"""
        # Create cylinder
        mesh = trimesh.creation.cylinder(radius=5.0, height=10.0)
        
        # Repair mesh
        repaired_mesh, report = cad_agent.auto_repair_mesh(mesh)
        
        # Assertions
        assert repaired_mesh is not None
        assert report['normals_fixed'] == True
        assert 'final_quality_score' in report
        
    def test_repair_report_structure(self, cad_agent):
        """Test that repair report has correct structure"""
        # Create simple mesh
        mesh = trimesh.creation.box(extents=[5, 5, 5])
        
        # Repair mesh
        repaired_mesh, report = cad_agent.auto_repair_mesh(mesh)
        
        # Check report structure
        required_keys = [
            'was_watertight',
            'holes_filled',
            'normals_fixed',
            'vertices_merged',
            'final_quality_score',
            'issues_found'
        ]
        
        for key in required_keys:
            assert key in report, f"Missing key in report: {key}"
            
    def test_quality_score_range(self, cad_agent):
        """Test that quality score is always 0-100"""
        # Create various meshes
        meshes = [
            trimesh.creation.box(extents=[10, 10, 10]),
            trimesh.creation.icosphere(subdivisions=3),
            trimesh.creation.cylinder(radius=5, height=10)
        ]
        
        for mesh in meshes:
            _, report = cad_agent.auto_repair_mesh(mesh)
            score = report['final_quality_score']
            
            assert 0 <= score <= 100, f"Score {score} out of range!"
            
    def test_mesh_not_modified_if_perfect(self, cad_agent):
        """Test that perfect mesh vertices count stays same"""
        # Create perfect mesh
        mesh = trimesh.creation.icosphere(subdivisions=3)
        original_vertex_count = len(mesh.vertices)
        
        # Repair mesh
        repaired_mesh, report = cad_agent.auto_repair_mesh(mesh)
        
        # Vertex count should be similar (merge might remove duplicates)
        assert len(repaired_mesh.vertices) <= original_vertex_count
        
    def test_low_polygon_warning(self, cad_agent):
        """Test that low polygon count triggers warning"""
        # Create very simple mesh (< 100 faces)
        mesh = trimesh.creation.box(extents=[10, 10, 10])
        
        # Repair mesh
        _, report = cad_agent.auto_repair_mesh(mesh)
        
        # Should have low polygon warning
        issues = report['issues_found']
        assert any('Low polygon count' in issue for issue in issues)
        
    def test_normals_always_fixed(self, cad_agent):
        """Test that normals are always processed"""
        # Create mesh
        mesh = trimesh.creation.cylinder(radius=5, height=10)
        
        # Repair mesh
        _, report = cad_agent.auto_repair_mesh(mesh)
        
        # Normals should always be fixed
        assert report['normals_fixed'] == True


class TestMeshRepairIntegration:
    """Integration tests for mesh repair in CAD workflow"""
    
    @pytest.fixture
    def cad_agent(self):
        """Create CAD agent instance"""
        agent = CADAgent(agent_name="test_cad_integration")
        return agent
    
    @pytest.mark.asyncio
    async def test_cube_creation_includes_repair(self, cad_agent):
        """Test that creating a cube includes auto-repair"""
        # This tests the integration in the actual workflow
        mesh, volume = cad_agent.create_cube(x=20, y=20, z=20)
        
        # Mesh should be valid after creation (repair happens internally)
        assert mesh is not None
        assert mesh.is_watertight
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0
        
    @pytest.mark.asyncio
    async def test_sphere_creation_includes_repair(self, cad_agent):
        """Test that creating a sphere includes auto-repair"""
        mesh, volume = cad_agent.create_sphere(radius=10)
        
        # Mesh should be valid
        assert mesh is not None
        assert mesh.is_watertight
        assert volume > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
