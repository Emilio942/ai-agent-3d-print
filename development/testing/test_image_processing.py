#!/usr/bin/env python3
"""
Test script for the Image Processing Agent

This script tests the image-to-3D conversion functionality by:
1. Creating a simple test image
2. Processing it through the image processing agent
3. Generating a 3D model using the CAD agent
4. Validating the complete workflow
"""

import asyncio
import numpy as np
import cv2
from PIL import Image
import io
import tempfile
from pathlib import Path

# Test the import
try:
    from agents.image_processing_agent import ImageProcessingAgent
    from agents.cad_agent import CADAgent
    print("✅ Successfully imported image processing modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

async def test_image_processing():
    """Test the complete image processing workflow"""
    print("🚀 Starting image processing test...")
    
    # Create a simple test image (a circle)
    print("1. Creating test image...")
    image_size = (200, 200)
    image = np.zeros(image_size, dtype=np.uint8)
    
    # Draw a circle
    center = (100, 100)
    radius = 60
    cv2.circle(image, center, radius, 255, -1)
    
    # Convert to PIL and then to bytes
    pil_image = Image.fromarray(image)
    image_bytes = io.BytesIO()
    pil_image.save(image_bytes, format='PNG')
    image_data = image_bytes.getvalue()
    print(f"   Test image created: {len(image_data)} bytes")
    
    # Initialize agents
    print("2. Initializing agents...")
    image_agent = ImageProcessingAgent()
    cad_agent = CADAgent()
    
    # Test image validation
    print("3. Validating image...")
    validation_result = image_agent.validate_image(image_data, "test_circle.png")
    print(f"   Validation result: {validation_result}")
    
    if not validation_result["valid"]:
        print("❌ Image validation failed")
        return False
    
    # Process image to 3D
    print("4. Processing image to 3D...")
    processing_params = {
        "default_extrusion_height": 8.0,
        "base_thickness": 2.0,
        "max_image_size": (400, 400),
        "canny_threshold1": 50,
        "canny_threshold2": 150
    }
    
    try:
        result = await image_agent.process_image_to_3d(
            image_data, "test_circle.png", processing_params
        )
        
        if not result["success"]:
            print("❌ Image processing failed")
            return False
            
        print(f"   ✅ Image processed successfully!")
        print(f"   - Found {result['contours_found']} contours")
        print(f"   - Estimated volume: {result['geometry_data']['estimated_volume']:.2f} mm³")
        
        # Test CAD generation
        print("5. Creating 3D model from contours...")
        cad_input = result["cad_agent_input"]
        
        task_data = {
            "operation": "create_from_contours",
            "contours": cad_input["contours"],
            "extrusion_height": cad_input["extrusion_height"],
            "base_thickness": cad_input["base_thickness"]
        }
        
        cad_result = await cad_agent.execute_task(task_data)
        
        if not cad_result.success:
            print(f"❌ CAD generation failed: {cad_result.error_message}")
            return False
        
        print(f"   ✅ 3D model generated successfully!")
        print(f"   - Model file: {cad_result.data.get('model_file_path', 'N/A')}")
        print(f"   - Volume: {cad_result.data.get('volume', 0):.2f} mm³")
        print(f"   - Printability score: {cad_result.data.get('printability_score', 0):.1f}/100")
        
        # Check if file was created
        model_file = cad_result.data.get('model_file_path')
        if model_file and Path(model_file).exists():
            file_size = Path(model_file).stat().st_size
            print(f"   - STL file size: {file_size} bytes")
            
            # Clean up
            Path(model_file).unlink()
            print("   - Cleaned up temporary files")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_contour_extraction():
    """Test contour extraction separately"""
    print("\n🔍 Testing contour extraction...")
    
    # Create a more complex test image with multiple shapes
    image = np.zeros((300, 300), dtype=np.uint8)
    
    # Rectangle
    cv2.rectangle(image, (50, 50), (120, 120), 255, -1)
    
    # Circle
    cv2.circle(image, (200, 200), 40, 255, -1)
    
    # Save test image for inspection
    test_image_path = "/home/emilio/Documents/ai/ai-agent-3d-print/test_shapes.png"
    cv2.imwrite(test_image_path, image)
    print(f"   Test image saved to: {test_image_path}")
    
    # Test edge detection
    edges = cv2.Canny(image, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    print(f"   Found {len(contours)} contours")
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        print(f"   - Contour {i}: area={area:.1f}, perimeter={perimeter:.1f}")
    
    return len(contours) > 0

async def main():
    """Run all tests"""
    print("🧪 Image Processing Agent Test Suite")
    print("=" * 50)
    
    # Test 1: Contour extraction
    contour_test = test_contour_extraction()
    
    # Test 2: Full workflow
    workflow_test = await test_image_processing()
    
    print("\n📊 Test Results:")
    print(f"   Contour extraction: {'✅ PASS' if contour_test else '❌ FAIL'}")
    print(f"   Full workflow: {'✅ PASS' if workflow_test else '❌ FAIL'}")
    
    if contour_test and workflow_test:
        print("\n🎉 All tests passed! Image→3D processing is working!")
        return True
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
