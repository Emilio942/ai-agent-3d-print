#!/usr/bin/env python3
"""
Printer Emulator Module for AI Agent 3D Print System

This module provides printer emulation for testing and development purposes.
"""

import time
import threading
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class EmulatedPrinterType(Enum):
    """Types of emulated printers."""
    ENDER3 = "ender3"
    PRUSA_MK3S = "prusa_mk3s"
    MARLIN_GENERIC = "marlin_generic"
    KLIPPER = "klipper"


@dataclass
class PrinterState:
    """Current state of the emulated printer."""
    hotend_temp: float = 25.0
    bed_temp: float = 25.0
    hotend_target: float = 0.0
    bed_target: float = 0.0
    x_pos: float = 0.0
    y_pos: float = 0.0
    z_pos: float = 0.0
    e_pos: float = 0.0
    fan_speed: int = 0
    is_homed: bool = False
    is_printing: bool = False
    print_progress: float = 0.0


class PrinterEmulator:
    """Emulates a 3D printer for testing purposes."""

    def __init__(self, printer_type: EmulatedPrinterType = EmulatedPrinterType.ENDER3):
        """Initialize the printer emulator."""
        self.printer_type = printer_type
        self.state = PrinterState()
        self.is_connected = False
        self.command_responses = self._init_responses()
        self.heating_thread = None
        logger.info(f"PrinterEmulator initialized as {printer_type.value}")

    def _init_responses(self) -> Dict[str, str]:
        """Initialize command responses based on printer type."""
        if self.printer_type == EmulatedPrinterType.ENDER3:
            return {
                "M115": "FIRMWARE_NAME:Marlin 1.1.9 (Github) SOURCE_CODE_URL:https://github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:Ender-3 EXTRUDER_COUNT:1 UUID:cede2a2f-41a2-4748-9b12-c55c62f367ff",
                "default": "ok",
            }
        elif self.printer_type == EmulatedPrinterType.PRUSA_MK3S:
            return {
                "M115": "FIRMWARE_NAME:Prusa-Firmware 3.11.0 based on Marlin FIRMWARE_URL:https://github.com/prusa3d/Prusa-Firmware PROTOCOL_VERSION:1.0 MACHINE_TYPE:Prusa i3 MK3S EXTRUDER_COUNT:1",
                "default": "ok",
            }
        elif self.printer_type == EmulatedPrinterType.KLIPPER:
            return {
                "M115": "// Klipper state: Ready\n// MCU config\nok",
                "default": "ok",
            }
        else:
            return {
                "M115": "FIRMWARE_NAME:Marlin 2.0.0 SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:Generic EXTRUDER_COUNT:1",
                "default": "ok",
            }

    def connect(self) -> bool:
        """Connect to the emulated printer."""
        try:
            self.is_connected = True
            self._start_heating_simulation()
            logger.info(f"Connected to emulated {self.printer_type.value}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to emulated printer: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the emulated printer."""
        try:
            self.is_connected = False
            self._stop_heating_simulation()
            logger.info(f"Disconnected from emulated {self.printer_type.value}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from emulated printer: {e}")
            return False

    def send_command(self, command: str) -> str:
        """Send a command to the emulated printer."""
        if not self.is_connected:
            return "error: not connected"

        try:
            command = command.strip().upper()

            # Handle specific commands
            if command == "M115":
                return self.command_responses.get("M115", "ok")

            elif command == "M105":  # Temperature report
                return (
                    f"ok T:{self.state.hotend_temp:.1f} /{self.state.hotend_target:.1f} "
                    f"B:{self.state.bed_temp:.1f} /{self.state.bed_target:.1f}"
                )

            elif command == "M114":  # Position report
                return (
                    f"ok X:{self.state.x_pos:.2f} Y:{self.state.y_pos:.2f} "
                    f"Z:{self.state.z_pos:.2f} E:{self.state.e_pos:.2f}"
                )

            elif command.startswith("M104"):  # Set hotend temperature
                try:
                    temp = float(command.split("S")[1])
                    self.state.hotend_target = temp
                    return "ok"
                except Exception:
                    return "error: invalid temperature"

            elif command.startswith("M140"):  # Set bed temperature
                try:
                    temp = float(command.split("S")[1])
                    self.state.bed_target = temp
                    return "ok"
                except Exception:
                    return "error: invalid temperature"

            elif command == "M106":  # Fan on
                self.state.fan_speed = 255
                return "ok"

            elif command == "M107":  # Fan off
                self.state.fan_speed = 0
                return "ok"

            elif command.startswith("M106"):  # Fan speed
                try:
                    speed = int(command.split("S")[1])
                    self.state.fan_speed = min(255, max(0, speed))
                    return "ok"
                except Exception:
                    return "error: invalid fan speed"

            elif command == "G28":  # Home
                self.state.x_pos = 0.0
                self.state.y_pos = 0.0
                self.state.z_pos = 0.0
                self.state.is_homed = True
                return "ok"

            elif command.startswith("G0") or command.startswith("G1"):  # Move
                self._parse_move_command(command)
                return "ok"

            elif command == "G21":  # Set units to millimeters
                return "ok"

            elif command == "G90":  # Absolute positioning
                return "ok"

            elif command == "G91":  # Relative positioning
                return "ok"

            elif command == "G92":  # Set position
                return "ok"

            elif command == "M84":  # Disable steppers
                return "ok"

            else:
                return self.command_responses.get("default", "ok")

        except Exception as e:
            logger.error(f"Error processing command '{command}': {e}")
            return f"error: {str(e)}"

    def process_command(self, command: str) -> str:
        """Backward-compatible alias for :meth:`send_command`."""
        return self.send_command(command)

    def _parse_move_command(self, command: str):
        """Parse and simulate a move command."""
        try:
            parts = command.split()
            for part in parts[1:]:  # Skip G0/G1
                if part.startswith("X"):
                    self.state.x_pos = float(part[1:])
                elif part.startswith("Y"):
                    self.state.y_pos = float(part[1:])
                elif part.startswith("Z"):
                    self.state.z_pos = float(part[1:])
                elif part.startswith("E"):
                    self.state.e_pos = float(part[1:])
        except Exception as e:
            logger.warning(f"Error parsing move command '{command}': {e}")

    def _start_heating_simulation(self):
        """Start the heating simulation thread."""
        if self.heating_thread and self.heating_thread.is_alive():
            return

        self.heating_thread = threading.Thread(target=self._heating_loop, daemon=True)
        self.heating_thread.start()

    def _stop_heating_simulation(self):
        """Stop the heating simulation."""
        # Thread will stop automatically when is_connected becomes False
        pass

    def _heating_loop(self):
        """Simulate heating/cooling behavior."""
        while self.is_connected:
            try:
                # Simulate hotend heating/cooling
                if self.state.hotend_temp < self.state.hotend_target:
                    self.state.hotend_temp = min(
                        self.state.hotend_target, self.state.hotend_temp + 2.0
                    )
                elif self.state.hotend_temp > self.state.hotend_target:
                    self.state.hotend_temp = max(
                        self.state.hotend_target, self.state.hotend_temp - 1.0
                    )

                # Simulate bed heating/cooling (slower)
                if self.state.bed_temp < self.state.bed_target:
                    self.state.bed_temp = min(
                        self.state.bed_target, self.state.bed_temp + 1.0
                    )
                elif self.state.bed_temp > self.state.bed_target:
                    self.state.bed_temp = max(
                        self.state.bed_target, self.state.bed_temp - 0.5
                    )

                # Ambient cooling when no target set
                if self.state.hotend_target == 0 and self.state.hotend_temp > 25:
                    self.state.hotend_temp = max(25, self.state.hotend_temp - 3.0)
                if self.state.bed_target == 0 and self.state.bed_temp > 25:
                    self.state.bed_temp = max(25, self.state.bed_temp - 1.0)

                time.sleep(1.0)

            except Exception as e:
                logger.error(f"Error in heating simulation: {e}")
                break

    def get_status(self) -> Dict[str, Any]:
        """Get the current printer status."""
        return {
            "name": f"{self.printer_type.value.replace('_', ' ').title()}",
            "connected": self.is_connected,
            "type": self.printer_type.value,
            "state": {
                "hotend_temp": self.state.hotend_temp,
                "bed_temp": self.state.bed_temp,
                "hotend_target": self.state.hotend_target,
                "bed_target": self.state.bed_target,
                "position": {
                    "x": self.state.x_pos,
                    "y": self.state.y_pos,
                    "z": self.state.z_pos,
                    "e": self.state.e_pos,
                },
                "fan_speed": self.state.fan_speed,
                "is_homed": self.state.is_homed,
                "is_printing": self.state.is_printing,
                "print_progress": self.state.print_progress,
            },
        }


class PrinterEmulatorManager:
    """Manages multiple printer emulators."""

    def __init__(self):
        """Initialize the emulator manager."""
        self.emulators: Dict[str, PrinterEmulator] = {}
        logger.info("PrinterEmulatorManager initialized")

    def create_emulator(self, name: str, printer_type: EmulatedPrinterType) -> PrinterEmulator:
        """Create a new printer emulator."""
        emulator = PrinterEmulator(printer_type)
        self.emulators[name] = emulator
        logger.info(f"Created emulator '{name}' of type {printer_type.value}")
        return emulator

    def get_emulator(self, name: str) -> Optional[PrinterEmulator]:
        """Get an emulator by name."""
        if name not in self.emulators:
            type_map = {
                "ender3": EmulatedPrinterType.ENDER3,
                "prusa_mk3s": EmulatedPrinterType.PRUSA_MK3S,
                "marlin_generic": EmulatedPrinterType.MARLIN_GENERIC,
                "klipper": EmulatedPrinterType.KLIPPER,
            }

            printer_type = type_map.get(name)
            if printer_type:
                return self.create_emulator(name, printer_type)
            return None

        return self.emulators[name]

    def list_emulators(self) -> List[str]:
        """List all emulator names."""
        return list(self.emulators.keys())

    def remove_emulator(self, name: str) -> bool:
        """Remove an emulator."""
        if name in self.emulators:
            emulator = self.emulators[name]
            if emulator.is_connected:
                emulator.disconnect()
            del self.emulators[name]
            logger.info(f"Removed emulator '{name}'")
            return True
        return False

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all emulators."""
        return {name: emulator.get_status() for name, emulator in self.emulators.items()}


# Test function
def test_printer_emulator():
    """Test the printer emulator functionality."""
    print("🧪 Testing Printer Emulator")
    print("=" * 40)

    # Create emulator manager
    manager = PrinterEmulatorManager()

    # Create different types of emulators
    ender3 = manager.create_emulator("ender3", EmulatedPrinterType.ENDER3)
    prusa = manager.create_emulator("prusa", EmulatedPrinterType.PRUSA_MK3S)

    print(f"Created emulators: {manager.list_emulators()}")

    # Test Ender 3 emulator
    print("\n🖨️ Testing Ender 3 Emulator:")
    ender3.connect()

    print(f"M115: {ender3.send_command('M115')}")
    print(f"M105: {ender3.send_command('M105')}")
    print(f"M114: {ender3.send_command('M114')}")

    # Set temperatures
    print(f"M104 S200: {ender3.send_command('M104 S200')}")
    print(f"M140 S60: {ender3.send_command('M140 S60')}")

    # Wait a bit for heating simulation
    time.sleep(2)
    print(f"M105 after heating: {ender3.send_command('M105')}")

    # Test movement
    print(f"G28: {ender3.send_command('G28')}")
    print(f"G1 X10 Y20 Z5: {ender3.send_command('G1 X10 Y20 Z5')}")
    print(f"M114: {ender3.send_command('M114')}")

    ender3.disconnect()

    print("\n✅ Printer emulator test completed!")


if __name__ == "__main__":
    test_printer_emulator()
