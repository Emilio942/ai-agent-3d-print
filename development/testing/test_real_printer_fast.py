#!/usr/bin/env python3
"""
Quick test for real printer detection
"""

import asyncio
import sys
import os
import pytest
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_printer_support import MultiPrinterDetector

@pytest.mark.asyncio
async def test_real_printer_detection():
    print("🔧 Testing REAL Printer Detection (Fast Version)")
    print("=" * 50)
    
    detector = MultiPrinterDetector()
    
    print("⏱️ Starting scan with 2-second timeout...")
    start_time = asyncio.get_event_loop().time()
    
    try:
        printers = await detector.scan_for_printers(timeout=2.0)
        end_time = asyncio.get_event_loop().time()
        
        print(f"⏱️ Scan completed in {end_time - start_time:.1f} seconds")
        print(f"🔍 Found {len(printers)} printer(s):")
        
        for i, printer in enumerate(printers, 1):
            print(f"\n   [{i}] {printer['name']}")
            print(f"       Port: {printer['port']}")
            print(f"       Baudrate: {printer['baudrate']}")
            print(f"       Type: {printer['type']}")
            print(f"       Firmware: {printer['firmware_response'][:100]}...")
        
        if not printers:
            print("❌ No real printers found")
            print("   Make sure your 3D printer is:")
            print("   - Connected via USB")
            print("   - Powered on")
            print("   - Shows up as /dev/ttyUSB* or /dev/ttyACM*")
            
    except Exception as e:
        print(f"❌ Error during scan: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_printer_detection())
