#!/usr/bin/env python3
"""
Fixed Main Entry Point for AI Agent 3D Print System - Minimal Working Version

This is a working version focused on core functionality.
"""

import asyncio
import argparse
import logging
import sys
import traceback
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Core system imports
from core.parent_agent import ParentAgent, WorkflowState
from core.logger import get_logger
from core.exceptions import WorkflowError, ValidationError
from agents.research_agent import ResearchAgent
from agents.cad_agent import CADAgent
from agents.slicer_agent import SlicerAgent
from agents.printer_agent import PrinterAgent
from config.settings import load_config

# Web server imports
try:
    import uvicorn
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from api.main import app as api_app
    WEB_SERVER_ENABLED = True
except ImportError:
    WEB_SERVER_ENABLED = False
    api_app = None
    uvicorn = None
    StaticFiles = None
    Jinja2Templates = None

# Setup logging
logger = get_logger(__name__)


class WorkflowOrchestrator:
    """Complete workflow orchestrator for the AI Agent 3D Print System."""
    
    def __init__(self):
        """Initialize the workflow orchestrator."""
        self.config = load_config()
        self.parent_agent: Optional[ParentAgent] = None
        self.initialized = False
        
        # Agent instances for direct access
        self.research_agent: Optional[ResearchAgent] = None
        self.cad_agent: Optional[CADAgent] = None
        self.slicer_agent: Optional[SlicerAgent] = None
        self.printer_agent: Optional[PrinterAgent] = None
        
        # Workflow state
        self.current_workflow_id: Optional[str] = None
        self.cleanup_tasks = []
        
    async def initialize(self) -> None:
        """Initialize all agents and systems."""
        try:
            logger.info("🚀 Initializing AI Agent 3D Print System...")
            
            # Initialize individual agents
            self.research_agent = ResearchAgent("research_agent")
            self.cad_agent = CADAgent("cad_agent")
            self.slicer_agent = SlicerAgent("slicer_agent")
            self.printer_agent = PrinterAgent("printer_agent")
            
            # Initialize parent agent
            self.parent_agent = ParentAgent("parent_agent")
            await self.parent_agent.startup()
            
            # Initialize agents with actual instances
            self.parent_agent._research_agent = self.research_agent
            self.parent_agent._cad_agent = self.cad_agent
            self.parent_agent._slicer_agent = self.slicer_agent
            self.parent_agent._printer_agent = self.printer_agent
            
            # Enable mock mode for testing
            self.slicer_agent.set_mock_mode(True)
            logger.info(f"Set slicer mock mode to: {self.slicer_agent.mock_mode}")
            
            # Register agents for communication
            self.parent_agent.register_agent("research_agent")
            self.parent_agent.register_agent("cad_agent")
            self.parent_agent.register_agent("slicer_agent")
            self.parent_agent.register_agent("printer_agent")
            
            self.initialized = True
            logger.info("✅ System initialization completed successfully")
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def execute_complete_workflow(
        self, 
        user_request: str,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """Execute the complete 3D printing workflow."""
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        workflow_result = {
            "success": False,
            "workflow_id": None,
            "user_request": user_request,
            "start_time": datetime.now().isoformat(),
            "phases": {},
            "error_message": None,
            "files_generated": [],
            "cleanup_performed": False
        }
        
        try:
            logger.info(f"🎯 Starting complete workflow for: '{user_request}'")
            
            # Progress callback for user feedback
            async def progress_callback(progress_data: Dict[str, Any]):
                if show_progress:
                    percentage = progress_data.get('percentage', 0)
                    step = progress_data.get('current_step', 'Processing')
                    message = progress_data.get('message', '')
                    print(f"[{percentage:3.0f}%] {step}: {message}")
            
            # Create workflow
            workflow_id = await self.parent_agent.create_workflow(
                user_request, 
                progress_callback=progress_callback
            )
            self.current_workflow_id = workflow_id
            workflow_result["workflow_id"] = workflow_id
            
            if show_progress:
                print(f"📋 Created workflow: {workflow_id}")
            
            # Execute phases using ParentAgent methods
            logger.info("🔄 Executing complete workflow...")
            
            # Phase 1: Research
            workflow_result["phases"]["research"] = await self._execute_research_phase(
                user_request, workflow_id, progress_callback
            )
            
            # Phase 2: CAD
            workflow_result["phases"]["cad"] = await self._execute_cad_phase(
                workflow_result["phases"]["research"], workflow_id, progress_callback
            )
            
            # Phase 3: Slicer
            workflow_result["phases"]["slicer"] = await self._execute_slicer_phase(
                workflow_result["phases"]["cad"], workflow_id, progress_callback
            )
            
            # Phase 4: Printer
            workflow_result["phases"]["printer"] = await self._execute_printer_phase(
                workflow_result["phases"]["slicer"], workflow_id, progress_callback
            )
            
            # Mark as successful
            workflow_result["success"] = True
            workflow_result["end_time"] = datetime.now().isoformat()
            
            if show_progress:
                print("🎉 Workflow completed successfully!")
            
            logger.info("✅ Complete workflow executed successfully")
            return workflow_result
            
        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {e}")
            workflow_result["error_message"] = str(e)
            workflow_result["end_time"] = datetime.now().isoformat()
            
            # Perform cleanup
            await self._perform_cleanup()
            workflow_result["cleanup_performed"] = True
            
            if show_progress:
                print(f"❌ Workflow failed: {e}")
                print("🧹 Performing cleanup...")
            
            raise
    
    async def _execute_research_phase(self, user_request: str, workflow_id: str, progress_callback) -> Dict[str, Any]:
        """Execute the research phase."""
        logger.info(f"🔬 Starting research phase for workflow {workflow_id}...")
        phase_result = {"status": "pending", "output": None, "error": None}
        try:
            research_output = await self.parent_agent.execute_research_workflow(
                user_request, progress_callback
            )
            phase_result["status"] = "completed"
            phase_result["output"] = research_output
            logger.info(f"✅ Research phase completed for workflow {workflow_id}")
        except Exception as e:
            logger.error(f"❌ Research phase failed for workflow {workflow_id}: {e}")
            phase_result["status"] = "failed"
            phase_result["error"] = str(e)
            raise WorkflowError(f"Research phase failed: {e}") from e
        return phase_result

    async def _execute_cad_phase(self, research_output: Dict[str, Any], workflow_id: str, progress_callback) -> Dict[str, Any]:
        """Execute the CAD phase."""
        logger.info(f"📐 Starting CAD phase for workflow {workflow_id}...")
        phase_result = {"status": "pending", "output": None, "error": None}
        try:
            research_data = research_output.get("output", {})
            if not research_data:
                raise WorkflowError("Research data not found in research output.")

            cad_output = await self.parent_agent.execute_cad_workflow(
                research_data, progress_callback
            )
            phase_result["status"] = "completed"
            phase_result["output"] = cad_output
            logger.info(f"✅ CAD phase completed for workflow {workflow_id}")
        except Exception as e:
            logger.error(f"❌ CAD phase failed for workflow {workflow_id}: {e}")
            phase_result["status"] = "failed"
            phase_result["error"] = str(e)
            raise WorkflowError(f"CAD phase failed: {e}") from e
        return phase_result
        
    async def _execute_slicer_phase(self, cad_output: Dict[str, Any], workflow_id: str, progress_callback) -> Dict[str, Any]:
        """Execute the slicer phase."""
        logger.info(f"🔧 Starting slicer phase for workflow {workflow_id}...")
        phase_result = {"status": "pending", "output": None, "error": None}
        try:
            cad_data = cad_output.get("output", {})
            if not cad_data:
                raise WorkflowError("CAD data not found in CAD output.")

            slicer_output = await self.parent_agent.execute_slicer_workflow(
                cad_data, progress_callback
            )
            phase_result["status"] = "completed"
            phase_result["output"] = slicer_output
            logger.info(f"✅ Slicer phase completed for workflow {workflow_id}")
        except Exception as e:
            logger.error(f"❌ Slicer phase failed for workflow {workflow_id}: {e}")
            phase_result["status"] = "failed"
            phase_result["error"] = str(e)
            raise WorkflowError(f"Slicer phase failed: {e}") from e
        return phase_result
        
    async def _execute_printer_phase(self, slicer_output: Dict[str, Any], workflow_id: str, progress_callback) -> Dict[str, Any]:
        """Execute the printer phase."""
        logger.info(f"🖨️ Starting printer phase for workflow {workflow_id}...")
        phase_result = {"status": "pending", "output": None, "error": None}
        try:
            slicer_data = slicer_output.get("output", {})
            if not slicer_data:
                raise WorkflowError("Slicer data not found in slicer output.")

            printer_output = await self.parent_agent.execute_printer_workflow(
                slicer_data, progress_callback
            )
            phase_result["status"] = "completed"
            phase_result["output"] = printer_output
            logger.info(f"✅ Printer phase completed for workflow {workflow_id}")
        except Exception as e:
            logger.error(f"❌ Printer phase failed for workflow {workflow_id}: {e}")
            phase_result["status"] = "failed"
            phase_result["error"] = str(e)
            raise WorkflowError(f"Printer phase failed: {e}") from e
        return phase_result

    async def _perform_cleanup(self) -> None:
        """Perform cleanup after workflow failure or completion."""
        try:
            logger.info("🧹 Performing cleanup...")
            
            # Clean up generated files
            import os
            files_cleaned = 0
            for cleanup_type, resource in self.cleanup_tasks:
                try:
                    if cleanup_type == "file" and os.path.exists(resource):
                        os.remove(resource)
                        files_cleaned += 1
                        logger.debug(f"Removed file: {resource}")
                except Exception as e:
                    logger.warning(f"Could not remove {resource}: {e}")
            
            # Reset workflow state
            if self.current_workflow_id and self.parent_agent:
                try:
                    await self.parent_agent.cancel_workflow(self.current_workflow_id)
                    logger.info(f"Cancelled workflow: {self.current_workflow_id}")
                except Exception as e:
                    logger.warning(f"Could not cancel workflow: {e}")
            
            # Clear cleanup tasks
            self.cleanup_tasks.clear()
            self.current_workflow_id = None
            
            logger.info(f"✅ Cleanup completed - removed {files_cleaned} files")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the system gracefully."""
        try:
            logger.info("🔽 Shutting down AI Agent 3D Print System...")
            
            # Perform final cleanup
            await self._perform_cleanup()
            
            # Shutdown agents
            if self.parent_agent:
                await self.parent_agent.shutdown()
            
            logger.info("✅ System shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}")


async def detect_and_list_printers():
    """Detect and list available 3D printers."""
    print("🔍 Detecting available 3D printers...")
    print("=" * 50)
    
    try:
        printer_agent = PrinterAgent("printer_detector")
        detected_printers = await printer_agent._detect_printers()
        
        if detected_printers:
            print(f"✅ Found {len(detected_printers)} potential 3D printer(s):")
            print()
            
            for i, printer_info in enumerate(detected_printers, 1):
                port = printer_info.get('port', 'Unknown')
                description = printer_info.get('description', 'No description')
                manufacturer = printer_info.get('manufacturer', 'Unknown')
                product = printer_info.get('product', 'Unknown')
                
                print(f"{i}. Serial Port: {port}")
                print(f"   Description: {description}")
                print(f"   Manufacturer: {manufacturer}")
                print(f"   Product: {product}")
                print()
            
            print("💡 To use a detected printer:")
            print(f"   python main.py --web --use-real-printer --printer-port {detected_printers[0].get('port', '/dev/ttyUSB0')}")
            print()
            print("📝 Or update config/settings.yaml:")
            print("   printer:")
            print("     enabled: true")
            print("     mock_mode: false")
            print("     serial:")
            print(f"       port: \"{detected_printers[0].get('port', '/dev/ttyUSB0')}\"")
            print("       baudrate: 115200")
            
        else:
            print("❌ No 3D printers detected.")
            print()
            print("🔧 Troubleshooting:")
            print("1. Make sure your 3D printer is connected via USB")
            print("2. Check that the printer is powered on")
            print("3. Verify USB cable is working")
            print("4. Try running: ls -la /dev/tty* | grep -E '(USB|ACM)'")
            print("5. Check USB devices: lsusb")
        
        print("\n" + "=" * 50)
        return True
        
    except Exception as e:
        print(f"❌ Error during printer detection: {e}")
        logger.error(f"Printer detection failed: {e}")
        return False


async def configure_printer_settings(args):
    """Configure printer settings based on command line arguments."""
    config = load_config()
    changes_made = False
    
    if args.use_real_printer:
        print("🔧 Configuring for real printer mode...")
        config.setdefault('printer', {})['mock_mode'] = False
        changes_made = True
    
    if args.printer_port:
        print(f"🔧 Setting printer port to: {args.printer_port}")
        config.setdefault('printer', {}).setdefault('serial', {})['port'] = args.printer_port
        changes_made = True
    
    if args.baudrate != 115200:
        print(f"🔧 Setting printer baudrate to: {args.baudrate}")
        config.setdefault('printer', {}).setdefault('serial', {})['baudrate'] = args.baudrate
        changes_made = True
    
    if changes_made:
        print("✅ Printer configuration updated for this session")
    
    return config


async def run_end_to_end_test() -> bool:
    """Run the end-to-end test: 'Print a 2cm cube'."""
    print("🧪 Running End-to-End Test: 'Print a 2cm cube'")
    print("=" * 60)
    
    orchestrator = WorkflowOrchestrator()
    
    try:
        await orchestrator.initialize()
        result = await orchestrator.execute_complete_workflow(
            "Print a 2cm cube",
            show_progress=True
        )
        
        if result["success"]:
            print("\n✅ End-to-End Test PASSED!")
            print(f"   - Workflow ID: {result['workflow_id']}")
            print(f"   - All phases completed successfully")
            
            phases = result.get("phases", {})
            required_phases = ["research", "cad", "slicer", "printer"]
            
            for phase in required_phases:
                if phase in phases and phases[phase].get("status") == "completed":
                    print(f"   ✅ {phase.capitalize()} phase: SUCCESS")
                else:
                    print(f"   ❌ {phase.capitalize()} phase: FAILED")
                    return False
            
            return True
        else:
            print(f"\n❌ End-to-End Test FAILED: {result.get('error_message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ End-to-End Test FAILED: {e}")
        logger.error(f"Test failed: {e}")
        return False
    
    finally:
        await orchestrator.shutdown()


async def run_interactive_mode():
    """Run the system in interactive mode."""
    print("🤖 AI Agent 3D Print System - Interactive Mode")
    print("=" * 50)
    print("Enter natural language descriptions of objects to print.")
    print("Type 'quit' or 'exit' to stop.")
    print()
    
    orchestrator = WorkflowOrchestrator()
    
    try:
        await orchestrator.initialize()
        
        while True:
            try:
                user_input = input("What would you like to print? ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                print(f"\n🎯 Processing request: '{user_input}'")
                print("-" * 40)
                
                result = await orchestrator.execute_complete_workflow(
                    user_input,
                    show_progress=True
                )
                
                if result["success"]:
                    print(f"\n🎉 Request completed successfully!")
                    print(f"Workflow ID: {result['workflow_id']}")
                else:
                    print(f"\n❌ Request failed: {result.get('error_message', 'Unknown error')}")
                
                print("\n" + "=" * 50)
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error processing request: {e}")
                logger.error(f"Interactive mode error: {e}")
    
    finally:
        await orchestrator.shutdown()


async def main():
    """Main function to run the AI Agent 3D Print System."""
    parser = argparse.ArgumentParser(description="AI Agent 3D Print System")
    parser.add_argument("request", nargs='?', help="User request for 3D printing (e.g., 'Print a 2cm cube')")
    parser.add_argument("--test", action="store_true", help="Run end-to-end test workflow")
    parser.add_argument("--web", action="store_true", help="Start API server and web interface")
    parser.add_argument("--port", type=int, default=8000, help="Port for the web server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for the web server")
    parser.add_argument("--printer-port", type=str, help="Serial port for 3D printer (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baudrate", type=int, default=115200, help="Baud rate for printer communication")
    parser.add_argument("--use-real-printer", action="store_true", help="Use real printer instead of mock mode")
    parser.add_argument("--detect-printers", action="store_true", help="Detect available 3D printers and exit")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle printer detection first (early exit)
    if args.detect_printers:
        success = await detect_and_list_printers()
        sys.exit(0 if success else 1)
    
    # Configure printer settings based on command line arguments
    if args.use_real_printer or args.printer_port or args.baudrate != 115200:
        await configure_printer_settings(args)

    # Handle web server mode
    if args.web:
        if not WEB_SERVER_ENABLED:
            print("❌ Web server functionality not available.")
            print("Please install required dependencies: pip install fastapi uvicorn python-multipart jinja2 aiofiles")
            sys.exit(1)
        
        print(f"🌐 Starting AI Agent 3D Print System Web Interface...")
        print(f"   Host: {args.host}")
        print(f"   Port: {args.port}")
        if args.use_real_printer:
            print(f"   Printer Mode: REAL (Port: {args.printer_port or 'from config'})")
        else:
            print(f"   Printer Mode: MOCK")
        print()
        
        try:
            # Initialize orchestrator for the web server
            orchestrator = WorkflowOrchestrator()
            await orchestrator.initialize()
            
            # Mount static files
            api_app.mount("/static", StaticFiles(directory="static"), name="static")
            api_app.mount("/web", StaticFiles(directory="web"), name="web")
            
            # Add root route to serve the main web interface
            @api_app.get("/")
            async def read_index():
                from fastapi.responses import FileResponse
                return FileResponse("web/index.html")
            
            # Start the server
            config = uvicorn.Config(
                app=api_app,
                host=args.host,
                port=args.port,
                log_level="info" if not args.verbose else "debug"
            )
            server = uvicorn.Server(config)
            
            # Create server task
            server_task = asyncio.create_task(server.serve())
            
            # Give the server a moment to start
            await asyncio.sleep(1)
            
            # Open browser
            display_host = "localhost" if args.host in ["127.0.0.1", "0.0.0.0"] else args.host
            print(f"Web server starting. Attempting to open browser to http://{display_host}:{args.port}")
            try:
                webbrowser.open_new_tab(f"http://{display_host}:{args.port}")
            except Exception as e:
                logger.warning(f"Could not open browser automatically: {e}. Please open it manually.")

            await server_task
            
        except KeyboardInterrupt:
            logger.info("Web server stopped by user.")
        except Exception as e:
            logger.error(f"Failed to start or run web server: {e}")
            logger.error(traceback.format_exc())
            sys.exit(1)
        
        return
    
    try:
        if args.test:
            # Run end-to-end test
            success = await run_end_to_end_test()
            sys.exit(0 if success else 1)
        
        elif args.request:
            # Process direct request
            orchestrator = WorkflowOrchestrator()
            try:
                await orchestrator.initialize()
                result = await orchestrator.execute_complete_workflow(
                    args.request,
                    show_progress=True
                )
                
                if result["success"]:
                    print(f"\n🎉 Successfully completed: '{args.request}'")
                    sys.exit(0)
                else:
                    print(f"\n❌ Failed to complete: '{args.request}'")
                    print(f"Error: {result.get('error_message', 'Unknown error')}")
                    sys.exit(1)
            finally:
                await orchestrator.shutdown()
        
        else:
            # Interactive mode
            await run_interactive_mode()
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ System error: {e}")
        logger.error(f"Main error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 AI Agent 3D Print System")
    print("Task 5.1: Complete Workflow Implementation")
    print("=" * 50)
    
    asyncio.run(main())
