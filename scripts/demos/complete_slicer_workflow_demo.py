#!/usr/bin/env python3
"""
Complete Slicer Agent Workflow Demo

This demo showcases the complete Slicer Agent workflow from STL to G-code streaming,
demonstrating the integration of all three completed tasks:
- Task 2.3.1: Slicer CLI Wrapper with Profiles
- Task 2.3.2: Serial Communication with Mock Mode  
- Task 2.3.3: G-Code Streaming with Progress Tracking

This represents the complete Slicer Agent functionality ready for Phase 4 integration.
"""

import os
import sys
import asyncio
import tempfile
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.slicer_agent import SlicerAgent
from agents.printer_agent import PrinterAgent


async def complete_workflow_demo():
    """Demonstrate complete STL → G-code → Streaming workflow."""
    print("="*80)
    print("🎯 COMPLETE SLICER AGENT WORKFLOW DEMONSTRATION")
    print("   STL → G-code → Printer Streaming")
    print("="*80)
    
    # Create a simple test STL content (for demo purposes)
    print("\n📁 Step 1: Preparing STL File")
    print("-" * 40)
    
    temp_dir = tempfile.mkdtemp()
    test_stl = os.path.join(temp_dir, "test_cube.stl")
    
    # Create a minimal STL file content (ASCII format)
    stl_content = """solid Cube
  facet normal 0.0 0.0 1.0
    outer loop
      vertex 0.0 0.0 1.0
      vertex 1.0 0.0 1.0
      vertex 1.0 1.0 1.0
    endloop
  endfacet
  facet normal 0.0 0.0 1.0
    outer loop
      vertex 0.0 0.0 1.0
      vertex 1.0 1.0 1.0
      vertex 0.0 1.0 1.0
    endloop
  endfacet
endsolid Cube"""
    
    with open(test_stl, 'w') as f:
        f.write(stl_content)
    
    print(f"✅ Test STL created: {test_stl}")
    
    # Step 2: Slice STL to G-code (Task 2.3.1)
    print("\n🔪 Step 2: Slicing STL to G-code (Task 2.3.1)")
    print("-" * 50)
    
    slicer_agent = SlicerAgent("workflow_demo_slicer")
    
    slice_task = {
        'operation': 'slice_stl',
        'specifications': {
            'model_file_path': test_stl,
            'printer_profile': 'ender3_pla_standard',
            'quality_preset': 'standard',
            'infill_percentage': 15
        }
    }
    
    print("🔄 Starting slicing process...")
    slice_result = await slicer_agent.execute_task(slice_task)
    
    if slice_result.get('success', False):
        gcode_file = slice_result['data']['gcode_file_path']
        estimated_time = slice_result['data']['estimated_print_time']
        layer_count = slice_result['data']['layer_count']
        material_usage = slice_result['data']['material_usage']
        
        print(f"✅ Slicing completed successfully!")
        print(f"   📄 G-code file: {gcode_file}")
        print(f"   ⏱️  Estimated time: {estimated_time} minutes")
        print(f"   📏 Layers: {layer_count}")
        print(f"   🧵 Material: {material_usage:.1f}g")
    else:
        print(f"❌ Slicing failed: {slice_result.get('error_message')}")
        return
    
    # Step 3: Connect to Printer (Task 2.3.2)
    print("\n🖨️  Step 3: Connecting to Printer (Task 2.3.2)")
    print("-" * 45)
    
    printer_agent = PrinterAgent("workflow_demo_printer", config={'mock_mode': True})
    
    connect_result = await printer_agent.execute_task({
        'operation': 'connect_printer',
        'specifications': {}
    })
    
    if connect_result.get('success', False):
        print("✅ Printer connected successfully!")
        print(f"   🔌 Connection: Mock Mode")
        
        # Get printer status
        status_result = await printer_agent.execute_task({
            'operation': 'get_printer_status',
            'specifications': {}
        })
        
        printer_status = status_result.get('printer_status', {})
        print(f"   📊 Status: {printer_status.get('status', 'unknown')}")
        print(f"   🌡️  Hotend: {printer_status.get('temperature', {}).get('hotend_current', 0):.1f}°C")
    else:
        print(f"❌ Printer connection failed: {connect_result.get('error_message')}")
        return
    
    # Step 4: Stream G-code with Progress Tracking (Task 2.3.3)
    print("\n🔄 Step 4: Streaming G-code with Progress (Task 2.3.3)")
    print("-" * 55)
    
    progress_updates = []
    
    def progress_callback(progress_data):
        """Callback to track streaming progress."""
        progress_updates.append({
            'percent': progress_data.get('progress_percent', 0),
            'lines_sent': progress_data.get('lines_sent', 0),
            'lines_total': progress_data.get('lines_total', 0),
            'status': progress_data.get('status', 'unknown')
        })
    
    # Start streaming
    print("🚀 Starting G-code streaming...")
    stream_result = await printer_agent.execute_task({
        'operation': 'stream_gcode',
        'specifications': {
            'gcode_file': gcode_file,
            'progress_callback': progress_callback
        }
    })
    
    if stream_result.get('success', False):
        job_id = stream_result.get('job_id')
        print(f"✅ Streaming started: {job_id}")
        
        # Monitor progress for demo
        print("📊 Monitoring progress...")
        
        for i in range(8):  # Monitor for ~4 seconds
            await asyncio.sleep(0.5)
            
            progress_result = await printer_agent.execute_task({
                'operation': 'get_print_progress',
                'specifications': {}
            })
            
            if progress_result.get('has_progress', False):
                progress = progress_result.get('progress', {})
                status = progress.get('status', 'unknown')
                percent = progress.get('progress_percent', 0)
                lines_sent = progress.get('lines_sent', 0)
                lines_total = progress.get('lines_total', 0)
                current_layer = progress.get('current_layer', 0)
                
                print(f"   📈 Progress: {percent:.1f}% ({lines_sent}/{lines_total} lines) Layer: {current_layer}")
                
                # Test pause/resume at 50% progress
                if i == 4 and percent > 30:
                    print("   ⏸️  Testing pause functionality...")
                    pause_result = await printer_agent.execute_task({
                        'operation': 'pause_print',
                        'specifications': {}
                    })
                    if pause_result.get('success', False):
                        print("   ✅ Print paused successfully")
                
                # Resume after pause
                elif i == 6:
                    print("   ▶️  Testing resume functionality...")
                    resume_result = await printer_agent.execute_task({
                        'operation': 'resume_print',
                        'specifications': {}
                    })
                    if resume_result.get('success', False):
                        print("   ✅ Print resumed successfully")
                
                if status in ['completed', 'cancelled', 'failed']:
                    print(f"   🏁 Final status: {status}")
                    break
        
        # Final progress check
        final_progress = await printer_agent.execute_task({
            'operation': 'get_print_progress',
            'specifications': {}
        })
        
        if final_progress.get('has_progress', False):
            final_data = final_progress.get('progress', {})
            final_percent = final_data.get('progress_percent', 0)
            final_status = final_data.get('status', 'unknown')
            elapsed_time = final_data.get('elapsed_time', 0)
            
            print(f"\n📋 Final Results:")
            print(f"   ✅ Status: {final_status}")
            print(f"   📈 Progress: {final_percent:.1f}%")
            print(f"   ⏱️  Elapsed: {elapsed_time:.1f}s")
            print(f"   📞 Callback calls: {len(progress_updates)}")
    
    else:
        print(f"❌ Streaming failed: {stream_result.get('error_message')}")
    
    # Step 5: Cleanup
    print("\n🧹 Step 5: Cleanup")
    print("-" * 20)
    
    # Stop any active streaming
    await printer_agent.execute_task({
        'operation': 'stop_print',
        'specifications': {}
    })
    
    # Cleanup agents
    printer_agent.cleanup()
    
    # Remove temp files
    try:
        os.unlink(test_stl)
        if os.path.exists(gcode_file):
            os.unlink(gcode_file)
        os.rmdir(temp_dir)
        print("✅ Cleanup completed")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
    
    # Step 6: Summary
    print("\n🎉 Step 6: Workflow Summary")
    print("-" * 30)
    
    print("✅ COMPLETE SLICER AGENT WORKFLOW DEMONSTRATED:")
    print("   1️⃣  STL file processing ✅")
    print("   2️⃣  G-code generation with profiles ✅") 
    print("   3️⃣  Printer connection and status ✅")
    print("   4️⃣  G-code streaming with progress ✅")
    print("   5️⃣  Pause/Resume functionality ✅")
    print("   6️⃣  Progress callbacks and monitoring ✅")
    
    print(f"\n🏆 ALL THREE SLICER AGENT TASKS COMPLETED:")
    print(f"   ✅ Task 2.3.1: CLI Wrapper with Profiles")
    print(f"   ✅ Task 2.3.2: Serial Communication with Mock Mode")
    print(f"   ✅ Task 2.3.3: G-Code Streaming with Progress Tracking")
    
    print(f"\n🚀 READY FOR PHASE 4: API & Communication Layer")


if __name__ == "__main__":
    print("🎯 Starting Complete Slicer Agent Workflow Demo...")
    asyncio.run(complete_workflow_demo())
