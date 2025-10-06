"""
Printer Agent - Serial Communication and 3D Printer Control

This module implements the Printer Agent responsible for direct communication with 3D printers
via serial port, including mock mode for testing and development.

Task 2.3.2: Serial Communication with Mock Mode
- Robust serial port communication with Marlin firmware
- Virtual/Mock printer for testing without hardware
- Connection monitoring and auto-reconnect functionality  
- USB device detection and auto-identification
- Comprehensive error handling and recovery
"""

import os
import asyncio
import threading
import time
import re
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
from queue import Queue, Empty
from dataclasses import dataclass
from enum import Enum

# Serial communication imports
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

# Enhanced Multi-Printer Support
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_printer_support import MultiPrinterDetector, EnhancedPrinterCommunicator
    from printer_support.printer_emulator import PrinterEmulatorManager, EmulatedPrinterType
    ENHANCED_PRINTER_SUPPORT = True
except ImportError:
    ENHANCED_PRINTER_SUPPORT = False
    # Only show warning in verbose mode
    import os
    if os.getenv('VERBOSE_MODE') == '1' or '--verbose' in ' '.join(__import__('sys').argv):
        print("Warning: Enhanced printer support not available, using basic mode only")

from core.base_agent import BaseAgent
from core.logger import get_logger
from core.exceptions import (
    PrinterAgentError, PrinterConnectionError, PrinterNotConnectedError, SerialCommunicationError,
    GCodeStreamingError, PrinterTimeoutError, ValidationError, ConfigurationError
)
from core.api_schemas import PrinterAgentInput, PrinterAgentOutput, TaskResult


class PrinterStatus(Enum):
    """Printer status enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    IDLE = "idle"
    PRINTING = "printing"
    PAUSED = "paused"
    ERROR = "error"
    OFFLINE = "offline"


class PrintJobStatus(Enum):
    """Print job status enumeration."""
    QUEUED = "queued"
    STARTING = "starting"
    PRINTING = "printing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PrinterInfo:
    """Container for printer information."""
    printer_id: str
    name: str
    firmware: str
    firmware_version: str
    capabilities: List[str]
    serial_port: Optional[str] = None
    baudrate: int = 115200
    is_mock: bool = False


@dataclass
class TemperatureData:
    """Container for temperature information."""
    hotend_current: float = 0.0
    hotend_target: float = 0.0
    bed_current: float = 0.0
    bed_target: float = 0.0
    chamber_current: Optional[float] = None
    chamber_target: Optional[float] = None


@dataclass
class PrintProgress:
    """Container for print progress information."""
    job_id: str
    status: PrintJobStatus
    progress_percentage: float = 0.0
    lines_total: int = 0
    lines_sent: int = 0
    current_layer: int = 0
    elapsed_time: float = 0.0
    estimated_remaining: float = 0.0
    current_command: str = ""
    gcode_file: Optional[str] = None
    start_time: Optional[datetime] = None
    pause_time: Optional[datetime] = None
    resume_time: Optional[datetime] = None


@dataclass 
class StreamingStatus:
    """Container for G-code streaming status."""
    is_streaming: bool = False
    is_paused: bool = False
    can_pause: bool = True
    can_resume: bool = False
    emergency_stop_available: bool = True


class MockPrinter:
    """Mock printer for testing without hardware."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("mock_printer")
        self.firmware_version = "Marlin 2.1.2.4 (Mock)"
        self.temperature = TemperatureData()
        self.status = PrinterStatus.IDLE
        self.simulate_delays = config.get('simulate_delays', True)
        self.simulate_errors = config.get('simulate_errors', False)
        self.error_probability = config.get('error_probability', 0.05)
        self.connected = False
        self.response_queue = Queue()
        self.last_command = ""
        self.heating_started = {}
        
    def connect(self) -> bool:
        """Simulate printer connection."""
        if self.simulate_delays:
            time.sleep(0.1)  # Simulate connection delay
            
        self.connected = True
        self.status = PrinterStatus.CONNECTED
        self.logger.info("Mock printer connected")
        return True
        
    def disconnect(self) -> bool:
        """Simulate printer disconnection."""
        self.connected = False
        self.status = PrinterStatus.DISCONNECTED
        self.logger.info("Mock printer disconnected")
        return True
        
    def send_command(self, command: str) -> str:
        """Simulate sending G-code command and return response."""
        if not self.connected:
            raise SerialCommunicationError("Mock printer not connected")
            
        self.last_command = command.strip()
        
        # Simulate processing delay
        if self.simulate_delays:
            time.sleep(0.01 + (len(command) * 0.001))
            
        # Simulate random errors
        if self.simulate_errors:
            import random
            if random.random() < self.error_probability:
                return "Error:Checksum mismatch"
            
        return self._process_gcode_command(command)
        
    def _process_gcode_command(self, command: str) -> str:
        """Process G-code command and return appropriate response."""
        cmd = command.strip().upper()
        
        # Remove line numbers and checksums
        if cmd.startswith('N'):
            cmd = re.sub(r'^N\d+\s+', '', cmd)
        if '*' in cmd:
            cmd = cmd.split('*')[0].strip()
            
        # Information commands
        if cmd == "M115":  # Firmware version
            return (f"FIRMWARE_NAME:{self.firmware_version} "
                   f"PROTOCOL_VERSION:1.0 MACHINE_TYPE:RepRap EXTRUDER_COUNT:1")
                   
        elif cmd.startswith("M105"):  # Temperature report
            return (f"ok T:{self.temperature.hotend_current:.1f}/"
                   f"{self.temperature.hotend_target:.1f} "
                   f"B:{self.temperature.bed_current:.1f}/"
                   f"{self.temperature.bed_target:.1f}")
                   
        elif cmd.startswith("M114"):  # Position report
            return "ok X:0.00 Y:0.00 Z:0.00 E:0.00"
            
        # Temperature setting commands
        elif cmd.startswith("M104"):  # Set hotend temperature
            temp_match = re.search(r'S(\d+)', cmd)
            if temp_match:
                target_temp = float(temp_match.group(1))
                self.temperature.hotend_target = target_temp
                if target_temp > 0:
                    self.heating_started['hotend'] = time.time()
                return "ok"
                
        elif cmd.startswith("M140"):  # Set bed temperature
            temp_match = re.search(r'S(\d+)', cmd)
            if temp_match:
                target_temp = float(temp_match.group(1))
                self.temperature.bed_target = target_temp
                if target_temp > 0:
                    self.heating_started['bed'] = time.time()
                return "ok"
                
        # Movement commands
        elif cmd.startswith(("G0", "G1", "G28", "G29")):
            if self.simulate_delays:
                time.sleep(0.05)  # Simulate movement time
            return "ok"
            
        # Print control commands (Task 2.3.3)
        elif cmd.startswith("M24"):  # Resume print
            return "ok"
            
        elif cmd.startswith("M25"):  # Pause print
            return "ok"
            
        elif cmd.startswith("M112"):  # Emergency stop
            # Reset temperatures on emergency stop
            self.temperature.hotend_target = 0.0
            self.temperature.bed_target = 0.0
            return "ok"
            
        # Default response
        return "ok"
        
    def update_temperatures(self):
        """Update simulated temperatures."""
        current_time = time.time()
        
        # Simulate hotend heating
        if 'hotend' in self.heating_started:
            heat_time = current_time - self.heating_started['hotend']
            if self.temperature.hotend_target > 0:
                # Faster heating for testing (5 seconds instead of 30)
                progress = min(1.0, heat_time / 5.0)
                self.temperature.hotend_current = (
                    20 + (self.temperature.hotend_target - 20) * progress
                )
                if progress >= 1.0:
                    del self.heating_started['hotend']
            else:
                # Cooling down
                self.temperature.hotend_current = max(20, 
                    self.temperature.hotend_current - 2.0)
                    
        # Simulate bed heating
        if 'bed' in self.heating_started:
            heat_time = current_time - self.heating_started['bed']
            if self.temperature.bed_target > 0:
                # Faster heating for testing (10 seconds instead of 60)
                progress = min(1.0, heat_time / 10.0)
                self.temperature.bed_current = (
                    20 + (self.temperature.bed_target - 20) * progress
                )
                if progress >= 1.0:
                    del self.heating_started['bed']
            else:
                # Cooling down
                self.temperature.bed_current = max(20,
                    self.temperature.bed_current - 1.0)


class PrinterAgent(BaseAgent):
    """
    Printer Agent for serial communication and 3D printer control.
    
    Features:
    - Serial port communication with Marlin firmware
    - Mock printer mode for testing
    - Connection monitoring and auto-reconnect
    - USB device detection and auto-identification
    - Temperature monitoring and control
    - Error handling and recovery
    """
    
    def __init__(self, agent_id: str = "printer_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id)
        
        self.config = config or {}
        self.logger = get_logger("printer_agent")
        
        # Serial communication settings
        self.serial_port = None
        self.serial_connection = None
        self.baudrate = self.config.get('baudrate', 115200)
        self.timeout = self.config.get('timeout', 10)
        self.reconnect_attempts = self.config.get('reconnect_attempts', 3)
        self.reconnect_delay = self.config.get('reconnect_delay', 5)
        
        # Printer state
        self.printer_info = None
        self.printer_status = PrinterStatus.DISCONNECTED
        self.temperature_data = TemperatureData()
        self.current_job = None
        
        # Mock mode settings
        self.mock_mode = self.config.get('mock_mode', True)
        self.mock_printer = None
        
        # Communication monitoring
        self.communication_thread = None
        self.stop_monitoring = threading.Event()
        self.response_queue = Queue()
        self.command_lock = threading.Lock()
        self.state_lock = threading.RLock()  # Reentrant lock for shared state
        
        # G-code streaming state (Task 2.3.3)
        self.streaming_status = StreamingStatus()
        self.print_progress = None
        self.streaming_thread = None
        self.streaming_stop_event = threading.Event()
        self.streaming_queue = Queue()
        self.progress_callbacks = []
        self.progress_callbacks_lock = threading.Lock()
        self.checksum_enabled = self.config.get('gcode', {}).get('streaming', {}).get('checksum_enabled', True)
        self.chunk_size = self.config.get('gcode', {}).get('streaming', {}).get('chunk_size', 1)
        self.ack_timeout = self.config.get('gcode', {}).get('streaming', {}).get('ack_timeout', 5)
        
        # Print job management
        self.active_jobs = {}
        self.print_statistics = {
            'total_prints': 0,
            'successful_prints': 0,
            'failed_prints': 0,
            'cancelled_prints': 0,
            'total_print_time': 0.0
        }
        
        # Initialize mock printer if needed
        if self.mock_mode:
            mock_config = self.config.get('mock_printer', {})
            self.mock_printer = MockPrinter(mock_config)
            # Auto-connect mock printer
            self.mock_printer.connect()
            self.logger.info("Mock printer auto-connected")
        
        # Enhanced Multi-Printer Support
        self.multi_printer_detector = None
        self.emulator_manager = None
        self.enhanced_communicator = None
        self.available_printers = []
        self.connected_printers = {}
        
        if ENHANCED_PRINTER_SUPPORT:
            self.multi_printer_detector = MultiPrinterDetector()
            self.emulator_manager = PrinterEmulatorManager()
            # EnhancedPrinterCommunicator will be created when needed
            self.enhanced_communicator = None
            self.logger.info("Enhanced multi-printer support enabled")
        else:
            self.logger.warning("Enhanced multi-printer support not available, using basic mode")
        
        self.logger.info(f"Printer Agent initialized (mock_mode: {self.mock_mode})")

    @property
    def connection_status(self) -> PrinterStatus:
        """Expose current printer connection status."""
        return self.printer_status

    @connection_status.setter
    def connection_status(self, value: PrinterStatus) -> None:
        """Allow tests and callers to set the connection status explicitly."""
        if not isinstance(value, PrinterStatus):
            raise ValueError("connection_status must be a PrinterStatus instance")
        self.printer_status = value

    def is_connected(self) -> bool:
        """Return True when the agent considers the printer connected."""
        return self.printer_status in {PrinterStatus.CONNECTED, PrinterStatus.IDLE, PrinterStatus.PRINTING, PrinterStatus.PAUSED}
        
    async def execute_task(self, task_details: Dict[str, Any]) -> Union[Dict[str, Any], TaskResult]:
        """Execute printer-related tasks."""
        operation = task_details.get('operation', 'unknown')
        task_id = task_details.get('task_id')
        
        try:
            # Handle operations that should return TaskResult
            if operation == 'start_print':
                return await self._handle_start_print_task(task_details)
            
            # Handle other operations normally
            if operation == 'connect_printer':
                return await self._handle_connect_printer(task_details)
            elif operation == 'disconnect_printer':
                return await self._handle_disconnect_printer(task_details)
            elif operation == 'get_printer_status':
                return await self._handle_get_printer_status(task_details)
            elif operation == 'send_gcode_command':
                return await self._handle_send_gcode_command(task_details)
            elif operation == 'set_temperature':
                return await self._handle_set_temperature(task_details)
            elif operation == 'get_temperature':
                return await self._handle_get_temperature(task_details)
            elif operation == 'detect_printers':
                return await self._handle_detect_printers(task_details)
            elif operation == 'auto_connect':
                return await self._handle_auto_connect(task_details)
            elif operation == 'stream_gcode':
                return await self._handle_stream_gcode(task_details)
            elif operation == 'pause_print':
                                return await self._handle_pause_print(task_details)
            elif operation == 'resume_print':
                return await self._handle_resume_print(task_details)
            elif operation == 'stop_print':
                return await self._handle_stop_print(task_details)
            elif operation == 'get_print_progress':
                return await self._handle_get_print_progress(task_details)
            elif operation == 'discover_all_printers':
                return await self._handle_discover_all_printers(task_details)
            else:
                raise PrinterAgentError(f"Unknown operation: {operation}")
                
        except ValidationError as e:
            # For start_print operations, let ValidationError propagate to match test expectations
            if operation == 'start_print':
                raise e
            
            if task_id:
                return TaskResult(
                    success=False,
                    data={},
                    error_message=str(e),
                    metadata={"task_id": task_id},
                    task_id=task_id
                )
            else:
                raise e

        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            if task_id:
                return TaskResult(
                    success=False,
                    data={},
                    error_message=str(e),
                    metadata={"task_id": task_id},
                    task_id=task_id
                )
            else:
                return {
                    'success': False,
                    'error_message': str(e),
                    'error_type': type(e).__name__
                }
    
    async def _handle_start_print_task(self, task_details: Dict[str, Any]) -> TaskResult:
        """Handle start_print task and return TaskResult."""
        task_id = task_details.get('task_id', 'unknown')
        gcode_file_path = task_details.get('gcode_file_path')
        
        if not gcode_file_path:
            raise ValidationError("gcode_file_path is required for start_print operation")
        
        if not os.path.exists(gcode_file_path):
            raise ValidationError(f"G-code file not found: {gcode_file_path}")
        
        # Create specifications for streaming
        specifications = {
            'gcode_file': gcode_file_path,
            'progress_callback': None
        }
        
        stream_task_details = {
            'operation': 'stream_gcode',
            'specifications': specifications
        }
        
        try:
            result = await self._handle_stream_gcode(stream_task_details)
            
            return TaskResult(
                success=result.get('success', False),
                data=result,
                error_message=result.get('error_message'),
                metadata={'task_id': task_id},
                task_id=task_id
            )
        except Exception as e:
            return TaskResult(
                success=False,
                data={},
                error_message=str(e),
                metadata={'task_id': task_id},
                task_id=task_id
            )
            
    async def _handle_connect_printer(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle printer connection request."""
        specifications = task_details.get('specifications', {})
        port = specifications.get('serial_port')
        baudrate = specifications.get('baudrate', self.baudrate)
        
        if self.mock_mode:
            success = await self._connect_mock_printer()
        else:
            success = await self._connect_real_printer(port, baudrate)
            
        if success:
            return {
                'success': True,
                'printer_id': self.printer_info.printer_id if self.printer_info else 'unknown',
                'status': self.printer_status.value,
                'firmware': self.printer_info.firmware if self.printer_info else 'unknown',
                'is_mock': self.mock_mode
            }
        else:
            return {
                'success': False,
                'error_message': 'Failed to connect to printer'
            }
            
    async def _handle_disconnect_printer(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle printer disconnection request."""
        success = await self._disconnect_printer()
        
        return {
            'success': success,
            'status': self.printer_status.value
        }
        
    async def _handle_get_printer_status(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle printer status request."""
        status_data = await self._get_printer_status()
        
        return {
            'success': True,
            'status': status_data['status'],
            'temperature': status_data['temperature'],
            'position': status_data['position'],
            'printer_info': status_data['printer_info'],
            'connection_info': status_data['connection_info']
        }
        
    async def _handle_send_gcode_command(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle G-code command sending."""
        specifications = task_details.get('specifications', {})
        command = specifications.get('command', '')
        
        if not command:
            raise ValidationError("G-code command is required")
            
        response = await self._send_gcode_command(command)
        
        return {
            'success': True,
            'command': command,
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        
    async def _handle_set_temperature(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle temperature setting request."""
        specifications = task_details.get('specifications', {})
        hotend_temp = specifications.get('hotend_temperature')
        bed_temp = specifications.get('bed_temperature')
        
        success = await self._set_temperatures(hotend_temp, bed_temp)
        
        return {
            'success': success,
            'hotend_target': hotend_temp,
            'bed_target': bed_temp,
            'timestamp': datetime.now().isoformat()
        }
        
    async def _handle_get_temperature(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle temperature reading request."""
        temp_data = await self._get_temperatures()
        
        return {
            'success': True,
            'temperature': {
                'hotend_current': temp_data.hotend_current,
                'hotend_target': temp_data.hotend_target,
                'bed_current': temp_data.bed_current,
                'bed_target': temp_data.bed_target
            },
            'timestamp': datetime.now().isoformat()
        }
        
    async def _handle_detect_printers(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle printer detection request using enhanced multi-printer support."""
        include_emulated = task_details.get('specifications', {}).get('include_emulated', True)
        
        if ENHANCED_PRINTER_SUPPORT:
            printers = await self.discover_all_printers(include_emulated=include_emulated)
            return {
                'success': True,
                'printers': printers,
                'count': len(printers),
                'enhanced_support': True
            }
        else:
            # Fallback to basic detection
            printers = await self._detect_printers()
            return {
                'success': True,
                'printers': printers,
                'count': len(printers),
                'enhanced_support': False
            }
        
    async def _handle_auto_connect(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle auto-connect request."""
        success, printer_info = await self._auto_connect()
        
        if success:
            return {
                'success': True,
                'printer_info': {
                    'printer_id': printer_info.printer_id,
                    'name': printer_info.name,
                    'firmware': printer_info.firmware,
                    'serial_port': printer_info.serial_port,
                    'is_mock': printer_info.is_mock
                }
            }
        else:
            return {
                'success': False,
                'error_message': 'No compatible printers found'
            }
            
    # ===== G-CODE STREAMING HANDLERS (Task 2.3.3) =====
    
    async def _handle_stream_gcode(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle G-code streaming request."""
        specifications = task_details.get('specifications', {})
        gcode_file = specifications.get('gcode_file')
        progress_callback = specifications.get('progress_callback')
        
        if not gcode_file:
            raise ValidationError("G-code file path is required")
            
        if not os.path.exists(gcode_file):
            raise ValidationError(f"G-code file not found: {gcode_file}")
            
        if self.streaming_status.is_streaming:
            raise GCodeStreamingError("Already streaming G-code")
            
        # Prepare streaming
        job_id = specifications.get('job_id') or self._create_print_job(gcode_file)
        success = await self._start_gcode_streaming(gcode_file, job_id, progress_callback)
        
        if success:
            return {
                'success': True,
                'job_id': job_id,
                'streaming_started': True,
                'gcode_file': gcode_file
            }
        else:
            return {
                'success': False,
                'error_message': 'Failed to start G-code streaming'
            }
    
    async def _handle_pause_print(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle print pause request."""
        if not self.streaming_status.is_streaming:
            raise GCodeStreamingError("No active print job to pause")
            
        if self.streaming_status.is_paused:
            return {
                'success': True,
                'message': 'Print is already paused',
                'was_paused': True
            }
            
        success = await self._pause_streaming()
        
        return {
            'success': success,
            'paused': success,
            'job_id': self.print_progress.job_id if self.print_progress else None
        }
    
    async def _handle_resume_print(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle print resume request."""
        if not self.streaming_status.is_streaming:
            raise GCodeStreamingError("No active print job to resume")
            
        if not self.streaming_status.is_paused:
            return {
                'success': True,
                'message': 'Print is not paused',
                'was_resumed': False
            }
            
        success = await self._resume_streaming()
        
        return {
            'success': success,
            'resumed': success,
            'job_id': self.print_progress.job_id if self.print_progress else None
        }
    
    async def _handle_stop_print(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency stop request."""
        if not self.streaming_status.is_streaming:
            return {
                'success': True,
                'message': 'No active print job to stop',
                'was_stopped': False
            }
            
        success = await self._emergency_stop()
        
        return {
            'success': success,
            'stopped': success,
            'emergency_stop': True,
            'job_id': self.print_progress.job_id if self.print_progress else None
        }
    
    async def _handle_get_print_progress(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle print progress request."""
        if not self.print_progress:
            return {
                'success': True,
                'has_progress': False,
                'message': 'No active print job'
            }
            
        progress_data = self._get_progress_data()
        
        return {
            'success': True,
            'has_progress': True,
            'progress': progress_data,
            'streaming_status': {
                'is_streaming': self.streaming_status.is_streaming,
                'is_paused': self.streaming_status.is_paused,
                'can_pause': self.streaming_status.can_pause,
                'can_resume': self.streaming_status.can_resume,
                'emergency_stop_available': self.streaming_status.emergency_stop_available
            }
        }
            
    async def _handle_discover_all_printers(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to discover all printers (real and emulated)."""
        printers = await self.discover_all_printers()
        return {
            'success': True,
            'printers': printers
        }

    # ===== PUBLIC CONTROL & UTILITY METHODS =====

    async def stream_gcode(self, gcode_file_path: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Public wrapper to stream a G-code file and wait for completion."""
        if not self._validate_gcode_file(gcode_file_path):
            return {
                'success': False,
                'error_message': f"Invalid G-code file: {gcode_file_path}"
            }

        if not self.is_connected():
            try:
                await self.execute_task({'operation': 'connect_printer', 'specifications': {}})
            except Exception as exc:  # pragma: no cover - defensive
                return {
                    'success': False,
                    'error_message': f"Failed to connect printer: {exc}"
                }

        task_details = {
            'operation': 'stream_gcode',
            'specifications': {
                'gcode_file': gcode_file_path,
                'progress_callback': progress_callback
            }
        }

        start_result = await self._handle_stream_gcode(task_details)
        if not start_result.get('success'):
            return start_result

        await self._wait_for_streaming_completion()

        progress = self._get_progress_data()
        job_status = None
        if self.print_progress:
            job_status = self.print_progress.status

        success = job_status == PrintJobStatus.COMPLETED if job_status else False
        result = {
            'success': success,
            'job_id': start_result['job_id'],
            'lines_sent': progress.get('lines_sent', 0),
            'total_lines': progress.get('lines_total', 0),
            'progress_percent': progress.get('progress_percent', 0.0),
            'status': job_status.value if job_status else None,
            'gcode_file': gcode_file_path
        }

        if not success:
            result['error_message'] = f"Print job ended with status {result['status']}"

        return result

    async def pause_streaming(self) -> Dict[str, Any]:
        """Pause the currently streaming print job."""
        if not self.streaming_status.is_streaming:
            return {
                'success': False,
                'error_message': 'No active print job to pause'
            }

        success = await self._pause_streaming()
        return {
            'success': success,
            'job_id': self.print_progress.job_id if self.print_progress else None,
            'status': self.print_progress.status.value if self.print_progress else None
        }

    async def resume_streaming(self) -> Dict[str, Any]:
        """Resume a previously paused print job."""
        if not self.streaming_status.is_streaming:
            return {
                'success': False,
                'error_message': 'No active print job to resume'
            }

        success = await self._resume_streaming()
        return {
            'success': success,
            'job_id': self.print_progress.job_id if self.print_progress else None,
            'status': self.print_progress.status.value if self.print_progress else None
        }

    def get_print_statistics(self) -> Dict[str, Any]:
        """Return accumulated print statistics."""
        return dict(self.print_statistics)

    def handle_error(self, error: Exception, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Extend base error handling with legacy error_message alias."""
        response = super().handle_error(error, task_details)

        if isinstance(error, SerialCommunicationError):
            response['error_message'] = f"Serial communication error: {response.get('message', str(error))}"
        elif isinstance(error, (PrinterConnectionError, PrinterNotConnectedError)):
            response['error_message'] = f"Printer connection error: {response.get('message', str(error))}"
        else:
            if 'error_message' not in response and 'message' in response:
                response['error_message'] = response['message']
        return response

    def _validate_gcode_file(self, gcode_file: str) -> bool:
        """Validate that the provided path points to a usable G-code file."""
        if not gcode_file:
            return False
        path = Path(gcode_file)
        if not path.exists() or not path.is_file():
            return False
        return path.suffix.lower() in {'.gcode', '.gco', '.gc', '.nc'}

    def _validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate printer configuration dictionaries used in tests."""
        if not isinstance(config, dict):
            return False

        mock_mode = config.get('mock_mode')
        if mock_mode is not None and not isinstance(mock_mode, bool):
            return False

        baud_rate = config.get('baud_rate') or config.get('baudrate')
        if baud_rate is not None:
            try:
                if int(baud_rate) <= 0:
                    return False
            except (TypeError, ValueError):
                return False

        serial_port = config.get('serial_port') or config.get('port')
        if serial_port is not None and not isinstance(serial_port, str):
            return False

        return True

    def _preprocess_gcode(self, gcode_file: str) -> List[str]:
        """Preprocess a G-code file into ready-to-stream commands."""
        return self._prepare_gcode_file(gcode_file)

    def _add_line_number_and_checksum(self, command: str, line_number: int) -> str:
        """Format a G-code command with line number and checksum."""
        if not command:
            raise ValueError("command cannot be empty")
        line_with_number = f"N{line_number} {command.strip()}"
        checksum = self._calculate_checksum(line_with_number)
        return f"{line_with_number}*{checksum}"

    def _detect_serial_ports(self) -> List[str]:
        """Detect available serial ports for real printers."""
        if self.mock_mode or not SERIAL_AVAILABLE:
            return ['MOCK']

        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports

    def _validate_temperature(self, temperature: float, target: str) -> bool:
        """Ensure temperature requests stay within safe operating limits."""
        if temperature is None:
            return False
        limits = {
            'hotend': (0, 300),
            'bed': (0, 130),
            'chamber': (0, 100)
        }
        low, high = limits.get(target.lower(), (0, 300))
        return low <= float(temperature) <= high

    def _create_print_job(self, gcode_file: str) -> str:
        """Create and register a new print job entry."""
        job_id = f"print_{int(time.time() * 1000)}"
        self.print_statistics['total_prints'] += 1
        self.active_jobs[job_id] = {
            'job_id': job_id,
            'gcode_file': gcode_file,
            'status': PrintJobStatus.QUEUED.value,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'lines_total': 0,
            'lines_sent': 0,
            'duration': 0.0
        }
        return job_id

    def _get_print_job_status(self, job_id: str) -> Dict[str, Any]:
        """Return stored metadata for a print job."""
        return self.active_jobs.get(job_id, {
            'job_id': job_id,
            'status': 'unknown'
        })

    async def _wait_for_streaming_completion(self, poll_interval: float = 0.05) -> None:
        """Poll until the streaming worker finishes."""
        while self.streaming_thread and self.streaming_thread.is_alive():
            await asyncio.sleep(poll_interval)
        # allow worker to update final state
        await asyncio.sleep(poll_interval)
    
    async def _connect_mock_printer(self) -> bool:
        """Connect to mock printer."""
        try:
            self.mock_printer.connect()
            
            self.printer_info = PrinterInfo(
                printer_id="mock_printer_001",
                name="Mock 3D Printer",
                firmware="Marlin",
                firmware_version=self.mock_printer.firmware_version,
                capabilities=["heating", "movement", "temperature_reporting"],
                is_mock=True
            )
            
            self.printer_status = PrinterStatus.CONNECTED
            
            # Start monitoring thread for mock printer
            self._start_monitoring()
            
            self.logger.info("Successfully connected to mock printer")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to mock printer: {e}")
            self.printer_status = PrinterStatus.ERROR
            return False
            
    async def _connect_real_printer(self, port: Optional[str], baudrate: int) -> bool:
        """Connect to real printer via serial port."""
        if not SERIAL_AVAILABLE:
            raise PrinterConnectionError("pyserial not available for real printer connection")
            
        try:
            # Auto-detect port if not specified
            if not port:
                detected = await self._detect_printers()
                if not detected:
                    raise PrinterConnectionError("No printers detected")
                port = detected[0]['port']
                
            self.logger.info(f"Attempting to connect to printer on {port} at {baudrate} baud")
            
            # Open serial connection
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # Wait for printer to initialize
            await asyncio.sleep(2)
            
            # Get printer info
            firmware_info = await self._send_gcode_command("M115")
            
            self.printer_info = PrinterInfo(
                printer_id=f"printer_{port.replace('/', '_')}",
                name=f"3D Printer on {port}",
                firmware="Marlin",
                firmware_version=self._parse_firmware_version(firmware_info),
                capabilities=["heating", "movement", "temperature_reporting"],
                serial_port=port,
                baudrate=baudrate,
                is_mock=False
            )
            
            self.printer_status = PrinterStatus.CONNECTED
            self.serial_port = port
            
            # Start monitoring thread
            self._start_monitoring()
            
            self.logger.info(f"Successfully connected to printer: {self.printer_info.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to real printer: {e}")
            self.printer_status = PrinterStatus.ERROR
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            raise PrinterConnectionError(f"Connection failed: {e}")
            
    async def _disconnect_printer(self) -> bool:
        """Disconnect from printer."""
        try:
            self.stop_monitoring.set()
            
            if self.communication_thread and self.communication_thread.is_alive():
                self.communication_thread.join(timeout=2)
                
            if self.mock_mode and self.mock_printer:
                self.mock_printer.disconnect()
            elif self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
                
            self.printer_status = PrinterStatus.DISCONNECTED
            self.printer_info = None
            self.serial_port = None
            self.stop_monitoring.clear()
            
            self.logger.info("Printer disconnected")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
            return False
            
    async def _send_gcode_command(self, command: str) -> str:
        """Send G-code command to printer."""
        if self.printer_status not in [PrinterStatus.CONNECTED, PrinterStatus.IDLE]:
            raise SerialCommunicationError("Printer not connected")
            
        with self.command_lock:
            try:
                if self.mock_mode:
                    response = self.mock_printer.send_command(command)
                else:
                    response = await self._send_real_command(command)
                    
                self.logger.debug(f"Command: {command} -> Response: {response}")
                return response
                
            except Exception as e:
                self.logger.error(f"Command failed: {command} -> {e}")
                raise SerialCommunicationError(f"Command failed: {e}", command=command)
                
    async def _send_real_command(self, command: str) -> str:
        """Send command to real printer via serial."""
        if not self.serial_connection or not self.serial_connection.is_open:
            raise SerialCommunicationError("Serial connection not available")
            
        try:
            # Send command
            full_command = f"{command}\n"
            self.serial_connection.write(full_command.encode('utf-8'))
            self.serial_connection.flush()
            
            # Read response
            response = ""
            start_time = time.time()
            
            while time.time() - start_time < self.timeout:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    response += line
                    
                    if line.startswith('ok') or line.startswith('Error'):
                        break
                        
                await asyncio.sleep(0.01)
                
            if not response:
                raise PrinterTimeoutError("No response from printer", timeout_seconds=self.timeout)
                
            return response
            
        except Exception as e:
            raise SerialCommunicationError(f"Serial communication error: {e}")
            
    async def _get_printer_status(self) -> Dict[str, Any]:
        """Get comprehensive printer status."""
        if self.mock_mode and self.mock_printer:
            self.mock_printer.update_temperatures()
            self.temperature_data = self.mock_printer.temperature
            
        return {
            'status': self.printer_status.value,
            'temperature': {
                'hotend_current': self.temperature_data.hotend_current,
                'hotend_target': self.temperature_data.hotend_target,
                'bed_current': self.temperature_data.bed_current,
                'bed_target': self.temperature_data.bed_target
            },
            'position': {
                'x': 0.0,
                'y': 0.0,
                'z': 0.0,
                'e': 0.0
            },
            'printer_info': {
                'printer_id': self.printer_info.printer_id if self.printer_info else None,
                'name': self.printer_info.name if self.printer_info else None,
                'firmware': self.printer_info.firmware if self.printer_info else None,
                'is_mock': self.mock_mode
            },
            'connection_info': {
                'serial_port': self.serial_port,
                'baudrate': self.baudrate,
                'connected': self.printer_status in [PrinterStatus.CONNECTED, PrinterStatus.IDLE]
            }
        }
        
    async def _set_temperatures(self, hotend_temp: Optional[float], bed_temp: Optional[float]) -> bool:
        """Set printer temperatures."""
        try:
            success = True
            
            if hotend_temp is not None:
                response = await self._send_gcode_command(f"M104 S{hotend_temp}")
                if not response.startswith('ok'):
                    success = False
                    
            if bed_temp is not None:
                response = await self._send_gcode_command(f"M140 S{bed_temp}")
                if not response.startswith('ok'):
                    success = False
                    
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to set temperatures: {e}")
            return False
            
    async def _get_temperatures(self) -> TemperatureData:
        """Get current printer temperatures."""
        try:
            response = await self._send_gcode_command("M105")
            return self._parse_temperature_response(response)
            
        except Exception as e:
            self.logger.error(f"Failed to get temperatures: {e}")
            return self.temperature_data
            
    async def _detect_printers(self) -> List[Dict[str, Any]]:
        """Detect available printers."""
        detected = []
        
        if self.mock_mode:
            detected.append({
                'port': 'MOCK',
                'description': 'Mock 3D Printer',
                'manufacturer': 'AI Agent 3D Print System',
                'product': 'Mock Printer',
                'is_mock': True
            })
        else:
            if SERIAL_AVAILABLE:
                ports = serial.tools.list_ports.comports()
                for port in ports:
                    # Filter for likely 3D printer ports
                    description = port.description.lower()
                    if any(keyword in description for keyword in 
                          ['arduino', 'ch340', 'cp210', 'ftdi', 'usb']):
                        detected.append({
                            'port': port.device,
                            'description': port.description,
                            'manufacturer': port.manufacturer,
                            'product': port.product,
                            'is_mock': False
                        })
                        
        self.logger.info(f"Detected {len(detected)} potential printers")
        return detected
        
    async def _auto_connect(self) -> Tuple[bool, Optional[PrinterInfo]]:
        """Automatically detect and connect to a printer."""
        detected_printers = await self._detect_printers()
        
        if not detected_printers:
            return False, None
            
        # Try connecting to each detected printer
        for printer in detected_printers:
            try:
                if printer['is_mock']:
                    success = await self._connect_mock_printer()
                else:
                    success = await self._connect_real_printer(printer['port'], self.baudrate)
                    
                if success:
                    return True, self.printer_info
                    
            except Exception as e:
                self.logger.warning(f"Failed to connect to {printer['port']}: {e}")
                continue
                
        return False, None
        
    def _start_monitoring(self):
        """Start communication monitoring thread."""
        if self.communication_thread and self.communication_thread.is_alive():
            return
            
        self.stop_monitoring.clear()
        self.communication_thread = threading.Thread(
            target=self._monitor_communication,
            daemon=True
        )
        self.communication_thread.start()
        
    def _monitor_communication(self):
        """Monitor printer communication in background thread."""
        self.logger.info("Communication monitoring started")
        
        while not self.stop_monitoring.is_set():
            try:
                with self.state_lock:
                    if self.mock_mode and self.mock_printer:
                        self.mock_printer.update_temperatures()
                        self.temperature_data = self.mock_printer.temperature
                        
                    elif self.serial_connection and self.serial_connection.is_open:
                        # Check for unrequested messages from printer
                        if self.serial_connection.in_waiting > 0:
                            message = self.serial_connection.readline().decode('utf-8').strip()
                            self._process_unrequested_message(message)
                
                # Use Event.wait() instead of time.sleep() for better shutdown
                if self.stop_monitoring.wait(timeout=1.0):
                    break  # Event was set, time to stop
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                if not self.stop_monitoring.is_set():
                    self.stop_monitoring.wait(timeout=5.0)  # Wait before retry
                    
        self.logger.info("Communication monitoring stopped")
        
    def _process_unrequested_message(self, message: str):
        """Process unrequested messages from printer."""
        if message.startswith('Error'):
            self.logger.warning(f"Printer error: {message}")
        elif 'T:' in message:  # Temperature report
            self.temperature_data = self._parse_temperature_response(message)
            
    def _parse_firmware_version(self, response: str) -> str:
        """Parse firmware version from M115 response."""
        match = re.search(r'FIRMWARE_NAME:([^\s]+)', response)
        return match.group(1) if match else "Unknown"
        
    def _parse_temperature_response(self, response: str) -> TemperatureData:
        """Parse temperature data from M105 response."""
        temp_data = TemperatureData()
        
        # Parse hotend temperature: T:200.0/210.0
        hotend_match = re.search(r'T:(\d+\.?\d*)/(\d+\.?\d*)', response)
        if hotend_match:
            temp_data.hotend_current = float(hotend_match.group(1))
            temp_data.hotend_target = float(hotend_match.group(2))
            
        # Parse bed temperature: B:60.0/65.0
        bed_match = re.search(r'B:(\d+\.?\d*)/(\d+\.?\d*)', response)
        if bed_match:
            temp_data.bed_current = float(bed_match.group(1))
            temp_data.bed_target = float(bed_match.group(2))
            
        return temp_data
        
    def set_mock_mode(self, enabled: bool) -> None:
        """Enable or disable mock mode."""
        if self.printer_status != PrinterStatus.DISCONNECTED:
            raise PrinterAgentError("Cannot change mock mode while connected")
            
        self.mock_mode = enabled
        
        if enabled and not self.mock_printer:
            mock_config = self.config.get('mock_printer', {})
            self.mock_printer = MockPrinter(mock_config)
            
        self.logger.info(f"Mock mode {'enabled' if enabled else 'disabled'}")
    
    # ===== G-CODE STREAMING CORE METHODS (Task 2.3.3) =====
    
    async def _start_gcode_streaming(self, gcode_file: str, job_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """Start streaming G-code file to printer."""
        try:
            # Validate printer connection (skip in mock mode)
            if not self.mock_mode and self.printer_status not in [PrinterStatus.CONNECTED, PrinterStatus.IDLE]:
                raise GCodeStreamingError("Printer not connected")
            
            # Read and prepare G-code
            gcode_lines = self._prepare_gcode_file(gcode_file)
            
            # Initialize progress tracking
            self.print_progress = PrintProgress(
                job_id=job_id,
                status=PrintJobStatus.STARTING,
                lines_total=len(gcode_lines),
                gcode_file=gcode_file,
                start_time=datetime.now()
            )

            if job_id in self.active_jobs:
                self.active_jobs[job_id].update({
                    'status': PrintJobStatus.STARTING.value,
                    'updated_at': datetime.now(),
                    'lines_total': len(gcode_lines),
                    'lines_sent': 0
                })
            else:
                self.active_jobs[job_id] = {
                    'job_id': job_id,
                    'gcode_file': gcode_file,
                    'status': PrintJobStatus.STARTING.value,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'lines_total': len(gcode_lines),
                    'lines_sent': 0,
                    'duration': 0.0
                }
            
            # Update streaming status
            self.streaming_status.is_streaming = True
            self.streaming_status.is_paused = False
            self.streaming_status.can_pause = True
            self.streaming_status.can_resume = False
            
            # Add progress callback if provided (thread-safe)
            if progress_callback:
                with self.progress_callbacks_lock:
                    self.progress_callbacks.append(progress_callback)
            
            # Start streaming thread
            self.streaming_thread = threading.Thread(
                target=self._stream_gcode_worker,
                args=(gcode_lines,),
                daemon=True
            )
            self.streaming_thread.start()
            
            self.logger.info(f"Started G-code streaming: {job_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start G-code streaming: {e}")
            self._reset_streaming_state()
            return False
    
    def _prepare_gcode_file(self, gcode_file: str) -> List[str]:
        """Read and prepare G-code file for streaming."""
        try:
            with open(gcode_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filter and prepare lines
            prepared_lines = []
            line_number = 1
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and comments (but keep layer info)
                if not line or (line.startswith(';') and not line.startswith(';LAYER')):
                    continue
                
                # Add line number and checksum if enabled
                if self.checksum_enabled:
                    line_with_number = f"N{line_number} {line}"
                    checksum = self._calculate_checksum(line_with_number)
                    prepared_lines.append(f"{line_with_number}*{checksum}")
                    line_number += 1
                else:
                    prepared_lines.append(line)
            
            self.logger.info(f"Prepared {len(prepared_lines)} G-code lines for streaming")
            return prepared_lines
            
        except Exception as e:
            raise GCodeStreamingError(f"Failed to prepare G-code file: {e}")
    
    def _calculate_checksum(self, line: str) -> int:
        """Calculate checksum for G-code line."""
        checksum = 0
        for char in line:
            checksum ^= ord(char)
        return checksum
    
    def _stream_gcode_worker(self, gcode_lines: List[str]):
        """Worker thread for streaming G-code lines with improved concurrency."""
        self.logger.info("G-code streaming worker started")
        
        try:
            with self.state_lock:
                self.print_progress.status = PrintJobStatus.PRINTING
                self.printer_status = PrinterStatus.PRINTING
            
            for i, line in enumerate(gcode_lines):
                # Check for stop requests using Event
                if self.streaming_stop_event.is_set():
                    break
                
                # Check streaming status with lock
                with self.state_lock:
                    if not self.streaming_status.is_streaming:
                        break
                
                # Handle pause with timeout
                while True:
                    with self.state_lock:
                        if not self.streaming_status.is_paused or not self.streaming_status.is_streaming:
                            break
                    # Use Event.wait() instead of sleep for better responsiveness
                    if self.streaming_stop_event.wait(timeout=0.1):
                        break
                
                # Final check after pause
                with self.state_lock:
                    if not self.streaming_status.is_streaming:
                        break
                
                try:
                    # Update current command safely
                    with self.state_lock:
                        self.print_progress.current_command = line
                    
                    # Send command with retry logic
                    success = self._send_gcode_line_sync(line)
                    
                    if success:
                        with self.state_lock:
                            self.print_progress.lines_sent = i + 1
                            
                            # Update layer tracking
                            if line.startswith(';LAYER'):
                                layer_match = re.search(r';LAYER:(\d+)', line)
                                if layer_match:
                                    self.print_progress.current_layer = int(layer_match.group(1))

                            job_id = self.print_progress.job_id
                            if job_id in self.active_jobs:
                                self.active_jobs[job_id].update({
                                    'lines_sent': self.print_progress.lines_sent,
                                    'updated_at': datetime.now()
                                })
                        
                        self._update_progress()
                    else:
                        self.logger.error(f"Failed to send G-code line: {line}")
                        
                except Exception as e:
                    self.logger.error(f"Error sending G-code line: {e}")
                    
                # Respect chunk size and timing
                if (i + 1) % self.chunk_size == 0:
                    if self.streaming_stop_event.wait(timeout=0.01):
                        break  # Stop immediately if requested
            
            # Check completion status safely
            with self.state_lock:
                if self.streaming_status.is_streaming and not self.streaming_status.is_paused:
                    self._complete_print_job()
                else:
                    self._cancel_print_job()
                
        except Exception as e:
            self.logger.error(f"G-code streaming worker error: {e}")
            self._fail_print_job(str(e))
        
        finally:
            self.logger.info("G-code streaming worker finished")
    
    def _send_gcode_line_sync(self, line: str) -> bool:
        """Send single G-code line synchronously."""
        try:
            if self.mock_mode and self.mock_printer and self.mock_printer.connected:
                response = self.mock_printer.send_command(line)
                return response.startswith('ok')
            elif self.mock_mode and self.mock_printer and not self.mock_printer.connected:
                # Auto-reconnect mock printer if disconnected
                self.mock_printer.connect()
                response = self.mock_printer.send_command(line)
                return response.startswith('ok')
            elif self.serial_connection and self.serial_connection.is_open:
                # Send line
                self.serial_connection.write(f"{line}\n".encode('utf-8'))
                self.serial_connection.flush()
                
                # Wait for acknowledgment
                start_time = time.time()
                while time.time() - start_time < self.ack_timeout:
                    if self.serial_connection.in_waiting > 0:
                        response = self.serial_connection.readline().decode('utf-8').strip()
                        if response.startswith('ok') or response.startswith('Error'):
                            return response.startswith('ok')
                    time.sleep(0.01)
                
                # Timeout occurred
                self.logger.warning(f"Timeout waiting for acknowledgment: {line}")
                return False
            else:
                # In mock mode without connection, simulate success
                if self.mock_mode:
                    self.logger.debug(f"Mock mode: simulating success for command: {line}")
                    return True
                else:
                    raise GCodeStreamingError("No active printer connection")
                
        except Exception as e:
            self.logger.error(f"Failed to send G-code line: {line} - Error: {e}")
            # In mock mode, don't fail completely
            if self.mock_mode:
                self.logger.debug("Mock mode: continuing despite error")
                return True
            return False
    
    def _update_progress(self):
        """Update progress calculations and notify callbacks."""
        if not self.print_progress:
            return
        
        # Calculate progress percentage
        if self.print_progress.lines_total > 0:
            self.print_progress.progress_percentage = (
                self.print_progress.lines_sent / self.print_progress.lines_total
            ) * 100
        
        # Calculate elapsed time
        if self.print_progress.start_time:
            total_elapsed = (datetime.now() - self.print_progress.start_time).total_seconds()
            
            # Subtract pause time if applicable
            if self.print_progress.pause_time and not self.streaming_status.is_paused:
                pause_duration = (self.print_progress.resume_time - self.print_progress.pause_time).total_seconds()
                total_elapsed -= pause_duration
            elif self.streaming_status.is_paused and self.print_progress.pause_time:
                pause_duration = (datetime.now() - self.print_progress.pause_time).total_seconds()
                total_elapsed -= pause_duration
            
            self.print_progress.elapsed_time = total_elapsed
        
        # Estimate remaining time
        if self.print_progress.progress_percentage > 0:
            estimated_total = self.print_progress.elapsed_time / (self.print_progress.progress_percentage / 100)
            self.print_progress.estimated_remaining = estimated_total - self.print_progress.elapsed_time
        
        # Notify callbacks
        self._notify_progress_callbacks()
    
    def _notify_progress_callbacks(self):
        """Notify all registered progress callbacks (thread-safe)."""
        with self.progress_callbacks_lock:
            if not self.progress_callbacks or not self.print_progress:
                return
            
            # Make a copy to avoid modification during iteration
            callbacks = self.progress_callbacks.copy()
        
        progress_data = self._get_progress_data()
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # Schedule async callback safely
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(callback(progress_data))
                    except RuntimeError:
                        # No event loop in current thread
                        self.logger.debug("No event loop available for async callback")
                else:
                    # Call sync callback
                    callback(progress_data)
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")
    
    def _get_progress_data(self) -> Dict[str, Any]:
        """Get current progress data."""
        if not self.print_progress:
            return {}
        
        return {
            'job_id': self.print_progress.job_id,
            'status': self.print_progress.status.value,
            'lines_total': self.print_progress.lines_total,
            'lines_sent': self.print_progress.lines_sent,
            'progress_percent': round(self.print_progress.progress_percentage, 2),
            'current_layer': self.print_progress.current_layer,
            'elapsed_time': round(self.print_progress.elapsed_time, 1),
            'estimated_remaining': round(self.print_progress.estimated_remaining, 1) if self.print_progress.estimated_remaining else 0,
            'current_command': self.print_progress.current_command,
            'gcode_file': self.print_progress.gcode_file,
            'start_time': self.print_progress.start_time.isoformat() if self.print_progress.start_time else None,
            'is_paused': self.streaming_status.is_paused
        }
    
    async def _pause_streaming(self) -> bool:
        """Pause G-code streaming."""
        try:
            if not self.streaming_status.can_pause:
                return False
            
            self.streaming_status.is_paused = True
            self.streaming_status.can_pause = False
            self.streaming_status.can_resume = True
            
            if self.print_progress:
                self.print_progress.status = PrintJobStatus.PAUSED
                self.print_progress.pause_time = datetime.now()
            
            self.printer_status = PrinterStatus.PAUSED
            
            # Send pause command to printer if connected
            try:
                if self.mock_mode and self.mock_printer and self.mock_printer.connected:
                    self.mock_printer.send_command("M25")  # Pause command
                elif self.serial_connection and self.serial_connection.is_open:
                    self.serial_connection.write("M25\n".encode('utf-8'))
                    self.serial_connection.flush()
            except Exception as e:
                self.logger.warning(f"Failed to send pause command to printer: {e}")
            
            self.logger.info("Print job paused")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pause streaming: {e}")
            return False
    
    async def _resume_streaming(self) -> bool:
        """Resume G-code streaming."""
        try:
            if not self.streaming_status.can_resume:
                return False
            
            self.streaming_status.is_paused = False
            self.streaming_status.can_pause = True
            self.streaming_status.can_resume = False
            
            if self.print_progress:
                self.print_progress.status = PrintJobStatus.PRINTING
                self.print_progress.resume_time = datetime.now()
            
            self.printer_status = PrinterStatus.PRINTING
            
            # Send resume command to printer if connected
            try:
                if self.mock_mode and self.mock_printer and self.mock_printer.connected:
                    self.mock_printer.send_command("M24")  # Resume command
                elif self.serial_connection and self.serial_connection.is_open:
                    self.serial_connection.write("M24\n".encode('utf-8'))
                    self.serial_connection.flush()
            except Exception as e:
                self.logger.warning(f"Failed to send resume command to printer: {e}")
            
            self.logger.info("Print job resumed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resume streaming: {e}")
            return False
    
    async def _emergency_stop(self) -> bool:
        """Emergency stop G-code streaming and printer."""
        try:
            # Stop streaming immediately
            self.streaming_status.is_streaming = False
            self.streaming_status.is_paused = False
            
            # Send emergency stop commands
            try:
                if self.mock_mode and self.mock_printer and self.mock_printer.connected:
                    self.mock_printer.send_command("M112")  # Emergency stop
                    self.mock_printer.send_command("M104 S0")  # Turn off hotend
                    self.mock_printer.send_command("M140 S0")  # Turn off bed
                elif self.serial_connection and self.serial_connection.is_open:
                    self.serial_connection.write("M112\n".encode('utf-8'))  # Emergency stop
                    self.serial_connection.flush()
                    self.serial_connection.write("M104 S0\n".encode('utf-8'))  # Turn off hotend
                    self.serial_connection.flush()
                    self.serial_connection.write("M140 S0\n".encode('utf-8'))  # Turn off bed
                    self.serial_connection.flush()
            except Exception as e:
                self.logger.warning(f"Failed to send emergency stop commands: {e}")
            
            # Update status
            if self.print_progress:
                self.print_progress.status = PrintJobStatus.CANCELLED
            
            self.printer_status = PrinterStatus.IDLE
            
            self._reset_streaming_state()
            
            self.logger.warning("Emergency stop executed")
            return True
            
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")
            return False
    
    def _complete_print_job(self):
        """Mark print job as completed."""
        duration = 0.0
        if self.print_progress:
            self.print_progress.status = PrintJobStatus.COMPLETED
            self.print_progress.progress_percentage = 100.0
            if self.print_progress.start_time:
                duration = (datetime.now() - self.print_progress.start_time).total_seconds()
            job_id = self.print_progress.job_id
            if job_id in self.active_jobs:
                self.active_jobs[job_id].update({
                    'status': PrintJobStatus.COMPLETED.value,
                    'updated_at': datetime.now(),
                    'lines_sent': self.print_progress.lines_sent,
                    'lines_total': self.print_progress.lines_total,
                    'duration': duration
                })
            
        self.printer_status = PrinterStatus.IDLE
        self.print_statistics['successful_prints'] += 1
        self.print_statistics['total_print_time'] += duration
        self._reset_streaming_state()
        
        self.logger.info(f"Print job completed: {self.print_progress.job_id if self.print_progress else 'unknown'}")
    
    def _cancel_print_job(self):
        """Mark print job as cancelled."""
        duration = 0.0
        if self.print_progress:
            self.print_progress.status = PrintJobStatus.CANCELLED
            if self.print_progress.start_time:
                duration = (datetime.now() - self.print_progress.start_time).total_seconds()
            job_id = self.print_progress.job_id
            if job_id in self.active_jobs:
                self.active_jobs[job_id].update({
                    'status': PrintJobStatus.CANCELLED.value,
                    'updated_at': datetime.now(),
                    'lines_sent': self.print_progress.lines_sent,
                    'lines_total': self.print_progress.lines_total,
                    'duration': duration
                })
            
        self.printer_status = PrinterStatus.IDLE
        self.print_statistics['cancelled_prints'] += 1
        self.print_statistics['total_print_time'] += duration
        self._reset_streaming_state()
        
        self.logger.info(f"Print job cancelled: {self.print_progress.job_id if self.print_progress else 'unknown'}")
    
    def _fail_print_job(self, error_message: str):
        """Mark print job as failed."""
        duration = 0.0
        if self.print_progress:
            self.print_progress.status = PrintJobStatus.FAILED
            if self.print_progress.start_time:
                duration = (datetime.now() - self.print_progress.start_time).total_seconds()
            job_id = self.print_progress.job_id
            if job_id in self.active_jobs:
                self.active_jobs[job_id].update({
                    'status': PrintJobStatus.FAILED.value,
                    'updated_at': datetime.now(),
                    'lines_sent': self.print_progress.lines_sent,
                    'lines_total': self.print_progress.lines_total,
                    'duration': duration,
                    'error_message': error_message
                })
            
        self.printer_status = PrinterStatus.ERROR
        self.print_statistics['failed_prints'] += 1
        self.print_statistics['total_print_time'] += duration
        self._reset_streaming_state()
        
        self.logger.error(f"Print job failed: {error_message}")
    
    def _reset_streaming_state(self):
        """Reset streaming state variables with proper thread cleanup."""
        # Signal threads to stop
        self.streaming_stop_event.set()
        
        with self.state_lock:
            self.streaming_status = StreamingStatus()
            
        # Clear callbacks safely
        with self.progress_callbacks_lock:
            self.progress_callbacks = []
        
        # Clean up streaming thread
        if (self.streaming_thread and 
            self.streaming_thread.is_alive() and 
            self.streaming_thread != threading.current_thread()):
            try:
                self.streaming_thread.join(timeout=3.0)
                if self.streaming_thread.is_alive():
                    self.logger.warning("Streaming thread did not stop gracefully")
            except Exception as e:
                self.logger.error(f"Error during streaming thread cleanup: {e}")
        
        self.streaming_thread = None
        self.streaming_stop_event.clear()  # Reset for next use
        
    def get_printer_capabilities(self) -> List[str]:
        """Get list of printer capabilities."""
        if self.printer_info:
            return self.printer_info.capabilities
        elif self.is_connected():
            # Return default capabilities when connected but printer_info is not available
            return ["heating", "movement", "temperature_reporting", "g_code_streaming"]
        elif self.mock_mode:
            # Return mock capabilities in mock mode
            return ["temperature_control", "movement_control", "gcode_execution", "status_monitoring"]
        return []
    
    async def emergency_stop(self) -> Dict[str, Any]:
        """
        Public method to perform emergency stop.
        
        Returns:
            Dict[str, Any]: Result with success status
        """
        success = await self._emergency_stop()
        return {
            'success': success,
            'message': 'Emergency stop executed' if success else 'Emergency stop failed'
        }
        
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.printer_status != PrinterStatus.DISCONNECTED:
            # Use direct sync method for cleanup
            self._cleanup_sync()
            
        self.logger.info("Printer Agent cleanup completed")
        
    def _cleanup_sync(self):
        """Synchronous cleanup method."""
        try:
            self.stop_monitoring.set()
            
            # Stop streaming if active
            if self.streaming_status.is_streaming:
                self.streaming_status.is_streaming = False
                if self.streaming_thread and self.streaming_thread.is_alive():
                    self.streaming_thread.join(timeout=2)
            
            if self.communication_thread and self.communication_thread.is_alive():
                self.communication_thread.join(timeout=2)
                
            if self.mock_mode and self.mock_printer:
                self.mock_printer.disconnect()
            elif self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
                
            self.printer_status = PrinterStatus.DISCONNECTED
            self.printer_info = None
            self.serial_port = None
            self._reset_streaming_state()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            
    async def discover_all_printers(self, include_emulated: bool = True) -> list:
        """Discover all available printers (real and emulated) - FIXED VERSION."""
        all_printers = []
        if ENHANCED_PRINTER_SUPPORT and self.multi_printer_detector:
            try:
                self.logger.info("Scanning for real 3D printers (FAST mode)...")
                
                # Use the fixed scanner with timeout protection
                # Try the enhanced scan first, fallback to basic scan
                try:
                    real_printers = await asyncio.wait_for(
                        self.multi_printer_detector.scan_for_printers_with_fallback(timeout=2.0),
                        timeout=10.0  # Hard timeout to prevent hanging
                    )
                except AttributeError:
                    # Fallback to basic scan if enhanced method not available
                    self.logger.info("Using basic scan method")
                    real_printers = await asyncio.wait_for(
                        self.multi_printer_detector.scan_for_printers(timeout=2.0),
                        timeout=10.0
                    )
                
                for printer in real_printers:
                    printer_info = {
                        'id': f"real_{printer['port'].replace('/', '_')}",
                        'name': printer['name'],
                        'type': 'real',
                        'port': printer['port'],
                        'firmware_type': printer.get('type', 'unknown'),
                        'capabilities': printer.get('capabilities', []),
                        'connection_settings': printer.get('connection_settings', {})
                    }
                    all_printers.append(printer_info)
                    self.logger.info(f"Found real printer: {printer['name']} on {printer['port']}")
                
                # Add emulated printers if requested
                if include_emulated and self.emulator_manager:
                    self.logger.info("Adding emulated printers...")
                    emulator_types = ['ender3', 'prusa_mk3s', 'marlin_generic', 'klipper']
                    
                    for emulator_type in emulator_types:
                        emulator = self.emulator_manager.get_emulator(emulator_type)
                        status = emulator.get_status()
                        
                        printer_info = {
                            'id': f"emulated_{emulator_type}",
                            'name': f"{status['name']} (Emulated)",
                            'type': 'emulated',
                            'port': f"emulated://{emulator_type}",
                            'firmware_type': emulator_type,
                            'capabilities': ['emulation', 'testing'],
                            'connection_settings': {'emulated': True}
                        }
                        all_printers.append(printer_info)
                        self.logger.info(f"Added emulated printer: {status['name']}")
                
                self.available_printers = all_printers
                return all_printers
                
            except asyncio.TimeoutError:
                self.logger.warning("Printer scan timed out - using emulated printers only")
            except Exception as e:
                self.logger.error(f"Error discovering printers: {e}")
        
        # Fallback: Only emulated printers
        if include_emulated and self.emulator_manager:
            self.logger.info("Using emulated printers only...")
            emulator_types = ['ender3', 'prusa_mk3s', 'marlin_generic', 'klipper']
            
            for emulator_type in emulator_types:
                emulator = self.emulator_manager.get_emulator(emulator_type)
                status = emulator.get_status()
                
                printer_info = {
                    'id': f"emulated_{emulator_type}",
                    'name': f"{status['name']} (Emulated)",
                    'type': 'emulated',
                    'port': f"emulated://{emulator_type}",
                    'firmware_type': emulator_type,
                    'capabilities': ['emulation', 'testing'],
                    'connection_settings': {'emulated': True}
                }
                all_printers.append(printer_info)
        else:
            # Final fallback: Mock printer
            all_printers.append({
                'id': 'mock',
                'name': 'Mock Printer',
                'type': 'mock',
                'port': 'mock',
                'firmware_type': 'mock',
                'capabilities': ['emulation'],
                'connection_settings': {'emulated': True}
            })
        
        self.available_printers = all_printers
        return all_printers
    
    async def shutdown(self):
        """Shutdown the printer agent and clean up all resources."""
        self.logger.info("Shutting down PrinterAgent...")
        
        try:
            # Stop monitoring and streaming
            self.stop_monitoring.set()
            self._reset_streaming_state()
            
            # Wait for communication thread to stop
            if (self.communication_thread and 
                self.communication_thread.is_alive() and 
                self.communication_thread != threading.current_thread()):
                try:
                    self.communication_thread.join(timeout=5.0)
                    if self.communication_thread.is_alive():
                        self.logger.warning("Communication thread did not stop gracefully")
                except Exception as e:
                    self.logger.error(f"Error stopping communication thread: {e}")
            
            # Disconnect from printers
            try:
                await self.disconnect()
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
            
            # Disconnect mock printer
            if self.mock_printer and self.mock_printer.connected:
                try:
                    self.mock_printer.disconnect()
                except Exception as e:
                    self.logger.error(f"Error disconnecting mock printer: {e}")
            
            self.logger.info("PrinterAgent shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during PrinterAgent shutdown: {e}")

async def connect_printer(port: Optional[str] = None, baudrate: int = 115200, 
                         mock_mode: bool = True) -> PrinterAgent:
    """Convenience function to connect to a printer."""
    agent = PrinterAgent("quick_connect", config={'mock_mode': mock_mode})
    
    task = {
        'operation': 'connect_printer',
        'specifications': {
            'serial_port': port,
            'baudrate': baudrate
        }
    }
    
    result = await agent.execute_task(task)
    if not result['success']:
        raise PrinterConnectionError(result.get('error_message', 'Connection failed'))
        
    return agent


def detect_printers() -> List[Dict[str, Any]]:
    """Convenience function to detect available printers."""
    agent = PrinterAgent("detector")
    return asyncio.run(agent._detect_printers())
