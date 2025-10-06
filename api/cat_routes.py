"""
Cat conversion API routes

POST /api/convert/cat → returns printable STL from a single cat photo
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from core.logger import get_logger
from core.cat_to_3d import image_to_3d_cat_async


logger = get_logger(__name__)
router = APIRouter(prefix="/api/convert", tags=["cat"])


@router.post("/cat")
async def convert_cat_image(
    image: UploadFile = File(..., description="Cat image (jpg/png)"),
    material: str = Form("PLA"),
    pose: Optional[str] = Form(None, description="sitzend|stehend|schlafend (optional)"),
    enforce_safety: bool = Form(True),
    pixel_size_mm: float = Form(0.3),
    max_size: int = Form(192),
    height_scale: float = Form(8.0),
    base_thickness: float = Form(2.0),
    # Mesh clean tunables (optional)
    clean_mesh: bool = Form(True),
    smoothing_iterations: int = Form(10),
    smoothing_lambda: float = Form(0.5),
    smoothing_mu: float = Form(-0.53),
    decimation_target_faces: Optional[int] = Form(None),
    decimation_ratio: float = Form(0.7),
    target_height_mm: Optional[float] = Form(None),
    orient_to_bed: bool = Form(True),
    # Printability tunables
    nozzle_diameter_mm: float = Form(0.4),
    layer_height_mm: float = Form(0.2),
    support_overhang_deg: float = Form(50.0),
    # Hollowing tunables
    hollow_enabled: bool = Form(False),
    wall_thickness_mm: float = Form(2.5),
    drain_holes_count: int = Form(2),
    drain_hole_diameter_mm: float = Form(4.0),
    drain_hole_edge_margin_mm: float = Form(10.0),
):
    """Convert a single image to a printable cat STL, returning metadata and file paths."""
    try:
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload an image file")

        image_bytes = await image.read()
        params: Dict[str, Any] = {
            "material": material,
            "pose": pose,
            "enforce_safety": enforce_safety,
            "pixel_size_mm": pixel_size_mm,
            "max_size": max_size,
            "height_scale": height_scale,
            "base_thickness": base_thickness,
            # Mesh clean tunables
            "clean_mesh": clean_mesh,
            "smoothing_iterations": smoothing_iterations,
            "smoothing_lambda": smoothing_lambda,
            "smoothing_mu": smoothing_mu,
            "decimation_target_faces": decimation_target_faces,
            "decimation_ratio": decimation_ratio,
            "target_height_mm": target_height_mm,
            "orient_to_bed": orient_to_bed,
            # Printability
            "nozzle_diameter_mm": nozzle_diameter_mm,
            "layer_height_mm": layer_height_mm,
            "support_overhang_deg": support_overhang_deg,
            # Hollowing
            "hollow_enabled": hollow_enabled,
            "wall_thickness_mm": wall_thickness_mm,
            "drain_holes_count": drain_holes_count,
            "drain_hole_diameter_mm": drain_hole_diameter_mm,
            "drain_hole_edge_margin_mm": drain_hole_edge_margin_mm,
        }

        result = await image_to_3d_cat_async(image_bytes, params)
        return {
            "success": True,
            "created_at": datetime.now().isoformat(),
            **result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cat conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
