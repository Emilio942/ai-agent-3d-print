#!/usr/bin/env python3
"""
Project Structure Test
Tests the clean project organization after reorganization
"""

import os
import sys
from pathlib import Path

def test_project_structure():
    """Test the reorganized project structure."""
    
    print("🧹 AI Agent 3D Print System - Project Structure Test")
    print("=" * 60)
    
    base_path = Path(__file__).parent
    
    # Expected directories
    expected_dirs = [
        "agents",
        "api", 
        "core",
        "config",
        "web",
        "printer_support",  # NEW
        "test_data",        # NEW
        "development",      # NEW
        "validation",       # NEW
        "tests",
        "documentation",
        "data",
        "logs",
        "scripts"
    ]
    
    print("\n1️⃣ Testing Directory Structure...")
    missing_dirs = []
    for dir_name in expected_dirs:
        dir_path = base_path / dir_name
        if dir_path.exists():
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ❌ {dir_name}/ - MISSING")
            missing_dirs.append(dir_name)
    
    # Test core files in root
    print("\n2️⃣ Testing Core Files...")
    core_files = [
        "main.py",
        "requirements.txt", 
        "README.md",
        "__init__.py",
        "PROJECT_STRUCTURE_CLEAN.md"
    ]
    
    missing_files = []
    for file_name in core_files:
        file_path = base_path / file_name
        if file_path.exists():
            print(f"   ✅ {file_name}")
        else:
            print(f"   ❌ {file_name} - MISSING")
            missing_files.append(file_name)
    
    # Test new organized directories
    print("\n3️⃣ Testing New Directory Contents...")
    
    # Printer support
    printer_support_files = ["multi_printer_support.py", "enhanced_printer_agent.py", "README.md"]
    print("   📁 printer_support/")
    for file_name in printer_support_files:
        file_path = base_path / "printer_support" / file_name
        if file_path.exists():
            print(f"      ✅ {file_name}")
        else:
            print(f"      ❌ {file_name} - MISSING")
    
    # Test data
    test_data_files = ["test_circle.png", "test_shapes.png", "README.md"]
    print("   📁 test_data/")
    for file_name in test_data_files:
        file_path = base_path / "test_data" / file_name
        if file_path.exists():
            print(f"      ✅ {file_name}")
        else:
            print(f"      ❌ {file_name} - MISSING")
    
    # Development
    dev_files = ["web_server.py", "api_debug.py", "auto_web_interface.py", "README.md"]
    print("   📁 development/")
    for file_name in dev_files:
        file_path = base_path / "development" / file_name
        if file_path.exists():
            print(f"      ✅ {file_name}")
        else:
            print(f"      ❌ {file_name} - MISSING")
    
    # Validation
    validation_files = ["AUFGABENLISTE_VALIDIERUNG.md", "COMPLETE_TASK_STATUS.md", "README.md"]
    print("   📁 validation/")
    for file_name in validation_files:
        file_path = base_path / "validation" / file_name
        if file_path.exists():
            print(f"      ✅ {file_name}")
        else:
            print(f"      ❌ {file_name} - MISSING")
    
    # Test that root directory is clean
    print("\n4️⃣ Testing Root Directory Cleanliness...")
    root_files = list(base_path.glob("*.py"))
    allowed_root_files = ["main.py", "__init__.py"]
    
    clean_root = True
    for file_path in root_files:
        if file_path.name not in allowed_root_files:
            print(f"   ⚠️  Unexpected Python file in root: {file_path.name}")
            clean_root = False
    
    if clean_root:
        print("   ✅ Root directory is clean (only main.py and __init__.py)")
    
    # Summary
    print("\n" + "=" * 60)
    if not missing_dirs and not missing_files and clean_root:
        print("✅ PROJECT STRUCTURE TEST PASSED!")
        print("\n🎯 Project is well organized:")
        print("   • Clean root directory")
        print("   • Proper module separation")
        print("   • Logical directory structure")
        print("   • Documentation for all modules")
        print("   • Development tools separated")
        print("   • Test data organized")
        print("   • Validation documents collected")
        
        return True
    else:
        print("❌ PROJECT STRUCTURE TEST FAILED!")
        if missing_dirs:
            print(f"   Missing directories: {missing_dirs}")
        if missing_files:
            print(f"   Missing files: {missing_files}")
        if not clean_root:
            print("   Root directory is not clean")
        
        return False

if __name__ == "__main__":
    success = test_project_structure()
    sys.exit(0 if success else 1)
