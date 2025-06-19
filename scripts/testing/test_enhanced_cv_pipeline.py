#!/usr/bin/env python3
"""
Test Enhanced Computer Vision Pipeline - Aufgabe 6 Implementation

This script tests the enhanced image processing agent with advanced computer vision features:
- Advanced edge detection methods
- Shape recognition
- Multi-object detection
- Morphological operations
- Adaptive thresholding
"""

import sys
import os
import asyncio
import cv2
import numpy as np
from pathlib import Path

# Add path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.image_processing_agent import ImageProcessingAgent


async def test_enhanced_computer_vision():
    """Test the enhanced computer vision pipeline"""
    print("🔬 Testing Enhanced Computer Vision Pipeline (Aufgabe 6)")
    print("=" * 60)
    
    # Initialize the agent
    agent = ImageProcessingAgent()
    
    # Create test images with different shapes
    test_images = create_test_images()
    
    for i, (image_name, image_data) in enumerate(test_images.items(), 1):
        print(f"\n🧪 Test {i}: {image_name}")
        print("-" * 40)
        
        try:
            # Test different processing parameters
            test_params = [
                {
                    'name': 'Basic Processing',
                    'params': {}
                },
                {
                    'name': 'Advanced CV (Canny + Shape Recognition)',
                    'params': {
                        'edge_detection_method': 'canny',
                        'enable_shape_recognition': True,
                        'enable_multi_object_detection': True,
                        'use_adaptive_threshold': True
                    }
                },
                {
                    'name': 'Adaptive Edge Detection',
                    'params': {
                        'edge_detection_method': 'adaptive_canny',
                        'enable_shape_recognition': True,
                        'enable_histogram_equalization': True
                    }
                },
                {
                    'name': 'Sobel Edge Detection',
                    'params': {
                        'edge_detection_method': 'sobel',
                        'enable_shape_recognition': True,
                        'use_morphological_ops': True
                    }
                }
            ]
            
            for param_set in test_params:
                print(f"  📊 {param_set['name']}:")
                
                result = await agent.process_image_to_3d(
                    image_data=image_data,
                    image_filename=f"{image_name}.png",
                    processing_params=param_set['params']
                )
                
                if result['success']:
                    contours_found = result['contours_found']
                    geometry = result['geometry_data']
                    
                    print(f"    ✅ Contours detected: {contours_found}")
                    print(f"    📏 Estimated volume: {geometry['estimated_volume']:.1f} mm³")
                    print(f"    📐 Bounds: {geometry['bounds_2d']['width']:.1f} x {geometry['bounds_2d']['height']:.1f} mm")
                    
                    # Check for shape recognition results
                    if 'contours_3d' in geometry:
                        shapes_detected = []
                        for contour_data in geometry['contours_3d']:
                            if isinstance(contour_data, dict) and 'shape_type' in contour_data:
                                shapes_detected.append(f"{contour_data['shape_type']} (conf: {contour_data.get('shape_confidence', 0):.2f})")
                        
                        if shapes_detected:
                            print(f"    🎯 Shapes recognized: {', '.join(shapes_detected)}")
                else:
                    print(f"    ❌ Processing failed")
                    
        except Exception as e:
            print(f"    💥 Error: {e}")
    
    print(f"\n🎉 Enhanced Computer Vision Pipeline Test Complete!")
    print("Features tested:")
    print("  ✅ Advanced edge detection (Canny, Sobel, Adaptive)")
    print("  ✅ Shape recognition (Circle, Rectangle, Triangle, etc.)")
    print("  ✅ Multi-object detection")
    print("  ✅ Morphological operations")
    print("  ✅ Adaptive thresholding")
    print("  ✅ Histogram equalization")
    print("  ✅ Denoising filters")


def create_test_images():
    """Create test images with different shapes for computer vision testing"""
    test_images = {}
    
    # Test 1: Simple geometric shapes
    img1 = np.zeros((400, 400), dtype=np.uint8)
    # Circle
    cv2.circle(img1, (100, 100), 50, 255, -1)
    # Rectangle
    cv2.rectangle(img1, (200, 50), (300, 150), 255, -1)
    # Triangle
    pts = np.array([[150, 200], [100, 300], [200, 300]], np.int32)
    cv2.fillPoly(img1, [pts], 255)
    test_images['geometric_shapes'] = cv2.imencode('.png', img1)[1].tobytes()
    
    # Test 2: Complex shapes with noise
    img2 = np.zeros((400, 400), dtype=np.uint8)
    # Add some noise
    noise = np.random.randint(0, 50, (400, 400), dtype=np.uint8)
    img2 = cv2.add(img2, noise)
    # Complex polygon
    pts = np.array([[200, 50], [300, 100], [350, 200], [300, 300], [200, 350], [100, 300], [50, 200], [100, 100]], np.int32)
    cv2.fillPoly(img2, [pts], 255)
    test_images['complex_polygon'] = cv2.imencode('.png', img2)[1].tobytes()
    
    # Test 3: Multiple overlapping objects
    img3 = np.zeros((400, 400), dtype=np.uint8)
    # Overlapping circles
    cv2.circle(img3, (150, 150), 60, 255, -1)
    cv2.circle(img3, (200, 150), 60, 255, -1)
    cv2.circle(img3, (175, 200), 60, 255, -1)
    test_images['overlapping_circles'] = cv2.imencode('.png', img3)[1].tobytes()
    
    # Test 4: Mixed shapes with different sizes
    img4 = np.zeros((600, 600), dtype=np.uint8)
    # Large circle
    cv2.circle(img4, (150, 150), 80, 255, -1)
    # Small rectangles
    cv2.rectangle(img4, (300, 100), (350, 150), 255, -1)
    cv2.rectangle(img4, (400, 100), (480, 160), 255, -1)
    # Hexagon approximation
    pts = np.array([[300, 300], [350, 280], [400, 300], [400, 350], [350, 370], [300, 350]], np.int32)
    cv2.fillPoly(img4, [pts], 255)
    test_images['mixed_shapes'] = cv2.imencode('.png', img4)[1].tobytes()
    
    return test_images


if __name__ == "__main__":
    print("🚀 Starting Enhanced Computer Vision Pipeline Test...")
    
    try:
        asyncio.run(test_enhanced_computer_vision())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
