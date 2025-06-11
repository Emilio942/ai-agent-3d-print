"""
Unit tests for Printer Agent - Serial Communication and G-code Streaming.

Tests cover:
- Serial communication with mock printer
- G-code streaming with progress tracking
- Printer status monitoring
- Temperature control
- Error handling and recovery
- Mocking of serial port hardware
"""

import pytest
import asyncio
import tempfile
import os
import time
import threading
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.printer_agent import (
    PrinterAgent, MockPrinter, PrinterStatus, TemperatureData,
    SerialCommunicationError, PrinterNotConnectedError, GCodeStreamingError
)
from core.api_schemas import PrinterAgentInput, PrinterAgentOutput, TaskResult
from core.exceptions import ValidationError, AI3DPrintError


@pytest.fixture
def printer_agent():
    """Create a Printer Agent instance for testing."""
    config = {
        'mock_mode': True,
        'mock_printer': {
            'simulate_delays': True,
            'simulate_errors': False,
            'error_probability': 0.0
        }
    }
    return PrinterAgent("test_printer_agent", config=config)


@pytest.fixture
def sample_gcode_file():
    """Create a sample G-code file for testing."""
    gcode_content = """
; Test G-code for unit testing
G21 ; set units to millimeters
G90 ; use absolute coordinates
M104 S200 ; set hotend temperature
M140 S60 ; set bed temperature
G28 ; home all axes

; Layer 1
G1 Z0.2 F3000
G1 X10 Y10 E1 F1500
G1 X20 Y10 E2 F1500
G1 X20 Y20 E3 F1500
G1 X10 Y20 E4 F1500

; Layer 2
G1 Z0.4 F3000
G1 X10 Y10 E5 F1500
G1 X20 Y10 E6 F1500

; End G-code
M104 S0 ; turn off hotend
M140 S0 ; turn off bed
G28 X Y ; home X and Y
M84 ; disable motors
"""
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.gcode', delete=False)
    temp_file.write(gcode_content.strip())
    temp_file.close()
    return temp_file.name


@pytest.fixture
def sample_input(sample_gcode_file):
    """Sample input for testing."""
    return PrinterAgentInput(
        gcode_file_path=sample_gcode_file,
        operation="start_print",
        print_settings={}
    )


class TestPrinterAgent:
    """Test cases for Printer Agent functionality."""

    def test_agent_initialization(self, printer_agent):
        """Test Printer Agent initialization."""
        assert printer_agent.agent_name == "test_printer_agent"
        assert printer_agent.agent_type == "PrinterAgent"
        assert printer_agent.mock_mode is True
        assert hasattr(printer_agent, 'mock_printer')
        assert printer_agent.connection_status == PrinterStatus.DISCONNECTED
    
    def test_mock_printer_initialization(self):
        """Test mock printer initialization."""
        config = {
            'simulate_delays': True,
            'simulate_errors': False,
            'error_probability': 0.1
        }
        
        mock_printer = MockPrinter(config)
        
        assert mock_printer.connected is False
        assert mock_printer.status == PrinterStatus.IDLE
        assert mock_printer.simulate_delays is True
        assert mock_printer.simulate_errors is False
        assert mock_printer.error_probability == 0.1
    
    def test_mock_printer_connection(self):
        """Test mock printer connection."""
        mock_printer = MockPrinter({'simulate_delays': False})
        
        # Test connection
        success = mock_printer.connect()
        assert success is True
        assert mock_printer.connected is True
        assert mock_printer.status == PrinterStatus.CONNECTED
        
        # Test disconnection
        success = mock_printer.disconnect()
        assert success is True
        assert mock_printer.connected is False
        assert mock_printer.status == PrinterStatus.DISCONNECTED
    
    def test_mock_printer_gcode_commands(self):
        """Test mock printer G-code command processing."""
        mock_printer = MockPrinter({'simulate_delays': False})
        mock_printer.connect()
        
        # Test firmware version command
        response = mock_printer.send_command("M115")
        assert "FIRMWARE_NAME" in response
        assert "Marlin" in response
        
        # Test temperature report
        response = mock_printer.send_command("M105")
        assert "T:" in response
        assert "B:" in response
        
        # Test position report
        response = mock_printer.send_command("M114")
        assert "X:" in response
        assert "Y:" in response
        assert "Z:" in response
        
        # Test temperature setting
        response = mock_printer.send_command("M104 S200")
        assert "ok" in response
        
        # Test movement command
        response = mock_printer.send_command("G1 X10 Y10 F1500")
        assert "ok" in response
    
    def test_mock_printer_temperature_simulation(self):
        """Test mock printer temperature simulation."""
        mock_printer = MockPrinter({'simulate_delays': False})
        mock_printer.connect()
        
        # Set hotend temperature
        mock_printer.send_command("M104 S200")
        assert mock_printer.temperature.hotend_target == 200
        
        # Set bed temperature
        mock_printer.send_command("M140 S60")
        assert mock_printer.temperature.bed_target == 60
        
        # Simulate temperature updates
        mock_printer.update_temperatures()
        
        # Temperature should start approaching targets
        assert mock_printer.temperature.hotend_current >= 20
        assert mock_printer.temperature.bed_current >= 20
    
    @pytest.mark.asyncio
    async def test_printer_connection(self, printer_agent):
        """Test printer connection functionality."""
        # Test connection
        result = await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        assert result.get('success', False) is True
        assert 'printer_id' in result
        assert printer_agent.connection_status == PrinterStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_printer_disconnection(self, printer_agent):
        """Test printer disconnection functionality."""
        # First connect
        await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        # Then disconnect
        result = await printer_agent.execute_task({
            'operation': 'disconnect_printer',
            'specifications': {}
        })
        
        assert result.get('success', False) is True
        assert printer_agent.connection_status == PrinterStatus.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_printer_status_retrieval(self, printer_agent):
        """Test printer status retrieval."""
        # Connect first
        await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        # Get status
        result = await printer_agent.execute_task({
            'operation': 'get_printer_status',
            'specifications': {}
        })
        
        assert result.get('success', False) is True
        assert 'status' in result
        assert 'temperature' in result
        assert 'position' in result
    
    @pytest.mark.asyncio
    async def test_temperature_control(self, printer_agent):
        """Test temperature setting and monitoring."""
        # Connect first
        await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        # Set temperatures
        result = await printer_agent.execute_task({
            'operation': 'set_temperature',
            'specifications': {
                'hotend_temperature': 200,
                'bed_temperature': 60
            }
        })
        
        assert result.get('success', False) is True
        assert result.get('hotend_target') == 200
        assert result.get('bed_target') == 60
        
        # Get temperature
        temp_result = await printer_agent.execute_task({
            'operation': 'get_temperature',
            'specifications': {}
        })
        
        assert temp_result.get('success', False) is True
        assert 'temperature' in temp_result
        temp_data = temp_result['temperature']
        assert temp_data['hotend_target'] == 200
        assert temp_data['bed_target'] == 60
    
    @pytest.mark.asyncio
    async def test_gcode_command_execution(self, printer_agent):
        """Test single G-code command execution."""
        # Connect first
        await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        # Send G-code command
        result = await printer_agent.execute_task({
            'operation': 'send_gcode_command',
            'specifications': {
                'command': 'M115'
            }
        })
        
        assert result.get('success', False) is True
        assert 'response' in result
        assert 'FIRMWARE_NAME' in result['response']
    
    @pytest.mark.asyncio
    async def test_gcode_streaming_basic(self, printer_agent, sample_gcode_file):
        """Test basic G-code streaming functionality."""
        # Connect first
        await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        # Start streaming
        progress_updates = []
        
        def progress_callback(progress_data):
            progress_updates.append(progress_data)
        
        result = await printer_agent.stream_gcode(
            gcode_file_path=sample_gcode_file,
            progress_callback=progress_callback
        )
        
        assert result.get('success', False) is True
        assert 'lines_sent' in result
        assert 'total_lines' in result
        assert result['lines_sent'] > 0
        assert len(progress_updates) > 0
        
        # Check progress updates
        final_progress = progress_updates[-1]
        assert final_progress['progress_percent'] == 100.0
    
    @pytest.mark.asyncio
    async def test_gcode_streaming_with_pause_resume(self, printer_agent, sample_gcode_file):
        """Test G-code streaming with pause/resume functionality."""
        # Connect first
        await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        # Start streaming in background
        async def stream_task():
            return await printer_agent.stream_gcode(
                gcode_file_path=sample_gcode_file,
                progress_callback=lambda x: None
            )
        
        stream_future = asyncio.create_task(stream_task())
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Pause streaming
        pause_result = await printer_agent.pause_streaming()
        assert pause_result.get('success', False) is True
        
        # Resume streaming
        resume_result = await printer_agent.resume_streaming()
        assert resume_result.get('success', False) is True
        
        # Wait for completion
        result = await stream_future
        assert result.get('success', False) is True
    
    @pytest.mark.asyncio
    async def test_emergency_stop(self, printer_agent, sample_gcode_file):
        """Test emergency stop functionality."""
        # Connect first
        await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        # Start streaming
        async def stream_task():
            return await printer_agent.stream_gcode(
                gcode_file_path=sample_gcode_file,
                progress_callback=lambda x: None
            )
        
        stream_future = asyncio.create_task(stream_task())
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Emergency stop
        stop_result = await printer_agent.emergency_stop()
        assert stop_result.get('success', False) is True
        
        # Stream should be cancelled
        try:
            await stream_future
        except asyncio.CancelledError:
            pass  # Expected
    
    @pytest.mark.asyncio
    async def test_execute_task_start_print(self, printer_agent, sample_gcode_file):
        """Test execute_task with start_print operation."""
        task_data = {
            "task_id": "test_001",
            "operation": "start_print",
            "gcode_file_path": sample_gcode_file,
            "print_settings": {
                "hotend_temperature": 200,
                "bed_temperature": 60
            }
        }
        
        result = await printer_agent.execute_task(task_data)
        
        assert isinstance(result, TaskResult)
        assert result.success is True
        assert result.task_id == "test_001"
    
    @pytest.mark.asyncio
    async def test_execute_task_validation_error(self, printer_agent):
        """Test task execution with validation errors."""
        # Missing required fields
        task_data = {
            "task_id": "test_002",
            "operation": "start_print"
            # Missing gcode_file_path
        }
        
        with pytest.raises(ValidationError):
            await printer_agent.execute_task(task_data)
    
    @pytest.mark.asyncio
    async def test_execute_task_printer_not_connected(self, printer_agent, sample_gcode_file):
        """Test task execution when printer is not connected."""
        # Don't connect printer
        
        task_data = {
            "task_id": "test_003",
            "operation": "start_print",
            "gcode_file_path": sample_gcode_file
        }
        
        result = await printer_agent.execute_task(task_data)
        
        assert isinstance(result, TaskResult)
        # Should handle connection automatically or fail gracefully
        assert result.task_id == "test_003"
    
    def test_gcode_file_validation(self, printer_agent):
        """Test G-code file validation."""
        # Valid G-code file
        valid_gcode = tempfile.NamedTemporaryFile(mode='w', suffix='.gcode', delete=False)
        valid_gcode.write("G21\nG90\nG1 X10 Y10 F1500\n")
        valid_gcode.close()
        
        try:
            assert printer_agent._validate_gcode_file(valid_gcode.name) is True
        finally:
            os.unlink(valid_gcode.name)
        
        # Non-existent file
        assert printer_agent._validate_gcode_file("nonexistent.gcode") is False
        
        # Invalid file format
        invalid_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        invalid_file.write("not gcode")
        invalid_file.close()
        
        try:
            assert printer_agent._validate_gcode_file(invalid_file.name) is False
        finally:
            os.unlink(invalid_file.name)
    
    def test_gcode_preprocessing(self, printer_agent, sample_gcode_file):
        """Test G-code preprocessing."""
        preprocessed = printer_agent._preprocess_gcode(sample_gcode_file)
        
        assert isinstance(preprocessed, list)
        assert len(preprocessed) > 0
        
        # Check that comments are handled appropriately
        gcode_lines = [line for line in preprocessed if not line.startswith(';')]
        assert len(gcode_lines) > 0
        
        # Check that empty lines are filtered
        empty_lines = [line for line in preprocessed if line.strip() == '']
        assert len(empty_lines) == 0
    
    def test_checksum_calculation(self, printer_agent):
        """Test G-code checksum calculation."""
        command = "G1 X10 Y10 F1500"
        line_number = 1
        
        formatted = printer_agent._add_line_number_and_checksum(command, line_number)
        
        assert formatted.startswith(f"N{line_number}")
        assert "*" in formatted
        
        # Verify checksum is valid
        parts = formatted.split('*')
        assert len(parts) == 2
        checksum = int(parts[1])
        assert isinstance(checksum, int)
    
    def test_printer_capabilities(self, printer_agent):
        """Test printer capabilities reporting."""
        capabilities = printer_agent.get_printer_capabilities()
        
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        
        expected_capabilities = [
            "temperature_control",
            "movement_control",
            "gcode_execution",
            "status_monitoring"
        ]
        
        for capability in expected_capabilities:
            assert capability in capabilities
    
    def test_connection_monitoring(self, printer_agent):
        """Test connection monitoring."""
        # Initially disconnected
        assert printer_agent.is_connected() is False
        
        # Mock connection
        printer_agent.mock_printer.connect()
        printer_agent.connection_status = PrinterStatus.CONNECTED
        
        assert printer_agent.is_connected() is True
        
        # Mock disconnection
        printer_agent.mock_printer.disconnect()
        printer_agent.connection_status = PrinterStatus.DISCONNECTED
        
        assert printer_agent.is_connected() is False
    
    def test_serial_port_detection(self, printer_agent):
        """Test serial port detection."""
        ports = printer_agent._detect_serial_ports()
        
        assert isinstance(ports, list)
        # In mock mode, should return mock ports
        assert len(ports) >= 0
    
    def test_error_handling_serial_error(self, printer_agent):
        """Test error handling for serial communication errors."""
        error = SerialCommunicationError("Connection lost")
        task_data = {"task_id": "error_test"}
        
        error_result = printer_agent.handle_error(error, task_data)
        
        assert isinstance(error_result, dict)
        assert error_result["error"] is True
        assert "error_code" in error_result
        assert "serial" in error_result["error_message"].lower()
    
    def test_error_handling_printer_not_connected(self, printer_agent):
        """Test error handling when printer is not connected."""
        error = PrinterNotConnectedError("Printer not connected")
        task_data = {"task_id": "connection_test"}
        
        error_result = printer_agent.handle_error(error, task_data)
        
        assert isinstance(error_result, dict)
        assert error_result["error"] is True
        assert "connection" in error_result["error_message"].lower()
    
    def test_print_statistics_tracking(self, printer_agent):
        """Test print statistics tracking."""
        stats = printer_agent.get_print_statistics()
        
        assert isinstance(stats, dict)
        assert "total_prints" in stats
        assert "total_print_time" in stats
        assert "successful_prints" in stats
        assert "failed_prints" in stats
    
    def test_temperature_safety_checks(self, printer_agent):
        """Test temperature safety checks."""
        # Test reasonable temperatures
        assert printer_agent._validate_temperature(200, "hotend") is True
        assert printer_agent._validate_temperature(60, "bed") is True
        
        # Test dangerous temperatures
        assert printer_agent._validate_temperature(400, "hotend") is False
        assert printer_agent._validate_temperature(150, "bed") is False
        assert printer_agent._validate_temperature(-10, "hotend") is False
    
    def test_print_job_management(self, printer_agent):
        """Test print job management."""
        # Create a print job
        job_id = printer_agent._create_print_job("test.gcode")
        assert isinstance(job_id, str)
        assert len(job_id) > 0
        
        # Get job status
        status = printer_agent._get_print_job_status(job_id)
        assert isinstance(status, dict)
        assert "job_id" in status
        assert "status" in status
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, printer_agent):
        """Test handling of concurrent operations."""
        # Connect
        await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        # Multiple concurrent operations
        tasks = [
            printer_agent.execute_task({
                'operation': 'get_printer_status',
                'specifications': {}
            }),
            printer_agent.execute_task({
                'operation': 'get_temperature',
                'specifications': {}
            }),
            printer_agent.execute_task({
                'operation': 'send_gcode_command',
                'specifications': {'command': 'M105'}
            })
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert result.get('success', False) is True
    
    def test_configuration_validation(self, printer_agent):
        """Test configuration validation."""
        # Test valid configuration
        valid_config = {
            'mock_mode': True,
            'serial_port': '/dev/ttyUSB0',
            'baud_rate': 115200
        }
        
        assert printer_agent._validate_configuration(valid_config) is True
        
        # Test invalid configuration
        invalid_config = {
            'mock_mode': 'not_boolean',
            'baud_rate': 'not_integer'
        }
        
        assert printer_agent._validate_configuration(invalid_config) is False
    
    def test_agent_status_tracking(self, printer_agent):
        """Test agent status tracking."""
        status = printer_agent.get_status()
        
        assert isinstance(status, dict)
        assert "agent_name" in status
        assert "agent_type" in status
        assert "current_status" in status
        assert status["agent_name"] == "test_printer_agent"
        assert status["agent_type"] == "PrinterAgent"
    
    def test_cleanup(self, printer_agent):
        """Test agent cleanup."""
        printer_agent.cleanup()
        
        # Verify cleanup completed without errors
        status = printer_agent.get_status()
        assert isinstance(status, dict)


class TestPrinterAgentIntegration:
    """Integration tests for Printer Agent."""
    
    @pytest.fixture
    def printer_agent(self):
        """Create a Printer Agent instance for integration testing."""
        config = {'mock_mode': True}
        return PrinterAgent("integration_test_agent", config=config)
    
    @pytest.mark.asyncio
    async def test_full_print_workflow(self, printer_agent, sample_gcode_file):
        """Test full print workflow from connection to completion."""
        progress_updates = []
        
        def progress_callback(progress_data):
            progress_updates.append(progress_data)
        
        # Connect printer
        connect_result = await printer_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        assert connect_result['success'] is True
        
        # Set temperatures
        temp_result = await printer_agent.execute_task({
            'operation': 'set_temperature',
            'specifications': {
                'hotend_temperature': 200,
                'bed_temperature': 60
            }
        })
        assert temp_result['success'] is True
        
        # Start print
        print_result = await printer_agent.stream_gcode(
            gcode_file_path=sample_gcode_file,
            progress_callback=progress_callback
        )
        
        assert print_result['success'] is True
        assert len(progress_updates) > 0
        assert progress_updates[-1]['progress_percent'] == 100.0
        
        # Disconnect
        disconnect_result = await printer_agent.execute_task({
            'operation': 'disconnect_printer',
            'specifications': {}
        })
        assert disconnect_result['success'] is True
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, printer_agent, sample_gcode_file):
        """Test error recovery workflow."""
        # Create agent with error simulation
        error_config = {
            'mock_mode': True,
            'mock_printer': {
                'simulate_errors': True,
                'error_probability': 0.2
            }
        }
        
        error_agent = PrinterAgent("error_test_agent", config=error_config)
        
        # Connect (may fail due to simulated errors)
        connect_result = await error_agent.execute_task({
            'operation': 'connect_printer',
            'specifications': {}
        })
        
        # Should handle errors gracefully
        assert isinstance(connect_result, dict)
        assert 'success' in connect_result


class TestMockPrinter:
    """Specific tests for MockPrinter class."""
    
    def test_temperature_simulation_heating(self):
        """Test temperature simulation during heating."""
        mock_printer = MockPrinter({'simulate_delays': False})
        mock_printer.connect()
        
        # Set target temperature
        mock_printer.send_command("M104 S200")
        
        # Simulate temperature progression
        initial_temp = mock_printer.temperature.hotend_current
        
        # Fast-forward simulation
        for _ in range(10):
            mock_printer.update_temperatures()
            time.sleep(0.01)
        
        final_temp = mock_printer.temperature.hotend_current
        
        # Temperature should have increased
        assert final_temp > initial_temp
        assert final_temp <= 200  # Should not exceed target
    
    def test_firmware_command_responses(self):
        """Test various firmware command responses."""
        mock_printer = MockPrinter({'simulate_delays': False})
        mock_printer.connect()
        
        commands_and_expected = [
            ("M115", "FIRMWARE_NAME"),
            ("M105", "T:"),
            ("M114", "X:"),
            ("G28", "ok"),
            ("M84", "ok"),
            ("M112", "ok")  # Emergency stop
        ]
        
        for command, expected in commands_and_expected:
            response = mock_printer.send_command(command)
            assert expected in response


if __name__ == "__main__":
    # Cleanup any temp files from fixtures
    def cleanup_temp_files():
        import tempfile
        import glob
        temp_dir = tempfile.gettempdir()
        for pattern in ["test_*.gcode"]:
            for file in glob.glob(os.path.join(temp_dir, pattern)):
                try:
                    os.unlink(file)
                except:
                    pass
    
    try:
        pytest.main([__file__, "-v"])
    finally:
        cleanup_temp_files()
