"""Utility helpers for generating stylised cat height-maps for CAD image workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def _draw_cat_silhouette(img: Image.Image) -> Image.Image:
    """Render a minimalist sitting-cat silhouette with soft gradients.

    The output is purposefully high-contrast (0-255) so the CAD height-map
    step has a meaningful Z range while still leaving smooth transitions after
    blurring.  All coordinates are expressed in image space.
    """

    width, height = img.size
    draw = ImageDraw.Draw(img)

    def _box(cx: float, cy: float, w: float, h: float) -> tuple[float, float, float, float]:
        return (
            cx - w / 2.0,
            cy - h / 2.0,
            cx + w / 2.0,
            cy + h / 2.0,
        )

    # Body – slightly asymmetric ellipse for a seated pose
    body_center = (width * 0.52, height * 0.63)
    body_box = _box(body_center[0], body_center[1], width * 0.55, height * 0.65)
    draw.ellipse(body_box, fill=185)

    # Head
    head_center = (width * 0.46, height * 0.32)
    head_box = _box(head_center[0], head_center[1], width * 0.32, height * 0.32)
    draw.ellipse(head_box, fill=215)

    # Ears (triangles)
    left_ear = [
        (width * 0.35, height * 0.18),
        (width * 0.28, height * 0.02),
        (width * 0.44, height * 0.14),
    ]
    right_ear = [
        (width * 0.55, height * 0.18),
        (width * 0.64, height * 0.04),
        (width * 0.62, height * 0.18),
    ]
    draw.polygon(left_ear, fill=200)
    draw.polygon(right_ear, fill=200)

    # Tail – arcing bezier approximation using polygon fan
    tail_path = [
        (width * 0.76, height * 0.62),
        (width * 0.86, height * 0.55),
        (width * 0.88, height * 0.48),
        (width * 0.83, height * 0.40),
        (width * 0.78, height * 0.44),
        (width * 0.74, height * 0.50),
        (width * 0.70, height * 0.60),
        (width * 0.73, height * 0.68),
    ]
    draw.polygon(tail_path, fill=160)

    # Chest fluff – lighter oval to break up silhouette
    fluff_box = _box(width * 0.45, height * 0.47, width * 0.22, height * 0.20)
    draw.ellipse(fluff_box, fill=230)

    # Paws – overlapping ellipses
    paw_radius = width * 0.09
    paw_y = height * 0.86
    draw.ellipse(_box(width * 0.40, paw_y, paw_radius, paw_radius * 0.7), fill=200)
    draw.ellipse(_box(width * 0.52, paw_y, paw_radius, paw_radius * 0.7), fill=205)

    # Eyes – small dark ovals create slight recesses
    eye_radius = width * 0.03
    eye_y = height * 0.30
    draw.ellipse(_box(width * 0.41, eye_y, eye_radius, eye_radius * 0.6), fill=80)
    draw.ellipse(_box(width * 0.49, eye_y, eye_radius, eye_radius * 0.6), fill=80)

    return img


def _apply_shading(data: np.ndarray) -> np.ndarray:
    """Blend vertical gradient and vignette so the heightmap feels sculpted."""

    h, w = data.shape
    y = np.linspace(0.0, 1.0, h)[:, None]
    x = np.linspace(0.0, 1.0, w)[None, :]
    vertical_gradient = 0.9 + 0.2 * (1.0 - y)  # lighter up top
    vignette = 0.85 + 0.3 * ((x - 0.5) ** 2 + (y - 0.45) ** 2)
    shading = vertical_gradient * vignette
    shaded = data * shading
    shaded = np.clip(shaded, 0.0, 255.0)
    return shaded


def generate_cat_heightmap(
    output_path: Path,
    *,
    size: int = 256,
    blur_radius: float = 3.5,
) -> Path:
    """Render and persist a procedural cat height-map to ``output_path``.

    Parameters
    ----------
    output_path:
        Target location for the generated PNG.
    size:
        Width/height of the square canvas in pixels.
    blur_radius:
        Gaussian blur radius to soften hard edges so the resulting mesh has
        smooth transitions rather than brick-like stairs.
    """

    size = max(96, int(size))
    img = Image.new("L", (size, size), color=0)
    img = _draw_cat_silhouette(img)

    if blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=float(blur_radius)))

    data = np.asarray(img, dtype=np.float32)
    data = _apply_shading(data)
    img = Image.fromarray(data.astype(np.uint8), mode="L")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path


def ensure_default_cat_heightmap(directory: Optional[Path] = None) -> Path:
    """Ensure a reusable cat height-map exists on disk and return its path."""

    base = directory or Path("data") / "generated"
    base.mkdir(parents=True, exist_ok=True)
    path = base / "cat_heightmap.png"
    if not path.exists():
        generate_cat_heightmap(path)
    return path

__all__ = ["generate_cat_heightmap", "ensure_default_cat_heightmap"]
