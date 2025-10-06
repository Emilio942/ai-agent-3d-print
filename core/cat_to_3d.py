"""
Cat-specific Image→3D conversion service

Implements image_to_3d_cat(): Single-image reconstruction to a printable STL,
leveraging the CADAgent's optimized image heightmap path plus printability guardrails.
"""

from __future__ import annotations

import io
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import trimesh
from PIL import Image

# Local imports
from agents.cad_agent import CADAgent
from core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class CatConversionParams:
    """Parameters for cat image→3D conversion."""
    material: str = "PLA"
    enforce_safety: bool = True
    pixel_size_mm: float = 0.3  # finer XY scaling for details
    max_size: int = 192  # cap to keep mesh sizes sane
    height_scale: float = 8.0
    base_thickness: float = 2.0
    pose: Optional[str] = None  # "sitzend|stehend|schlafend" (advisory for future)
    # Mesh clean tunables
    clean_mesh: bool = True
    smoothing_iterations: int = 10
    smoothing_lambda: float = 0.5  # for Laplacian; Taubin will override
    smoothing_mu: float = -0.53     # for Taubin smoothing second pass
    decimation_target_faces: Optional[int] = None  # if None, compute from ratio
    decimation_ratio: float = 0.7  # keep 70% faces by default
    target_height_mm: Optional[float] = None  # scale model so Z height == value
    orient_to_bed: bool = True  # translate so min Z = 0; optional axis align
    # Printability check tunables
    nozzle_diameter_mm: float = 0.4
    layer_height_mm: float = 0.2
    support_overhang_deg: float = 50.0
    # Hollowing & drain holes (optional)
    hollow_enabled: bool = False
    wall_thickness_mm: float = 2.5
    drain_holes_count: int = 2
    drain_hole_diameter_mm: float = 4.0
    drain_hole_edge_margin_mm: float = 10.0


def _ensure_dirs() -> Dict[str, Path]:
    base = Path("data")
    uploads = base / "uploads" / "cats"
    outputs = base / "converted_models"
    uploads.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)
    return {"uploads": uploads, "outputs": outputs}


def _save_image_bytes(image_bytes: bytes, uploads_dir: Path) -> Path:
    """Persist uploaded image bytes to a deterministic path (PNG)."""
    # Validate image by loading through PIL; fallback to OpenCV if needed
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
    except Exception:
        try:
            import numpy as _np
            import cv2 as _cv2
            arr = _np.frombuffer(image_bytes, dtype=_np.uint8)
            bgr = _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError("Failed to decode image bytes")
            rgb = _cv2.cvtColor(bgr, _cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
        except Exception as e:
            raise ValueError(f"Invalid image data: {e}")
    model_id = f"cat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    img_path = uploads_dir / f"{model_id}.png"
    img.save(img_path)
    return img_path


def _repair_mesh_if_needed(stl_path: Path) -> Dict[str, Any]:
    """Load, attempt simple repairs if not watertight, save back, return metrics."""
    try:
        mesh = trimesh.load_mesh(str(stl_path))
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.dump().values()))
        # Initial metrics
        metrics = {
            "vertex_count": int(len(mesh.vertices)),
            "face_count": int(len(mesh.faces)),
            "surface_area": float(mesh.area),
            "volume_mm3": float(mesh.volume),
            "is_watertight": bool(mesh.is_watertight),
        }
        if mesh.is_watertight:
            return metrics
        # Try light repairs
        try:
            mesh.remove_degenerate_faces()
            mesh.remove_duplicate_faces()
            mesh.remove_unreferenced_vertices()
            mesh.fix_normals()
            # fill_holes may not always be available/robust; guard with try
            try:
                mesh.fill_holes()
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Mesh cleanup failed: {e}")
        # If still not watertight, attempt Manifold3D repair, then convex hull as last resort
        if not mesh.is_watertight:
            # Manifold3D attempt
            try:
                import numpy as _np
                import manifold3d as _mf
                v = _np.asarray(mesh.vertices, dtype=_np.float64)
                f = _np.asarray(mesh.faces, dtype=_np.int32)
                m = _mf.Manifold(_mf.Mesh(v, f))
                pos, tri = m.to_mesh()
                if pos is not None and tri is not None and len(pos) > 0 and len(tri) > 0:
                    mesh = trimesh.Trimesh(vertices=_np.asarray(pos), faces=_np.asarray(tri), process=True)
            except Exception as e:
                logger.warning(f"Manifold3D repair failed: {e}")
            # Convex hull fallback guarantees watertightness
            if not mesh.is_watertight:
                try:
                    hull = mesh.convex_hull
                    if isinstance(hull, trimesh.Trimesh):
                        mesh = hull
                except Exception as e:
                    logger.warning(f"Convex hull fallback failed: {e}")
        # Re-evaluate and save back
        mesh.export(str(stl_path))
        metrics.update({
            "vertex_count": int(len(mesh.vertices)),
            "face_count": int(len(mesh.faces)),
            "surface_area": float(mesh.area),
            "volume_mm3": float(mesh.volume),
            "is_watertight": bool(mesh.is_watertight),
        })
        return metrics
    except Exception as e:
        logger.warning(f"Failed to validate/repair STL: {e}")
        return {"error": str(e)}


def _try_smoothing(mesh: trimesh.Trimesh, iterations: int, lam: float, mu: float) -> None:
    """Apply gentle smoothing to reduce stair-steps while preserving features.
    Prefer Taubin smoothing if available; fall back to Laplacian.
    """
    try:
        from trimesh.smoothing import filter_taubin
        filter_taubin(mesh, lamb=lam, nu=mu, iterations=iterations)
        return
    except Exception:
        pass
    try:
        from trimesh.smoothing import filter_laplacian
        filter_laplacian(mesh, lamb=lam, iterations=iterations)
    except Exception as e:
        logger.debug(f"Smoothing skipped: {e}")


def _try_decimate(mesh: trimesh.Trimesh, target_faces: Optional[int], ratio: float) -> None:
    """Decimate mesh to target face count or ratio using quadratic error metric if available."""
    try:
        # Determine target
        faces_now = int(len(mesh.faces))
        target = target_faces if (target_faces and target_faces > 0) else max(1000, int(faces_now * ratio))
        target = min(target, max(faces_now - 1, 1000))
        if target <= 0 or target >= faces_now:
            return
        # Try trimesh's built-in QEM decimator
        try:
            mesh_simplified = trimesh.remesh.simplify_quadratic_decimation(mesh, target)
            if isinstance(mesh_simplified, trimesh.Trimesh) and len(mesh_simplified.faces) < faces_now:
                mesh.vertices = mesh_simplified.vertices
                mesh.faces = mesh_simplified.faces
                mesh.fix_normals()
                return
        except Exception:
            pass
        # Some versions offer method on the mesh instance
        try:
            simplified = mesh.simplify_quadratic_decimation(target)
            if isinstance(simplified, trimesh.Trimesh) and len(simplified.faces) < faces_now:
                mesh.vertices = simplified.vertices
                mesh.faces = simplified.faces
                mesh.fix_normals()
        except Exception as e:
            logger.debug(f"Decimation skipped: {e}")
    except Exception as e:
        logger.debug(f"Decimation error: {e}")


def _orient_and_place_on_bed(mesh: trimesh.Trimesh, pose: Optional[str], orient_to_bed: bool) -> None:
    """Simple orientation: optionally align primary axis and place min Z at 0."""
    try:
        if orient_to_bed:
            # Optional axis alignment: align the axis of greatest extent to Z for standing pose
            if pose and pose.lower() in {"stehend", "standing"}:
                extents = mesh.extents
                # Index of largest extent
                axis = int(np.argmax(extents))
                basis = [np.array([1, 0, 0], dtype=float), np.array([0, 1, 0], dtype=float), np.array([0, 0, 1], dtype=float)]
                target = np.array([0, 0, 1], dtype=float)
                source = basis[axis]
                T = trimesh.geometry.align_vectors(source, target)
                mesh.apply_transform(T)
            # Always move onto Z=0 bed
            min_z = float(mesh.bounds[0][2])
            if min_z != 0.0:
                mesh.apply_translation([0.0, 0.0, -min_z])
    except Exception as e:
        logger.debug(f"Orientation skipped: {e}")


def _scale_to_target_height(mesh: trimesh.Trimesh, target_height_mm: Optional[float]) -> None:
    """Uniformly scale mesh so its Z height equals target_height_mm."""
    if not target_height_mm or target_height_mm <= 0:
        return
    try:
        size = mesh.extents
        z_height = float(size[2])
        if z_height <= 0:
            return
        s = float(target_height_mm) / z_height
        mesh.apply_scale(s)
    except Exception as e:
        logger.debug(f"Scaling skipped: {e}")


def mesh_clean_cat(stl_path: Path, params: CatConversionParams) -> Dict[str, Any]:
    """Clean, repair, smooth, decimate, scale, and orient the generated STL.

    Returns mesh metrics including watertight flag. Guarantees watertight via
    manifold repair and convex hull fallback (as in _repair_mesh_if_needed).
    """
    try:
        mesh = trimesh.load_mesh(str(stl_path))
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.dump().values()))
        # Basic cleanup
        try:
            mesh.remove_degenerate_faces()
            mesh.remove_duplicate_faces()
            mesh.remove_unreferenced_vertices()
            mesh.fix_normals()
            try:
                mesh.fill_holes()
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Initial cleanup issue: {e}")

        # Non-manifold repair attempt
        if not mesh.is_watertight:
            try:
                import numpy as _np
                import manifold3d as _mf
                v = _np.asarray(mesh.vertices, dtype=_np.float64)
                f = _np.asarray(mesh.faces, dtype=_np.int32)
                m = _mf.Manifold(_mf.Mesh(v, f))
                pos, tri = m.to_mesh()
                if pos is not None and tri is not None and len(pos) > 0 and len(tri) > 0:
                    mesh = trimesh.Trimesh(vertices=_np.asarray(pos), faces=_np.asarray(tri), process=True)
            except Exception as e:
                logger.debug(f"Manifold repair skipped: {e}")

        # Smoothing
        if params.clean_mesh:
            _try_smoothing(mesh, params.smoothing_iterations, params.smoothing_lambda, params.smoothing_mu)

        # Decimation
        if params.clean_mesh:
            _try_decimate(mesh, params.decimation_target_faces, params.decimation_ratio)

        # Scale and orient
        _scale_to_target_height(mesh, params.target_height_mm)
        _orient_and_place_on_bed(mesh, params.pose, params.orient_to_bed)

        # Final guardrail: ensure watertight
        if not mesh.is_watertight:
            try:
                hull = mesh.convex_hull
                if isinstance(hull, trimesh.Trimesh):
                    mesh = hull
            except Exception as e:
                logger.debug(f"Convex hull fallback skipped: {e}")

        # Export over original path
        mesh.export(str(stl_path))
        metrics = {
            "vertex_count": int(len(mesh.vertices)),
            "face_count": int(len(mesh.faces)),
            "surface_area": float(mesh.area),
            "volume_mm3": float(mesh.volume),
            "is_watertight": bool(mesh.is_watertight),
        }
        return metrics
    except Exception as e:
        logger.warning(f"mesh_clean_cat failed: {e}")
        # Fall back to previous repair for best-effort output
        return _repair_mesh_if_needed(stl_path)


def _material_density_g_cm3(material: str) -> float:
    mapping = {
        "PLA": 1.24,
        "PETG": 1.27,
        "ABS": 1.04,
        "ASA": 1.07,
    }
    return mapping.get((material or "").upper(), 1.20)


def printability_check(stl_path: Path, params: CatConversionParams) -> Dict[str, Any]:
    """Estimate printability metrics:
    - min_local_edge_length_mm as proxy for min wall/detail
    - overhang area fraction above threshold
    - volume and solid mass estimate (upper bound)

    Note: True wall thickness is complex; we use the minimum unique edge length
    as a conservative proxy for printable feature thickness.
    """
    try:
        mesh = trimesh.load_mesh(str(stl_path))
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.dump().values()))
        # Edge-based feature proxy
        try:
            edge_lengths = mesh.edges_unique_length
            min_edge = float(edge_lengths.min()) if len(edge_lengths) else float("inf")
        except Exception:
            # Fallback via face edges
            lengths = []
            try:
                for e in mesh.edges_unique:
                    a, b = mesh.vertices[e[0]], mesh.vertices[e[1]]
                    lengths.append(float(np.linalg.norm(a - b)))
            except Exception:
                pass
            min_edge = float(min(lengths)) if lengths else float("inf")

        # Overhangs relative to +Z
        try:
            normals = mesh.face_normals
            nz = normals[:, 2]
            nz = np.clip(nz, -1.0, 1.0)
            angles = np.degrees(np.arccos(np.abs(nz)))  # 0=vertical, 90=horizontal
            face_area = mesh.area_faces
            over_mask = angles > float(params.support_overhang_deg)
            over_area = float(face_area[over_mask].sum())
            total_area = float(face_area.sum()) or 1.0
            overhang_fraction = over_area / total_area
        except Exception:
            overhang_fraction = 0.0

        # Volume and mass (upper bound; assumes solid)
        vol_mm3 = float(mesh.volume) if mesh.volume is not None else 0.0
        density = _material_density_g_cm3(params.material)
        mass_g = (vol_mm3 / 1000.0) * density  # mm^3 -> cm^3

        wall_req = 2.0 * float(params.nozzle_diameter_mm)
        detail_req = 3.0 * float(params.layer_height_mm)
        wall_ok = bool(min_edge >= wall_req)
        detail_ok = bool(min_edge >= detail_req)
        support_recommended = bool(overhang_fraction > 0.15)

        return {
            "nozzle_diameter_mm": float(params.nozzle_diameter_mm),
            "layer_height_mm": float(params.layer_height_mm),
            "overhang_threshold_deg": float(params.support_overhang_deg),
            "min_local_edge_length_mm": None if np.isinf(min_edge) else float(min_edge),
            "min_wall_requirement_mm": wall_req,
            "min_detail_requirement_mm": detail_req,
            "wall_ok": wall_ok,
            "detail_ok": detail_ok,
            "overhang_area_fraction": float(overhang_fraction),
            "support_recommended": support_recommended,
            "volume_mm3": vol_mm3,
            "estimated_mass_g": mass_g,
        }
    except Exception as e:
        logger.warning(f"printability_check failed: {e}")
        return {"error": str(e)}


def _to_manifold(mesh: trimesh.Trimesh):
    import numpy as _np
    import manifold3d as _mf
    v = _np.asarray(mesh.vertices, dtype=_np.float64)
    f = _np.asarray(mesh.faces, dtype=_np.int32)
    return _mf.Manifold(_mf.Mesh(v, f))


def _from_manifold(m) -> trimesh.Trimesh:
    import numpy as _np
    pos, tri = m.to_mesh()
    return trimesh.Trimesh(vertices=_np.asarray(pos), faces=_np.asarray(tri), process=True)


def auto_hollow_and_add_drains(stl_path: Path, params: CatConversionParams) -> Dict[str, Any]:
    """Hollow the mesh to a shell of wall_thickness_mm and add underside drain holes.
    Uses Manifold3D booleans when available; falls back gracefully if operations fail.
    Modifies the STL in-place and returns a summary.
    """
    info: Dict[str, Any] = {"hollow_enabled": bool(params.hollow_enabled), "hollowed": False, "drain_holes_added": 0}
    if not params.hollow_enabled:
        return info
    try:
        mesh = trimesh.load_mesh(str(stl_path))
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.dump().values()))
        # Ensure mesh is watertight before manifold ops
        if not mesh.is_watertight:
            logger.debug("auto_hollow: input not watertight; attempting repair first")
            mesh.export(str(stl_path))
            _ = _repair_mesh_if_needed(stl_path)
            mesh = trimesh.load_mesh(str(stl_path))

        # Manifold hollowing (preferred)
        try:
            outer = _to_manifold(mesh)
            wt = float(max(0.2, params.wall_thickness_mm))
            # Offset inward to create inner solid (Manifold >= v4 supports offset)
            try:
                inner = outer.offset(-wt)
            except Exception as e_off:
                # Fall back to voxel-based offset
                raise RuntimeError(f"manifold_offset_unavailable: {e_off}")
            # If offset removed the model entirely, abort
            try:
                pos_i, tri_i = inner.to_mesh()
                if pos_i is None or len(pos_i) == 0:
                    raise ValueError("Inner offset produced empty mesh")
            except Exception:
                raise
            shell = outer - inner

            # Prepare drain cylinders
            bbox = mesh.bounds
            z0 = float(bbox[0][2])
            ext = mesh.extents
            cx, cy = mesh.centroid[0], mesh.centroid[1]
            hole_radius = float(max(0.5, params.drain_hole_diameter_mm * 0.5))
            height = float(ext[2] + 2.0 * hole_radius + 2.0)
            # Place holes along X around center, margin from edges
            margin = float(params.drain_hole_edge_margin_mm)
            half_x = ext[0] * 0.5
            dx = max(margin, half_x * 0.35)
            positions = []
            n = int(max(1, params.drain_holes_count))
            if n == 1:
                positions = [(cx, cy)]
            elif n == 2:
                positions = [(cx - dx, cy), (cx + dx, cy)]
            else:
                # distribute in a small circle
                import math
                rpos = max(margin, min(half_x * 0.6, ext[1] * 0.3))
                for k in range(n):
                    ang = 2.0 * math.pi * (k / n)
                    positions.append((cx + rpos * math.cos(ang), cy + rpos * math.sin(ang)))

            import numpy as _np
            import manifold3d as _mf
            added = 0
            for (px, py) in positions:
                cyl = trimesh.creation.cylinder(radius=hole_radius, height=height, sections=32)
                # Move cylinder so it passes through from below
                T = np.eye(4)
                T[0, 3] = float(px)
                T[1, 3] = float(py)
                T[2, 3] = float(z0 - 1.0)  # start slightly below bed to ensure pass-through
                cyl.apply_transform(T)
                m_cyl = _to_manifold(cyl)
                shell = shell - m_cyl
                added += 1

            shell_mesh = _from_manifold(shell)
            if shell_mesh.is_empty:
                raise ValueError("Shell result empty after booleans")
            shell_mesh.export(str(stl_path))
            info.update({"hollowed": True, "drain_holes_added": added})
            return info
        except Exception as e:
            logger.warning(f"auto_hollow (manifold) failed: {e}")
            # Voxel fallback using scikit-image morphology
            try:
                import numpy as _np
                from skimage.morphology import ball
                # Voxelize mesh at a resolution derived from wall thickness
                pitch = max(0.8, min(wt / 3.0, 2.0))  # mm per voxel
                vox = mesh.voxelized(pitch)
                vol = vox.matrix
                if vol is None or vol.size == 0:
                    raise ValueError("voxelization failed")
                # Erode volume to create inner cavity
                radius = max(1, int(round(wt / pitch)))
                selem = ball(radius)
                from scipy.ndimage import binary_erosion
                eroded = binary_erosion(vol, structure=selem)
                # Shell = vol - eroded
                shell_vol = vol & (~eroded)
                # Convert back to mesh
                # Reconstruct a VoxelGrid with same transform and run marching cubes
                try:
                    from trimesh.voxel import VoxelGrid
                    grid = VoxelGrid(shell_vol, transform=getattr(vox, 'transform', np.eye(4)))
                    shell_mesh = grid.marching_cubes
                except Exception:
                    # Older API: ops.matrix_to_marching_cubes without origin
                    shell_mesh = trimesh.voxel.ops.matrix_to_marching_cubes(shell_vol, pitch=pitch)
                if not isinstance(shell_mesh, trimesh.Trimesh):
                    raise ValueError("marching cubes failed")
                # Drain holes (skip for voxel fallback to reduce complexity)
                shell_mesh.export(str(stl_path))
                info.update({"hollowed": True, "drain_holes_added": 0, "method": "voxel"})
                return info
            except Exception as e2:
                logger.warning(f"auto_hollow (voxel) failed: {e2}")
                return info
    except Exception as e:
        logger.warning(f"auto_hollow failed: {e}")
        return info


async def image_to_3d_cat_async(image_bytes: bytes, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Async variant suitable for FastAPI handlers."""
    p = CatConversionParams(**(params or {}))
    dirs = _ensure_dirs()
    img_path = _save_image_bytes(image_bytes, dirs["uploads"])

    cad = CADAgent(agent_name="cat_cad")
    task = {
        "operation": "create_from_image",
        "image_path": str(img_path),
        "material": p.material,
        "enforce_safety": p.enforce_safety,
        "pixel_size_mm": p.pixel_size_mm,
        "max_size": p.max_size,
        "height_scale": p.height_scale,
        "base_thickness": p.base_thickness,
        "pose": p.pose,
    }

    result = await cad.execute_task(task)
    if not result or not getattr(result, "success", False):
        err = getattr(result, "error_message", "Unknown error") if result else "No result"
        raise RuntimeError(f"CADAgent conversion failed: {err}")

    data = result.data if hasattr(result, "data") else result
    stl_tmp = Path(data.get("stl_file") or data.get("model_file"))
    if not stl_tmp.exists():
        raise FileNotFoundError(f"STL not created: {stl_tmp}")

    model_id = img_path.stem
    out_path = dirs["outputs"] / f"{model_id}.stl"
    try:
        stl_tmp.replace(out_path)
    except Exception:
        out_path.write_bytes(stl_tmp.read_bytes())
        try:
            stl_tmp.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass

    # Mesh clean & metrics
    metrics = mesh_clean_cat(out_path, p) if p.clean_mesh else _repair_mesh_if_needed(out_path)

    # Optional hollowing + drains
    hollow_info = auto_hollow_and_add_drains(out_path, p)
    if hollow_info.get("hollowed"):
        # Recalculate metrics after geometry change
        metrics = _repair_mesh_if_needed(out_path)

    # Printability assessment
    printable = printability_check(out_path, p)
    response = {
        "success": True,
        "model_id": model_id,
        "stl_path": str(out_path),
        "source_image": str(img_path),
        "material": p.material,
        "parameters": {
            "enforce_safety": p.enforce_safety,
            "pixel_size_mm": p.pixel_size_mm,
            "max_size": p.max_size,
            "height_scale": p.height_scale,
            "base_thickness": p.base_thickness,
            "pose": p.pose,
        },
        "mesh_metrics": metrics,
    "hollowing": hollow_info,
    "printability": printable,
    }
    if isinstance(metrics, dict) and not metrics.get("is_watertight", False):
        logger.warning("Generated mesh is not watertight after repair attempts")
        response["warning"] = "mesh_not_watertight"
    return response


def image_to_3d_cat(image_bytes: bytes, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Sync wrapper for scripts/CLIs (spawns a temporary event loop if needed)."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # Running inside an event loop: create a new task and wait via run_until_complete is not allowed
        # Use asyncio.run_coroutine_threadsafe on a new loop in a separate thread would be overkill; 
        # here we fall back to creating a new loop temporarily.
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(image_to_3d_cat_async(image_bytes, params))
        finally:
            new_loop.close()
    else:
        return asyncio.run(image_to_3d_cat_async(image_bytes, params))
