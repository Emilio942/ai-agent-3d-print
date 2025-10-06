#!/usr/bin/env python3
"""
Generate visual proofs (STL + PNG) for CADAgent outputs.

Creates:
 - data/visual_proofs/*.stl
 - data/visual_proofs/*.png
 - data/visual_proofs/summary.json
"""

import os
import json
import tempfile
from pathlib import Path
import numpy as np
import sys

# Ensure headless rendering
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.cad_agent import CADAgent


OUT_DIR = Path("data/visual_proofs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def render_mesh_png(mesh, out_png: Path):
    v = np.asarray(mesh.vertices)
    f = np.asarray(mesh.faces)
    if len(v) == 0 or len(f) == 0:
        # Empty mesh placeholder
        fig = plt.figure(figsize=(4, 4))
        plt.text(0.5, 0.5, "Empty mesh", ha="center", va="center")
        plt.axis("off")
        fig.savefig(out_png, dpi=180)
        plt.close(fig)
        return

    tris = v[f]
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection="3d")
    coll = Poly3DCollection(tris, facecolor="#6baed6", edgecolor="#1f3349", linewidths=0.15, alpha=0.95)
    ax.add_collection3d(coll)

    mins = v.min(axis=0)
    maxs = v.max(axis=0)
    spans = np.maximum(maxs - mins, 1e-6)
    ax.set_xlim(mins[0], maxs[0])
    ax.set_ylim(mins[1], maxs[1])
    ax.set_zlim(mins[2], maxs[2])
    try:
        ax.set_box_aspect(spans)
    except Exception:
        pass
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def export_mesh(mesh, stem: str):
    stl_path = OUT_DIR / f"{stem}.stl"
    png_path = OUT_DIR / f"{stem}.png"
    mesh.export(str(stl_path))
    render_mesh_png(mesh, png_path)
    return stl_path, png_path


def main():
    agent = CADAgent()
    summary = {}

    # 1) Primitive proof
    cube, vol_cube = agent.create_cube(30, 20, 10)
    stl, png = export_mesh(cube, "primitive_cube")
    summary["primitive_cube"] = {
        "stl": str(stl),
        "png": str(png),
        "volume_mm3": float(vol_cube),
    }

    cyl, vol_cyl = agent.create_cylinder(10, 25)
    stl, png = export_mesh(cyl, "primitive_cylinder")
    summary["primitive_cylinder"] = {
        "stl": str(stl),
        "png": str(png),
        "volume_mm3": float(vol_cyl),
    }

    # 2) Image→3D proof
    # Prefer repo test image if loadable; otherwise create a gradient image
    # Always ensure we pass a valid path to CADAgent
    test_img = PROJECT_ROOT / "test_input.jpg"
    gen_img = OUT_DIR / "test_input_generated.png"
    import cv2
    img_path = None
    if test_img.exists():
        im = cv2.imread(str(test_img))
        if im is not None:
            img_path = test_img
    if img_path is None:
        grad = (np.linspace(0, 255, 128, dtype=np.uint8)[None, :].repeat(128, 0))
        cv2.imwrite(str(gen_img), grad)
        img_path = gen_img
    import asyncio

    async def run_img():
        res = await agent.execute_task({
            "operation": "create_from_image",
            "image_path": str(img_path),
            "height_scale": 6.0,
            "base_thickness": 2.0,
        })
        if not res.success:
            summary["image_heightmap"] = {"error": res.error_message if hasattr(res, 'error_message') else "failed", "source_image": str(img_path)}
            return
        stl_file = res.data.get("stl_file")
        if stl_file and os.path.exists(stl_file):
            # Load back for rendering
            import trimesh
            m = trimesh.load_mesh(stl_file)
            png_out = OUT_DIR / "image_heightmap.png"
            render_mesh_png(m, png_out)
            # Copy STL into proofs directory for convenience
            stl_out = OUT_DIR / "image_heightmap.stl"
            try:
                import shutil
                shutil.copyfile(stl_file, stl_out)
                stl_file = stl_out
            except Exception:
                pass
            summary["image_heightmap"] = {
                "stl": stl_file,
                "png": str(png_out),
                "faces": int(res.data.get("faces", 0)),
                "vertices": int(res.data.get("vertices", 0)),
                "source_image": str(img_path),
            }
        else:
            summary["image_heightmap"] = {"error": "stl_not_created", "source_image": str(img_path)}

    asyncio.run(run_img())

    # 2b) Complex: Mandelbrot heightmap
    def mandelbrot(h=256, w=256, max_iter=50):
        y, x = np.ogrid[-1.5:1.5:h*1j, -2:1:w*1j]
        c = x + 1j*y
        z = np.zeros_like(c)
        div_time = np.full(z.shape, max_iter, dtype=np.int32)
        for i in range(max_iter):
            z = z*z + c
            diverge = np.greater(np.abs(z), 2, out=np.zeros_like(np.abs(z), dtype=bool))
            newly = diverge & (div_time == max_iter)
            div_time[newly] = i
            z[diverge] = 2
        return div_time.astype(np.uint8)

    m_img = OUT_DIR / "mandelbrot.png"
    if not m_img.exists():
        import cv2
        cv2.imwrite(str(m_img), mandelbrot(192, 256, 80))

    async def run_mandelbrot():
        res = await agent.execute_task({
            "operation": "create_from_image",
            "image_path": str(m_img),
            "height_scale": 10.0,
            "base_thickness": 2.0,
            "material": "PETG",
            "enforce_safety": True,
            "pixel_size_mm": 0.3,
            "max_size": 192
        })
        if res.success:
            import trimesh
            m = trimesh.load_mesh(res.data["stl_file"])
            png_out = OUT_DIR / "mandelbrot_heightmap.png"
            render_mesh_png(m, png_out)
            stl_out = OUT_DIR / "mandelbrot_heightmap.stl"
            import shutil
            shutil.copyfile(res.data["stl_file"], stl_out)
            summary["mandelbrot_heightmap"] = {
                "stl": str(stl_out),
                "png": str(png_out),
                "faces": int(res.data.get("faces", 0)),
                "vertices": int(res.data.get("vertices", 0)),
                "material": "PETG",
                "safety": res.data.get("safety", {}),
            }
        else:
            summary["mandelbrot_heightmap"] = {"error": "generation_failed"}

    asyncio.run(run_mandelbrot())

    # 3) Contours→Extrusion proof
    rect = {"points": [(0, 0), (50, 0), (50, 20), (0, 20)]}
    circ = {"points": [(25 + 8 * np.cos(t), 10 + 8 * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 64, endpoint=False)]}
    mesh, vol = agent.create_from_contours([rect, circ], extrusion_height=6, base_thickness=1)
    stl, png = export_mesh(mesh, "contours_extrusion")
    summary["contours_extrusion"] = {
        "stl": str(stl),
        "png": str(png),
        "volume_mm3": float(vol),
        "contours_used": 2,
    }

    # Save summary
    # Cast any Path objects to str for JSON
    def to_jsonable(o):
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, dict):
            return {k: to_jsonable(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [to_jsonable(x) for x in o]
        return o
    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(to_jsonable(summary), f, indent=2)

    # Console output for quick inspection
    for k, v in summary.items():
        print(f"[OK] {k}: STL={v.get('stl')} PNG={v.get('png')}")

    agent.cleanup()


if __name__ == "__main__":
    main()
