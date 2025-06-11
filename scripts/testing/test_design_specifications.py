#!/usr/bin/env python3
"""
Test script for Task 2.1.3: Design Specification Generator

This script tests the comprehensive design specification generation functionality
that transforms research results into detailed 3D specifications for the CAD Agent.
"""

import sys
import os
import json
from typing import Dict, Any

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.research_agent import ResearchAgent, create_test_intent_request
from core.logger import AgentLogger


def test_design_specifications_basic():
    """Test basic design specification generation."""
    print("\n=== TEST 1: Basic Design Specifications ===")
    
    agent = ResearchAgent("test_design_specs")
    
    test_cases = [
        {
            "request": "I want to print a 20mm cube in PLA",
            "expected_type": "cube",
            "expected_material": "PLA"
        },
        {
            "request": "Create a cylinder 30mm diameter and 50mm height",
            "expected_type": "cylinder",
            "expected_material": "PLA"
        },
        {
            "request": "Make a phone case for iPhone 14",
            "expected_type": "phone_case",
            "expected_material": "PLA"
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['request']}")
        
        task_details = create_test_intent_request(test_case["request"], "detailed")
        result = agent.execute_task(task_details)
        
        if result["success"]:
            specs = result["data"]["object_specifications"]
            print(f"✅ Success - Object Type: {specs['metadata']['object_type']}")
            print(f"   Material: {specs['materials']['type']}")
            print(f"   Geometry Type: {specs['geometry']['type']}")
            print(f"   Has Primitives: {'primitives' in specs}")
            print(f"   Has Manufacturing Specs: {'manufacturing' in specs}")
            print(f"   Has Constraints: {'constraints' in specs}")
            
            # Validate expected values
            if specs['metadata']['object_type'] == test_case['expected_type']:
                print(f"   ✓ Object type matches expected")
            else:
                print(f"   ✗ Object type mismatch: expected {test_case['expected_type']}")
        else:
            print(f"❌ Failed: {result.get('error_message', 'Unknown error')}")


def test_design_specifications_detailed():
    """Test detailed design specification generation."""
    print("\n=== TEST 2: Detailed Design Specifications ===")
    
    agent = ResearchAgent("test_detailed_specs")
    
    # Test with gear specifications
    test_request = "Create a gear with 24 teeth, module 2.5, thickness 8mm in ABS"
    print(f"\nTesting detailed gear: {test_request}")
    
    task_details = create_test_intent_request(test_request, "detailed")
    result = agent.execute_task(task_details)
    
    if result["success"]:
        specs = result["data"]["object_specifications"]
        print(f"✅ Success - Generated detailed specifications")
        
        # Check gear-specific parameters
        if "gear_parameters" in specs:
            gear_params = specs["gear_parameters"]
            print(f"   Teeth Count: {gear_params.get('teeth_count', 'Not specified')}")
            print(f"   Module: {gear_params.get('module', 'Not specified')}")
            print(f"   Pitch Diameter: {gear_params.get('pitch_diameter', 'Not specified'):.1f}mm")
            print(f"   Outer Diameter: {gear_params.get('outer_diameter', 'Not specified'):.1f}mm")
            print(f"   Pressure Angle: {gear_params.get('pressure_angle', 'Not specified')}°")
        
        # Check manufacturing specifications
        if "manufacturing" in specs:
            mfg = specs["manufacturing"]
            print(f"   Layer Height: {mfg.get('layer_height', 'Not specified')}mm")
            print(f"   Infill: {mfg.get('infill_percentage', 'Not specified')}%")
            print(f"   Print Speed: {mfg.get('print_speed', 'Not specified')}mm/s")
        
        # Check constraints
        if "constraints" in specs:
            constraints = specs["constraints"]
            print(f"   Min Wall Thickness: {constraints.get('minimum_wall_thickness', 'Not specified')}mm")
            print(f"   Max Overhang: {constraints.get('maximum_overhang_angle', 'Not specified')}°")
    else:
        print(f"❌ Failed: {result.get('error_message', 'Unknown error')}")


def test_design_specifications_complex():
    """Test complex object design specifications."""
    print("\n=== TEST 3: Complex Object Specifications ===")
    
    agent = ResearchAgent("test_complex_specs")
    
    # Test phone case with specific features
    test_request = "Make a flexible phone case for iPhone 14 with textured surface"
    print(f"\nTesting complex phone case: {test_request}")
    
    task_details = create_test_intent_request(test_request, "detailed")
    result = agent.execute_task(task_details)
    
    if result["success"]:
        specs = result["data"]["object_specifications"]
        print(f"✅ Success - Generated complex specifications")
        
        # Check primitives and operations
        if "primitives" in specs:
            print(f"   Primitives Count: {len(specs['primitives'])}")
            for i, primitive in enumerate(specs['primitives']):
                print(f"   Primitive {i+1}: {primitive.get('type', 'Unknown')} - {primitive.get('name', 'Unnamed')}")
        
        if "operations" in specs:
            print(f"   Operations Count: {len(specs['operations'])}")
            for i, operation in enumerate(specs['operations']):
                print(f"   Operation {i+1}: {operation.get('type', 'Unknown')}")
        
        if "cutouts" in specs:
            print(f"   Cutouts Count: {len(specs['cutouts'])}")
            for i, cutout in enumerate(specs['cutouts']):
                print(f"   Cutout {i+1}: {cutout.get('type', 'Unknown')}")
        
        # Check features
        if "features" in specs:
            features = specs["features"]
            print(f"   Special Features: {list(features.keys())}")
            
            if "surface_texture" in features:
                texture = features["surface_texture"]
                print(f"   Texture Type: {texture.get('type', 'Not specified')}")
                print(f"   Texture Pattern: {texture.get('pattern', 'Not specified')}")
    else:
        print(f"❌ Failed: {result.get('error_message', 'Unknown error')}")


def test_material_suitability():
    """Test material suitability calculations."""
    print("\n=== TEST 4: Material Suitability ===")
    
    agent = ResearchAgent("test_material_suitability")
    
    test_cases = [
        ("Create a gear with 20 teeth in ABS", "gear", "ABS"),
        ("Make a phone case in TPU", "phone_case", "TPU"),
        ("Print a bracket in PETG", "bracket", "PETG")
    ]
    
    for request, expected_type, expected_material in test_cases:
        print(f"\nTesting: {request}")
        
        task_details = create_test_intent_request(request, "standard")
        result = agent.execute_task(task_details)
        
        if result["success"]:
            specs = result["data"]["object_specifications"]
            materials = specs.get("materials", {})
            
            print(f"✅ Material: {materials.get('type', 'Unknown')}")
            print(f"   Suitability Score: {materials.get('suitability_score', 'Not calculated'):.1f}/10")
            print(f"   Alternative Materials: {materials.get('alternative_materials', [])}")
            
            # Check material properties
            if "properties" in materials:
                props = materials["properties"]
                print(f"   Density: {props.get('density', 'Unknown')}g/cm³")
                print(f"   Melting Point: {props.get('melting_point', 'Unknown')}°C")
                print(f"   Flexibility: {props.get('flexibility', 'Unknown')}")
        else:
            print(f"❌ Failed: {result.get('error_message', 'Unknown error')}")


def test_analysis_depth_variations():
    """Test different analysis depth settings."""
    print("\n=== TEST 5: Analysis Depth Variations ===")
    
    agent = ResearchAgent("test_analysis_depth")
    
    base_request = "Create a 25mm cube"
    depth_levels = ["basic", "standard", "detailed"]
    
    for depth in depth_levels:
        print(f"\nTesting analysis depth: {depth}")
        
        task_details = create_test_intent_request(base_request, depth)
        result = agent.execute_task(task_details)
        
        if result["success"]:
            specs = result["data"]["object_specifications"]
            mfg = specs.get("manufacturing", {})
            
            print(f"✅ Analysis Depth: {depth}")
            print(f"   Layer Height: {mfg.get('layer_height', 'Not specified')}mm")
            print(f"   Print Speed: {mfg.get('print_speed', 'Not specified')}mm/s")
            print(f"   Infill: {mfg.get('infill_percentage', 'Not specified')}%")
            print(f"   Wall Count: {mfg.get('wall_count', 'Not specified')}")
        else:
            print(f"❌ Failed: {result.get('error_message', 'Unknown error')}")


def test_specification_validation():
    """Test specification validation and completeness."""
    print("\n=== TEST 6: Specification Validation ===")
    
    agent = ResearchAgent("test_validation")
    
    test_request = "Create a hollow sphere 40mm diameter"
    print(f"\nTesting validation: {test_request}")
    
    task_details = create_test_intent_request(test_request, "detailed")
    result = agent.execute_task(task_details)
    
    if result["success"]:
        specs = result["data"]["object_specifications"]
        
        # Check required sections
        required_sections = ["geometry", "materials", "manufacturing", "constraints", "metadata"]
        missing_sections = []
        
        for section in required_sections:
            if section in specs:
                print(f"✅ {section.title()} section present")
            else:
                missing_sections.append(section)
                print(f"❌ {section.title()} section missing")
        
        # Check validation status
        if "validation" in specs:
            validation = specs["validation"]
            print(f"✅ Validation Status: {validation.get('status', 'Unknown')}")
            
            if "warnings" in validation and validation["warnings"]:
                print(f"   Warnings: {len(validation['warnings'])}")
                for warning in validation["warnings"]:
                    print(f"   - {warning}")
            else:
                print("   No warnings")
        
        # Check hollow feature specifications
        if "features" in specs and "hollow" in specs["features"]:
            hollow = specs["features"]["hollow"]
            print(f"✅ Hollow Feature Detected")
            print(f"   Wall Thickness: {hollow.get('wall_thickness', 'Not specified')}mm")
            print(f"   Drainage Holes: {hollow.get('drainage_holes', 'Not specified')}")
        
        if not missing_sections:
            print("✅ All required sections present")
    else:
        print(f"❌ Failed: {result.get('error_message', 'Unknown error')}")


def save_sample_specifications():
    """Save sample specifications to files for inspection."""
    print("\n=== Saving Sample Specifications ===")
    
    agent = ResearchAgent("test_sample_specs")
    
    samples = [
        ("cube_20mm_pla.json", "Create a 20mm cube in PLA"),
        ("gear_24t_abs.json", "Make a gear with 24 teeth in ABS"),
        ("phone_case_tpu.json", "Create a flexible phone case in TPU"),
        ("hollow_sphere_40mm.json", "Make a hollow sphere 40mm diameter")
    ]
    
    output_dir = "data/sample_specifications"
    os.makedirs(output_dir, exist_ok=True)
    
    for filename, request in samples:
        print(f"Generating: {filename}")
        
        task_details = create_test_intent_request(request, "detailed")
        result = agent.execute_task(task_details)
        
        if result["success"]:
            specs = result["data"]["object_specifications"]
            
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(specs, f, indent=2)
            
            print(f"✅ Saved to {filepath}")
        else:
            print(f"❌ Failed to generate {filename}")


def main():
    """Run all tests for design specification generation."""
    print("TESTING TASK 2.1.3: Design Specification Generator")
    print("=" * 60)
    
    try:
        test_design_specifications_basic()
        test_design_specifications_detailed()
        test_design_specifications_complex()
        test_material_suitability()
        test_analysis_depth_variations()
        test_specification_validation()
        save_sample_specifications()
        
        print("\n" + "=" * 60)
        print("✅ TASK 2.1.3 TESTING COMPLETED")
        print("📋 Features tested:")
        print("   - Basic design specification generation")
        print("   - Detailed geometric specifications")
        print("   - Complex object specifications (phone case, gear)")
        print("   - Material suitability calculations")
        print("   - Analysis depth variations")
        print("   - Specification validation and completeness")
        print("   - Sample specification file generation")
        
    except Exception as e:
        print(f"\n❌ Testing failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
