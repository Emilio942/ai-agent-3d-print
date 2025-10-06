"""
Slicer API routes to slice STL files and list profiles.

Exposes:
- POST /api/slicer/slice: slice an STL using a given profile/preset
- GET  /api/slicer/profiles: list available profiles
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os

from agents.slicer_agent import SlicerAgent
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/slicer", tags=["slicer"])


class SliceRequest(BaseModel):
    stl_path: str = Field(..., description="Absolute path to STL to slice")
    profile: str = Field(..., description="Slicer profile name, e.g. 'cat_high_detail'")
    material_type: str = Field(default="PLA")
    quality_preset: str = Field(default="fine")
    infill_percentage: int = Field(default=12, ge=0, le=100)
    layer_height: Optional[float] = Field(default=None, gt=0, le=1.0)
    print_speed: Optional[int] = Field(default=None, gt=0, le=300)


@router.get("/profiles")
async def list_profiles() -> Dict[str, Any]:
    try:
        agent = SlicerAgent("api_slicer", config={"mock_mode": True})
        return {"profiles": list(agent.list_profiles().keys())}
    except Exception as e:
        logger.error(f"Failed to list profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/slice")
async def slice_model(req: SliceRequest) -> Dict[str, Any]:
    try:
        if not os.path.exists(req.stl_path):
            raise HTTPException(status_code=400, detail=f"STL not found: {req.stl_path}")

        agent = SlicerAgent("api_slicer", config={"mock_mode": True})
        result = await agent.slice_stl(
            stl_path=req.stl_path,
            profile_name=req.profile,
            material_type=req.material_type,
            quality_preset=req.quality_preset,
            infill_percentage=req.infill_percentage,
            layer_height=req.layer_height if req.layer_height else 0.12,
            print_speed=req.print_speed if req.print_speed else 35,
        )

        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Slicing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
