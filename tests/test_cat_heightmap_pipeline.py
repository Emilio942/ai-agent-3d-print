import tempfile
from pathlib import Path

import pytest
import trimesh

from agents.cad_agent import CADAgent
from core.cat_heightmap import generate_cat_heightmap


@pytest.mark.asyncio
async def test_generated_cat_heightmap_produces_positive_volume(tmp_path: Path) -> None:
    """Ensure the procedural cat heightmap yields a watertight mesh with volume."""
    heightmap_path = generate_cat_heightmap(tmp_path / "cat_heightmap.png", size=192)
    cad_agent = CADAgent("test_cat_heightmap")
    task = {
        "task_id": "cat_heightmap_test",
        "operation": "create_from_image",
        "image_path": str(heightmap_path),
        "material": "PLA",
        "enforce_safety": True,
        "pixel_size_mm": 0.35,
        "height_scale": 8.0,
        "base_thickness": 2.0,
        "max_size": 192,
    }

    result = await cad_agent.execute_task(task)
    assert result.success, result.error_message or "CAD agent reported failure"

    stl_path = Path(result.data["stl_file_path"])
    assert stl_path.exists(), "CAD agent did not emit STL file"

    reported_volume = result.data.get("volume_mm3")
    assert reported_volume is None or reported_volume > 0, "CAD agent reported non-positive volume"

    mesh = trimesh.load_mesh(stl_path)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.dump().values()))

    assert mesh.volume is not None and mesh.volume > 0, "Generated cat mesh has non-positive volume"
    # Rough sanity checks on extents to ensure it's not a flat plate
    extents = mesh.extents
    assert extents[2] > 3.0, f"Cat height too small: {extents[2]:.2f}mm"
    assert extents[0] > 20.0 and extents[1] > 20.0, "Cat footprint unexpectedly small"
