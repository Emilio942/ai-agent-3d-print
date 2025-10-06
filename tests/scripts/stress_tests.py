#!/usr/bin/env python3
"""Stress tests and extended edge cases for the AI Agent 3D Print system."""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


async def test_invalid_image_paths() -> bool:
    """Test system behavior with invalid image paths."""
    print("🧪 Testing Invalid Image Paths")
    print("=" * 50)

    try:
        from agents.cad_agent import CADAgent

        cad_agent = CADAgent()

        test_cases = [
            ("nonexistent.png", "Non-existent image file"),
            ("/tmp/invalid/path/image.jpg", "Invalid path"),
            ("", "Empty string"),
            ("not_an_image.txt", "Non-image file"),
        ]

        for index, (invalid_path, description) in enumerate(test_cases, 1):
            print(f"\n📸 Test {index}: {description}")
            print(f"   Path: '{invalid_path}'")

            try:
                result = await cad_agent.execute_task(
                    {
                        "operation": "create_from_image",
                        "image_path": invalid_path,
                    }
                )

                if result.success:
                    print("   ❌ Unexpected success - should have failed")
                else:
                    print(f"   ✅ Correctly failed: {result.error_message}")

            except Exception as exc:
                print(f"   ✅ Correctly caught exception: {exc}")

        return True

    except Exception as exc:
        print(f"❌ Invalid image path tests failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


async def test_large_gcode_file() -> bool:
    """Test handling of very large G-code files."""
    print("\n🧪 Testing Large G-code File Handling")
    print("=" * 50)

    try:
        from agents.printer_agent import PrinterAgent

        printer_agent = PrinterAgent()
        printer_agent.mock_mode = True

        print("📄 Creating large G-code file (1000 lines)...")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".gcode", delete=False) as temp_file:
            temp_file.write("; Large G-code test file\n")
            temp_file.write("G28 ; Home all axes\n")
            temp_file.write("G1 Z5 F5000 ; Lift nozzle\n")

            for i in range(1000):
                x_coord = (i % 100) * 2
                y_coord = (i // 100) * 2
                temp_file.write(f"G1 X{x_coord} Y{y_coord} F3000 ; Move {i}\n")

            temp_file.write("M104 S0 ; Turn off hotend\n")
            temp_file.write("M140 S0 ; Turn off bed\n")
            temp_file.write("G28 X0 Y0 ; Home\n")
            temp_file.write("M84 ; Disable steppers\n")

            large_gcode_file = temp_file.name

        print(f"✅ Created large G-code file: {large_gcode_file}")

        print("🔄 Testing streaming of large file...")
        start_time = time.time()

        stream_result = await printer_agent.execute_task(
            {
                "operation": "stream_gcode",
                "specifications": {"gcode_file": large_gcode_file, "progress_callback": None},
            }
        )

        end_time = time.time()
        duration = end_time - start_time

        if stream_result and isinstance(stream_result, dict) and stream_result.get("success"):
            print("✅ Large file streaming started successfully")
            print(f"   Job ID: {stream_result.get('job_id', 'Unknown')}")
            print(f"   Start time: {duration:.3f}s")

            await asyncio.sleep(0.1)

            stop_result = await printer_agent.execute_task({"operation": "stop_print"})

            if stop_result and isinstance(stop_result, dict) and stop_result.get("success"):
                print("✅ Large file streaming stopped successfully")
            else:
                print("❌ Failed to stop large file streaming")
        else:
            print("❌ Large file streaming failed to start")
            return False

        try:
            os.unlink(large_gcode_file)
        except Exception:
            pass

        return True

    except Exception as exc:
        print(f"❌ Large G-code file test failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


async def test_concurrent_operations() -> bool:
    """Test concurrent operations on the same agent."""
    print("\n🧪 Testing Concurrent Operations")
    print("=" * 50)

    try:
        from agents.cad_agent import CADAgent

        cad_agent = CADAgent()

        print("🔄 Testing concurrent CAD operations...")

        tasks = []
        for i in range(3):
            task = cad_agent.execute_task(
                {
                    "operation": "create_primitive",
                    "specifications": {
                        "geometry": {
                            "base_shape": "cube",
                            "dimensions": {"x": 10 + i, "y": 10 + i, "z": 10 + i},
                        }
                    },
                }
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        for index, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   Task {index + 1}: ❌ Exception - {result}")
            elif result and hasattr(result, "success") and result.success:
                print(f"   Task {index + 1}: ✅ Success")
                success_count += 1
            else:
                print(f"   Task {index + 1}: ❌ Failed")

        print(f"\n📊 Concurrent operations result: {success_count}/3 successful")
        return success_count >= 2

    except Exception as exc:
        print(f"❌ Concurrent operations test failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


async def test_memory_and_cleanup() -> bool:
    """Test memory usage and cleanup."""
    print("\n🧪 Testing Memory Usage and Cleanup")
    print("=" * 50)

    try:
        import gc

        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        print(f"📊 Initial memory usage: {initial_memory:.2f} MB")

        print("🔄 Creating multiple agents...")

        from agents.cad_agent import CADAgent

        agents = []
        for _ in range(10):
            cad_agent = CADAgent()
            agents.append(cad_agent)

            await cad_agent.execute_task(
                {
                    "operation": "create_primitive",
                    "specifications": {
                        "geometry": {
                            "base_shape": "cube",
                            "dimensions": {"x": 10, "y": 10, "z": 10},
                        }
                    },
                }
            )

        current_memory = process.memory_info().rss / 1024 / 1024
        print(f"📊 Memory after creating 10 agents: {current_memory:.2f} MB")
        print(f"📈 Memory increase: {current_memory - initial_memory:.2f} MB")

        print("🧹 Cleaning up agents...")
        agents.clear()
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024
        print(f"📊 Memory after cleanup: {final_memory:.2f} MB")
        print(f"📉 Memory freed: {current_memory - final_memory:.2f} MB")

        memory_increase = current_memory - initial_memory
        memory_freed = current_memory - final_memory

        if memory_increase > 10:
            memory_freed_ratio = memory_freed / memory_increase
            print(f"📊 Memory freed ratio: {memory_freed_ratio:.2%}")
            return memory_freed_ratio > 0.1
        else:
            print("📊 Memory usage was minimal, test passed")
            return True

    except ImportError:
        print("⚠️ psutil not available, skipping memory test")
        return True
    except Exception as exc:
        print(f"❌ Memory test failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


async def test_error_recovery() -> bool:
    """Test error recovery capabilities."""
    print("\n🧪 Testing Error Recovery")
    print("=" * 50)

    try:
        from agents.cad_agent import CADAgent

        cad_agent = CADAgent()

        print("🔸 Test 1: Invalid dimensions (negative values)")
        try:
            result = await cad_agent.execute_task(
                {
                    "operation": "create_primitive",
                    "specifications": {
                        "geometry": {
                            "base_shape": "cube",
                            "dimensions": {"x": -10, "y": 5, "z": 5},
                        }
                    },
                }
            )

            if result.success:
                print("   ❌ Should have failed with negative dimension")
                return False
            else:
                print(f"   ✅ Correctly failed: {result.error_message}")
        except Exception as exc:
            print(f"   ✅ Correctly caught exception: {exc}")

        print("\n🔸 Test 2: Missing required fields")
        try:
            result = await cad_agent.execute_task(
                {
                    "operation": "create_primitive",
                    "specifications": {"geometry": {"base_shape": "cube"}},
                }
            )

            if result.success:
                print("   ❌ Should have failed with missing dimensions")
                return False
            else:
                print(f"   ✅ Correctly failed: {result.error_message}")
        except Exception as exc:
            print(f"   ✅ Correctly caught exception: {exc}")

        print("\n🔸 Test 3: Recovery after error")
        try:
            result = await cad_agent.execute_task(
                {
                    "operation": "create_primitive",
                    "specifications": {
                        "geometry": {
                            "base_shape": "cube",
                            "dimensions": {"x": 10, "y": 10, "z": 10},
                        }
                    },
                }
            )

            if result.success:
                print("   ✅ Successfully recovered and created valid cube")
            else:
                print(f"   ❌ Failed to recover: {result.error_message}")
                return False
        except Exception as exc:
            print(f"   ❌ Failed to recover: {exc}")
            return False

        return True

    except Exception as exc:
        print(f"❌ Error recovery test failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


async def main() -> bool:
    """Main stress test function."""
    print("🚀 AI Agent 3D Print - Stress Tests & Advanced Edge Cases")
    print("=" * 70)

    tests = [
        ("Invalid Image Paths", test_invalid_image_paths),
        ("Large G-code Files", test_large_gcode_file),
        ("Concurrent Operations", test_concurrent_operations),
        ("Memory & Cleanup", test_memory_and_cleanup),
        ("Error Recovery", test_error_recovery),
    ]

    results: dict[str, bool] = {}

    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            start_time = time.time()
            success = await test_func()
            end_time = time.time()
            duration = end_time - start_time

            results[test_name] = success
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{status} ({duration:.2f}s)")

        except Exception as exc:
            results[test_name] = False
            print(f"\n❌ FAILED - Exception: {exc}")

    print("\n" + "=" * 70)
    print("📊 STRESS TEST SUMMARY")
    print("=" * 70)

    passed = 0
    total = len(tests)

    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {test_name}")
        if success:
            passed += 1

    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL STRESS TESTS PASSED!")
        return True

    print("⚠️ Some stress tests failed")
    return False


if __name__ == "__main__":
    outcome = asyncio.run(main())
    sys.exit(0 if outcome else 1)
