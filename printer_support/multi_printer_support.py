"""
Multi-Printer Support System for AI Agent 3D Print
Supports various printer types: Marlin, Ender 3, Prusa MK3, Klipper, etc.
"""

import re
import time
import asyncio
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import serial
import serial.tools.list_ports

class PrinterType(Enum):
    """Supported printer firmware types."""
    MARLIN = "marlin"
    KLIPPER = "klipper" 
    REPETIER = "repetier"
    PRUSA = "prusa"
    ENDER = "ender"
    UNKNOWN = "unknown"

class PrinterBrand(Enum):
    """Supported printer brands."""
    PRUSA = "prusa"
    CREALITY = "creality"
    ENDER = "ender"
    BAMBU = "bambu"
    ULTIMAKER = "ultimaker"
    GENERIC = "generic"

@dataclass
class PrinterProfile:
    """Printer configuration profile."""
    name: str
    brand: PrinterBrand
    firmware_type: PrinterType
    build_volume: tuple  # (x, y, z) in mm
    max_feedrate: Dict[str, int]  # mm/min for X,Y,Z,E
    max_acceleration: Dict[str, int]  # mm/s²
    temperature_limits: Dict[str, tuple]  # (min, max) for hotend, bed
    auto_level: bool
    filament_sensor: bool
    power_resume: bool
    firmware_commands: Dict[str, str]  # Custom G-code commands
    connection_settings: Dict[str, Any]  # Baudrate, timeout, etc.

class PrinterProfileManager:
    """Manages different printer profiles and auto-detection."""
    
    def __init__(self):
        self.profiles = self._init_default_profiles()
        self.detection_patterns = self._init_detection_patterns()
    
    def _init_default_profiles(self) -> Dict[str, PrinterProfile]:
        """Initialize default printer profiles."""
        profiles = {}
        
        # Ender 3 Profile
        profiles["ender3"] = PrinterProfile(
            name="Creality Ender 3",
            brand=PrinterBrand.CREALITY,
            firmware_type=PrinterType.MARLIN,
            build_volume=(220, 220, 250),
            max_feedrate={"X": 500, "Y": 500, "Z": 5, "E": 25},
            max_acceleration={"X": 500, "Y": 500, "Z": 100, "E": 1000},
            temperature_limits={"hotend": (0, 260), "bed": (0, 80)},
            auto_level=False,
            filament_sensor=False,
            power_resume=False,
            firmware_commands={
                "home": "G28",
                "auto_level": "G29",
                "disable_steppers": "M84",
                "fan_on": "M106 S255",
                "fan_off": "M107"
            },
            connection_settings={
                "baudrate": 115200,
                "timeout": 2.0,
                "write_timeout": 1.0
            }
        )
        
        # Prusa MK3S Profile
        profiles["prusa_mk3s"] = PrinterProfile(
            name="Original Prusa i3 MK3S",
            brand=PrinterBrand.PRUSA,
            firmware_type=PrinterType.PRUSA,
            build_volume=(250, 210, 210),
            max_feedrate={"X": 200, "Y": 200, "Z": 12, "E": 120},
            max_acceleration={"X": 1000, "Y": 1000, "Z": 200, "E": 5000},
            temperature_limits={"hotend": (0, 300), "bed": (0, 120)},
            auto_level=True,
            filament_sensor=True,
            power_resume=True,
            firmware_commands={
                "home": "G28",
                "mesh_level": "G80",
                "load_filament": "M701",
                "unload_filament": "M702",
                "preheat_pla": "M104 S215\\nM140 S60",
                "preheat_petg": "M104 S240\\nM140 S85"
            },
            connection_settings={
                "baudrate": 115200,
                "timeout": 3.0,
                "write_timeout": 2.0
            }
        )
        
        # Generic Marlin Profile
        profiles["marlin_generic"] = PrinterProfile(
            name="Generic Marlin Printer",
            brand=PrinterBrand.GENERIC,
            firmware_type=PrinterType.MARLIN,
            build_volume=(200, 200, 200),
            max_feedrate={"X": 300, "Y": 300, "Z": 5, "E": 25},
            max_acceleration={"X": 800, "Y": 800, "Z": 100, "E": 1000},
            temperature_limits={"hotend": (0, 250), "bed": (0, 80)},
            auto_level=False,
            filament_sensor=False,
            power_resume=False,
            firmware_commands={
                "home": "G28",
                "auto_level": "G29",
                "disable_steppers": "M84"
            },
            connection_settings={
                "baudrate": 250000,
                "timeout": 2.0,
                "write_timeout": 1.0
            }
        )
        
        # Klipper Profile
        profiles["klipper"] = PrinterProfile(
            name="Klipper Firmware Printer",
            brand=PrinterBrand.GENERIC,
            firmware_type=PrinterType.KLIPPER,
            build_volume=(220, 220, 250),
            max_feedrate={"X": 300, "Y": 300, "Z": 10, "E": 50},
            max_acceleration={"X": 3000, "Y": 3000, "Z": 300, "E": 5000},
            temperature_limits={"hotend": (0, 300), "bed": (0, 120)},
            auto_level=True,
            filament_sensor=False,
            power_resume=True,
            firmware_commands={
                "home": "G28",
                "quad_gantry_level": "QUAD_GANTRY_LEVEL",
                "bed_mesh": "BED_MESH_CALIBRATE",
                "pressure_advance": "SET_PRESSURE_ADVANCE ADVANCE=0.05"
            },
            connection_settings={
                "baudrate": 250000,
                "timeout": 5.0,
                "write_timeout": 3.0
            }
        )
        
        return profiles
    
    def _init_detection_patterns(self) -> Dict[PrinterType, List[str]]:
        """Initialize firmware detection patterns."""
        return {
            PrinterType.MARLIN: [
                r"FIRMWARE_NAME:Marlin",
                r"Marlin \d+\.\d+",
                r"echo:.*Marlin",
                r"Creality"
            ],
            PrinterType.PRUSA: [
                r"FIRMWARE_NAME:Prusa",
                r"Prusa-Firmware",
                r"Original Prusa",
                r"MK3S"
            ],
            PrinterType.KLIPPER: [
                r"Klipper",
                r"// Klipper state:",
                r"MCU config"
            ],
            PrinterType.REPETIER: [
                r"FIRMWARE_NAME:Repetier",
                r"Repetier-Firmware"
            ]
        }
    
    def detect_printer_type(self, firmware_response: str) -> PrinterType:
        """Detect printer type from firmware response."""
        firmware_response = firmware_response.upper()
        
        for printer_type, patterns in self.detection_patterns.items():
            for pattern in patterns:
                if re.search(pattern, firmware_response, re.IGNORECASE):
                    return printer_type
        
        return PrinterType.UNKNOWN
    
    def get_profile_for_type(self, printer_type: PrinterType) -> Optional[PrinterProfile]:
        """Get best matching profile for detected printer type."""
        type_mapping = {
            PrinterType.MARLIN: "marlin_generic",
            PrinterType.PRUSA: "prusa_mk3s", 
            PrinterType.KLIPPER: "klipper",
            PrinterType.ENDER: "ender3"
        }
        
        profile_key = type_mapping.get(printer_type)
        return self.profiles.get(profile_key) if profile_key else None
    
    def get_profile(self, profile_name: str) -> Optional[PrinterProfile]:
        """Get specific printer profile by name."""
        return self.profiles.get(profile_name)
    
    def list_profiles(self) -> List[str]:
        """List all available printer profiles."""
        return list(self.profiles.keys())

class MultiPrinterDetector:
    """Detects and identifies connected 3D printers."""
    
    def __init__(self):
        self.profile_manager = PrinterProfileManager()
        self.detected_printers = []
    
    async def scan_for_printers(self, timeout: float = 5.0) -> List[Dict]:
        """Scan for connected 3D printers on USB ports only - FAST VERSION."""
        detected = []
        
        # Get ONLY USB ports to avoid scanning 33+ serial ports
        usb_ports = self._get_usb_ports_only()
        
        if not usb_ports:
            print("🔍 No USB ports found for 3D printers")
            return []
            
        print(f"🔍 Scanning {len(usb_ports)} USB ports for 3D printers (max {timeout}s per port)...")
        
        for port_info in usb_ports:
            port = port_info.device
            print(f"  🔌 Testing port: {port}")
            
            try:
                # Use shorter timeout per port
                printer_info = await asyncio.wait_for(
                    self._test_printer_connection_fast(port, min(timeout, 3.0)),
                    timeout=4.0  # Hard timeout to prevent hanging
                )
                
                if printer_info:
                    detected.append(printer_info)
                    print(f"  ✅ Found printer: {printer_info['name']} ({printer_info['type']})")
                else:
                    print(f"  ❌ No printer found on {port}")
                    
            except asyncio.TimeoutError:
                print(f"  ⏰ Timeout testing {port}")
            except Exception as e:
                print(f"  ⚠️ Error testing {port}: {e}")
        
        self.detected_printers = detected
        return detected
    
    async def scan_for_printers_with_fallback(self, timeout: float = 5.0) -> List[Dict]:
        """Enhanced scan with fallback for problematic hardware."""
        print("🔧 Enhanced printer scan with hardware fallback...")
        
        # Try normal detection first
        detected = await self.scan_for_printers(timeout)
        
        # If no printers found, try enhanced detection for problematic hardware
        if not detected:
            print("🔄 No printers found with standard scan, trying enhanced detection...")
            detected = await self._enhanced_hardware_detection()
        
        return detected
    
    async def _enhanced_hardware_detection(self) -> List[Dict]:
        """Enhanced detection for problematic/non-standard printers."""
        usb_ports = self._get_usb_ports_only()
        detected = []
        
        for port_info in usb_ports:
            port = port_info.device
            print(f"  🔍 Enhanced test: {port}")
            
            # Try multiple approaches for difficult hardware
            approaches = [
                (250000, [b'\n', b'M105\n']),  # High baud, simple commands
                (115200, [b'\n', b'M105\n']),  # Standard baud
                (9600, [b'\n']),               # Low baud fallback
            ]
            
            for baudrate, commands in approaches:
                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self._test_problematic_hardware, port, baudrate, commands
                    )
                    
                    if result:
                        detected.append(result)
                        print(f"  ✅ Enhanced detection found: {result['name']}")
                        break  # Found something, stop trying other approaches
                        
                except Exception:
                    continue
        
        return detected
    
    def _test_problematic_hardware(self, port: str, baudrate: int, commands: list) -> Optional[Dict]:
        """Test problematic hardware with multiple attempts."""
        for attempt in range(2):  # 2 attempts per approach
            try:
                with serial.Serial(port, baudrate, timeout=2.0) as ser:
                    time.sleep(1.0 if attempt == 0 else 2.0)  # Longer wait on retry
                    
                    ser.reset_input_buffer()
                    response = ""
                    
                    for cmd in commands:
                        ser.write(cmd)
                        time.sleep(0.8)
                        
                        if ser.in_waiting > 0:
                            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            response += data
                    
                    # Accept any response as a detected device
                    if len(response.strip()) > 1:
                        return {
                            'port': port,
                            'baudrate': baudrate,
                            'type': 'hardware_detected',
                            'firmware_response': response.strip()[:100],
                            'name': f"Hardware Device on {port}",
                            'profile': None,
                            'note': 'Detected via enhanced scan - may need manual configuration'
                        }
                        
            except Exception:
                continue
        
        return None
    
    def _get_available_ports(self) -> List:
        """Get list of available serial ports - optimized for 3D printers."""
        try:
            ports = list(serial.tools.list_ports.comports())
            # Filter for 3D printer specific ports first
            printer_ports = [
                p for p in ports 
                if any(keyword in p.device.lower() for keyword in 
                      ['ttyusb', 'ttyacm'])  # Most 3D printers use USB/ACM
            ]
            if printer_ports:
                return printer_ports
                
            # Fallback: filter for any USB/serial devices  
            usb_ports = [
                p for p in ports 
                if any(keyword in p.device.lower() for keyword in 
                      ['usb', 'acm', 'com'])
            ]
            return usb_ports[:5]  # Limit to 5 ports max to avoid endless scanning
        except Exception as e:
            print(f"Warning: Could not enumerate serial ports: {e}")
            return []
    
    def _get_usb_ports_only(self) -> List:
        """Get ONLY USB ports that 3D printers typically use - FAST."""
        try:
            ports = list(serial.tools.list_ports.comports())
            # Only USB/ACM ports - no ttyS* ports that slow things down
            usb_ports = [
                p for p in ports 
                if any(keyword in p.device.lower() for keyword in ['ttyusb', 'ttyacm'])
            ]
            print(f"🔍 Found {len(usb_ports)} USB/ACM ports out of {len(ports)} total")
            return usb_ports
        except Exception as e:
            print(f"Warning: Could not enumerate USB ports: {e}")
            return []
    
    async def _test_printer_connection(self, port: str, timeout: float) -> Optional[Dict]:
        """Test connection to a specific port and identify printer - WORKING VERSION."""
        try:
            # Try common baudrates for 3D printers, prioritizing the most common
            baudrates = [250000, 115200]  # 250000 first, since it worked in sync test
            
            for baudrate in baudrates:
                try:
                    with serial.Serial(port, baudrate, timeout=2.0) as ser:
                        time.sleep(1.0)  # Let connection settle properly
                        
                        # Clear buffers
                        ser.reset_input_buffer()
                        ser.reset_output_buffer()
                        
                        # Try different commands
                        commands = [b'\n', b'M115\n', b'M105\n', b'?\n']
                        response = ""
                        
                        for cmd in commands:
                            ser.write(cmd)
                            time.sleep(0.8)  # Wait longer for response
                            
                            if ser.in_waiting > 0:
                                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                                response += data
                                
                                # If we got any meaningful response, we found a printer
                                if len(response.strip()) > 5:  # Reasonable response length
                                    break
                        
                        if response and len(response.strip()) > 5:
                            # Determine printer type from response
                            printer_type = self.profile_manager.detect_printer_type(response)
                            profile = self.profile_manager.get_profile_for_type(printer_type)
                            
                            return {
                                'port': port,
                                'baudrate': baudrate,
                                'type': printer_type.value,
                                'firmware_response': response.strip(),
                                'name': profile.name if profile else f"3D Printer ({printer_type.value})",
                                'profile': profile
                            }
                            
                except serial.SerialException as e:
                    continue  # Try next baudrate
                except Exception as e:
                    continue  # Try next baudrate
                    
        except Exception as e:
            print(f"  ⚠️ Exception testing {port}: {e}")
        
        return None
    
    async def _test_printer_connection_fast(self, port: str, timeout: float) -> Optional[Dict]:
        """Fast printer connection test with strict timeout."""
        try:
            # Only test the 2 most common baudrates to save time
            baudrates = [250000, 115200]
            
            for baudrate in baudrates:
                try:
                    # Use run_in_executor to prevent blocking
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self._sync_test_connection, port, baudrate, timeout
                    )
                    if result:
                        return result
                        
                except Exception:
                    continue  # Try next baudrate
                    
        except Exception as e:
            print(f"  ⚠️ Exception testing {port}: {e}")
        
        return None
    
    def _sync_test_connection(self, port: str, baudrate: int, timeout: float) -> Optional[Dict]:
        """Synchronous connection test - runs in thread to prevent blocking."""
        try:
            with serial.Serial(port, baudrate, timeout=1.0) as ser:
                time.sleep(0.5)  # Quick settle
                
                ser.reset_input_buffer()
                ser.write(b'\n')  # Simple command
                time.sleep(0.3)   # Quick wait
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    
                    if len(response.strip()) > 3:
                        # Quick type detection
                        if 'echo:' in response or 'marlin' in response.lower():
                            printer_type = PrinterType.MARLIN
                            name = "Marlin 3D Printer"
                        elif 'prusa' in response.lower():
                            printer_type = PrinterType.PRUSA
                            name = "Prusa 3D Printer"
                        elif 'klipper' in response.lower():
                            printer_type = PrinterType.KLIPPER
                            name = "Klipper 3D Printer"
                        else:
                            printer_type = PrinterType.UNKNOWN
                            name = "Unknown 3D Printer"
                        
                        profile = self.profile_manager.get_profile_for_type(printer_type)
                        
                        return {
                            'port': port,
                            'baudrate': baudrate,
                            'type': printer_type.value,
                            'firmware_response': response.strip(),
                            'name': name,
                            'profile': profile
                        }
        except:
            pass  # Silent fail for speed
        
        return None
    
    def get_detected_printers(self) -> List[Dict]:
        """Get list of detected printers."""
        return self.detected_printers
    
    def get_printer_by_port(self, port: str) -> Optional[Dict]:
        """Get detected printer info by port."""
        for printer in self.detected_printers:
            if printer['port'] == port:
                return printer
        return None

class EnhancedPrinterCommunicator:
    """Enhanced printer communication with multi-printer support."""
    
    def __init__(self, printer_info: Dict):
        self.printer_info = printer_info
        self.profile = printer_info.get('profile')
        self.serial_connection = None
        self.connected = False
        
    async def connect(self) -> bool:
        """Connect to the printer."""
        try:
            port = self.printer_info['port']
            baudrate = self.printer_info['baudrate']
            settings = self.profile.connection_settings if self.profile else {}
            
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=settings.get('timeout', 2.0),
                write_timeout=settings.get('write_timeout', 1.0)
            )
            
            # Wait for connection to stabilize
            await asyncio.sleep(1.0)
            
            # Verify connection with M115
            response = await self.send_command("M115")
            if response and 'FIRMWARE_NAME' in response:
                self.connected = True
                return True
                
        except Exception as e:
            print(f"Failed to connect to printer: {e}")
        
        return False
    
    async def send_command(self, command: str, timeout: float = 5.0) -> str:
        """Send G-code command to printer."""
        if not self.connected or not self.serial_connection:
            raise Exception("Printer not connected")
        
        try:
            # Send command
            cmd_bytes = f"{command}\\n".encode('utf-8')
            self.serial_connection.write(cmd_bytes)
            
            # Read response
            response = ""
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.serial_connection.in_waiting:
                    data = self.serial_connection.read(self.serial_connection.in_waiting)
                    response += data.decode('utf-8', errors='ignore')
                    
                    if 'ok' in response.lower() or 'error' in response.lower():
                        break
                        
                await asyncio.sleep(0.01)
            
            return response.strip()
            
        except Exception as e:
            raise Exception(f"Communication error: {e}")
    
    def disconnect(self):
        """Disconnect from printer."""
        if self.serial_connection:
            self.serial_connection.close()
            self.serial_connection = None
        self.connected = False
    
    def get_printer_info(self) -> Dict:
        """Get printer information."""
        return {
            'name': self.printer_info.get('name', 'Unknown'),
            'type': self.printer_info.get('type', 'unknown'),
            'port': self.printer_info.get('port'),
            'connected': self.connected,
            'profile': self.profile.name if self.profile else None
        }

# Test script for multi-printer detection
async def test_multi_printer_detection():
    """Test the multi-printer detection system."""
    print("🚀 AI Agent 3D Print - Multi-Printer Detection Test")
    print("=" * 60)
    
    detector = MultiPrinterDetector()
    
    # List available profiles
    print("📋 Available printer profiles:")
    for profile_name in detector.profile_manager.list_profiles():
        profile = detector.profile_manager.get_profile(profile_name)
        print(f"  • {profile.name} ({profile.firmware_type.value})")
    print()
    
    # Scan for printers
    detected = await detector.scan_for_printers(timeout=3.0)
    
    print(f"\\n🎯 Detection Results: {len(detected)} printer(s) found")
    print("=" * 60)
    
    if not detected:
        print("❌ No 3D printers detected")
        print("💡 Make sure a 3D printer is connected via USB")
        return
    
    for i, printer in enumerate(detected, 1):
        print(f"🖨️ Printer {i}: {printer['name']}")
        print(f"   📍 Port: {printer['port']}")
        print(f"   ⚡ Baudrate: {printer['baudrate']}")
        print(f"   🔧 Type: {printer['type']}")
        print(f"   📡 Response: {printer['firmware_response'][:100]}...")
        print()
        
        # Test communication
        print(f"🔌 Testing communication with {printer['name']}...")
        communicator = EnhancedPrinterCommunicator(printer)
        
        try:
            if await communicator.connect():
                print("  ✅ Connection successful!")
                
                # Send test commands
                temp_response = await communicator.send_command("M105")
                print(f"  🌡️ Temperature: {temp_response}")
                
                pos_response = await communicator.send_command("M114")
                print(f"  📍 Position: {pos_response}")
                
            else:
                print("  ❌ Failed to establish communication")
                
        except Exception as e:
            print(f"  ⚠️ Communication error: {e}")
        finally:
            communicator.disconnect()
    
    print("\\n✅ Multi-printer detection test completed!")

if __name__ == "__main__":
    asyncio.run(test_multi_printer_detection())
