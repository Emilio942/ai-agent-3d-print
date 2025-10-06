#!/usr/bin/env python3
"""Project structure validation for the AI Agent 3D Print repository."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

BASE_PATH = Path(__file__).resolve().parent.parent
EXPECTED_DIRS = [
    "agents",
    "api",
    "core",
    "config",
    "web",
    "printer_support",
    "test_data",
    "development",
    "validation",
    "tests",
    "documentation",
    "data",
    "logs",
    "scripts",
]
CORE_FILES = [
    "main.py",
    "requirements.txt",
    "README.md",
    "__init__.py",
    "PROJECT_STRUCTURE_CLEAN.md",
]
ALLOWED_ROOT_FILES = {"main.py", "__init__.py", "conftest.py"}


def _is_compatibility_stub(file_path: Path) -> bool:
    """Return True if the file is one of the lightweight compatibility stubs."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    return "Compatibility stub" in content


def test_project_structure() -> None:
    """Validate the repository structure and report a readable summary."""
    print("🧹 AI Agent 3D Print System - Project Structure Test")
    print("=" * 60)

    missing_dirs: list[str] = []
    print("\n1️⃣ Testing Directory Structure...")
    for dir_name in EXPECTED_DIRS:
        dir_path = BASE_PATH / dir_name
        if dir_path.exists():
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ❌ {dir_name}/ - MISSING")
            missing_dirs.append(dir_name)

    missing_files: list[str] = []
    print("\n2️⃣ Testing Core Files...")
    for file_name in CORE_FILES:
        file_path = BASE_PATH / file_name
        if file_path.exists():
            print(f"   ✅ {file_name}")
        else:
            print(f"   ❌ {file_name} - MISSING")
            missing_files.append(file_name)

    print("\n3️⃣ Testing New Directory Contents...")

    printer_support_files = ["multi_printer_support.py", "enhanced_printer_agent.py", "README.md"]
    print("   📁 printer_support/")
    for file_name in printer_support_files:
        file_path = BASE_PATH / "printer_support" / file_name
        status = "✅" if file_path.exists() else "❌"
        suffix = "" if status == "✅" else " - MISSING"
        print(f"      {status} {file_name}{suffix}")

    test_data_files = ["test_circle.png", "test_shapes.png", "README.md"]
    print("   📁 test_data/")
    for file_name in test_data_files:
        file_path = BASE_PATH / "test_data" / file_name
        status = "✅" if file_path.exists() else "❌"
        suffix = "" if status == "✅" else " - MISSING"
        print(f"      {status} {file_name}{suffix}")

    dev_files = ["web_server.py", "api_debug.py", "auto_web_interface.py", "README.md"]
    print("   📁 development/")
    for file_name in dev_files:
        file_path = BASE_PATH / "development" / file_name
        status = "✅" if file_path.exists() else "❌"
        suffix = "" if status == "✅" else " - MISSING"
        print(f"      {status} {file_name}{suffix}")

    validation_files = ["AUFGABENLISTE_VALIDIERUNG.md", "COMPLETE_TASK_STATUS.md", "README.md"]
    print("   📁 validation/")
    for file_name in validation_files:
        file_path = BASE_PATH / "validation" / file_name
        status = "✅" if file_path.exists() else "❌"
        suffix = "" if status == "✅" else " - MISSING"
        print(f"      {status} {file_name}{suffix}")

    print("\n4️⃣ Testing Root Directory Cleanliness...")
    root_files = list(BASE_PATH.glob("*.py"))
    unexpected_files: list[str] = []

    for file_path in root_files:
        file_name = file_path.name
        if file_name in ALLOWED_ROOT_FILES:
            continue
        if _is_compatibility_stub(file_path):
            print(f"   ℹ️  Compatibility stub detected: {file_name}")
            continue
        unexpected_files.append(file_name)
        print(f"   ⚠️  Unexpected Python file in root: {file_name}")

    if not unexpected_files:
        print("   ✅ Root directory is clean (only main.py, __init__.py, and stubs)")

    print("\n" + "=" * 60)

    assert not missing_dirs, f"Missing directories: {missing_dirs}"
    assert not missing_files, f"Missing core files: {missing_files}"
    assert not unexpected_files, f"Unexpected Python files in root: {unexpected_files}"