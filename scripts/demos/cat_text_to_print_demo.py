#!/usr/bin/env python3
"""Cat Pipeline Demo: Text → Research → CAD → Slicer → Printer (Mock).

This script exercises the complete AI Agent 3D Print workflow using the
existing agents. It takes a text prompt (default: "Katze") and optionally a
reference image to generate an STL via the CAD agent's image-to-3D pipeline,
produces mock G-code with the slicer agent, and finally streams the result to
the mock printer agent so you can verify end-to-end behavior without real
hardware.

Usage (from repository root):

    poetry run python scripts/demos/cat_text_to_print_demo.py --prompt "Katze"

Switch out the image or output directory via command-line options to explore
other scenarios.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.research_agent import ResearchAgent
from agents.cad_agent import CADAgent
from agents.slicer_agent import SlicerAgent
from agents.printer_agent import PrinterAgent
from core.api_schemas import TaskResult
from core.cat_heightmap import generate_cat_heightmap, ensure_default_cat_heightmap

# Default assets bundled with the repository
DEFAULT_OUTPUT_DIR = Path("output/cat_demo")


def _print_title(title: str) -> None:
    print("\n" + title)
    print("=" * len(title))


def _summarize_result(label: str, result: TaskResult) -> None:
    status = "✅" if result.success else "❌"
    print(f"{status} {label}")
    if result.error_message:
        print(f"   Error: {result.error_message}")
    elif result.data:
        snippet = json.dumps(result.data, indent=2, ensure_ascii=False)[:400]
        print("   Key data snippet:")
        for line in snippet.splitlines():
            print(f"     {line}")


def build_cad_task(
    research_result: TaskResult,
    image_path: Optional[Path],
    output_dir: Path,
) -> Dict[str, Any]:
    """Create CAD task based on research output and optional image."""
    materials = research_result.data.get("material_recommendations") or ["PLA"]
    material = materials[0]

    if image_path and image_path.exists():
        return {
            "task_id": "cad_image_cat",
            "operation": "create_from_image",
            "image_path": str(image_path),
            "material": material,
            "enforce_safety": True,
            "pixel_size_mm": 0.4,
            "height_scale": 8.0,
            "base_thickness": 2.0,
            "max_size": 160,
        }

    # Fallback: simple primitive based on research dimensions
    geometry = (
        research_result.data.get("object_specifications", {})
        .get("geometry", {})
        .get("dimensions", {})
    )
    x = float(geometry.get("length") or geometry.get("x") or 40)
    y = float(geometry.get("width") or geometry.get("y") or 40)
    z = float(geometry.get("height") or geometry.get("z") or 60)

    return {
        "task_id": "cad_primitive_cat",
        "operation": "create_primitive",
        "specifications": {
            "geometry": {
                "base_shape": "sphere",
                "dimensions": {"x": x, "y": y, "z": z},
            }
        },
        "requirements": {},
        "format_preference": "stl",
        "quality_level": "standard",
    }


def copy_artifact(path: Optional[str], target_dir: Path) -> Optional[Path]:
    if not path:
        return None
    source = Path(path)
    if not source.exists():
        return None
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / source.name
    shutil.copy2(source, destination)
    return destination


async def run_pipeline(
    prompt: str,
    image_path: Optional[Path],
    analysis_depth: str,
    output_dir: Path,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if image_path is None:
        default_dir = output_dir / "heightmaps"
        default_dir.mkdir(parents=True, exist_ok=True)
        image_path = generate_cat_heightmap(default_dir / f"cat_heightmap_{timestamp}.png")
        print(f"   🖼️ Generated procedural cat heightmap at: {image_path}")
    elif not image_path.exists():
        print(f"   ⚠️  Provided image path '{image_path}' not found; falling back to default cat heightmap")
        image_path = ensure_default_cat_heightmap()
        print(f"   🖼️ Using fallback cat heightmap: {image_path}")

    # Phase 1: Research Agent
    _print_title("Phase 1: Research Agent")
    research_agent = ResearchAgent("cat_demo_research")
    research_task = {
        "task_id": f"research_{timestamp}",
        "user_request": prompt,
        "analysis_depth": analysis_depth,
    }
    research_result = research_agent.execute_task(research_task)
    _summarize_result("Research completed", research_result)
    if not research_result.success:
        raise RuntimeError("Research agent failed; aborting pipeline")

    # Phase 2: CAD Agent
    _print_title("Phase 2: CAD Agent")
    cad_agent = CADAgent("cat_demo_cad")
    cad_task = build_cad_task(research_result, image_path, output_dir)
    cad_result = await cad_agent.execute_task(cad_task)
    _summarize_result("CAD model generated", cad_result)
    if not cad_result.success:
        raise RuntimeError("CAD agent failed; aborting pipeline")

    # Normalize STL path and keep a copy
    stl_path = (
        cad_result.data.get("stl_file_path")
        or cad_result.data.get("model_file_path")
        or cad_result.data.get("model_file")
    )
    stl_copy = copy_artifact(stl_path, output_dir)
    if stl_copy:
        print(f"   📦 STL stored at: {stl_copy}")
    else:
        print("   ⚠️  STL file not found in CAD result")

    # Phase 3: Slicer Agent
    _print_title("Phase 3: Slicer Agent")
    slicer_agent = SlicerAgent(
        "cat_demo_slicer",
        config={"mock_mode": True, "default_slicer": "prusaslicer"},
    )
    slicer_task = {
        "task_id": f"slicer_{timestamp}",
        "model_file_path": stl_path,
        "printer_profile": "cat_high_detail",
        "material_type": research_result.data.get("material_recommendations", ["PLA"])[0],
        "quality_preset": "fine",
    }
    slicer_result = await slicer_agent.execute_task(slicer_task)
    _summarize_result("Slicing completed", slicer_result)
    if not slicer_result.success:
        raise RuntimeError("Slicer agent failed; aborting pipeline")

    gcode_path = slicer_result.data.get("gcode_file_path")
    gcode_copy = copy_artifact(gcode_path, output_dir)
    if gcode_copy:
        print(f"   🧾 G-code stored at: {gcode_copy}")
    else:
        print("   ⚠️  G-code file not found in slicer result")

    # Phase 4: Printer Agent (mock)
    _print_title("Phase 4: Printer Agent (Mock)")
    printer_agent = PrinterAgent("cat_demo_printer", config={"mock_mode": True})
    printer_task = {
        "task_id": f"printer_{timestamp}",
        "operation": "start_print",
        "gcode_file_path": gcode_path,
    }
    printer_result = await printer_agent.execute_task(printer_task)
    _summarize_result("Print job dispatched", printer_result)
    if not printer_result.success:
        raise RuntimeError("Printer agent failed to start mock print job")

    return {
        "research": research_result,
        "cad": cad_result,
        "slicer": slicer_result,
        "printer": printer_result,
        "stl_copy": stl_copy,
        "gcode_copy": gcode_copy,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the cat text-to-print demo pipeline")
    parser.add_argument(
        "--prompt",
        default="Erstelle eine stilisierte Katze als Tischdekoration",
        help="Text prompt for the research agent",
    )
    parser.add_argument(
        "--analysis-depth",
        default="standard",
        choices=["minimal", "standard", "detailed"],
        help="How deep the research agent should analyze the prompt",
    )
    parser.add_argument(
        "--image-path",
        type=Path,
        default=None,
        help="Optional heightmap image for the CAD agent (defaults to generated cat heightmap)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for storing generated STL/G-code artifacts",
    )
    return parser.parse_args()


async def async_main(args: argparse.Namespace) -> None:
    try:
        results = await run_pipeline(
            prompt=args.prompt,
            image_path=args.image_path,
            analysis_depth=args.analysis_depth,
            output_dir=args.output_dir,
        )
        final_summary = {
            "stl": str(results.get("stl_copy")) if results.get("stl_copy") else None,
            "gcode": str(results.get("gcode_copy")) if results.get("gcode_copy") else None,
        }
        print("\n🎉 Pipeline completed successfully!")
        print(json.dumps(final_summary, indent=2, ensure_ascii=False))
    except Exception as exc:
        print("\n❌ Pipeline failed:", exc)
        raise


def main() -> None:
    args = parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
