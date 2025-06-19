#!/usr/bin/env python3
"""
WORKING Multi-Printer Detection System
Based on the successful synchronous test
"""

import asyncio
import serial
import time
from typing import Dict, List, Optional

class WorkingPrinterDetector:
    """A printer detector that actually works."""
    
    def __init__(self):
        self.detected_printers = []
        
    def sync_detect_printer(self, port: str) -> Optional[Dict]:
        """Synchronous printer detection that works."""
        baudrates = [250000, 115200]  # Test both, start with what worked
        
        for baudrate in baudrates:
            try:
                with serial.Serial(port, baudrate, timeout=2.0) as ser:
                    time.sleep(1.0)  # Connection settle time
                    
                    # Clear buffers
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()
                    
                    # Try commands
                    commands = [b'\n', b'M115\n', b'M105\n', b'?\n']
                    response = ""
                    
                    for cmd in commands:
                        ser.write(cmd)
                        time.sleep(0.8)  # Wait for response
                        
                        if ser.in_waiting > 0:
                            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            response += data
                            
                            if len(response.strip()) > 5:
                                break
                    
                    if response and len(response.strip()) > 5:
                        # Determine type from response
                        if 'marlin' in response.lower():
                            printer_type = 'marlin'
                            name = 'Marlin 3D Printer'
                        elif 'prusa' in response.lower():
                            printer_type = 'prusa'
                            name = 'Prusa 3D Printer'
                        elif 'klipper' in response.lower():
                            printer_type = 'klipper'
                            name = 'Klipper 3D Printer'
                        elif 'echo:' in response:
                            printer_type = 'marlin'  # Echo indicates Marlin
                            name = 'Marlin-based 3D Printer'
                        else:
                            printer_type = 'unknown'
                            name = 'Unknown 3D Printer'
                        
                        return {
                            'port': port,
                            'baudrate': baudrate,
                            'type': printer_type,
                            'firmware_response': response.strip(),
                            'name': name,
                            'id': f"real_{port.replace('/', '_')}",
                            'emulated': False
                        }
                        
            except Exception as e:
                continue  # Try next baudrate
        
        return None
    
    async def scan_for_printers(self, timeout: float = 3.0) -> List[Dict]:
        """Scan for real printers - async wrapper for sync function."""
        detected = []
        
        # Get USB ports only
        try:
            import serial.tools.list_ports
            all_ports = list(serial.tools.list_ports.comports())
            usb_ports = [p.device for p in all_ports if 'USB' in p.device.upper()]
            
            print(f"🔍 Scanning {len(usb_ports)} USB ports for 3D printers...")
            
            for port in usb_ports:
                print(f"  🔌 Testing port: {port}")
                
                # Run sync detection in thread pool to keep it async
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.sync_detect_printer, port
                )
                
                if result:
                    detected.append(result)
                    print(f"  ✅ Found printer: {result['name']} on {port}")
                else:
                    print(f"  ❌ No printer found on {port}")
                    
        except Exception as e:
            print(f"Error during scan: {e}")
        
        self.detected_printers = detected
        return detected

async def test_working_detector():
    """Test the working detector."""
    print("🚀 WORKING Multi-Printer Detection Test")
    print("=" * 45)
    
    detector = WorkingPrinterDetector()
    printers = await detector.scan_for_printers()
    
    print(f"\n📊 Results:")
    print(f"   Found: {len(printers)} real printer(s)")
    
    for i, printer in enumerate(printers, 1):
        print(f"\n   [{i}] {printer['name']}")
        print(f"       Port: {printer['port']}")
        print(f"       Baudrate: {printer['baudrate']}")
        print(f"       Type: {printer['type']}")
        print(f"       Response: {printer['firmware_response'][:50]}...")
    
    return printers

if __name__ == "__main__":
    asyncio.run(test_working_detector())
