#!/usr/bin/env python3
"""
Synchronous printer detection - working version
"""

import serial
import time
import sys
import os
import pytest
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_printer_support import PrinterType, PrinterBrand

def sync_detect_printer(port: str, timeout: float = 3.0):
    """Synchronous printer detection that actually works."""
    print(f"🔧 Testing {port} synchronously...")
    
    baudrates = [115200, 250000]
    
    for baudrate in baudrates:
        print(f"  📡 Trying {baudrate} baud...")
        
        try:
            with serial.Serial(port, baudrate, timeout=2.0) as ser:
                print(f"    ✅ Connected")
                
                # Wait for connection to settle
                time.sleep(1.0)
                
                # Clear buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Try different commands
                commands = [b'\n', b'M115\n', b'M105\n', b'?\n']
                response = ""
                
                for cmd in commands:
                    print(f"    📤 Sending: {repr(cmd)}")
                    ser.write(cmd)
                    time.sleep(0.8)  # Wait longer
                    
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        response += data
                        print(f"    📥 Got: {repr(data[:50])}")
                        
                        if len(response.strip()) > 2:
                            print(f"    🎉 DETECTED: Response length {len(response)}")
                            
                            # Determine printer type
                            if 'marlin' in response.lower():
                                printer_type = 'marlin'
                            elif 'prusa' in response.lower():
                                printer_type = 'prusa'
                            elif 'klipper' in response.lower():
                                printer_type = 'klipper'
                            else:
                                printer_type = 'unknown'
                            
                            return {
                                'port': port,
                                'baudrate': baudrate,
                                'type': printer_type,
                                'firmware_response': response.strip(),
                                'name': f"3D Printer ({printer_type})",
                                'detected': True
                            }
                
                print(f"    ❌ No response to any command")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    return None

@pytest.mark.asyncio
async def test_sync_detection():
    """Test the synchronous detection."""
    print("🚀 Synchronous Printer Detection Test")
    print("=" * 45)
    
    result = sync_detect_printer("/dev/ttyUSB0")
    
    if result:
        print(f"\n✅ SUCCESS! Printer detected:")
        print(f"   Name: {result['name']}")
        print(f"   Port: {result['port']}")
        print(f"   Baudrate: {result['baudrate']}")
        print(f"   Type: {result['type']}")
        print(f"   Response: {result['firmware_response'][:100]}...")
    else:
        print(f"\n❌ No printer detected")
    
    return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_sync_detection())
