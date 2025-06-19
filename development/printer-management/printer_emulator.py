#!/usr/bin/env python3
"""
3D Printer Emulator - Simulates different printer types for testing
Emulates Marlin, Prusa, Ender 3, and Klipper firmware responses
"""

import asyncio
import time
import random
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class EmulatedPrinterType(Enum):
    """Types of emulated printers."""
    ENDER3 = "ender3"
    PRUSA_MK3S = "prusa_mk3s" 
    MARLIN_GENERIC = "marlin_generic"
    KLIPPER = "klipper"

@dataclass
class PrinterState:
    """Current state of emulated printer."""
    hotend_temp: float = 25.0
    hotend_target: float = 0.0
    bed_temp: float = 25.0
    bed_target: float = 0.0
    position: Dict[str, float] = None
    is_homed: bool = False
    is_printing: bool = False
    fan_speed: int = 0
    
    def __post_init__(self):
        if self.position is None:
            self.position = {"X": 0.0, "Y": 0.0, "Z": 0.0, "E": 0.0}

class PrinterEmulator:
    """Emulates different 3D printer firmware responses."""
    
    def __init__(self, printer_type: EmulatedPrinterType):
        self.type = printer_type
        self.state = PrinterState()
        self.firmware_info = self._get_firmware_info()
        self.command_history = []
        
    def _get_firmware_info(self) -> Dict[str, str]:
        """Get firmware information based on printer type."""
        firmware_responses = {
            EmulatedPrinterType.ENDER3: {
                "M115": "FIRMWARE_NAME:Marlin 2.0.8 SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:Ender-3 EXTRUDER_COUNT:1 UUID:cede2a2f-41a2-4748-9b12-c55c62f367ff",
                "name": "Creality Ender 3",
                "version": "Marlin 2.0.8"
            },
            EmulatedPrinterType.PRUSA_MK3S: {
                "M115": "FIRMWARE_NAME:Prusa-Firmware 3.10.0 based on Marlin FIRMWARE_URL:https://github.com/prusa3d/Prusa-Firmware PROTOCOL_VERSION:1.0 MACHINE_TYPE:Prusa_i3_MK3S EXTRUDER_COUNT:1 UUID:00000000-0000-0000-0000-000000000000",
                "name": "Original Prusa i3 MK3S+", 
                "version": "Prusa-Firmware 3.10.0"
            },
            EmulatedPrinterType.MARLIN_GENERIC: {
                "M115": "FIRMWARE_NAME:Marlin 2.1.1 SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:RepRap EXTRUDER_COUNT:1 UUID:cede2a2f-41a2-4748-9b12-c55c62f367ff",
                "name": "Generic Marlin Printer",
                "version": "Marlin 2.1.1"
            },
            EmulatedPrinterType.KLIPPER: {
                "M115": "// Klipper state: Ready\\n// Host Software: MainsailOS\\nok",
                "name": "Klipper Firmware Printer",
                "version": "Klipper v0.11"
            }
        }
        return firmware_responses[self.type]
    
    def process_command(self, command: str) -> str:
        """Process G-code command and return appropriate response."""
        cmd = command.strip().upper()
        self.command_history.append(cmd)
        
        # Remove line numbers and checksums
        if cmd.startswith('N'):
            cmd = re.sub(r'^N\\d+\\s+', '', cmd)
        if '*' in cmd:
            cmd = cmd.split('*')[0].strip()
        
        # Simulate processing delay
        time.sleep(0.01 + random.uniform(0.0, 0.05))
        
        # Handle specific commands
        if cmd == "M115":  # Firmware version
            return self.firmware_info["M115"]
            
        elif cmd.startswith("M105"):  # Temperature report
            # Simulate temperature changes
            self._update_temperatures()
            return (f"ok T:{self.state.hotend_temp:.1f}/"
                   f"{self.state.hotend_target:.1f} "
                   f"B:{self.state.bed_temp:.1f}/"
                   f"{self.state.bed_target:.1f} "
                   f"@:0 B@:0")
                   
        elif cmd.startswith("M104"):  # Set hotend temperature
            match = re.search(r'S(\\d+)', cmd)
            if match:
                self.state.hotend_target = float(match.group(1))
            return "ok"
            
        elif cmd.startswith("M140"):  # Set bed temperature
            match = re.search(r'S(\\d+)', cmd)
            if match:
                self.state.bed_target = float(match.group(1))
            return "ok"
            
        elif cmd.startswith("M114"):  # Position report
            return (f"X:{self.state.position['X']:.2f} "
                   f"Y:{self.state.position['Y']:.2f} "
                   f"Z:{self.state.position['Z']:.2f} "
                   f"E:{self.state.position['E']:.2f} "
                   f"Count X:0 Y:0 Z:0\\nok")
                   
        elif cmd == "G28":  # Home all axes
            if self.type == EmulatedPrinterType.PRUSA_MK3S:
                time.sleep(0.5)  # Prusa homing takes longer
                return "echo:busy: processing\\necho:busy: processing\\nX:125.00 Y:105.00 Z:0.40 E:0.00 Count A:10000 B:8400 Z:128\\nok"
            else:
                self.state.position = {"X": 0.0, "Y": 0.0, "Z": 0.0, "E": 0.0}
                self.state.is_homed = True
                return "ok"
                
        elif cmd.startswith("G1"):  # Linear move
            self._process_move_command(cmd)
            return "ok"
            
        elif cmd.startswith("M106"):  # Fan on
            match = re.search(r'S(\\d+)', cmd)
            if match:
                self.state.fan_speed = int(match.group(1))
            return "ok"
            
        elif cmd == "M107":  # Fan off
            self.state.fan_speed = 0
            return "ok"
            
        elif cmd == "G29" and self.type != EmulatedPrinterType.KLIPPER:  # Auto bed leveling
            return self._simulate_bed_leveling()
            
        elif cmd == "G80" and self.type == EmulatedPrinterType.PRUSA_MK3S:  # Prusa mesh leveling
            return self._simulate_prusa_mesh_leveling()
            
        elif cmd == "M84":  # Disable steppers
            return "ok"
            
        elif cmd.startswith("M220"):  # Set feedrate percentage
            return "ok"
            
        elif cmd.startswith("M221"):  # Set flow rate percentage
            return "ok"
            
        # Klipper specific commands
        elif self.type == EmulatedPrinterType.KLIPPER:
            if cmd == "BED_MESH_CALIBRATE":
                return "// Bed mesh calibration started\\nok"
            elif cmd == "QUAD_GANTRY_LEVEL":
                return "// Quad gantry leveling started\\nok"
                
        # Default responses
        elif cmd.startswith("M"):
            return "ok"  # Most M commands just return ok
        elif cmd.startswith("G"):
            return "ok"  # Most G commands just return ok
        else:
            return "ok"  # Unknown command
    
    def _update_temperatures(self):
        """Simulate temperature changes towards targets."""
        # Hotend temperature
        if self.state.hotend_temp < self.state.hotend_target:
            self.state.hotend_temp += random.uniform(0.5, 2.0)
            if self.state.hotend_temp > self.state.hotend_target:
                self.state.hotend_temp = self.state.hotend_target
        elif self.state.hotend_temp > self.state.hotend_target:
            self.state.hotend_temp -= random.uniform(0.2, 1.0)
            if self.state.hotend_temp < self.state.hotend_target:
                self.state.hotend_temp = self.state.hotend_target
                
        # Bed temperature  
        if self.state.bed_temp < self.state.bed_target:
            self.state.bed_temp += random.uniform(0.2, 1.0)
            if self.state.bed_temp > self.state.bed_target:
                self.state.bed_temp = self.state.bed_target
        elif self.state.bed_temp > self.state.bed_target:
            self.state.bed_temp -= random.uniform(0.1, 0.5)
            if self.state.bed_temp < self.state.bed_target:
                self.state.bed_temp = self.state.bed_target
    
    def _process_move_command(self, cmd: str):
        """Process G1 movement command."""
        # Extract coordinates
        for axis in ['X', 'Y', 'Z', 'E']:
            match = re.search(f'{axis}([\\d.-]+)', cmd)
            if match:
                self.state.position[axis] = float(match.group(1))
    
    def _simulate_bed_leveling(self) -> str:
        """Simulate auto bed leveling process."""
        responses = [
            "echo:busy: processing",
            "Bilinear leveling Grid:",
            "      0      1      2",
            " 0 +0.012 +0.005 -0.002",
            " 1 +0.008 +0.001 -0.005",
            " 2 +0.003 -0.002 -0.008",
            "ok"
        ]
        return "\\n".join(responses)
    
    def _simulate_prusa_mesh_leveling(self) -> str:
        """Simulate Prusa mesh bed leveling."""
        responses = [
            "echo:busy: processing",
            "Mesh bed leveling activated.",
            "G80 - Mesh bed leveling",
            "Searching bed calibration point...",
            "ok"
        ]
        return "\\n".join(responses)
    
    def get_status(self) -> Dict:
        """Get current printer status."""
        return {
            "type": self.type.value,
            "name": self.firmware_info["name"],
            "version": self.firmware_info["version"],
            "state": {
                "hotend_temp": self.state.hotend_temp,
                "hotend_target": self.state.hotend_target,
                "bed_temp": self.state.bed_temp,
                "bed_target": self.state.bed_target,
                "position": self.state.position.copy(),
                "is_homed": self.state.is_homed,
                "is_printing": self.state.is_printing,
                "fan_speed": self.state.fan_speed
            },
            "commands_processed": len(self.command_history)
        }

class PrinterEmulatorManager:
    """Manages multiple printer emulators for testing."""
    
    def __init__(self):
        self.emulators = {}
        self._create_default_emulators()
    
    def _create_default_emulators(self):
        """Create default printer emulators."""
        for printer_type in EmulatedPrinterType:
            self.emulators[printer_type.value] = PrinterEmulator(printer_type)
    
    def get_emulator(self, printer_type: str) -> Optional[PrinterEmulator]:
        """Get specific printer emulator."""
        return self.emulators.get(printer_type)
    
    def list_emulators(self) -> List[str]:
        """List available emulators."""
        return list(self.emulators.keys())
    
    def get_all_status(self) -> Dict:
        """Get status of all emulators."""
        return {
            name: emulator.get_status() 
            for name, emulator in self.emulators.items()
        }

async def test_printer_emulators():
    """Test all printer emulators."""
    print("🎭 AI Agent 3D Print - Printer Emulator Test")
    print("=" * 60)
    
    manager = PrinterEmulatorManager()
    
    test_commands = [
        "M115",  # Firmware version
        "M105",  # Temperature  
        "M114",  # Position
        "G28",   # Home
        "M104 S200",  # Set hotend temp
        "M140 S60",   # Set bed temp
        "M105",  # Temperature again
        "G1 X10 Y10 Z0.2 F3000",  # Move
        "M114",  # Position
        "G29",   # Auto level (if supported)
    ]
    
    for emulator_name in manager.list_emulators():
        emulator = manager.get_emulator(emulator_name)
        status = emulator.get_status()
        
        print(f"\\n🖨️ Testing: {status['name']} ({status['type']})")
        print(f"   📦 Version: {status['version']}")
        print("-" * 40)
        
        for i, command in enumerate(test_commands, 1):
            print(f"[{i:2d}] > {command}")
            response = emulator.process_command(command)
            
            # Handle None response
            if response is None:
                response = "ok"
            
            # Truncate long responses
            if len(response) > 100:
                print(f"     < {response[:97]}...")
            else:
                print(f"     < {response}")
            
            await asyncio.sleep(0.1)  # Small delay between commands
        
        # Show final status
        final_status = emulator.get_status()
        state = final_status['state']
        print(f"\\n📊 Final State:")
        print(f"   🌡️ Hotend: {state['hotend_temp']:.1f}°C → {state['hotend_target']:.1f}°C")
        print(f"   🛏️ Bed: {state['bed_temp']:.1f}°C → {state['bed_target']:.1f}°C")
        print(f"   📍 Position: X{state['position']['X']} Y{state['position']['Y']} Z{state['position']['Z']}")
        print(f"   🏠 Homed: {state['is_homed']}")
        print(f"   📨 Commands: {final_status['commands_processed']}")
    
    print("\\n✅ Printer emulator testing completed!")
    print("\\n💡 These emulators can be used to test multi-printer support")
    print("   without requiring physical hardware.")

if __name__ == "__main__":
    asyncio.run(test_printer_emulators())
