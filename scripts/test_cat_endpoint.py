"""
Quick test for POST /api/convert/cat using FastAPI TestClient.

Runs the app in-process (no uvicorn needed), uploads the repo's test image,
and prints the response summary including watertight check.
"""

from __future__ import annotations

import json
from pathlib import Path
import io
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from api.main import app


def _make_test_image_bytes(w: int = 128, h: int = 128) -> bytes:
    # Create a simple radial gradient with a silhouette-like blob
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w // 2, h // 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    img = np.clip(255 - (r * 2), 0, 255).astype(np.uint8)
    # Add a small ellipse blob
    Y, X = np.ogrid[:h, :w]
    mask = ((X - cx) ** 2) / (w * 0.12) ** 2 + ((Y - cy) ** 2) / (h * 0.18) ** 2 <= 1
    img[mask] = 255
    rgb = np.stack([img, img, img], axis=-1)
    pil = Image.fromarray(rgb)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()


def run():
    with TestClient(app) as client:
        image_bytes = _make_test_image_bytes(128, 128)
        files = {"image": ("test.png", image_bytes, "image/png")}
        data = {
            "material": "PLA",
            "pose": "sitzend",
            "enforce_safety": "true",
            "pixel_size_mm": "0.3",
            "max_size": "96",
            "height_scale": "6.0",
            "base_thickness": "2.0",
        }
        r = client.post("/api/convert/cat", files=files, data=data, timeout=600)
        print("Status:", r.status_code)
        try:
            payload = r.json()
        except Exception:
            print(r.text[:2000])
            raise
        print(json.dumps({
            "success": payload.get("success"),
            "stl_path": payload.get("stl_path"),
            "mesh_metrics": payload.get("mesh_metrics"),
            "warning": payload.get("warning"),
        }, indent=2))

        metrics = payload.get("mesh_metrics") or {}
        is_watertight = bool(metrics.get("is_watertight", False))
        print("Watertight:", is_watertight)
        return is_watertight, payload


if __name__ == "__main__":
    ok, _ = run()
    # Exit code signals DoD success for CI usage
    import sys
    sys.exit(0 if ok else 2)
