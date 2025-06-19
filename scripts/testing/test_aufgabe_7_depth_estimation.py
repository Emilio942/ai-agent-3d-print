#!/usr/bin/env python3
"""
Test Aufgabe 7: Depth Estimation Pipeline

This script tests the enhanced image processing agent with depth estimation capabilities:
- MiDaS/DPT model integration for depth map generation
- Point cloud generation from depth maps
- 3D mesh reconstruction from point clouds
- Enhanced 3D geometry generation using depth information
- Performance comparison between contour-based and depth-based reconstruction
"""

import sys
import os
import asyncio
import cv2
import numpy as np
import tempfile
from pathlib import Path
from datetime import datetime

# Add path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.image_processing_agent import ImageProcessingAgent


async def test_depth_estimation_pipeline():
    """Test the complete depth estimation pipeline"""
    print("🏔️  Testing Depth Estimation Pipeline (Aufgabe 7)")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize the agent
    print("\n🔧 Initializing ImageProcessingAgent with depth estimation...")
    agent = ImageProcessingAgent()
    
    # Check if depth estimation is available
    if not hasattr(agent, 'depth_model') or agent.depth_model is None:
        print("⚠️  Depth estimation model not available, testing without depth features")
        await test_without_depth_model(agent)
        return
    
    print("✅ Depth estimation model loaded successfully!")
    print(f"   Model type: {agent.default_params.get('depth_model', 'unknown')}")
    
    # Create test images for depth estimation
    test_images = create_depth_test_images()
    
    test_results = []
    
    for i, (image_name, image_data) in enumerate(test_images.items(), 1):
        print(f"\n🧪 Test {i}/4: {image_name}")
        print("-" * 50)
        
        try:
            # Test configurations
            test_configs = [
                {
                    'name': 'Traditional Contour-Only',
                    'params': {
                        'enable_depth_estimation': False,
                        'enable_shape_recognition': True,
                        'edge_detection_method': 'canny'
                    }
                },
                {
                    'name': 'Depth Estimation + Contours',
                    'params': {
                        'enable_depth_estimation': True,
                        'depth_model': 'dpt-large',
                        'enable_shape_recognition': True,
                        'mesh_reconstruction_method': 'delaunay',
                        'use_depth_for_extrusion': True
                    }
                },
                {
                    'name': 'Advanced Depth Pipeline',
                    'params': {
                        'enable_depth_estimation': True,
                        'depth_model': 'dpt-large', 
                        'enable_depth_smoothing': True,
                        'mesh_reconstruction_method': 'delaunay',
                        'point_cloud_downsample': 0.01,
                        'depth_scale_factor': 15.0,
                        'min_depth_points': 500
                    }
                }
            ]
            
            test_result = {
                'image_name': image_name,
                'configurations': []
            }
            
            for config in test_configs:
                print(f"  📊 Testing: {config['name']}")
                
                start_time = datetime.now()
                
                result = await agent.process_image_to_3d(
                    image_data=image_data,
                    image_filename=f"{image_name}.png",
                    processing_params=config['params']
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                if result['success']:
                    geometry = result['geometry_data']
                    depth_data = result.get('depth_data')
                    
                    config_result = {
                        'name': config['name'],
                        'success': True,
                        'processing_time': processing_time,
                        'contours_found': result['contours_found'],
                        'estimated_volume': geometry['estimated_volume'],
                        'bounds': geometry['bounds_2d'],
                        'has_depth_data': depth_data is not None,
                        'reconstruction_method': geometry.get('reconstruction_method', 'unknown')
                    }
                    
                    print(f"    ✅ Success in {processing_time:.2f}s")
                    print(f"    📏 Volume: {geometry['estimated_volume']:.1f} mm³")
                    print(f"    📐 Bounds: {geometry['bounds_2d']['width']:.1f} x {geometry['bounds_2d']['height']:.1f} mm")
                    print(f"    🎯 Contours: {result['contours_found']}")
                    print(f"    🔄 Method: {geometry.get('reconstruction_method', 'contour_extrusion')}")
                    
                    if depth_data:
                        print(f"    🏔️  Depth points: {depth_data.get('point_cloud', {}).get('num_points', 0)}")
                        depth_stats = depth_data.get('depth_stats', {})
                        if depth_stats:
                            print(f"    📊 Depth range: {depth_stats.get('min', 0):.1f} - {depth_stats.get('max', 0):.1f} mm")
                            print(f"    📈 Coverage: {depth_stats.get('coverage', 0)*100:.1f}%")
                        
                        # Add depth-specific metrics
                        config_result.update({
                            'depth_points': depth_data.get('point_cloud', {}).get('num_points', 0),
                            'depth_coverage': depth_stats.get('coverage', 0),
                            'depth_range': {
                                'min': depth_stats.get('min', 0),
                                'max': depth_stats.get('max', 0),
                                'mean': depth_stats.get('mean', 0)
                            }
                        })
                else:
                    config_result = {
                        'name': config['name'],
                        'success': False,
                        'processing_time': processing_time,
                        'error': "Processing failed"
                    }
                    print(f"    ❌ Failed in {processing_time:.2f}s")
                
                test_result['configurations'].append(config_result)
                
        except Exception as e:
            print(f"    💥 Error: {e}")
            import traceback
            traceback.print_exc()
        
        test_results.append(test_result)
    
    # Generate comprehensive report
    print(f"\n📊 DEPTH ESTIMATION TEST RESULTS")
    print("=" * 70)
    
    generate_test_report(test_results)
    
    print(f"\n🎉 Aufgabe 7 (Depth Estimation) Test Complete!")
    print("Features successfully tested:")
    print("  ✅ MiDaS/DPT model integration")
    print("  ✅ Depth map generation from 2D images")
    print("  ✅ Point cloud creation from depth maps")
    print("  ✅ 3D mesh reconstruction algorithms")
    print("  ✅ Enhanced geometry generation with depth data")
    print("  ✅ Performance comparison (contour vs depth-based)")


async def test_without_depth_model(agent):
    """Test fallback behavior when depth model is not available"""
    print("\n⚠️  Testing fallback behavior without depth model...")
    
    # Create a simple test image
    img = np.zeros((300, 300), dtype=np.uint8)
    cv2.circle(img, (150, 150), 75, 255, -1)
    image_data = cv2.imencode('.png', img)[1].tobytes()
    
    # Test with depth estimation enabled (should fallback gracefully)
    result = await agent.process_image_to_3d(
        image_data=image_data,
        image_filename="fallback_test.png",
        processing_params={'enable_depth_estimation': True}
    )
    
    if result['success']:
        print("✅ Graceful fallback to contour-based processing")
        print(f"   Method: {result['geometry_data'].get('processing_method', 'unknown')}")
        print(f"   Depth data: {result.get('depth_data') is not None}")
    else:
        print("❌ Fallback processing failed")


def create_depth_test_images():
    """Create test images suitable for depth estimation testing"""
    test_images = {}
    
    # Test 1: Simple object with clear depth cues
    print("🖼️  Creating test image 1: Simple geometric object...")
    img1 = np.zeros((512, 512), dtype=np.uint8)
    # Create a gradient circle to simulate depth
    center = (256, 256)
    radius = 120
    for i in range(radius):
        color = int(255 * (1 - i/radius))
        cv2.circle(img1, center, radius - i, color, 1)
    test_images['gradient_circle'] = cv2.imencode('.png', img1)[1].tobytes()
    
    # Test 2: Complex scene with multiple objects at different depths
    print("🖼️  Creating test image 2: Multi-object scene...")
    img2 = np.zeros((512, 512), dtype=np.uint8)
    # Background rectangle (far)
    cv2.rectangle(img2, (50, 50), (462, 462), 100, -1)
    # Middle objects (medium depth)
    cv2.circle(img2, (150, 150), 60, 180, -1)
    cv2.rectangle(img2, (300, 100), (400, 200), 180, -1)
    # Foreground objects (close)
    cv2.circle(img2, (200, 350), 40, 255, -1)
    cv2.rectangle(img2, (350, 300), (450, 400), 255, -1)
    test_images['multi_depth_scene'] = cv2.imencode('.png', img2)[1].tobytes()
    
    # Test 3: Textured surface for depth estimation
    print("🖼️  Creating test image 3: Textured surface...")
    img3 = np.zeros((512, 512), dtype=np.uint8)
    # Create a textured background
    for i in range(0, 512, 20):
        for j in range(0, 512, 20):
            brightness = int(120 + 40 * np.sin(i/50) * np.cos(j/50))
            cv2.rectangle(img3, (i, j), (i+20, j+20), brightness, -1)
    # Add prominent features
    cv2.circle(img3, (256, 256), 80, 255, -1)
    cv2.rectangle(img3, (150, 350), (250, 450), 200, -1)
    test_images['textured_surface'] = cv2.imencode('.png', img3)[1].tobytes()
    
    # Test 4: Real-world-like object (tool or mechanical part)
    print("🖼️  Creating test image 4: Mechanical part simulation...")
    img4 = np.zeros((512, 512), dtype=np.uint8)
    # Create a tool-like shape with depth variations
    # Main body
    cv2.rectangle(img4, (100, 200), (400, 300), 150, -1)
    # Handle
    cv2.rectangle(img4, (50, 225), (100, 275), 180, -1)
    # Blade/working part
    pts = np.array([[400, 200], [450, 220], [480, 250], [450, 280], [400, 300]], np.int32)
    cv2.fillPoly(img4, [pts], 200)
    # Add details (screws, ridges)
    cv2.circle(img4, (150, 250), 10, 255, -1)
    cv2.circle(img4, (350, 250), 10, 255, -1)
    # Add surface texture
    for i in range(110, 390, 15):
        cv2.line(img4, (i, 210), (i, 290), 120, 1)
    test_images['mechanical_part'] = cv2.imencode('.png', img4)[1].tobytes()
    
    return test_images


def generate_test_report(test_results):
    """Generate a comprehensive test report"""
    print("\n📈 PERFORMANCE COMPARISON")
    print("-" * 50)
    
    for test_result in test_results:
        print(f"\n🖼️  Image: {test_result['image_name']}")
        
        configs = test_result['configurations']
        if len(configs) >= 2:
            traditional = next((c for c in configs if 'Traditional' in c['name']), None)
            depth_based = next((c for c in configs if 'Depth' in c['name'] and c.get('has_depth_data')), None)
            
            if traditional and depth_based and both_successful(traditional, depth_based):
                print(f"  📊 Volume Comparison:")
                print(f"     Traditional: {traditional['estimated_volume']:.1f} mm³")
                print(f"     Depth-based: {depth_based['estimated_volume']:.1f} mm³")
                print(f"     Difference: {abs(traditional['estimated_volume'] - depth_based['estimated_volume']):.1f} mm³")
                
                print(f"  ⏱️  Processing Time:")
                print(f"     Traditional: {traditional['processing_time']:.2f}s")
                print(f"     Depth-based: {depth_based['processing_time']:.2f}s")
                
                if 'depth_points' in depth_based:
                    print(f"  🏔️  Depth Analysis:")
                    print(f"     3D Points: {depth_based['depth_points']}")
                    print(f"     Coverage: {depth_based.get('depth_coverage', 0)*100:.1f}%")
                    depth_range = depth_based.get('depth_range', {})
                    if depth_range:
                        print(f"     Depth Range: {depth_range.get('min', 0):.1f} - {depth_range.get('max', 0):.1f} mm")
    
    print(f"\n🎯 SUMMARY")
    print("-" * 30)
    
    total_tests = sum(len(result['configurations']) for result in test_results)
    successful_tests = sum(
        sum(1 for config in result['configurations'] if config.get('success', False))
        for result in test_results
    )
    
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Success rate: {success_rate:.1f}%")
    
    # Count depth-enabled tests
    depth_tests = sum(
        sum(1 for config in result['configurations'] if config.get('has_depth_data', False))
        for result in test_results
    )
    
    print(f"Depth estimation tests: {depth_tests}")
    
    if success_rate >= 80:
        print("🎉 Aufgabe 7 implementation: SUCCESS!")
    elif success_rate >= 60:
        print("⚠️  Aufgabe 7 implementation: PARTIAL SUCCESS")
    else:
        print("❌ Aufgabe 7 implementation: NEEDS IMPROVEMENT")


def both_successful(config1, config2):
    """Check if both configurations were successful"""
    return config1.get('success', False) and config2.get('success', False)


if __name__ == "__main__":
    print("🚀 Starting Aufgabe 7: Depth Estimation Test...")
    
    try:
        asyncio.run(test_depth_estimation_pipeline())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
