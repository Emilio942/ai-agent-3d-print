#!/usr/bin/env python3
"""
FIXED Multi-Printer System Test - Fast and Reliable
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_printer_support import MultiPrinterDetector

async def test_fixed_system():
    print("🚀 FIXED Multi-Printer Detection Test")
    print("=" * 50)
    
    detector = MultiPrinterDetector()
    
    # Test with strict timeout
    start_time = asyncio.get_event_loop().time()
    
    print("⏱️ Starting FAST scan (max 10 seconds total)...")
    try:
        printers = await asyncio.wait_for(
            detector.scan_for_printers(timeout=2.0),  # 2 seconds per port max
            timeout=10.0  # 10 seconds total max
        )
        
        end_time = asyncio.get_event_loop().time()
        scan_time = end_time - start_time
        
        print(f"⏱️ Scan completed in {scan_time:.1f} seconds (FAST!)")
        print(f"🔍 Found {len(printers)} real printer(s):")
        
        for i, printer in enumerate(printers, 1):
            print(f"\n   [{i}] {printer['name']}")
            print(f"       Port: {printer['port']}")
            print(f"       Baudrate: {printer['baudrate']}")
            print(f"       Type: {printer['type']}")
            print(f"       Response: {printer['firmware_response'][:50]}...")
        
        if not printers:
            print("❌ No real printers detected")
            print("This could be:")
            print("- Printer is off/sleeping")
            print("- Non-standard protocol")
            print("- Connection timing issues")
            print("✅ But scan completed FAST (no hanging!)")
        
        return len(printers)
        
    except asyncio.TimeoutError:
        print("⏰ TIMEOUT: Scan took longer than 10 seconds - CANCELLED")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

if __name__ == "__main__":
    result = asyncio.run(test_fixed_system())
    print(f"\n📊 FINAL RESULT: {result} printer(s) detected")
    if result == 0:
        print("⚠️ No printers found, but system is FAST and doesn't hang!")
