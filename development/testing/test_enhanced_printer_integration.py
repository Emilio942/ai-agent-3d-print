#!/usr/bin/env python3
"""
Test Enhanced Printer Agent Integration
Direct test to validate multi-printer support integration
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test direct multi-printer support
from multi_printer_support import MultiPrinterDetector, PrinterProfileManager
from printer_emulator import PrinterEmulatorManager

async def test_enhanced_integration():
    """Test the enhanced printer support integration."""
    print("🚀 AI Agent 3D Print - Enhanced Printer Integration Test")
    print("=" * 65)
    
    # Test 1: Multi-Printer Detection
    print("\n1️⃣ Testing Multi-Printer Detection...")
    detector = MultiPrinterDetector()
    detected_printers = await detector.scan_for_printers(timeout=2.0)
    
    if detected_printers:
        print(f"✅ Found {len(detected_printers)} real printer(s):")
        for printer in detected_printers:
            print(f"   🖨️ {printer['name']} on {printer['port']}")
    else:
        print("⚠️ No real printers found - proceeding with emulated printers")
    
    # Test 2: Emulated Printers
    print("\n2️⃣ Testing Emulated Printers...")
    emulator_manager = PrinterEmulatorManager()
    
    available_emulators = ['ender3', 'prusa_mk3s', 'marlin_generic', 'klipper']
    emulated_printers = []
    
    for emulator_type in available_emulators:
        emulator = emulator_manager.get_emulator(emulator_type)
        status = emulator.get_status()
        
        printer_info = {
            'id': f"emulated_{emulator_type}",
            'name': f"{status['name']} (Emulated)",
            'type': 'emulated',
            'port': f"emulated://{emulator_type}",
            'firmware_type': emulator_type,
            'emulator': emulator
        }
        emulated_printers.append(printer_info)
        print(f"   🤖 {status['name']} (Emulated)")
    
    # Test 3: Communication with Emulated Printers
    print("\n3️⃣ Testing Communication with Emulated Printers...")
    
    # Test Ender 3 communication
    ender3_printer = None
    for printer in emulated_printers:
        if 'ender3' in printer['id']:
            ender3_printer = printer
            break
    
    if ender3_printer:
        print(f"\n🔌 Testing communication with: {ender3_printer['name']}")
        emulator = ender3_printer['emulator']
        
        # Test basic commands
        test_commands = [
            ("M115", "Firmware Info"),
            ("M105", "Temperature Status"),
            ("M114", "Current Position"),
            ("G28", "Home All Axes"),
            ("M104 S200", "Set Hotend to 200°C"),
            ("M140 S60", "Set Bed to 60°C")
        ]
        
        for command, description in test_commands:
            response = emulator.process_command(command)
            print(f"   > {command}  // {description}")
            print(f"   < {response[:60]}{'...' if len(response) > 60 else ''}")
    
    # Test 4: Profile Management
    print("\n4️⃣ Testing Printer Profile Management...")
    profile_manager = PrinterProfileManager()
    
    print("Available printer profiles:")
    for profile_name in profile_manager.profiles:
        profile = profile_manager.profiles[profile_name]
        print(f"   📋 {profile.name}")
        print(f"      Brand: {profile.brand.value}")
        print(f"      Firmware: {profile.firmware_type.value}")
        print(f"      Build Volume: {profile.build_volume[0]}x{profile.build_volume[1]}x{profile.build_volume[2]}mm")
        print(f"      Baudrate: {profile.connection_settings['baudrate']}")
    
    # Test 5: Summary
    print("\n5️⃣ Integration Summary:")
    total_printers = len(detected_printers) + len(emulated_printers)
    print(f"   📊 Total Printers Available: {total_printers}")
    print(f"   🖨️ Real Printers: {len(detected_printers)}")
    print(f"   🤖 Emulated Printers: {len(emulated_printers)}")
    print(f"   📋 Printer Profiles: {len(profile_manager.profiles)}")
    
    # Test 6: Printer Agent Integration Test
    print("\n6️⃣ Testing Printer Agent Integration...")
    try:
        from agents.printer_agent import PrinterAgent, ENHANCED_PRINTER_SUPPORT
        
        if ENHANCED_PRINTER_SUPPORT:
            print("✅ Enhanced printer support is available in PrinterAgent")
            
            # Create enhanced printer agent
            agent = PrinterAgent('integration_test', config={'mock_mode': True})
            
            # Test enhanced operations
            test_task = {
                'operation': 'detect_printers',
                'specifications': {'include_emulated': True}
            }
            
            result = await agent.execute_task(test_task)
            
            if result['success']:
                print(f"✅ Agent detected {result['count']} printers")
                print(f"   Enhanced Support: {result['enhanced_support']}")
                
                # Test discovery
                discovered = await agent.discover_all_printers(include_emulated=True)
                print(f"✅ Agent discovered {len(discovered)} printers via enhanced API")
            else:
                print(f"❌ Agent detection failed: {result.get('error_message')}")
        else:
            print("⚠️ Enhanced printer support not available in PrinterAgent")
            
    except Exception as e:
        print(f"❌ PrinterAgent integration error: {e}")
    
    print("\n✅ Enhanced Printer Integration Test Completed!")
    print(f"🎯 System Status: {'FULLY INTEGRATED' if ENHANCED_PRINTER_SUPPORT else 'BASIC MODE'}")


if __name__ == "__main__":
    asyncio.run(test_enhanced_integration())
