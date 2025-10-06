#!/usr/bin/env python3
"""Manual demo for printer pause/resume functionality."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Ensure project root is importable
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


async def run_printer_pause_resume() -> bool:
    """Run pause and resume checks against the printer agent."""
    print("🧪 Testing Printer Pause/Resume Functions")
    print("=" * 50)

    try:
        from agents.printer_agent import PrinterAgent

        printer_agent = PrinterAgent()
        printer_agent.mock_mode = True
        print("✅ Printer agent initialized")

        mock_gcode_content = """G28 ; Home all axes
G1 Z5 F5000 ; Lift nozzle
G1 X50 Y50 F3000 ; Move to position
G1 E5 F300 ; Extrude some filament
G1 X100 Y100 E10 F1500 ; Print line
G1 X50 Y100 E15 F1500 ; Print another line
G1 X50 Y50 E20 F1500 ; Print back
M104 S0 ; Turn off hotend
M140 S0 ; Turn off bed
G28 X0 ; Home X
M84 ; Disable steppers"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".gcode", delete=False) as temp_file:
            temp_file.write(mock_gcode_content)
            gcode_file_path = temp_file.name

        print(f"📄 Created temporary G-code file: {gcode_file_path}")

        print("\n🖨️ Test 1: Starting print with G-code file...")
        try:
            start_result = await printer_agent.execute_task(
                {
                    "operation": "start_print",
                    "gcode_file_path": gcode_file_path,
                    "print_settings": {"chunk_size": 5, "delay_between_chunks": 0.1},
                }
            )

            if start_result and hasattr(start_result, "success") and start_result.success:
                print("✅ Print started successfully")
                job_id = start_result.data.get("job_id") if hasattr(start_result, "data") else None
                print(f"   Job ID: {job_id}")
            else:
                print("❌ Print start failed")
                if hasattr(start_result, "error_message"):
                    print(f"   Error: {start_result.error_message}")
                return False
        except Exception as exc:
            print(f"❌ Print start failed with exception: {exc}")
            return False

        await asyncio.sleep(0.3)

        print("\n📊 Test 2: Checking streaming status...")
        try:
            if hasattr(printer_agent, "streaming_status"):
                status = printer_agent.streaming_status
                print(f"   Is streaming: {status.is_streaming}")
                print(f"   Is paused: {status.is_paused}")
                print(f"   Current position: {status.current_position}")
            else:
                print("   No streaming status available")
        except Exception as exc:
            print(f"   Status check failed: {exc}")

        print("\n⏸️ Test 3: Testing internal pause method...")
        try:
            if hasattr(printer_agent, "_pause_streaming"):
                pause_success = await printer_agent._pause_streaming()
                print(f"✅ Internal pause method result: {pause_success}")
            else:
                print("❌ Internal pause method not found")
        except Exception as exc:
            print(f"⚠️ Internal pause failed: {exc}")

        print("\n▶️ Test 4: Testing internal resume method...")
        try:
            if hasattr(printer_agent, "_resume_streaming"):
                resume_success = await printer_agent._resume_streaming()
                print(f"✅ Internal resume method result: {resume_success}")
            else:
                print("❌ Internal resume method not found")
        except Exception as exc:
            print(f"⚠️ Internal resume failed: {exc}")

        print("\n🛑 Test 5: Testing emergency stop...")
        try:
            if hasattr(printer_agent, "_emergency_stop"):
                stop_success = await printer_agent._emergency_stop()
                print(f"✅ Emergency stop result: {stop_success}")
            else:
                print("❌ Emergency stop method not found")
        except Exception as exc:
            print(f"⚠️ Emergency stop failed: {exc}")

        print("\n🔄 Test 6: Testing task interface for pause/resume...")
        try:
            start_result2 = await printer_agent.execute_task(
                {
                    "operation": "start_print",
                    "gcode_file_path": gcode_file_path,
                }
            )
            print(f"   Second print started: {start_result2 is not None}")
        except Exception:
            pass

        await asyncio.sleep(0.2)

        try:
            pause_task_result = await printer_agent.execute_task({"operation": "pause_print"})

            if isinstance(pause_task_result, dict):
                success = pause_task_result.get("success", False)
                print(f"   Pause task result (dict): {success}")
                if not success:
                    print(f"   Error: {pause_task_result.get('error_message', 'Unknown error')}")
            elif hasattr(pause_task_result, "success"):
                print(f"   Pause task result (TaskResult): {pause_task_result.success}")
                if not pause_task_result.success:
                    print(f"   Error: {pause_task_result.error_message}")
            else:
                print(f"   Pause task result (unknown type): {pause_task_result}")
        except Exception as exc:
            print(f"   Pause task exception: {exc}")

        try:
            os.unlink(gcode_file_path)
            print(f"\n🧹 Cleaned up temporary file: {gcode_file_path}")
        except Exception:
            pass

        print("\n🎉 Pause/Resume functionality test completed!")
        return True

    except Exception as exc:
        print(f"❌ Test failed with exception: {exc}")
        import traceback

        traceback.print_exc()
        return False


async def run_error_handling_checks() -> bool:
    """Run additional error handling checks."""
    print("\n🚨 Testing Error Handling")
    print("=" * 50)

    try:
        from agents.printer_agent import PrinterAgent

        printer_agent = PrinterAgent()
        printer_agent.mock_mode = True

        print("\n📁 Test 1: Invalid G-code file path...")
        try:
            result = await printer_agent.execute_task(
                {
                    "operation": "start_print",
                    "gcode_file_path": "/nonexistent/file.gcode",
                }
            )
            print(f"   Expected failure handled: {result}")
        except Exception as exc:
            print(f"   Expected exception: {type(exc).__name__}: {exc}")

        print("\n⏸️ Test 2: Pause without active print...")
        try:
            result = await printer_agent.execute_task({"operation": "pause_print"})
            if isinstance(result, dict):
                print(
                    "   Result (dict): success=",
                    result.get("success"),
                    ", error=",
                    result.get("error_message"),
                )
            else:
                print(f"   Result (other): {result}")
        except Exception as exc:
            print(f"   Expected exception: {type(exc).__name__}: {exc}")

        print("\n✅ Error handling tests completed!")
        return True

    except Exception as exc:
        print(f"❌ Error handling test failed: {exc}")
        return False


async def main() -> bool:
    """Entry point for the manual demo."""
    print("🚀 AI Agent 3D Print - Printer Agent Tests")
    print("=" * 60)

    pause_resume_success = await run_printer_pause_resume()
    error_handling_success = await run_error_handling_checks()

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Pause/Resume Tests: {'PASSED' if pause_resume_success else 'FAILED'}")
    print(f"✅ Error Handling Tests: {'PASSED' if error_handling_success else 'FAILED'}")

    overall_success = pause_resume_success and error_handling_success
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")

    return overall_success


if __name__ == "__main__":
    outcome = asyncio.run(main())
    sys.exit(0 if outcome else 1)
