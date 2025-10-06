#!/usr/bin/env python3
"""Manual demo covering advanced pause/resume scenarios."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


async def run_pause_resume_functionality() -> bool:
    """Test pause and resume functionality of the printer agent."""
    print("🧪 Testing Pause/Resume Functionality")
    print("=" * 50)

    try:
        from agents.printer_agent import PrinterAgent

        print("📚 Initializing printer agent...")
        printer_agent = PrinterAgent()
        printer_agent.mock_mode = True

        print("✅ Printer agent initialized")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".gcode", delete=False) as temp_file:
            gcode_content = """G28 ; Home
G1 Z5 F5000 ; Lift nozzle
G1 X50 Y50 F3000 ; Move to position
G1 E5 F300 ; Extrude
G1 X100 Y100 E10 F1500 ; Print line
M104 S0 ; Turn off hotend
M140 S0 ; Turn off bed
G28 X0 ; Home X
M84 ; Disable steppers"""
            temp_file.write(gcode_content)
            gcode_file_path = temp_file.name

        stream_result = await printer_agent.execute_task(
            {
                "operation": "stream_gcode",
                "specifications": {"gcode_file": gcode_file_path, "progress_callback": None},
            }
        )

        if stream_result and isinstance(stream_result, dict) and stream_result.get("success"):
            print("✅ Mock print job started successfully")
            print(f"   Job ID: {stream_result.get('job_id', 'Unknown')}")
        else:
            error_msg = (
                stream_result.get("error", "Unknown error")
                if isinstance(stream_result, dict)
                else str(stream_result)
            )
            print(f"❌ Print start failed: {error_msg}")
            return False

        await asyncio.sleep(0.2)

        print("\n⏸️ Test 2: Pausing print...")
        try:
            pause_result = await printer_agent.execute_task({"operation": "pause_print"})

            if pause_result and isinstance(pause_result, dict) and pause_result.get("success"):
                print("✅ Print paused successfully")
                print(f"   Details: {pause_result}")
            else:
                error_msg = (
                    pause_result.get("error", "Unknown error")
                    if isinstance(pause_result, dict)
                    else str(pause_result)
                )
                print(f"❌ Pause failed: {error_msg}")
                return False
        except Exception as exc:
            print(f"❌ Pause test failed with exception: {exc}")
            return False

        await asyncio.sleep(0.2)

        print("\n⏸️ Test 3: Trying to pause already paused print...")
        try:
            pause_again_result = await printer_agent.execute_task({"operation": "pause_print"})
            if pause_again_result and isinstance(pause_again_result, dict):
                print("✅ Second pause handled gracefully")
                print(f"   Message: {pause_again_result.get('message', 'No message')}")
            else:
                print(f"❌ Second pause failed: {pause_again_result}")
        except Exception as exc:
            print(f"⚠️ Second pause test failed with exception: {exc}")

        print("\n▶️ Test 4: Resuming print...")
        try:
            resume_result = await printer_agent.execute_task({"operation": "resume_print"})

            if resume_result and isinstance(resume_result, dict) and resume_result.get("success"):
                print("✅ Print resumed successfully")
                print(f"   Details: {resume_result}")
            else:
                error_msg = (
                    resume_result.get("error", "Unknown error")
                    if isinstance(resume_result, dict)
                    else str(resume_result)
                )
                print(f"❌ Resume failed: {error_msg}")
                return False
        except Exception as exc:
            print(f"❌ Resume test failed with exception: {exc}")
            return False

        await asyncio.sleep(0.2)

        print("\n▶️ Test 5: Trying to resume already running print...")
        try:
            resume_again_result = await printer_agent.execute_task({"operation": "resume_print"})
            if resume_again_result and isinstance(resume_again_result, dict):
                print("✅ Second resume handled gracefully")
                print(f"   Message: {resume_again_result.get('message', 'No message')}")
            else:
                print(f"❌ Second resume failed: {resume_again_result}")
        except Exception as exc:
            print(f"⚠️ Second resume test failed with exception: {exc}")

        print("\n🛑 Test 6: Emergency stop...")
        try:
            stop_result = await printer_agent.execute_task({"operation": "stop_print"})
            if stop_result and isinstance(stop_result, dict):
                print("✅ Emergency stop successful")
                print(f"   Details: {stop_result}")
            else:
                print(f"❌ Emergency stop failed: {stop_result}")
        except Exception as exc:
            print(f"⚠️ Emergency stop test failed with exception: {exc}")

        print("\n⏸️ Test 7: Testing operations on stopped print...")
        try:
            pause_stopped_result = await printer_agent.execute_task({"operation": "pause_print"})
            success = (
                pause_stopped_result
                and isinstance(pause_stopped_result, dict)
                and pause_stopped_result.get("success")
            )
            print(f"   Pause on stopped print: {success}")
            if not success:
                error_msg = (
                    pause_stopped_result.get("error", "Unknown error")
                    if isinstance(pause_stopped_result, dict)
                    else str(pause_stopped_result)
                )
                print(f"   Expected error: {error_msg}")
        except Exception as exc:
            print(f"   Expected exception for pause on stopped print: {exc}")

        try:
            os.unlink(gcode_file_path)
        except Exception:
            pass

        print("\n🎉 All pause/resume tests completed!")
        return True

    except Exception as exc:
        print(f"❌ Test failed with exception: {exc}")
        import traceback

        traceback.print_exc()
        return False


async def run_edge_case_checks() -> bool:
    """Test edge cases and error handling."""
    print("\n🧪 Testing Edge Cases")
    print("=" * 50)

    try:
        from agents.printer_agent import PrinterAgent

        printer_agent = PrinterAgent()
        printer_agent.mock_mode = True

        print("\n⏸️ Test 1: Pause without active print...")
        try:
            pause_result = await printer_agent.execute_task({"operation": "pause_print"})
            success = (
                pause_result and isinstance(pause_result, dict) and pause_result.get("success")
            )
            print(f"   Result success: {success}")
            if not success:
                error_msg = (
                    pause_result.get("error", "Unknown error")
                    if isinstance(pause_result, dict)
                    else str(pause_result)
                )
                print(f"   Expected error: {error_msg}")
        except Exception as exc:
            print(f"   Expected exception: {exc}")

        print("\n▶️ Test 2: Resume without active print...")
        try:
            resume_result = await printer_agent.execute_task({"operation": "resume_print"})
            success = (
                resume_result and isinstance(resume_result, dict) and resume_result.get("success")
            )
            print(f"   Result success: {success}")
            if not success:
                error_msg = (
                    resume_result.get("error", "Unknown error")
                    if isinstance(resume_result, dict)
                    else str(resume_result)
                )
                print(f"   Expected error: {error_msg}")
        except Exception as exc:
            print(f"   Expected exception: {exc}")

        print("\n❓ Test 3: Invalid operation...")
        try:
            invalid_result = await printer_agent.execute_task({"operation": "invalid_operation"})
            success = (
                invalid_result
                and isinstance(invalid_result, dict)
                and invalid_result.get("success")
            )
            print(f"   Result success: {success}")
            if not success:
                error_msg = (
                    invalid_result.get("error", "Unknown error")
                    if isinstance(invalid_result, dict)
                    else str(invalid_result)
                )
                print(f"   Expected error: {error_msg}")
        except Exception as exc:
            print(f"   Expected exception: {exc}")

        print("\n✅ Edge case tests completed!")
        return True

    except Exception as exc:
        print(f"❌ Edge case tests failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


async def main() -> bool:
    """Entry point for the advanced pause/resume demo."""
    print("🚀 AI Agent 3D Print - Advanced Function Tests")
    print("=" * 60)

    pause_resume_success = await run_pause_resume_functionality()
    edge_case_success = await run_edge_case_checks()

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Pause/Resume Tests: {'PASSED' if pause_resume_success else 'FAILED'}")
    print(f"✅ Edge Case Tests: {'PASSED' if edge_case_success else 'FAILED'}")

    overall_success = pause_resume_success and edge_case_success
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")

    return overall_success


if __name__ == "__main__":
    outcome = asyncio.run(main())
    sys.exit(0 if outcome else 1)
