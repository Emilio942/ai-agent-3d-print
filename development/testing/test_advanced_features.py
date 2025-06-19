#!/usr/bin/env python3
"""
Test Advanced Features Implementation
Test the newly implemented advanced image processing and template library features
"""

import asyncio
import sys
import traceback
from pathlib import Path
import cv2

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_advanced_image_processor():
    """Test the advanced image processor with new implementations"""
    print("🔍 Testing Advanced Image Processor...")
    
    try:
        from agents.advanced_image_processor import AdvancedImageProcessor
        import numpy as np
        
        # Create test processor with config parameter
        processor = AdvancedImageProcessor({"name": "test_processor"})
        
        # Create test image (simple gradient)
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        print("  Testing Heightmap Mode...")
        heightmap_result = await processor._process_heightmap_mode(test_image, {
            'max_height': 10.0,
            'scale_x': 1.0,
            'scale_y': 1.0,
            'blur_kernel': 5
        })
        
        if heightmap_result['status'] == 'completed':
            print(f"  ✅ Heightmap: {heightmap_result['mesh_info']['vertex_count']} vertices")
        else:
            print(f"  ❌ Heightmap failed: {heightmap_result.get('error', 'Unknown error')}")
        
        print("  Testing Multi-Object Mode...")
        multi_obj_result = await processor._process_multi_object_mode(test_image, {
            'min_object_area': 100,
            'max_objects': 5,
            'base_height': 2.0,
            'object_height': 5.0
        })
        
        if multi_obj_result['status'] == 'completed':
            print(f"  ✅ Multi-Object: {multi_obj_result['object_count']} objects found")
        else:
            print(f"  ❌ Multi-Object failed: {multi_obj_result.get('error', 'Unknown error')}")
        
        print("  Testing Surface Mode...")
        surface_result = await processor._process_surface_mode(test_image, {
            'depth_scale': 10.0,
            'resolution': 2,
            'smooth_kernel': 3
        })
        
        if surface_result['status'] == 'completed':
            print(f"  ✅ Surface: {surface_result['mesh_info']['vertex_count']} vertices")
        else:
            print(f"  ❌ Surface failed: {surface_result.get('error', 'Unknown error')}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Advanced Image Processor test failed: {e}")
        traceback.print_exc()
        return False

async def test_template_library():
    """Test the template library with real CAD generation"""
    print("\n🏗️ Testing Template Library...")
    
    try:
        from core.template_library import TemplateLibrary
        
        # Create template library (no initialize method needed)
        library = TemplateLibrary()
        
        # Get available templates
        templates = await library.get_templates()
        print(f"  Available templates: {len(templates)}")
        
        # Test phone stand generation
        print("  Testing Phone Stand generation...")
        result = await library.customize_template("Phone Stand", {
            'angle': 20,
            'width': 90,
            'depth': 50,
            'thickness': 4
        })
        
        if result.get('success', False):
            method = result.get('generation_method', 'unknown')
            print(f"  ✅ Phone Stand generated using: {method}")
            print(f"     File: {result.get('file_path', 'N/A')}")
        else:
            print(f"  ❌ Phone Stand failed: {result.get('error', 'Unknown error')}")
        
        # Test gear generation
        print("  Testing Gear generation...")
        gear_result = await library.customize_template("Simple Gear", {
            'teeth': 16,
            'diameter': 30,
            'thickness': 4,
            'bore_diameter': 4
        })
        
        if gear_result.get('success', False):
            method = gear_result.get('generation_method', 'unknown')
            print(f"  ✅ Gear generated using: {method}")
        else:
            print(f"  ❌ Gear failed: {gear_result.get('error', 'Unknown error')}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Template Library test failed: {e}")
        traceback.print_exc()
        return False

async def test_image_to_3d_pipeline():
    """Test the complete image-to-3D pipeline"""
    print("\n🖼️ Testing Complete Image-to-3D Pipeline...")
    
    try:
        from core.ai_image_to_3d import AIImageTo3DConverter
        import numpy as np
        
        # Create test converter (no config parameter needed)
        converter = AIImageTo3DConverter()
        
        # Create test image
        test_image = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
        
        # Test different conversion modes
        modes = ['lithophane', 'relief', 'emboss']
        
        for mode in modes:
            print(f"  Testing {mode} mode...")
            
            # Convert numpy array to bytes for the converter
            _, img_bytes = cv2.imencode('.png', test_image)
            
            result = await converter.convert_image_to_3d(
                img_bytes.tobytes()
            )
            
            if result.get('success', False):
                print(f"  ✅ {mode} conversion successful")
                print(f"     Quality: {result.get('quality_score', 'N/A')}")
            else:
                print(f"  ❌ {mode} conversion failed: {result.get('error', 'Unknown error')}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Image-to-3D pipeline test failed: {e}")
        traceback.print_exc()
        return False

async def test_system_integration():
    """Test the complete system with new features"""
    print("\n⚡ Testing Complete System Integration...")
    
    try:
        # Test text-to-3D workflow (should work)
        print("  Testing Text-to-3D workflow...")
        from main import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        await orchestrator.initialize()
        
        result = await orchestrator.execute_complete_workflow(
            "Create a 2cm cube",
            show_progress=False
        )
        
        if result.get('success', False):
            print("  ✅ Text-to-3D workflow successful")
        else:
            print(f"  ❌ Text-to-3D workflow failed: {result.get('error_message', 'Unknown error')}")
        
        await orchestrator.shutdown()
        return True
        
    except Exception as e:
        print(f"  ❌ System integration test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Advanced Features Implementation")
    print("=" * 60)
    
    tests = [
        test_advanced_image_processor,
        test_template_library,
        test_image_to_3d_pipeline,
        test_system_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"  Passed: {sum(results)}/{len(results)}")
    print(f"  Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All tests passed! Advanced features are working!")
        return True
    else:
        print("⚠️ Some tests failed. Check implementation.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)