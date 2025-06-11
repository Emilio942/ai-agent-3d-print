"""
Unit tests for Slicer Agent - CLI Wrapper with Profiles.

Tests cover:
- Slicer CLI wrapper functionality
- Profile management and configuration
- Mock slicing operations
- G-code analysis and metrics
- Error handling and edge cases
- Mocking of external slicer executables
"""

import pytest
import asyncio
import tempfile
import os
import json
import subprocess
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.slicer_agent import SlicerAgent
from core.api_schemas import SlicerAgentInput, SlicerAgentOutput, TaskResult
from core.exceptions import ValidationError, AI3DPrintError, SlicerExecutionError, SlicerProfileError


class TestSlicerAgent:
    """Test cases for Slicer Agent functionality."""
    
    @pytest.fixture
    def slicer_agent(self):
        """Create a Slicer Agent instance for testing."""
        config = {
            'mock_mode': True,
            'default_slicer': 'prusaslicer',
            'profiles_directory': tempfile.mkdtemp()
        }
        return SlicerAgent("test_slicer_agent", config=config)
    
    @pytest.fixture
    def sample_stl_file(self):
        """Create a sample STL file for testing."""
        stl_content = """solid test_cube
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 1 1 0
  endloop
endfacet
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 1 0
    vertex 0 1 0
  endloop
endfacet
endsolid test_cube"""
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False)
        temp_file.write(stl_content)
        temp_file.close()
        return temp_file.name
    
    @pytest.fixture
    def sample_input(self, sample_stl_file):
        """Sample input for testing."""
        return SlicerAgentInput(
            model_file_path=sample_stl_file,
            printer_profile="ender3_pla_standard",
            material_type="PLA",
            quality_preset="standard"
        )
    
    def test_agent_initialization(self, slicer_agent):
        """Test Slicer Agent initialization."""
        assert slicer_agent.agent_name == "test_slicer_agent"
        assert slicer_agent.agent_type == "SlicerAgent"
        assert slicer_agent.mock_mode is True
        assert hasattr(slicer_agent, 'slicer_engine')
        assert hasattr(slicer_agent, 'profiles')
    
    def test_mock_mode_toggle(self, slicer_agent):
        """Test mock mode toggle functionality."""
        original_mode = slicer_agent.mock_mode
        
        slicer_agent.set_mock_mode(False)
        assert slicer_agent.mock_mode is False
        
        slicer_agent.set_mock_mode(True)
        assert slicer_agent.mock_mode is True
        
        # Restore original mode
        slicer_agent.set_mock_mode(original_mode)
    
    def test_profile_loading(self, slicer_agent):
        """Test loading of slicer profiles."""
        profiles = slicer_agent.list_profiles()
        
        assert isinstance(profiles, dict)
        assert len(profiles) > 0
        
        # Check for expected profiles
        expected_profiles = [
            "ender3_pla_standard",
            "prusa_mk3s_petg_standard",
            "ender3_abs_standard"
        ]
        
        for profile in expected_profiles:
            assert profile in profiles
    
    def test_profile_validation(self, slicer_agent):
        """Test profile validation."""
        # Valid profile
        assert slicer_agent._validate_profile("ender3_pla_standard") is True
        
        # Invalid profile
        assert slicer_agent._validate_profile("nonexistent_profile") is False
        
        # None profile
        with pytest.raises(ValidationError):
            slicer_agent._validate_profile(None)
    
    def test_quality_preset_validation(self, slicer_agent):
        """Test quality preset validation."""
        valid_presets = ["draft", "standard", "fine", "ultra"]
        
        for preset in valid_presets:
            assert slicer_agent._validate_quality_preset(preset) is True
        
        # Invalid preset
        assert slicer_agent._validate_quality_preset("invalid") is False
    
    @pytest.mark.asyncio
    async def test_mock_slicing_operation(self, slicer_agent, sample_stl_file):
        """Test mock slicing operation."""
        result = await slicer_agent.slice_stl(
            stl_path=sample_stl_file,
            profile_name="ender3_pla_standard",
            quality_preset="standard"
        )
        
        assert isinstance(result, dict)
        assert "gcode_file_path" in result
        assert "estimated_print_time" in result
        assert "material_usage" in result
        assert "layer_count" in result
        assert "slicing_time" in result
        
        # Verify G-code file was created
        assert os.path.exists(result["gcode_file_path"])
        
        # Verify G-code content
        with open(result["gcode_file_path"], 'r') as f:
            gcode_content = f.read()
        
        assert "G21" in gcode_content  # Units to millimeters
        assert "G90" in gcode_content  # Absolute positioning
        assert "M104" in gcode_content  # Set hotend temperature
        assert "M140" in gcode_content  # Set bed temperature
    
    @pytest.mark.asyncio
    async def test_mock_slicing_different_presets(self, slicer_agent, sample_stl_file):
        """Test mock slicing with different quality presets."""
        presets = ["draft", "standard", "fine", "ultra"]
        
        for preset in presets:
            result = await slicer_agent.slice_stl(
                stl_path=sample_stl_file,
                profile_name="ender3_pla_standard",
                quality_preset=preset
            )
            
            assert isinstance(result, dict)
            assert result["estimated_print_time"] > 0
            assert result["layer_count"] > 0
            
            # Different presets should give different results
            if preset == "draft":
                assert result["layer_count"] <= 50  # Fewer layers for draft
            elif preset == "ultra":
                assert result["layer_count"] >= 100  # More layers for ultra
    
    def test_gcode_analysis(self, slicer_agent):
        """Test G-code analysis functionality."""
        gcode_content = """
; Start G-code
G21 ; set units to millimeters
G90 ; use absolute coordinates
M104 S200 ; set hotend temperature
M140 S60 ; set bed temperature
G28 ; home all axes

; Layer 1
G1 Z0.2 F3000
G1 X50 Y50 E1 F1500
G1 X100 Y50 E2 F1500

; Layer 2
G1 Z0.4 F3000
G1 X50 Y50 E3 F1500
G1 X100 Y50 E4 F1500

; End G-code
M104 S0 ; turn off hotend
M140 S0 ; turn off bed
"""
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.gcode', delete=False)
        temp_file.write(gcode_content)
        temp_file.close()
        
        try:
            analysis = slicer_agent._analyze_gcode_file(temp_file.name)
        
            assert isinstance(analysis, dict)
            assert "layer_count" in analysis
            assert "total_movements" in analysis
            assert "material_usage" in analysis
            assert "hotend_temperature" in analysis
            assert "bed_temperature" in analysis
            
            assert analysis["layer_count"] == 2
            assert analysis["hotend_temperature"] == 200
            assert analysis["bed_temperature"] == 60
            
        finally:
            os.unlink(temp_file.name)
    
    def test_gcode_analysis_invalid_file(self, slicer_agent):
        """Test G-code analysis with invalid file."""
        # Should return a safe result instead of raising exception
        result = slicer_agent._analyze_gcode_file("nonexistent_file.gcode")
        assert isinstance(result, dict)
        assert result.get("layer_count", 0) == 0
    
    def test_profile_customization(self, slicer_agent):
        """Test profile customization."""
        base_profile = "ender3_pla_standard"
        custom_settings = {
            "layer_height": 0.1,
            "infill_percentage": 30,
            "print_speed": 40
        }
        
        customized_profile = slicer_agent._customize_profile(base_profile, custom_settings)
        
        assert isinstance(customized_profile, dict)
        assert customized_profile["layer_height"] == 0.1
        assert customized_profile["infill_percentage"] == 30
        assert customized_profile["print_speed"] == 40
    
    def test_slicer_executable_detection(self, slicer_agent):
        """Test slicer executable detection."""
        # In mock mode, should always return available
        assert slicer_agent._is_slicer_available() is True
        
        # Test executable paths
        paths = slicer_agent.slicer_paths
        assert isinstance(paths, dict)
        assert len(paths) > 0
    
    @patch('subprocess.run')
    def test_cli_command_building(self, mock_subprocess, slicer_agent):
        """Test CLI command building."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        
        # Temporarily disable mock mode to test real CLI building
        slicer_agent.set_mock_mode(False)
        
        try:
            settings = {
                "input_file": "test.stl",
                "output_file": "test.gcode",
                "profile": "ender3_pla_standard"
            }
            
            # This should build a command but not execute it due to subprocess mock
            command = slicer_agent._build_prusaslicer_command(settings)
            
            assert isinstance(command, list)
            assert len(command) > 0
            assert any("--export-gcode" in str(cmd) for cmd in command)
            
        finally:
            slicer_agent.set_mock_mode(True)
    
    @pytest.mark.asyncio
    async def test_execute_task_success(self, slicer_agent, sample_input):
        """Test successful task execution."""
        task_data = {
            "task_id": "test_001",
            "model_file_path": sample_input.model_file_path,
            "printer_profile": sample_input.printer_profile,
            "material_type": sample_input.material_type,
            "quality_preset": sample_input.quality_preset,
            "infill_percentage": sample_input.infill_percentage,
            "layer_height": sample_input.layer_height,
            "print_speed": sample_input.print_speed
        }
        
        result = await slicer_agent.execute_task(task_data)
        
        assert isinstance(result, TaskResult)
        assert result.success is True
        assert isinstance(result.data, dict)
        
        # Check output structure
        output_data = result.data
        assert "gcode_file_path" in output_data
        assert "estimated_print_time" in output_data
        assert "material_usage" in output_data
    
    @pytest.mark.asyncio
    async def test_execute_task_validation_error(self, slicer_agent):
        """Test task execution with validation errors."""
        # Missing required fields
        task_data = {
            "task_id": "test_002"
            # Missing model_file_path
        }
        
        result = await slicer_agent.execute_task(task_data)
        
        # Should handle error gracefully
        assert isinstance(result, TaskResult)
        assert result.success is False
        assert "validation" in result.error_message.lower() or "required" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_task_invalid_profile(self, slicer_agent, sample_stl_file):
        """Test task execution with invalid profile."""
        task_data = {
            "task_id": "test_003",
            "model_file_path": sample_stl_file,
            "printer_profile": "nonexistent_profile",
            "material_type": "PLA",
            "quality_preset": "standard"
        }
        
        result = await slicer_agent.execute_task(task_data)
        
        # Should handle error gracefully
        assert isinstance(result, TaskResult)
        assert result.success is False
        assert "profile" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_task_missing_file(self, slicer_agent):
        """Test task execution with missing STL file."""
        task_data = {
            "task_id": "test_004",
            "model_file_path": "nonexistent_file.stl",
            "printer_profile": "ender3_pla_standard",
            "material_type": "PLA",
            "quality_preset": "standard"
        }
        
        result = await slicer_agent.execute_task(task_data)
        
        assert isinstance(result, TaskResult)
        assert result.success is False
        assert "file" in result.error_message.lower()
    
    def test_material_settings_mapping(self, slicer_agent):
        """Test material settings mapping."""
        materials = ["PLA", "PETG", "ABS", "TPU"]
        
        for material in materials:
            settings = slicer_agent._get_material_settings(material)
            
            assert isinstance(settings, dict)
            assert "hotend_temperature" in settings
            assert "bed_temperature" in settings
            assert "retraction_distance" in settings
            
            # Verify temperature ranges make sense
            assert 150 <= settings["hotend_temperature"] <= 300
            assert 0 <= settings["bed_temperature"] <= 120
    
    def test_printer_settings_mapping(self, slicer_agent):
        """Test printer settings mapping."""
        printers = ["ender3", "prusa_mk3s", "cr10"]
        
        for printer in printers:
            settings = slicer_agent._get_printer_settings(printer)
            
            assert isinstance(settings, dict)
            assert "build_volume" in settings
            assert "nozzle_diameter" in settings
            assert "max_print_speed" in settings
            
            # Verify build volume is reasonable
            build_volume = settings["build_volume"]
            assert len(build_volume) == 3
            assert all(v > 0 for v in build_volume)
    
    def test_quality_settings_mapping(self, slicer_agent):
        """Test quality settings mapping."""
        quality_levels = ["draft", "standard", "fine", "ultra"]
        
        for quality in quality_levels:
            settings = slicer_agent._get_quality_settings(quality)
            
            assert isinstance(settings, dict)
            assert "layer_height" in settings
            assert "infill_percentage" in settings
            assert "perimeters" in settings
            
            # Layer height should decrease with quality
            layer_height = settings["layer_height"]
            if quality == "draft":
                assert layer_height >= 0.3
            elif quality == "ultra":
                assert layer_height <= 0.1
    
    def test_estimate_print_time(self, slicer_agent):
        """Test print time estimation."""
        gcode_metrics = {
            "layer_count": 100,
            "total_movements": 5000,
            "estimated_filament": 10.5
        }
        
        print_time = slicer_agent._estimate_print_time(gcode_metrics)
        
        assert isinstance(print_time, (int, float))
        assert print_time > 0
        assert print_time < 1000  # Should be reasonable (< 1000 minutes)
    
    def test_estimate_material_usage(self, slicer_agent):
        """Test material usage estimation."""
        gcode_metrics = {
            "layer_count": 50,
            "total_movements": 2500,
            "build_volume": [220, 220, 250]
        }
        
        material_usage = slicer_agent._estimate_material_usage(gcode_metrics)
        
        assert isinstance(material_usage, (int, float))
        assert material_usage > 0
        assert material_usage < 1000  # Should be reasonable (< 1000g)
    
    def test_error_handling_invalid_stl(self, slicer_agent):
        """Test error handling with invalid STL file."""
        invalid_stl = tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False)
        invalid_stl.write("invalid stl content")
        invalid_stl.close()
        
        try:
            error_result = slicer_agent.handle_error(
                AI3DPrintError("Invalid STL file"),
                {"stl_file": invalid_stl.name}
            )
            
            assert isinstance(error_result, dict)
            assert error_result["error"] is True
            assert "error_code" in error_result
            
        finally:
            os.unlink(invalid_stl.name)
    
    def test_supported_file_formats(self, slicer_agent):
        """Test supported file format validation."""
        supported_formats = [".stl", ".obj", ".3mf", ".amf"]
        
        for fmt in supported_formats:
            test_file = f"test{fmt}"
            assert slicer_agent._is_supported_format(test_file) is True
        
        # Unsupported format
        assert slicer_agent._is_supported_format("test.txt") is False
    
    def test_concurrent_slicing_requests(self, slicer_agent, sample_stl_file):
        """Test handling of concurrent slicing requests."""
        async def slice_task(task_id):
            return await slicer_agent.slice_stl(
                stl_path=sample_stl_file,
                profile_name="ender3_pla_standard",
                quality_preset="standard"
            )
        
        async def run_concurrent_test():
            tasks = [slice_task(f"task_{i}") for i in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            assert len(results) == 3
            for result in results:
                assert isinstance(result, dict)
                assert "gcode_file_path" in result
        
        asyncio.run(run_concurrent_test())
    
    def test_profile_inheritance(self, slicer_agent):
        """Test profile inheritance and override."""
        base_profile = slicer_agent.profiles["ender3_pla_standard"]
        custom_settings = {
            "layer_height": 0.1,  # Override
            "new_setting": "custom"  # Add new
        }
        
        merged_profile = slicer_agent._merge_profile_settings(base_profile, custom_settings)
        
        assert merged_profile["layer_height"] == 0.1  # Overridden
        assert merged_profile["new_setting"] == "custom"  # Added
        assert "printer" in merged_profile  # Inherited from base
    
    def test_gcode_postprocessing(self, slicer_agent):
        """Test G-code post-processing."""
        gcode_content = """
G1 X10 Y10 E1 F1500
G1 X20 Y10 E2 F1500
G1 X20 Y20 E3 F1500
"""
        
        processed = slicer_agent._postprocess_gcode(gcode_content)
        
        assert isinstance(processed, str)
        assert len(processed) > 0
    
    def test_agent_status_tracking(self, slicer_agent):
        """Test agent status tracking."""
        status = slicer_agent.get_status()
        
        assert isinstance(status, dict)
        assert "agent_name" in status
        assert "agent_type" in status
        assert "current_status" in status
        assert status["agent_name"] == "test_slicer_agent"
        assert status["agent_type"] == "SlicerAgent"
    
    def test_cleanup(self, slicer_agent):
        """Test agent cleanup."""
        slicer_agent.cleanup()
        
        # Verify cleanup completed without errors
        status = slicer_agent.get_status()
        assert isinstance(status, dict)


class TestSlicerAgentIntegration:
    """Integration tests for Slicer Agent."""
    
    @pytest.fixture
    def slicer_agent(self):
        """Create a Slicer Agent instance for integration testing."""
        config = {'mock_mode': True}
        return SlicerAgent("integration_test_agent", config=config)
    
    @pytest.fixture
    def sample_stl_file(self):
        """Create a sample STL file for integration testing."""
        stl_content = """solid test_cube
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 1 1 0
  endloop
endfacet
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 1 0
    vertex 0 1 0
  endloop
endfacet
endsolid test_cube"""
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False)
        temp_file.write(stl_content)
        temp_file.close()
        return temp_file.name
    
    @pytest.mark.asyncio
    async def test_full_slicing_workflow(self, slicer_agent, sample_stl_file):
        """Test full slicing workflow from STL to G-code."""
        task_data = {
            "task_id": "integration_slice",
            "model_file_path": sample_stl_file,
            "printer_profile": "ender3_pla_standard",
            "material_type": "PLA",
            "quality_preset": "fine",
            "infill_percentage": 25,
            "print_speed": 50
        }
        
        result = await slicer_agent.execute_task(task_data)
        
        assert result.success is True
        assert os.path.exists(result.data["gcode_file_path"])
        assert result.data["estimated_print_time"] > 0
        assert result.data["material_usage"] > 0
        
        # Verify G-code quality
        with open(result.data["gcode_file_path"], 'r') as f:
            gcode = f.read()
        
        assert "; Layer" in gcode  # Should have layer comments
        assert "G1" in gcode  # Should have movement commands
        assert "E" in gcode  # Should have extrusion
    
    @pytest.mark.asyncio
    async def test_profile_variation_workflow(self, slicer_agent, sample_stl_file):
        """Test workflow with different profiles."""
        profiles = ["ender3_pla_standard", "prusa_mk3s_petg_standard"]
        
        for profile in profiles:
            task_data = {
                "task_id": f"profile_test_{profile}",
                "model_file_path": sample_stl_file,
                "printer_profile": profile,
                "material_type": "PLA",
                "quality_preset": "standard"
            }
            
            result = await slicer_agent.execute_task(task_data)
            
            assert result.success is True
            assert result.data["profile_used"] == profile


if __name__ == "__main__":
    # Cleanup any temp files from fixtures
    def cleanup_temp_files():
        import tempfile
        import glob
        temp_dir = tempfile.gettempdir()
        for pattern in ["test_*.stl", "test_*.gcode"]:
            for file in glob.glob(os.path.join(temp_dir, pattern)):
                try:
                    os.unlink(file)
                except:
                    pass
    
    try:
        pytest.main([__file__, "-v"])
    finally:
        cleanup_temp_files()
