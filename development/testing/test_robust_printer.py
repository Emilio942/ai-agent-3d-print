#!/usr/bin/env python3
"""
Robust printer detection that works with problematic printers
"""

import asyncio
import sys
import os
import serial
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def robust_printer_test():
    print("🔧 Robust Printer Detection Test")
    print("=" * 40)
    
    port = "/dev/ttyUSB0"
    print(f"Testing {port}...")
    
    # Multiple attempts with different strategies
    for attempt in range(3):
        print(f"\n🔄 Attempt {attempt + 1}:")
        
        try:
            with serial.Serial(port, 115200, timeout=3.0) as ser:
                print("  ✅ Connection opened")
                
                # Strategy 1: Multiple commands with longer waits
                commands = [b'\n', b'M105\n', b'M115\n', b'M503\n', b'?\n']
                
                for i, cmd in enumerate(commands):
                    print(f"    📤 Sending: {repr(cmd)}")
                    
                    ser.reset_input_buffer()
                    ser.write(cmd)
                    
                    # Wait longer and check multiple times
                    for check in range(5):
                        time.sleep(0.4)
                        if ser.in_waiting > 0:
                            response = ser.read(ser.in_waiting)
                            if response:
                                print(f"    📥 Got response: {repr(response)}")
                                decoded = response.decode('utf-8', errors='ignore')
                                print(f"    📝 Decoded: {repr(decoded)}")
                                
                                if len(decoded.strip()) > 1:
                                    print(f"    🎉 PRINTER DETECTED!")
                                    print(f"       Command: {repr(cmd)}")
                                    print(f"       Response: {repr(decoded)}")
                                    return True
                    
                print("    ❌ No response to any command")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Wait between attempts
        if attempt < 2:
            print("  ⏳ Waiting 2 seconds before retry...")
            time.sleep(2.0)
    
    print(f"\n❌ Printer not responding after 3 attempts")
    print("Possible issues:")
    print("- Printer is off or in sleep mode")
    print("- Wrong baudrate (try different baudrates)")
    print("- Printer uses different protocol")
    print("- Hardware connection problem")
    
    return False

if __name__ == "__main__":
    asyncio.run(robust_printer_test())
