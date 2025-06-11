#!/usr/bin/env python3
"""
Main Entry Point for AI Agent 3D Print System

This is the main entry point that implements Task 5.1: Complete Workflow Implementation.
It provides a comprehensive end-to-end workflow orchestration system with:

- Complete workflow: User Input → Research → CAD → Slicer → Printer
- Robust error handling at each step 
- Rollback and cleanup functionality
- Progress tracking and user feedback
- End-to-end testing capability

Usage:
    python main.py                     # Interactive mode
    python main.py "Print a 2cm cube"  # Direct command
    python main.py --test              # Run end-to-end test
    python main.py --api               # Start API server
"""

import asyncio
import argparse
import logging
import sys
import traceback
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

# Setup logging
logger = get_logger(__name__)


class WorkflowOrchestrator:
    """
    Complete workflow orchestrator for the AI Agent 3D Print System.
    
    Implements Task 5.1 requirements:
    - End-to-end workflow execution
    - Error handling with rollback
    - Progress tracking
    - Cleanup functionality
    """
    
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
        """
        Execute the complete 3D printing workflow.
        
        Workflow steps:
        1. User Input → Research Agent
        2. Research Result → CAD Agent  
        3. STL File → Slicer Agent
        4. G-Code → Printer Agent
        5. Progress Updates → User Interface
        
        Args:
            user_request: Natural language description of object to print
            show_progress: Whether to show progress updates
            
        Returns:
            Dict with workflow results and status
        """
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
            
            # Execute the complete workflow
            logger.info("🔄 Executing complete workflow...")
            
            # Phase 1: Research and Concept Generation
            workflow_result["phases"]["research"] = await self._execute_research_phase(
                user_request, workflow_id, progress_callback
            )
            
            # Phase 2: CAD Model Generation
            workflow_result["phases"]["cad"] = await self._execute_cad_phase(
                workflow_result["phases"]["research"], workflow_id, progress_callback
            )
            
            # Phase 3: Slicing and G-code Generation
            workflow_result["phases"]["slicer"] = await self._execute_slicer_phase(
                workflow_result["phases"]["cad"], workflow_id, progress_callback
            )
            
            # Phase 4: 3D Printing
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
            
            # Perform rollback and cleanup
            await self._perform_rollback_and_cleanup(workflow_result)
            workflow_result["cleanup_performed"] = True
            
            if show_progress:
                print(f"❌ Workflow failed: {e}")
                print("🧹 Performing cleanup...")
            
            raise
    
    async def _execute_research_phase(
        self, 
        user_request: str, 
        workflow_id: str,
        progress_callback
    ) -> Dict[str, Any]:
        """Execute the research and concept generation phase."""
        try:
            logger.info("🔍 Phase 1: Research and Concept Generation")
            
            input_data = {
                "user_request": user_request,
                "workflow_id": workflow_id,
                "metadata": {"phase": "research"}
            }
            
            result = await self.parent_agent.execute_research_workflow(
                input_data, progress_callback
            )
            
            if not result.success:
                raise WorkflowError(f"Research phase failed: {result.error_message}")
            
            logger.info("✅ Research phase completed")
            return {
                "success": True,
                "data": result.data,
                "design_specification": result.data.get("design_specification", {})
            }
            
        except Exception as e:
            logger.error(f"❌ Research phase failed: {e}")
            raise WorkflowError(f"Research phase failed: {str(e)}")
    
    async def _execute_cad_phase(
        self, 
        research_output: Dict[str, Any], 
        workflow_id: str,
        progress_callback
    ) -> Dict[str, Any]:
        """Execute the CAD model generation phase."""
        try:
            logger.info("🏗️ Phase 2: CAD Model Generation")
            
            input_data = {
                "research_output": research_output["data"],
                "workflow_id": workflow_id,
                "metadata": {"phase": "cad"}
            }
            
            result = await self.parent_agent.execute_cad_workflow(
                input_data, progress_callback
            )
            
            if not result.success:
                raise WorkflowError(f"CAD phase failed: {result.error_message}")
            
            # Track generated files for cleanup
            stl_file = result.data.get("stl_file")
            if stl_file:
                self.cleanup_tasks.append(("file", stl_file))
            
            logger.info("✅ CAD phase completed")
            return {
                "success": True,
                "data": result.data,
                "stl_file": stl_file
            }
            
        except Exception as e:
            logger.error(f"❌ CAD phase failed: {e}")
            raise WorkflowError(f"CAD phase failed: {str(e)}")
    
    async def _execute_slicer_phase(
        self, 
        cad_output: Dict[str, Any], 
        workflow_id: str,
        progress_callback
    ) -> Dict[str, Any]:
        """Execute the slicing and G-code generation phase."""
        try:
            logger.info("⚡ Phase 3: Slicing and G-code Generation")
            
            input_data = {
                "cad_output": cad_output["data"],
                "workflow_id": workflow_id,
                "metadata": {
                    "phase": "slicer",
                    "printer_profile": "ender3_pla",
                    "quality_level": "standard"
                }
            }
            
            result = await self.parent_agent.execute_slicer_workflow(
                input_data, progress_callback
            )
            
            if not result.success:
                raise WorkflowError(f"Slicer phase failed: {result.error_message}")
            
            # Track generated files for cleanup
            gcode_file = result.data.get("gcode_file")
            if gcode_file:
                self.cleanup_tasks.append(("file", gcode_file))
            
            logger.info("✅ Slicer phase completed")
            return {
                "success": True,
                "data": result.data,
                "gcode_file": gcode_file
            }
            
        except Exception as e:
            logger.error(f"❌ Slicer phase failed: {e}")
            raise WorkflowError(f"Slicer phase failed: {str(e)}")
    
    async def _execute_printer_phase(
        self, 
        slicer_output: Dict[str, Any], 
        workflow_id: str,
        progress_callback
    ) -> Dict[str, Any]:
        """Execute the 3D printing phase."""
        try:
            logger.info("🖨️ Phase 4: 3D Printing")
            
            input_data = {
                "slicing_output": slicer_output["data"],
                "workflow_id": workflow_id,
                "metadata": {"phase": "printer"}
            }
            
            result = await self.parent_agent.execute_printer_workflow(
                input_data, progress_callback
            )
            
            if not result.success:
                raise WorkflowError(f"Printer phase failed: {result.error_message}")
            
            logger.info("✅ Printer phase completed")
            return {
                "success": True,
                "data": result.data
            }
            
        except Exception as e:
            logger.error(f"❌ Printer phase failed: {e}")
            raise WorkflowError(f"Printer phase failed: {str(e)}")
    
    async def _perform_rollback_and_cleanup(self, workflow_result: Dict[str, Any]) -> None:
        """
        Perform rollback and cleanup operations.
        
        Cleanup includes:
        - Removing generated files (STL, G-code)
        - Stopping any active printing
        - Cleaning up temporary resources
        - Resetting agent states
        """
        try:
            logger.info("🧹 Performing rollback and cleanup...")
            
            # Stop any active printing
            if self.printer_agent:
                try:
                    # Emergency stop if printing
                    await self.printer_agent.execute_task({
                        "task_id": "emergency_stop",
                        "operation": "stop_print"
                    })
                    logger.info("🚨 Emergency stop executed")
                except Exception as e:
                    logger.warning(f"Could not execute emergency stop: {e}")
            
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
            # Don't raise here - cleanup failure shouldn't mask original error
    
    async def shutdown(self) -> None:
        """Shutdown the system gracefully."""
        try:
            logger.info("🔽 Shutting down AI Agent 3D Print System...")
            
            # Perform final cleanup
            await self._perform_rollback_and_cleanup({})
            
            # Shutdown agents
            if self.parent_agent:
                await self.parent_agent.shutdown()
            
            logger.info("✅ System shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}")


async def run_end_to_end_test() -> bool:
    """
    Run the end-to-end test: "Print a 2cm cube".
    
    This test validates the complete workflow implementation
    as required by Task 5.1.
    
    Returns:
        True if test passes, False otherwise
    """
    print("🧪 Running End-to-End Test: 'Print a 2cm cube'")
    print("=" * 60)
    
    orchestrator = WorkflowOrchestrator()
    
    try:
        # Initialize system
        await orchestrator.initialize()
        
        # Execute the test workflow
        result = await orchestrator.execute_complete_workflow(
            "Print a 2cm cube",
            show_progress=True
        )
        
        # Validate results
        if result["success"]:
            print("\n✅ End-to-End Test PASSED!")
            print(f"   - Workflow ID: {result['workflow_id']}")
            print(f"   - All phases completed successfully")
            print(f"   - Duration: {result.get('end_time', 'N/A')}")
            
            # Check that all phases executed
            phases = result.get("phases", {})
            required_phases = ["research", "cad", "slicer", "printer"]
            
            for phase in required_phases:
                if phase in phases and phases[phase].get("success"):
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
        logger.error(traceback.format_exc())
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


async def start_api_mode():
    """Start the API server mode."""
    print("🌐 Starting API Server Mode...")
    
    try:
        import uvicorn
        from api.main import app
        
        # Run the FastAPI server
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except ImportError:
        print("❌ FastAPI/uvicorn not available. Install with: pip install fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"❌ API server failed: {e}")
        logger.error(f"API server error: {e}")
        sys.exit(1)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Agent 3D Print System - Complete Workflow Implementation"
    )
    parser.add_argument(
        "request", 
        nargs="?", 
        help="Direct natural language request (e.g., 'Print a 2cm cube')"
    )
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Run end-to-end test"
    )
    parser.add_argument(
        "--api", 
        action="store_true", 
        help="Start API server"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.test:
            # Run end-to-end test
            success = await run_end_to_end_test()
            sys.exit(0 if success else 1)
        
        elif args.api:
            # Start API server
            await start_api_mode()
        
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
