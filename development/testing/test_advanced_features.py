#!/usr/bin/env python3
"""
Test Advanced Features Implementation
Test the newly implemented advanced image processing and template library features
"""

import asyncio
import sys
from pathlib import Path
import cv2
import pytest

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

pytestmark = pytest.mark.asyncio


async def test_advanced_image_processor():
    """Test the advanced image processor with new implementations."""
    from agents.advanced_image_processor import AdvancedImageProcessor
    import numpy as np

    processor = AdvancedImageProcessor({"name": "test_processor"})
    test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    heightmap_result = await processor._process_heightmap_mode(test_image, {
        "max_height": 10.0,
        "scale_x": 1.0,
        "scale_y": 1.0,
        "blur_kernel": 5,
    })
    assert heightmap_result["status"] == "completed", heightmap_result.get("error", "heightmap failed")
    assert heightmap_result["mesh_info"]["vertex_count"] > 0

    multi_obj_result = await processor._process_multi_object_mode(test_image, {
        "min_object_area": 100,
        "max_objects": 5,
        "base_height": 2.0,
        "object_height": 5.0,
    })
    assert multi_obj_result["status"] == "completed", multi_obj_result.get("error", "multi-object failed")
    assert multi_obj_result["object_count"] >= 0

    surface_result = await processor._process_surface_mode(test_image, {
        "depth_scale": 10.0,
        "resolution": 2,
        "smooth_kernel": 3,
    })
    assert surface_result["status"] == "completed", surface_result.get("error", "surface failed")
    assert surface_result["mesh_info"]["vertex_count"] > 0


async def test_template_library():
    """Test the template library with real CAD generation."""
    from core.template_library import TemplateLibrary

    library = TemplateLibrary()

    templates = await library.get_templates()
    assert isinstance(templates, list)
    assert templates, "Expected at least one template"

    template = templates[0]
    customization_result = await library.customize_template(template.id, {})
    assert customization_result.get("success", False), customization_result.get("error")


async def test_image_to_3d_pipeline():
    """Test the complete image-to-3D pipeline."""
    from core.ai_image_to_3d import AIImageTo3DConverter
    import numpy as np

    converter = AIImageTo3DConverter()
    test_image = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)

    modes = ["lithophane", "relief", "emboss"]
    for mode in modes:
        _, img_bytes = cv2.imencode(".png", test_image)
        result = await converter.convert_image_to_3d(img_bytes.tobytes())
        assert result.get("success", False), f"{mode} conversion failed: {result.get('error')}"


async def test_system_integration():
    """Test the complete system with new features."""
    from main import WorkflowOrchestrator

    orchestrator = WorkflowOrchestrator()
    await orchestrator.initialize()
    try:
        result = await orchestrator.execute_complete_workflow(
            "Create a 2cm cube",
            show_progress=False,
        )
        assert result.get("success", False), result.get("error_message")
    finally:
        await orchestrator.shutdown()