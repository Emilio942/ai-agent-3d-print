#!/usr/bin/env python3
"""
Enhanced Printer Agent with Multi-Printer Support
Integrates multi-printer detection and emulation into the main system
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_printer_support import MultiPrinterDetector, EnhancedPrinterCommunicator
from printer_support.printer_emulator import PrinterEmulatorManager, EmulatedPrinterType

class EnhancedPrinterAgent:
    """Enhanced printer agent with multi-printer support."""
    
    def __init__(self):
        self.detector = MultiPrinterDetector()
        self.emulator_manager = PrinterEmulatorManager()
        self.connected_printers = {}
        self.current_printer = None
        self.mock_mode = True
        
    async def initialize(self):
        """Initialize the printer agent and scan for printers."""
        print("🔧 Initializing Enhanced Printer Agent...")
        
        # Scan for real printers
        detected = await self.detector.scan_for_printers(timeout=3.0)
        
        if detected:
            print(f"✅ Found {len(detected)} real printer(s)")
            for printer in detected:
                print(f"   🖨️ {printer['name']} on {printer['port']}")
        else:
            print("⚠️ No real printers found - using emulated printers")
            
        # Always provide emulated printers for testing
        print("🎭 Setting up emulated printers...")
        for emulator_type in ['ender3', 'prusa_mk3s', 'marlin_generic', 'klipper']:
            emulator = self.emulator_manager.get_emulator(emulator_type)
            status = emulator.get_status()
            print(f"   🤖 {status['name']} (Emulated)")
        
        return True
    
    async def list_available_printers(self) -> list:
        """List all available printers (real + emulated)."""
        printers = []
        
        # Add real printers
        for printer in self.detector.get_detected_printers():
            printers.append({
                'id': f"real_{printer['port'].replace('/', '_')}",
                'name': printer['name'],
                'type': printer['type'],
                'port': printer['port'],
                'connection_type': 'real',
                'status': 'available'
            })
        
        # Add emulated printers
        for emulator_name in self.emulator_manager.list_emulators():
            emulator = self.emulator_manager.get_emulator(emulator_name)
            status = emulator.get_status()
            printers.append({
                'id': f"emulated_{emulator_name}",
                'name': f"{status['name']} (Emulated)",
                'type': status['type'],
                'port': f"emulated://{emulator_name}",
                'connection_type': 'emulated',
                'status': 'available'
            })
        
        return printers
    
    async def connect_to_printer(self, printer_id: str) -> bool:
        """Connect to a specific printer."""
        try:
            if printer_id.startswith('real_'):
                # Connect to real printer
                port = printer_id.replace('real_', '').replace('_', '/')
                printer_info = self.detector.get_printer_by_port(port)
                
                if not printer_info:
                    print(f"❌ Real printer not found: {port}")
                    return False
                
                communicator = EnhancedPrinterCommunicator(printer_info)
                if await communicator.connect():
                    self.connected_printers[printer_id] = communicator
                    self.current_printer = printer_id
                    self.mock_mode = False
                    print(f"✅ Connected to real printer: {printer_info['name']}")
                    return True
                else:
                    print(f"❌ Failed to connect to real printer: {printer_info['name']}")
                    return False
                    
            elif printer_id.startswith('emulated_'):
                # Connect to emulated printer
                emulator_name = printer_id.replace('emulated_', '')
                emulator = self.emulator_manager.get_emulator(emulator_name)
                
                if emulator:
                    self.connected_printers[printer_id] = emulator
                    self.current_printer = printer_id
                    self.mock_mode = True
                    status = emulator.get_status()
                    print(f"🎭 Connected to emulated printer: {status['name']}")
                    return True
                else:
                    print(f"❌ Emulated printer not found: {emulator_name}")
                    return False
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
        
        return False
    
    async def send_gcode(self, command: str) -> str:
        """Send G-code command to current printer."""
        if not self.current_printer:
            raise Exception("No printer connected")
        
        printer = self.connected_printers[self.current_printer]
        
        if hasattr(printer, 'send_command'):
            # Real printer
            return await printer.send_command(command)
        else:
            # Emulated printer
            return printer.process_command(command)
    
    async def get_printer_status(self) -> dict:
        """Get current printer status."""
        if not self.current_printer:
            return {'status': 'disconnected'}
        
        printer = self.connected_printers[self.current_printer]
        
        if hasattr(printer, 'get_printer_info'):
            # Real printer
            info = printer.get_printer_info()
            info['connection_type'] = 'real'
            return info
        else:
            # Emulated printer
            status = printer.get_status()
            return {
                'status': 'connected',
                'name': status['name'],
                'type': status['type'],
                'connection_type': 'emulated',
                'state': status['state']
            }
    
    async def disconnect_current_printer(self):
        """Disconnect from current printer."""
        if self.current_printer:
            printer = self.connected_printers[self.current_printer]
            
            if hasattr(printer, 'disconnect'):
                printer.disconnect()
            
            del self.connected_printers[self.current_printer]
            print(f"🔌 Disconnected from printer")
            self.current_printer = None
    
    async def test_printer_communication(self, printer_id: str) -> dict:
        """Test communication with a specific printer."""
        if await self.connect_to_printer(printer_id):
            try:
                # Test basic commands
                test_results = {}
                
                # Firmware version
                firmware = await self.send_gcode("M115")
                test_results['firmware'] = firmware[:100] + "..." if len(firmware) > 100 else firmware
                
                # Temperature
                temp = await self.send_gcode("M105")
                test_results['temperature'] = temp
                
                # Position
                pos = await self.send_gcode("M114")
                test_results['position'] = pos
                
                # Status
                status = await self.get_printer_status()
                test_results['status'] = status
                
                test_results['success'] = True
                return test_results
                
            except Exception as e:
                return {'success': False, 'error': str(e)}
            finally:
                await self.disconnect_current_printer()
        else:
            return {'success': False, 'error': 'Failed to connect'}

async def demo_enhanced_printer_agent():
    """Demonstrate the enhanced printer agent capabilities."""
    print("🚀 AI Agent 3D Print - Enhanced Printer Agent Demo")
    print("=" * 60)
    
    agent = EnhancedPrinterAgent()
    
    # Initialize
    await agent.initialize()
    print()
    
    # List available printers
    printers = await agent.list_available_printers()
    print(f"📋 Available Printers ({len(printers)}):")
    for i, printer in enumerate(printers, 1):
        print(f"   {i}. {printer['name']} ({printer['connection_type']})")
        print(f"      ID: {printer['id']}")
        print(f"      Type: {printer['type']}")
        print(f"      Port: {printer['port']}")
        print()
    
    if not printers:
        print("❌ No printers available")
        return
    
    # Test communication with each printer
    print("🧪 Testing Communication with All Printers:")
    print("=" * 60)
    
    for i, printer in enumerate(printers, 1):
        print(f"\\n[{i}/{len(printers)}] Testing: {printer['name']}")
        print("-" * 40)
        
        results = await agent.test_printer_communication(printer['id'])
        
        if results['success']:
            print("✅ Communication successful!")
            print(f"   🔧 Firmware: {results['firmware']}")
            print(f"   🌡️ Temperature: {results['temperature']}")
            print(f"   📍 Position: {results['position']}")
            print(f"   📊 Status: {results['status']['status']}")
        else:
            print(f"❌ Communication failed: {results['error']}")
    
    # Demo with first available printer
    if printers:
        print(f"\\n🎯 Extended Demo with: {printers[0]['name']}")
        print("=" * 60)
        
        if await agent.connect_to_printer(printers[0]['id']):
            commands = [
                ("M115", "Firmware Info"),
                ("M105", "Temperature Status"),
                ("M114", "Current Position"),
                ("G28", "Home All Axes"),
                ("M104 S200", "Set Hotend to 200°C"),
                ("M140 S60", "Set Bed to 60°C"),
                ("G1 X50 Y50 Z10 F3000", "Move to Center"),
                ("M105", "Check Temperatures"),
                ("M114", "Check Position")
            ]
            
            for cmd, description in commands:
                print(f"\\n> {cmd}  // {description}")
                try:
                    response = await agent.send_gcode(cmd)
                    if len(response) > 80:
                        print(f"< {response[:77]}...")
                    else:
                        print(f"< {response}")
                except Exception as e:
                    print(f"< ERROR: {e}")
                
                await asyncio.sleep(0.2)
            
            # Final status
            print(f"\\n📊 Final Status:")
            status = await agent.get_printer_status()
            print(f"   Connection: {status.get('connection_type', 'unknown')}")
            print(f"   Status: {status.get('status', 'unknown')}")
            if 'state' in status:
                state = status['state']
                print(f"   Temperature: {state.get('hotend_temp', 0):.1f}°C / {state.get('bed_temp', 0):.1f}°C")
                print(f"   Position: X{state['position']['X']} Y{state['position']['Y']} Z{state['position']['Z']}")
            
            await agent.disconnect_current_printer()
        else:
            print("❌ Failed to connect for extended demo")
    
    print("\\n✅ Enhanced Printer Agent Demo Completed!")
    print("🎉 Multi-printer support is fully functional!")

if __name__ == "__main__":
    asyncio.run(demo_enhanced_printer_agent())
