#!/usr/bin/env python3
"""
Example: How to use the AI 3D Backend Plugin System
AI Agent 3D Print System

This file demonstrates how to:
1. Use different AI backends
2. Switch between backends
3. Create custom backends
4. Configure backends via YAML
"""

import asyncio
from pathlib import Path
import trimesh

from core.ai_backends.backend_manager import get_ai_backend_manager
from core.ai_backends.base_backend import BaseAI3DBackend
from core.ai_backends.backend_registry import register_backend


# ============================================================================
# EXAMPLE 1: Basic Usage - Use Active Backend from Config
# ============================================================================

async def example_basic_usage():
    """Use the AI backend configured in ai_backends.yaml"""
    print("\n📦 EXAMPLE 1: Basic Usage")
    print("=" * 60)
    
    # Get manager instance
    manager = get_ai_backend_manager()
    await manager.initialize()
    
    # Check active backend
    info = manager.get_active_backend_info()
    print(f"Active Backend: {info['name']} v{info['version']}")
    print(f"Provider: {info['provider']}")
    
    # Generate 3D from text
    result = await manager.text_to_3d("a cool cube")
    if result['success']:
        mesh = result['mesh']
        print(f"✅ Generated mesh: {len(mesh.vertices)} vertices")
        mesh.export("output/example_cube.stl")
    
    await manager.cleanup()


# ============================================================================
# EXAMPLE 2: Switch Backends Dynamically
# ============================================================================

async def example_switch_backends():
    """Switch between different AI backends at runtime"""
    print("\n🔄 EXAMPLE 2: Switch Backends")
    print("=" * 60)
    
    manager = get_ai_backend_manager()
    await manager.initialize()
    
    # List available backends
    backends = manager.list_available_backends()
    print(f"Available backends: {list(backends.keys())}")
    
    # Try local backend
    print("\n→ Using local_depth backend:")
    await manager.switch_backend('local_depth')
    result1 = await manager.text_to_3d("sphere")
    print(f"Result: {result1['metadata']}")
    
    # Switch to mock cloud
    print("\n→ Switching to mock_cloud backend:")
    await manager.switch_backend('mock_cloud')
    result2 = await manager.text_to_3d("sphere")
    print(f"Result: {result2['metadata']}")
    
    await manager.cleanup()


# ============================================================================
# EXAMPLE 3: Create Your Own Custom Backend
# ============================================================================

@register_backend('my_custom_backend')
class MyCustomBackend(BaseAI3DBackend):
    """
    Example custom backend - implements your own AI model or API.
    """
    
    async def initialize(self) -> bool:
        print("🎨 Initializing My Custom Backend")
        self.is_initialized = True
        return True
    
    async def image_to_3d(self, image_path, params=None):
        # Your custom implementation here
        mesh = trimesh.creation.icosphere(radius=10)
        return {
            'mesh': mesh,
            'metadata': {'custom': 'This is my custom backend!'},
            'success': True
        }
    
    async def text_to_3d(self, prompt, params=None):
        # Your custom implementation here
        mesh = trimesh.creation.box([5, 5, 5])
        return {
            'mesh': mesh,
            'metadata': {'prompt': prompt, 'custom': True},
            'success': True
        }
    
    async def enhance_mesh(self, mesh, params=None):
        enhanced = mesh.subdivide()
        return {'mesh': enhanced, 'success': True, 'metadata': {}}
    
    def get_capabilities(self):
        return {
            'supports_image_to_3d': True,
            'supports_text_to_3d': True,
            'supports_mesh_enhancement': True,
            'max_resolution': (512, 512),
            'supported_formats': ['png', 'jpg'],
            'runs_locally': True,
            'requires_gpu': False,
            'cost_info': {'cost_per_generation': 0.0, 'currency': 'USD'}
        }
    
    def get_backend_info(self):
        return {
            'name': 'My Custom Backend',
            'version': '1.0.0',
            'provider': 'custom',
            'description': 'Example custom backend implementation'
        }


async def example_custom_backend():
    """Use your own custom backend"""
    print("\n🎨 EXAMPLE 3: Custom Backend")
    print("=" * 60)
    
    manager = get_ai_backend_manager()
    await manager.initialize()
    
    # Switch to your custom backend
    await manager.switch_backend('my_custom_backend')
    
    # Use it
    result = await manager.text_to_3d("custom object")
    print(f"✅ Custom backend result: {result['metadata']}")
    
    await manager.cleanup()


# ============================================================================
# EXAMPLE 4: Image to 3D with Different Backends
# ============================================================================

async def example_image_to_3d():
    """Convert image to 3D using configured backend"""
    print("\n📸 EXAMPLE 4: Image to 3D")
    print("=" * 60)
    
    manager = get_ai_backend_manager()
    await manager.initialize()
    
    # Assuming you have a test image
    image_path = "test_input.jpg"
    if not Path(image_path).exists():
        print(f"⚠️ Test image not found: {image_path}")
        return
    
    # Convert with parameters
    params = {
        'depth_scale': 1.5,
        'extrusion_height': 15.0,
        'smoothing': True
    }
    
    result = await manager.image_to_3d(image_path, params)
    
    if result['success']:
        mesh = result['mesh']
        print(f"✅ Generated 3D model:")
        print(f"   Vertices: {len(mesh.vertices)}")
        print(f"   Faces: {len(mesh.faces)}")
        print(f"   Watertight: {mesh.is_watertight}")
        print(f"   Metadata: {result['metadata']}")
        
        mesh.export("output/from_image.stl")
        print("   Saved to: output/from_image.stl")
    else:
        print(f"❌ Failed: {result['metadata']}")
    
    await manager.cleanup()


# ============================================================================
# EXAMPLE 5: Fallback on Error
# ============================================================================

async def example_fallback():
    """Demonstrate automatic fallback when primary backend fails"""
    print("\n🔄 EXAMPLE 5: Automatic Fallback")
    print("=" * 60)
    
    manager = get_ai_backend_manager()
    await manager.initialize()
    
    # This will try primary backend, then fallback if it fails
    result = await manager.text_to_3d(
        "complex object",
        use_fallback_on_error=True
    )
    
    print(f"Result: {result['metadata']}")
    
    await manager.cleanup()


# ============================================================================
# EXAMPLE 6: Check Backend Capabilities
# ============================================================================

async def example_check_capabilities():
    """Check what the current backend can do"""
    print("\n🔍 EXAMPLE 6: Check Capabilities")
    print("=" * 60)
    
    manager = get_ai_backend_manager()
    await manager.initialize()
    
    capabilities = manager.get_active_backend_capabilities()
    
    print("Current Backend Capabilities:")
    print(f"  Image to 3D: {capabilities.get('supports_image_to_3d')}")
    print(f"  Text to 3D: {capabilities.get('supports_text_to_3d')}")
    print(f"  Mesh Enhancement: {capabilities.get('supports_mesh_enhancement')}")
    print(f"  Max Resolution: {capabilities.get('max_resolution')}")
    print(f"  Runs Locally: {capabilities.get('runs_locally')}")
    print(f"  Requires GPU: {capabilities.get('requires_gpu')}")
    
    cost = capabilities.get('cost_info', {})
    print(f"  Cost per Generation: ${cost.get('cost_per_generation', 0)} {cost.get('currency', 'USD')}")
    
    await manager.cleanup()


# ============================================================================
# Run Examples
# ============================================================================

async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("AI 3D BACKEND PLUGIN SYSTEM - EXAMPLES")
    print("=" * 60)
    
    # await example_basic_usage()
    # await example_switch_backends()
    # await example_custom_backend()
    # await example_image_to_3d()
    # await example_fallback()
    await example_check_capabilities()
    
    print("\n✅ All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
