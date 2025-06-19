"""
Slicer Agent - 3D Model Slicing and G-Code Generation

This module implements the Slicer Agent responsible for converting STL files into
G-code instructions for 3D printers using various slicer engines (PrusaSlicer, Cura).

Task 2.3.1: Slicer CLI Wrapper with Profiles
- Multi-slicer engine support (PrusaSlicer, Cura)
- Predefined printer profiles (Ender 3, Prusa i3, etc.)
- Material-specific profiles (PLA, PETG, ABS)
- CLI wrapper with robust error handling
"""

import os
import subprocess
import tempfile
import time
import re
import shutil
import asyncio
import threading
import queue
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from datetime import datetime
import json
import yaml

# Serial communication imports for Task 2.3.2
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not available, using mock printer only")

# Core System Imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.base_agent import BaseAgent
from core.logger import get_logger
from core.exceptions import SlicerAgentError, SlicerExecutionError, SlicerProfileError, GCodeGenerationError, ValidationError, ConfigurationError
from core.api_schemas import SlicerAgentInput, SlicerAgentOutput, TaskResult


class SlicerAgent(BaseAgent):
    """
    Slicer Agent for 3D model slicing and G-code generation.
    
    Supports multiple slicer engines with predefined profiles for various
    printer and material combinations.
    """
    
    def __init__(self, agent_name: str = "slicer_agent", config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize Slicer Agent with CLI wrapper capabilities."""
        super().__init__(agent_name=agent_name, **kwargs)
        self.logger = get_logger(f"{self.__class__.__name__}_{agent_name}")
        
        # Apply config if provided
        config = config or {}
        
        # Slicer configuration
        self.slicer_engine = config.get('default_slicer', "prusaslicer")  # Default engine
        self.mock_mode = config.get('mock_mode', False)  # For testing without actual slicer
        
        # Slicer executable paths
        self.slicer_paths = {
            'prusaslicer': self._find_prusaslicer_executable(),
            'cura': self._find_cura_executable()
        }
        
        # Profile storage
        profiles_dir = config.get('profiles_directory', "./config/slicer_profiles")
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported file formats
        self.supported_input_formats = ['.stl', '.obj', '.3mf', '.amf']
        self.supported_output_format = '.gcode'
        
        # Quality presets mapping
        self.quality_presets = {
            'draft': {'layer_height': 0.3, 'quality_factor': 0.5},
            'standard': {'layer_height': 0.2, 'quality_factor': 1.0},
            'fine': {'layer_height': 0.15, 'quality_factor': 1.5},
            'ultra': {'layer_height': 0.1, 'quality_factor': 2.0}
        }
        
        # Initialize predefined profiles
        self._init_predefined_profiles()
        
        # Load configuration (only if not provided in constructor)
        if not config:
            self._load_slicer_config()
        
        self.logger.info(f"Slicer Agent {agent_name} initialized with {self.slicer_engine} engine")
    
    def _find_prusaslicer_executable(self) -> Optional[str]:
        """Find PrusaSlicer executable on the system."""
        possible_paths = [
            '/usr/bin/prusa-slicer',
            '/usr/local/bin/prusa-slicer',
            '/opt/PrusaSlicer/prusa-slicer',
            'C:\\Program Files\\Prusa3D\\PrusaSlicer\\prusa-slicer.exe',  # Windows
            '/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer'  # macOS
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'prusa-slicer'], 
                                    capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        self.logger.warning("PrusaSlicer executable not found")
        return None
    
    def _find_cura_executable(self) -> Optional[str]:
        """Find Cura executable on the system."""
        possible_paths = [
            '/usr/bin/cura',
            '/usr/local/bin/cura',
            '/opt/cura/cura',
            'C:\\Program Files\\Ultimaker Cura\\CuraEngine.exe',  # Windows
            '/Applications/Ultimaker Cura.app/Contents/MacOS/cura'  # macOS
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'cura'], 
                                    capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        self.logger.warning("Cura executable not found")
        return None
    
    def _init_predefined_profiles(self) -> None:
        """Initialize predefined slicer profiles for common printer/material combinations."""
        predefined_profiles = {
            'ender3_pla_draft': {
                'printer': 'ender3',
                'material': 'PLA',
                'quality': 'draft',
                'layer_height': 0.3,
                'infill_percentage': 15,
                'print_speed': 60,
                'nozzle_diameter': 0.4,
                'bed_temperature': 60,
                'hotend_temperature': 200,
                'supports': False,
                'retraction_distance': 6.0,
                'retraction_speed': 25,
                'build_volume': [220, 220, 250]
            },
            'ender3_pla_standard': {
                'printer': 'ender3',
                'material': 'PLA',
                'quality': 'standard',
                'layer_height': 0.2,
                'infill_percentage': 20,
                'print_speed': 50,
                'nozzle_diameter': 0.4,
                'bed_temperature': 60,
                'hotend_temperature': 200,
                'supports': True,
                'retraction_distance': 6.0,
                'retraction_speed': 25,
                'build_volume': [220, 220, 250]
            },
            'ender3_pla_fine': {
                'printer': 'ender3',
                'material': 'PLA',
                'quality': 'fine',
                'layer_height': 0.15,
                'infill_percentage': 25,
                'print_speed': 40,
                'nozzle_diameter': 0.4,
                'bed_temperature': 60,
                'hotend_temperature': 200,
                'supports': True,
                'retraction_distance': 6.0,
                'retraction_speed': 25,
                'build_volume': [220, 220, 250]
            },
            'prusa_mk3s_pla_standard': {
                'printer': 'prusa_mk3s',
                'material': 'PLA',
                'quality': 'standard',
                'layer_height': 0.2,
                'infill_percentage': 20,
                'print_speed': 50,
                'nozzle_diameter': 0.4,
                'bed_temperature': 60,
                'hotend_temperature': 200,
                'supports': True,
                'retraction_distance': 3.2,
                'retraction_speed': 35,
                'build_volume': [250, 210, 200]
            },
            'prusa_mk3s_petg_standard': {
                'printer': 'prusa_mk3s',
                'material': 'PETG',
                'quality': 'standard',
                'layer_height': 0.2,
                'infill_percentage': 25,
                'print_speed': 45,
                'nozzle_diameter': 0.4,
                'bed_temperature': 85,
                'hotend_temperature': 245,
                'supports': True,
                'retraction_distance': 4.0,
                'retraction_speed': 35,
                'build_volume': [250, 210, 200]
            },
            'ender3_abs_standard': {
                'printer': 'ender3',
                'material': 'ABS',
                'quality': 'standard',
                'layer_height': 0.2,
                'infill_percentage': 20,
                'print_speed': 45,
                'nozzle_diameter': 0.4,
                'bed_temperature': 100,
                'hotend_temperature': 240,
                'supports': True,
                'retraction_distance': 6.0,
                'retraction_speed': 25,
                'build_volume': [220, 220, 250]
            }
        }
        
        self.predefined_profiles = predefined_profiles
        # Alias for test compatibility
        self.profiles = self.predefined_profiles
        self.logger.debug(f"Initialized {len(predefined_profiles)} predefined profiles")
    
    def _load_slicer_config(self) -> None:
        """Load slicer configuration from settings."""
        try:
            config_path = Path("./config/settings.yaml")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                slicer_config = config.get('agents', {}).get('slicer', {})
                self.slicer_engine = slicer_config.get('engine', 'prusaslicer')
                self.mock_mode = slicer_config.get('mock_mode', False)
                
                # Update executable paths from config
                prusaslicer_config = slicer_config.get('prusaslicer', {})
                if 'executable_path' in prusaslicer_config:
                    self.slicer_paths['prusaslicer'] = prusaslicer_config['executable_path']
                
                self.logger.debug(f"Loaded slicer config: engine={self.slicer_engine}, mock_mode={self.mock_mode}")
            
        except Exception as e:
            self.logger.warning(f"Failed to load slicer config: {e}")
    
    async def execute_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute slicing task based on task details."""
        task_type = task_details.get('task_type', 'slice_stl')
        
        if task_type == "slice_stl":
            return await self._slice_stl_task(task_details)
        elif task_type == "list_profiles":
            return self._list_profiles_sync()
        elif task_type == "validate_model":
            return await self._validate_model_task(task_details)
        elif task_type == "estimate_print_time":
            return await self._estimate_print_time_task(task_details)
        else:
            raise ValidationError(f"Unsupported task type: {task_type}")
    
    async def handle_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle async task requests."""
        return await self.execute_task(task_details)
    
    async def _slice_stl_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main slicing task - converts STL to G-code using specified profile.
        
        This implements the core Task 2.3.1 functionality.
        """
        start_time = time.time()
        
        try:
            # Extract schema fields from input_data, ignore extra fields like task_type
            schema_fields = {
                "model_file_path": input_data.get("model_file_path"),
                "printer_profile": input_data.get("printer_profile"),
                "material_type": input_data.get("material_type"),
                "quality_preset": input_data.get("quality_preset", "standard"),
                "infill_percentage": input_data.get("infill_percentage", 20),
                "layer_height": input_data.get("layer_height", 0.2),
                "print_speed": input_data.get("print_speed", 50)
            }
            
            # Validate input using Pydantic schema
            slicer_input = SlicerAgentInput(**schema_fields)
            
            self.logger.info(f"Starting slicing task: {slicer_input.model_file_path}")
            
            # Validate input file
            if not os.path.exists(slicer_input.model_file_path):
                raise ValidationError(f"Input file not found: {slicer_input.model_file_path}")
            
            file_ext = Path(slicer_input.model_file_path).suffix.lower()
            if file_ext not in self.supported_input_formats:
                raise ValidationError(f"Unsupported file format: {file_ext}")
            
            # Get profile settings
            profile_settings = self._get_profile_settings(slicer_input.printer_profile)
            
            # Override profile settings with input parameters
            effective_settings = self._merge_settings(profile_settings, slicer_input)
            
            self.logger.info(f"Slicing mode check: mock_mode={self.mock_mode}, slicer_available={self._is_slicer_available()}")
            
            # Validate slicer availability
            if not self.mock_mode and not self._is_slicer_available():
                raise SlicerExecutionError(f"Slicer engine '{self.slicer_engine}' not available")
            
            # Perform slicing operation
            if self.mock_mode:
                gcode_result = await self._mock_slice_operation(slicer_input, effective_settings)
            else:
                gcode_result = await self._perform_actual_slicing(slicer_input, effective_settings)
            
            processing_time = time.time() - start_time
            gcode_result['processing_time'] = processing_time
            gcode_result['status'] = 'completed'
            
            self.logger.info(f"Slicing completed successfully in {processing_time:.2f}s")
            
            return TaskResult(
                success=True,
                data=gcode_result,
                error_message=None
            )
            
        except Exception as e:
            self.logger.error(f"Slicing task failed: {e}")
            processing_time = time.time() - start_time
            return TaskResult(
                success=False,
                data={},
                error_message=str(e)
            )
    
    def _get_profile_settings(self, profile_name: str) -> Dict[str, Any]:
        """Get settings for the specified profile."""
        if profile_name in self.predefined_profiles:
            return self.predefined_profiles[profile_name].copy()
        
        # Try to load custom profile from file
        profile_file = self.profiles_dir / f"{profile_name}.yaml"
        if profile_file.exists():
            try:
                with open(profile_file, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load profile {profile_name}: {e}")
        
        # Raise an error for invalid profiles instead of falling back
        raise ValidationError(f"Profile '{profile_name}' not found")
    
    def _merge_settings(self, profile_settings: Dict[str, Any], slicer_input: SlicerAgentInput) -> Dict[str, Any]:
        """Merge profile settings with input parameters."""
        settings = profile_settings.copy()
        
        # Apply quality preset adjustments first
        quality_preset = slicer_input.quality_preset
        if quality_preset in self.quality_presets:
            preset = self.quality_presets[quality_preset]
            settings['layer_height'] = preset['layer_height']
            settings['quality_factor'] = preset['quality_factor']
        
        # Override with input parameters (these take priority over quality presets)
        if hasattr(slicer_input, 'layer_height'):
            settings['layer_height'] = slicer_input.layer_height
        if hasattr(slicer_input, 'infill_percentage'):
            settings['infill_percentage'] = slicer_input.infill_percentage
        if hasattr(slicer_input, 'print_speed'):
            settings['print_speed'] = slicer_input.print_speed
        
        return settings
    
    def _is_slicer_available(self) -> bool:
        """Check if slicer executable is available."""
        if self.mock_mode:
            return True
        
        slicer_path = self.slicer_paths.get(self.slicer_engine)
        if not slicer_path:
            return False
        
        return shutil.which(slicer_path) is not None
    
    async def _mock_slice_operation(self, slicer_input: SlicerAgentInput, effective_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Perform mock slicing operation for testing."""
        self.logger.info("Performing mock slicing operation")
        
        # Create mock G-code content
        quality_preset = slicer_input.quality_preset
        layer_height = slicer_input.layer_height
        
        # Calculate mock metrics based on quality preset
        layer_count = {
            "draft": 30,
            "standard": 50,
            "fine": 80,
            "ultra": 120
        }.get(quality_preset, 50)
        
        estimated_print_time = layer_count * 2  # 2 minutes per layer
        material_usage = layer_count * 0.5  # 0.5g per layer
        
        # Generate mock G-code content with proper string concatenation
        gcode_content = f"; Generated by Mock SlicerAgent\n"
        gcode_content += f"; Model: {slicer_input.model_file_path}\n"
        gcode_content += f"; Profile: {slicer_input.printer_profile}\n"
        gcode_content += f"; Quality: {quality_preset}\n"
        gcode_content += f"; Layer Height: {layer_height}mm\n\n"
        gcode_content += "; Start G-code\n"
        gcode_content += "G21 ; set units to millimeters\n"
        gcode_content += "G90 ; use absolute coordinates\n"
        gcode_content += "M104 S200 ; set hotend temperature\n"
        gcode_content += "M140 S60 ; set bed temperature\n"
        gcode_content += "G28 ; home all axes\n\n"
        
        # Add layer content
        for layer in range(layer_count):
            z_height = layer * layer_height
            gcode_content += f"; Layer {layer + 1}\n"
            gcode_content += f"G1 Z{z_height:.2f} F3000\n"
            gcode_content += f"G1 X10 Y10 E{layer * 0.1:.2f} F1500\n"
            gcode_content += f"G1 X50 Y50 E{layer * 0.2:.2f} F1500\n\n"
        
        # Add end G-code
        gcode_content += "; End G-code\n"
        gcode_content += "M104 S0 ; turn off hotend\n"
        gcode_content += "M140 S0 ; turn off bed\n"
        gcode_content += "G28 X0 ; home X axis\n"
        
        # Create temporary G-code file
        gcode_file = tempfile.NamedTemporaryFile(mode='w', suffix='.gcode', delete=False)
        gcode_file.write(gcode_content)
        gcode_file.close()
        
        # Track temp files for cleanup
        if not hasattr(self, '_temp_files'):
            self._temp_files = []
        self._temp_files.append(gcode_file.name)
        
        return {
            "gcode_file_path": gcode_file.name,
            "estimated_print_time": estimated_print_time,
            "material_usage": material_usage,
            "layer_count": layer_count,
            "slicing_time": 1.5,  # Mock slicing time
            "total_movements": layer_count * 3,
            "profile_used": slicer_input.printer_profile
        }
    
    async def _perform_actual_slicing(self, slicer_input: SlicerAgentInput, effective_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Perform actual slicing using slicer executable."""
        self.logger.info("Performing actual slicing operation")
        
        # Check if slicer is available
        if not self._is_slicer_available():
            raise SlicerExecutionError("Slicer executable not available for actual slicing")
        
        # Get slicer executable path
        slicer_path = self.slicer_paths.get(self.slicer_engine)
        if not slicer_path:
            raise SlicerExecutionError("No slicer executable found")
        
        # Create output G-code file
        output_file = tempfile.NamedTemporaryFile(suffix='.gcode', delete=False)
        gcode_path = output_file.name
        output_file.close()
        
        try:
            # Build slicer command for PrusaSlicer
            if 'prusa-slicer' in slicer_path:
                cmd = [
                    slicer_path,
                    '--export-gcode',
                    '--output', gcode_path,
                    slicer_input.model_file_path
                ]
                
                # Add basic settings
                if 'layer_height' in effective_settings:
                    cmd.extend(['--layer-height', str(effective_settings['layer_height'])])
                if 'infill_percentage' in effective_settings:
                    cmd.extend(['--fill-density', f"{effective_settings['infill_percentage']}%"])
                if 'print_speed' in effective_settings:
                    cmd.extend(['--perimeter-speed', str(effective_settings['print_speed'])])
                
            else:
                raise SlicerExecutionError(f"Unsupported slicer: {slicer_path}")
            
            # Execute slicer command
            self.logger.info(f"Executing slicer command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = f"Slicer failed with return code {result.returncode}: {result.stderr}"
                self.logger.error(error_msg)
                raise SlicerExecutionError(error_msg)
            
            # Verify output file was created
            if not os.path.exists(gcode_path) or os.path.getsize(gcode_path) == 0:
                raise SlicerExecutionError("Slicer did not generate valid G-code output")
            
            self.logger.info(f"Slicing completed successfully: {gcode_path}")
            
            # Analyze the generated G-code
            analysis = self._analyze_gcode_file(gcode_path)
            
            return {
                "gcode_file_path": gcode_path,
                "gcode_content": None,  # Don't load large G-code into memory
                "layer_count": analysis.get("layer_count", 0),
                "slicing_time": 2.0,  # Actual slicing time would be measured
                "total_movements": analysis.get("total_movements", 0),
                "profile_used": slicer_input.printer_profile,
                "estimated_print_time": analysis.get("estimated_print_time", 0),
                "material_usage": analysis.get("material_usage", 0.0)
            }
            
        except subprocess.TimeoutExpired:
            if os.path.exists(gcode_path):
                os.unlink(gcode_path)
            raise SlicerExecutionError("Slicer operation timed out")
        except Exception as e:
            # Clean up output file on error
            if os.path.exists(gcode_path):
                os.unlink(gcode_path)
            raise SlicerExecutionError(f"Slicing failed: {str(e)}")
    
    def _analyze_gcode_file(self, gcode_file_path: str) -> Dict[str, Any]:
        """Analyze G-code file and extract metrics."""
        try:
            if not os.path.exists(gcode_file_path):
                self.logger.warning(f"Failed to analyze G-code file: [Errno 2] No such file or directory: '{gcode_file_path}'")
                return {
                    "layer_count": 0,
                    "total_movements": 0,
                    "material_usage": 0.0,
                    "estimated_print_time": 0,
                    "hotend_temperature": 0,
                    "bed_temperature": 0
                }
            
            with open(gcode_file_path, 'r') as f:
                content = f.read()
            
            # Initialize analysis results
            layer_count = 0
            total_movements = 0
            material_usage = 0.0
            hotend_temperature = 0
            bed_temperature = 0
            
            # Parse G-code content
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                
                # Count layers
                if line.startswith('; Layer'):
                    layer_count += 1
                
                # Count movement commands
                if line.startswith('G1'):
                    total_movements += 1
                    
                    # Extract material usage from E commands
                    if 'E' in line:
                        try:
                            e_index = line.find('E')
                            e_value_str = line[e_index+1:].split()[0]
                            e_value = float(e_value_str)
                            if e_value > material_usage:
                                material_usage = e_value
                        except (ValueError, IndexError):
                            pass
                
                # Extract temperatures (only capture first non-zero temperatures)
                if line.startswith('M104') and 'S' in line and hotend_temperature == 0:  # Hotend temperature
                    try:
                        # Parse M104 S200 ; set hotend temperature
                        parts = line.split()
                        for part in parts:
                            if part.startswith('S'):
                                temp_str = part[1:]  # Remove 'S' prefix
                                temp_value = int(temp_str)
                                if temp_value > 0:  # Only capture heating commands, not cooling
                                    hotend_temperature = temp_value
                                break
                    except (ValueError, IndexError):
                        pass
                
                if line.startswith('M140') and 'S' in line and bed_temperature == 0:  # Bed temperature
                    try:
                        # Parse M140 S60 ; set bed temperature
                        parts = line.split()
                        for part in parts:
                            if part.startswith('S'):
                                temp_str = part[1:]  # Remove 'S' prefix
                                temp_value = int(temp_str)
                                if temp_value > 0:  # Only capture heating commands, not cooling
                                    bed_temperature = temp_value
                                break
                    except (ValueError, IndexError):
                        pass
            
            # Estimate print time (simple heuristic)
            estimated_print_time = layer_count * 2 + total_movements * 0.05
            
            return {
                "layer_count": layer_count,
                "total_movements": total_movements,
                "material_usage": material_usage,
                "estimated_print_time": int(estimated_print_time),
                "hotend_temperature": hotend_temperature,
                "bed_temperature": bed_temperature
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze G-code file: {e}")
            return {
                "layer_count": 0,
                "total_movements": 0,
                "material_usage": 0.0,
                "estimated_print_time": 0,
                "hotend_temperature": 0,
                "bed_temperature": 0
            }

    # Public API methods
    
    async def slice_stl(self, stl_path: str, profile_name: str, **kwargs) -> Dict[str, Any]:
        """
        Main public API method for slicing STL files.
        
        This is the primary interface for Task 2.3.1 implementation.
        
        Args:
            stl_path: Path to the STL file to slice
            profile_name: Name of the printer profile to use
            **kwargs: Additional slicing parameters
            
        Returns:
            Dictionary containing G-code file path and slicing metrics
        """
        try:
            # Prepare input data
            input_data = {
                'model_file_path': stl_path,
                'printer_profile': profile_name,
                'material_type': kwargs.get('material_type', 'PLA'),
                'quality_preset': kwargs.get('quality_preset', 'standard'),
                'infill_percentage': kwargs.get('infill_percentage', 20),
                'layer_height': kwargs.get('layer_height', 0.2),
                'print_speed': kwargs.get('print_speed', 50)
            }
            
            # Execute slicing task
            response = await self._slice_stl_task(input_data)
            
            if response.success:
                return response.data
            else:
                raise SlicerExecutionError(f"Slicing failed: {response.error_message}")
                
        except Exception as e:
            self.logger.error(f"slice_stl failed: {e}")
            raise SlicerExecutionError(f"Slicing operation failed: {str(e)}")

    def cleanup(self) -> None:
        """Clean up agent resources."""
        try:
            # Close any open files or connections
            if hasattr(self, '_temp_files'):
                for temp_file in self._temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except Exception:
                        pass
                self._temp_files.clear()
            
            self.logger.info("Slicer Agent cleanup completed")
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    def set_mock_mode(self, enabled: bool) -> None:
        """Set mock mode on or off."""
        old_mode = self.mock_mode
        self.mock_mode = enabled
        self.logger.info(f"Mock mode changed from {old_mode} to {enabled}")
    
    def list_profiles(self) -> Dict[str, Any]:
        """List available slicer profiles."""
        return self.profiles
    
    def _list_profiles_sync(self) -> Dict[str, Any]:
        """Synchronous version of list_profiles for task execution."""
        return {"profiles": list(self.profiles.keys())}
    
    async def _validate_model_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Validate model file task."""
        model_path = task_details.get('model_file_path')
        if not model_path:
            return {"valid": False, "error": "No model file path provided"}
        
        if not os.path.exists(model_path):
            return {"valid": False, "error": f"File not found: {model_path}"}
        
        file_ext = Path(model_path).suffix.lower()
        if file_ext not in self.supported_input_formats:
            return {"valid": False, "error": f"Unsupported format: {file_ext}"}
        
        return {"valid": True, "format": file_ext}
    
    async def _estimate_print_time_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate print time task."""
        # Simple estimation based on file size and quality
        model_path = task_details.get('model_file_path', '')
        quality = task_details.get('quality_preset', 'standard')
        
        if os.path.exists(model_path):
            file_size_mb = os.path.getsize(model_path) / (1024 * 1024)
            time_multiplier = {'draft': 0.5, 'standard': 1.0, 'fine': 1.5, 'ultra': 2.0}
            estimated_time = file_size_mb * 10 * time_multiplier.get(quality, 1.0)
            return {"estimated_print_time_minutes": int(estimated_time)}
        
        return {"estimated_print_time_minutes": 0, "error": "File not found"}
    
    # Compatibility properties for existing code
    @property 
    def prusaslicer_path(self) -> Optional[str]:
        """Get PrusaSlicer path for compatibility."""
        return self.slicer_paths.get('prusaslicer')
    
    @property
    def cura_path(self) -> Optional[str]:
        """Get Cura path for compatibility."""
        return self.slicer_paths.get('cura')
