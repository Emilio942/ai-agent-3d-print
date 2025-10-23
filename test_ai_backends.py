#!/usr/bin/env python3
"""
Tests for AI 3D Backend Plugin System
"""

import pytest
import asyncio
import trimesh
from pathlib import Path

from core.ai_backends.base_backend import BaseAI3DBackend
from core.ai_backends.backend_registry import AI3DBackendRegistry, register_backend
from core.ai_backends.backend_manager import AI3DBackendManager


# Test Backend
@register_backend('test_backend')
class TestBackend(BaseAI3DBackend):
    """Simple test backend"""
    
    async def initialize(self) -> bool:
        self.is_initialized = True
        return True
    
    async def image_to_3d(self, image_path, params=None):
        mesh = trimesh.creation.box([5, 5, 5])
        return {'mesh': mesh, 'success': True, 'metadata': {'test': True}}
    
    async def text_to_3d(self, prompt, params=None):
        mesh = trimesh.creation.icosphere(radius=3)
        return {'mesh': mesh, 'success': True, 'metadata': {'prompt': prompt}}
    
    async def enhance_mesh(self, mesh, params=None):
        enhanced = mesh.subdivide()
        return {'mesh': enhanced, 'success': True, 'metadata': {}}
    
    def get_capabilities(self):
        return {
            'supports_image_to_3d': True,
            'supports_text_to_3d': True,
            'supports_mesh_enhancement': True
        }
    
    def get_backend_info(self):
        return {
            'name': 'Test Backend',
            'version': '1.0.0',
            'provider': 'test'
        }


class TestBackendRegistry:
    """Test the backend registry"""
    
    def test_register_backend(self):
        """Test registering a backend"""
        registry = AI3DBackendRegistry()
        
        # Test backend should be registered via decorator
        backends = registry.list_backends()
        assert 'test_backend' in backends
    
    def test_get_backend(self):
        """Test getting a backend instance"""
        registry = AI3DBackendRegistry()
        backend = registry.get_backend('test_backend')
        
        assert isinstance(backend, BaseAI3DBackend)
        assert isinstance(backend, TestBackend)
    
    def test_get_nonexistent_backend(self):
        """Test error when backend not found"""
        registry = AI3DBackendRegistry()
        
        with pytest.raises(KeyError):
            registry.get_backend('nonexistent_backend')


class TestBackendManager:
    """Test the backend manager"""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test manager initialization"""
        manager = AI3DBackendManager()
        success = await manager.initialize()
        
        assert success
        assert manager.active_backend is not None
    
    @pytest.mark.asyncio
    async def test_text_to_3d(self):
        """Test text to 3D generation"""
        manager = AI3DBackendManager()
        await manager.initialize()
        
        result = await manager.text_to_3d("test cube")
        
        assert result['success']
        assert result['mesh'] is not None
        assert isinstance(result['mesh'], trimesh.Trimesh)
        assert len(result['mesh'].vertices) > 0
    
    @pytest.mark.asyncio
    async def test_switch_backend(self):
        """Test switching backends"""
        manager = AI3DBackendManager()
        await manager.initialize()
        
        # Get current backend
        info1 = manager.get_active_backend_info()
        
        # Switch to test backend
        success = await manager.switch_backend('test_backend')
        assert success
        
        # Verify switch
        info2 = manager.get_active_backend_info()
        assert info2['name'] == 'Test Backend'
    
    @pytest.mark.asyncio
    async def test_backend_capabilities(self):
        """Test getting backend capabilities"""
        manager = AI3DBackendManager()
        await manager.initialize()
        
        capabilities = manager.get_active_backend_capabilities()
        
        assert 'supports_image_to_3d' in capabilities
        assert 'supports_text_to_3d' in capabilities
        assert 'supports_mesh_enhancement' in capabilities
    
    @pytest.mark.asyncio
    async def test_list_backends(self):
        """Test listing available backends"""
        manager = AI3DBackendManager()
        await manager.initialize()
        
        backends = manager.list_available_backends()
        
        assert isinstance(backends, dict)
        assert len(backends) > 0
        # At minimum local_depth and test_backend should be available
        assert 'local_depth' in backends or 'test_backend' in backends


class TestLocalDepthBackend:
    """Test the local depth backend"""
    
    @pytest.mark.asyncio
    async def test_local_backend_text_to_3d(self):
        """Test local backend text to 3D"""
        from core.ai_backends.local_depth_backend import LocalDepthBackend
        
        backend = LocalDepthBackend()
        await backend.initialize()
        
        result = await backend.text_to_3d("cube")
        
        assert result['success']
        assert result['mesh'] is not None
        assert len(result['mesh'].vertices) > 0
    
    @pytest.mark.asyncio
    async def test_local_backend_enhance_mesh(self):
        """Test mesh enhancement"""
        from core.ai_backends.local_depth_backend import LocalDepthBackend
        
        backend = LocalDepthBackend()
        await backend.initialize()
        
        # Create simple mesh
        original_mesh = trimesh.creation.box([10, 10, 10])
        original_vertices = len(original_mesh.vertices)
        
        # Enhance it
        result = await backend.enhance_mesh(
            original_mesh, 
            params={'subdivide': True}
        )
        
        assert result['success']
        enhanced_mesh = result['mesh']
        # Subdivided mesh should have more vertices
        assert len(enhanced_mesh.vertices) > original_vertices


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
