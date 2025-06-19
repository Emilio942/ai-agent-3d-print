#!/usr/bin/env python3
"""
Debug real printer connection step by step
"""

import serial
import time
import sys

def test_serial_connection():
    print("🔧 Debug: Testing Serial Connection to /dev/ttyUSB0")
    print("=" * 55)
    
    port = "/dev/ttyUSB0"
    baudrates = [115200, 250000, 9600, 57600]
    
    for baudrate in baudrates:
        print(f"\n📡 Testing {port} at {baudrate} baud...")
        
        try:
            with serial.Serial(port, baudrate, timeout=2.0) as ser:
                print(f"   ✅ Connection opened successfully")
                
                # Wait for initialization
                time.sleep(1.0)
                
                # Clear buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                print(f"   📤 Sending M115 command...")
                ser.write(b'M115\n')
                
                time.sleep(1.0)
                
                # Read any response
                response = ""
                attempts = 0
                while attempts < 10:
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        response += data
                        print(f"   📥 Received: {repr(data)}")
                    time.sleep(0.2)
                    attempts += 1
                
                if response.strip():
                    print(f"   ✅ Full response: {repr(response)}")
                    if 'ok' in response.lower() or 'firmware' in response.lower():
                        print(f"   🎉 PRINTER DETECTED!")
                        return True
                else:
                    print(f"   ❌ No response received")
                    
                # Try alternative commands
                for cmd in [b'M105\n', b'G28\n', b'\n']:
                    print(f"   📤 Trying command: {repr(cmd)}")
                    ser.write(cmd)
                    time.sleep(0.5)
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        print(f"   📥 Response: {repr(data)}")
                        if data.strip():
                            print(f"   🎉 PRINTER RESPONDED!")
                            return True
                    
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
    
    print(f"\n❌ No printer responses on any baudrate")
    return False

if __name__ == "__main__":
    test_serial_connection()
