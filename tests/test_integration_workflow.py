#!/usr/bin/env python3
"""
Comprehensive Integration Tests for AI Agent 3D Print System

This module tests the complete end-to-end workflow from user request
to final print job execution, validating all agent interactions.
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add core directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))

from core.api_schemas import TaskResult
from agents.research_agent import ResearchAgent  
from agents.cad_agent import CADAgent
from agents.slicer_agent import SlicerAgent
from agents.printer_agent import PrinterAgent


class TestIntegrationWorkflow:
    """Integration tests for complete workflow."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def research_agent(self):
        """Create research agent for testing."""
        return ResearchAgent("integration_research_agent")
    
    @pytest.fixture
    def cad_agent(self):
        """Create CAD agent for testing."""
        return CADAgent("integration_cad_agent")
    
    @pytest.fixture
    def slicer_agent(self):
        """Create slicer agent for testing."""
        config = {"mock_mode": True}
        return SlicerAgent("integration_slicer_agent", config)
    
    @pytest.fixture
    def printer_agent(self):
        """Create printer agent for testing."""
        config = {"mock_mode": True}
        return PrinterAgent("integration_printer_agent", config)
    
    @pytest.mark.asyncio
    async def test_research_to_cad_workflow(self, research_agent, cad_agent, temp_dir):
        """Test research agent → CAD agent workflow."""
        # Step 1: Research phase
        research_task = {
            "task_id": "research_001",
            "user_request": "Create a simple cube with 2cm sides",
            "analysis_depth": "standard"
        }
        
        research_result = research_agent.execute_task(research_task)
        
        assert research_result.success is True
        assert "object_specifications" in research_result.data
        
        # Step 2: CAD phase using research output
        cad_task = {
            "task_id": "cad_001", 
            "operation": "create_primitive",
            "specifications": {
                "geometry": {
                    "base_shape": "cube",
                    "dimensions": {"x": 2.0, "y": 2.0, "z": 2.0}
                }
            },
            "requirements": {},
            "format_preference": "stl",
            "quality_level": "standard"
        }
        
        cad_result = await cad_agent.execute_task(cad_task)

        assert cad_result.success is True
        assert "model_file_path" in cad_result.data

        print("✅ Research → CAD workflow successful")
    
    @pytest.mark.asyncio
    async def test_cad_to_slicer_workflow(self, cad_agent, slicer_agent, temp_dir):
        """Test CAD agent → Slicer agent workflow."""
        # Step 1: Create a model with CAD
        cad_task = {
            "task_id": "cad_002",
            "operation": "create_primitive",
            "specifications": {
                "geometry": {
                    "base_shape": "cube",
                    "dimensions": {"x": 2.0, "y": 2.0, "z": 2.0}
                }
            },
            "requirements": {},
            "format_preference": "stl",
            "quality_level": "standard"
        }
        
        cad_result = await cad_agent.execute_task(cad_task)
        assert cad_result.success is True
        
        # Step 2: Export to STL
        stl_file = os.path.join(temp_dir, "test_cube.stl")
        export_task = {
            "task_id": "export_002",
            "operation": "export_stl",
            "specifications": {
                "stl_export": {
                    "source_file_path": cad_result.data["model_file_path"],
                    "output_file_path": stl_file,
                    "quality_level": "standard"
                }
            },
            "requirements": {},
            "format_preference": "stl",
            "quality_level": "standard"
        }
        
        export_result = await cad_agent.execute_task(export_task)
        assert export_result.success is True
        assert os.path.exists(export_result.data.get("output_file_path", stl_file))
        print("✅ STL export completed")

        # Step 3: Slice the STL
        slicer_task = {
            "task_id": "slicer_002",
            "model_file_path": export_result.data.get("output_file_path", stl_file),
            "printer_profile": "ender3_pla_standard",
            "material_type": "PLA",
            "quality_preset": "standard"
        }
        
        slicer_result = await slicer_agent.execute_task(slicer_task)
        assert slicer_result.success is True
        assert "gcode_file_path" in slicer_result.data
        
        print("✅ CAD → Slicer workflow successful")
    
    @pytest.mark.asyncio
    async def test_slicer_to_printer_workflow(self, slicer_agent, printer_agent, temp_dir):
        """Test Slicer agent → Printer agent workflow."""
        # Step 1: Create mock G-code file
        gcode_file = os.path.join(temp_dir, "test.gcode")
        with open(gcode_file, 'w') as f:
            f.write("""
; Test G-code
G21 ; set units to millimeters
G90 ; use absolute coordinates
M104 S200 ; set hotend temperature
M140 S60 ; set bed temperature
G28 ; home all axes
G1 Z0.2 F3000
G1 X10 Y10 E5 F1500
M104 S0 ; turn off hotend
M140 S0 ; turn off bed
""")
        
        # Mock the slicer result
        slicer_result = TaskResult(
            success=True,
            data={"gcode_file_path": gcode_file},
            metadata={"task_id": "slicer_003"}
        )
        
        # Step 2: Send to printer
        printer_task = {
            "task_id": "printer_003",
            "operation": "start_print",
            "gcode_file_path": slicer_result.data["gcode_file_path"]
        }
        
        printer_result = await printer_agent.execute_task(printer_task)
        assert printer_result.success is True
        
        print("✅ Slicer → Printer workflow successful")
    
    @pytest.mark.asyncio
    async def test_complete_end_to_end_workflow(self, research_agent, cad_agent, slicer_agent, printer_agent, temp_dir):
        """Test complete end-to-end workflow from user request to print."""
        print("\n🚀 Starting Complete End-to-End Workflow Test")
        print("=" * 60)
        
        # Phase 1: Research
        print("📋 Phase 1: Research & Requirements Analysis")
        research_task = {
            "task_id": "e2e_research",
            "user_request": "Create a simple cube with 2cm sides for testing",
            "analysis_depth": "standard"
        }
        
        research_result = research_agent.execute_task(research_task)
        assert research_result.success is True
        print("✅ Research phase completed")
        
        # Phase 2: CAD Model Generation
        print("🔧 Phase 2: 3D Model Generation")
        cad_task = {
            "task_id": "e2e_cad",
            "operation": "create_primitive",
            "specifications": {
                "geometry": {
                    "base_shape": "cube",
                    "dimensions": {"x": 2.0, "y": 2.0, "z": 2.0}
                }
            },
            "requirements": {},
            "format_preference": "stl",
            "quality_level": "standard"
        }
        
        cad_result = await cad_agent.execute_task(cad_task)
        assert cad_result.success is True
        print("✅ CAD generation completed")
        
        # Phase 3: STL Export
        print("📦 Phase 3: STL Export")
        stl_file = os.path.join(temp_dir, "e2e_cube.stl")
        export_task = {
            "task_id": "e2e_export",
            "operation": "export_stl",
            "specifications": {
                "stl_export": {
                    "source_file_path": cad_result.data["model_file_path"],
                    "output_file_path": stl_file,
                    "quality_level": "standard"
                }
            },
            "requirements": {},
            "format_preference": "stl",
            "quality_level": "standard"
        }
        
        export_result = await cad_agent.execute_task(export_task)
        assert export_result.success is True
        assert os.path.exists(export_result.data.get("output_file_path", stl_file))
        print("✅ STL export completed")        # Phase 4: G-code Generation
        print("⚙️ Phase 4: G-code Generation")
        slicer_task = {
            "task_id": "e2e_slicer",
            "model_file_path": export_result.data.get("output_file_path", stl_file),
            "printer_profile": "ender3_pla_standard",
            "material_type": "PLA",
            "quality_preset": "standard"
        }
        
        slicer_result = await slicer_agent.execute_task(slicer_task)
        assert slicer_result.success is True
        print("✅ G-code generation completed")
        
        # Phase 5: Print Job
        print("🖨️ Phase 5: Print Job Execution")
        printer_task = {
            "task_id": "e2e_printer",
            "operation": "start_print",
            "gcode_file_path": slicer_result.data["gcode_file_path"]
        }
        
        printer_result = await printer_agent.execute_task(printer_task)
        assert printer_result.success is True
        print("✅ Print job started successfully")
        
        print("\n🎉 Complete End-to-End Workflow Test PASSED!")
        print("✅ All phases executed successfully")
        print("✅ Data flow between agents working correctly")
        
    def test_agent_error_recovery(self, research_agent):
        """Test error recovery mechanisms across agents."""
        # Test with invalid input
        invalid_task = {
            "task_id": "error_test",
            "user_request": "",  # Empty request should fail gracefully
            "analysis_depth": "invalid_depth"
        }
        
        result = research_agent.execute_task(invalid_task)
        
        # Should handle error gracefully without crashing
        assert isinstance(result, TaskResult)
        # May succeed or fail, but should not raise exception
        
        print("✅ Error recovery test passed")
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_operations(self, cad_agent):
        """Test concurrent operations on agents."""
        # Create multiple tasks concurrently
        tasks = []
        for i in range(3):
            task = {
                "task_id": f"concurrent_{i}",
                "operation": "create_primitive",
                "primitive_type": "sphere",
                "dimensions": {"radius": 1.0 + i * 0.5}
            }
            tasks.append(cad_agent.execute_task(task))
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, TaskResult)
        
        print("✅ Concurrent operations test passed")


class TestDataFlowValidation:
    """Test data flow and schema validation between agents."""
    
    def test_research_output_schema(self):
        """Test that research agent output matches expected schema."""
        agent = ResearchAgent("schema_test_research")
        
        task = {
            "task_id": "schema_test",
            "user_request": "Create a gear with 24 teeth",
            "analysis_depth": "standard"
        }
        
        result = agent.execute_task(task)
        
        # Validate structure
        assert isinstance(result, TaskResult)
        assert result.success is True
        assert "object_specifications" in result.data
        
        specs = result.data["object_specifications"]
        assert isinstance(specs, dict)
        
        print("✅ Research agent output schema valid")
    
    @pytest.mark.asyncio
    async def test_cad_input_validation(self):
        """Test CAD agent input validation."""
        agent = CADAgent("schema_test_cad")
        
        # Test valid input
        valid_task = {
            "task_id": "valid_test",
            "operation": "create_primitive",
            "specifications": {
                "geometry": {
                    "base_shape": "cube",
                    "dimensions": {"x": 2.0, "y": 2.0, "z": 2.0}
                }
            },
            "requirements": {},
            "format_preference": "stl",
            "quality_level": "standard"
        }
        
        result = await agent.execute_task(valid_task)
        assert result.success is True
        
        # Test invalid input
        invalid_task = {
            "task_id": "invalid_test", 
            "operation": "create_primitive",
            "specifications": {
                "geometry": {
                    "base_shape": "invalid_type",
                    "dimensions": {"x": -1.0}
                }
            },
            "requirements": {},
            "format_preference": "stl",
            "quality_level": "standard"
        }
        
        result = await agent.execute_task(invalid_task)
        assert result.success is False
        
        print("✅ CAD agent input validation working")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])
