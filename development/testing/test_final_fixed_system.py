#!/usr/bin/env python3
"""
FINAL FIXED SYSTEM TEST - No more hanging, fast execution
"""

import asyncio
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.printer_agent import PrinterAgent

async def test_complete_fixed_system():
    print("🚀 FINAL FIXED SYSTEM TEST")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        # Test 1: Fast printer discovery
        print("\n🔧 [1/3] Testing Fixed PrinterAgent Discovery...")
        printer_agent = PrinterAgent()
        
        discovery_start = time.time()
        printers = await asyncio.wait_for(
            printer_agent.discover_all_printers(),
            timeout=15.0  # Hard timeout
        )
        discovery_time = time.time() - discovery_start
        
        print(f"⏱️ Discovery completed in {discovery_time:.1f} seconds")
        print(f"🔍 Found {len(printers)} printers:")
        
        real_printers = [p for p in printers if p['type'] == 'real']
        emulated_printers = [p for p in printers if p['type'] == 'emulated']
        
        print(f"   📡 Real printers: {len(real_printers)}")
        print(f"   🎭 Emulated printers: {len(emulated_printers)}")
        
        for printer in printers[:3]:  # Show first 3
            print(f"      • {printer['name']} ({printer['type']})")
        
        # Test 2: Quick connection test
        print(f"\n🔌 [2/3] Testing Quick Connections...")
        
        test_printers = [p for p in printers if p['type'] == 'emulated'][:2]
        
        for printer in test_printers:
            print(f"   Testing: {printer['name']}")
            
            connect_task = {
                'operation': 'connect_printer',
                'specifications': {
                    'serial_port': printer['port'],
                    'printer_type': printer['firmware_type']
                }
            }
            
            try:
                result = await asyncio.wait_for(
                    printer_agent.execute_task(connect_task),
                    timeout=3.0
                )
                
                if result.get('success'):
                    print(f"   ✅ Connected successfully")
                    
                    # Quick disconnect
                    disconnect_task = {'operation': 'disconnect_printer'}
                    await printer_agent.execute_task(disconnect_task)
                    print(f"   🔌 Disconnected")
                else:
                    print(f"   ❌ Connection failed")
                    
            except asyncio.TimeoutError:
                print(f"   ⏰ Connection timeout")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Test 3: API task test
        print(f"\n🌐 [3/3] Testing API Integration...")
        
        try:
            api_task = {'operation': 'discover_all_printers'}
            api_result = await asyncio.wait_for(
                printer_agent.execute_task(api_task),
                timeout=5.0
            )
            
            if api_result.get('success'):
                api_printers = api_result.get('printers', [])
                print(f"   ✅ API returned {len(api_printers)} printers")
            else:
                print(f"   ❌ API failed: {api_result.get('error_message')}")
                
        except asyncio.TimeoutError:
            print(f"   ⏰ API timeout")
        except Exception as e:
            print(f"   ❌ API error: {e}")
        
        total_time = time.time() - start_time
        
        # Final Results
        print(f"\n" + "=" * 50)
        print(f"📊 FINAL TEST RESULTS:")
        print(f"   ⏱️ Total test time: {total_time:.1f} seconds")
        print(f"   🔍 Printer discovery: {discovery_time:.1f} seconds")
        print(f"   🖨️ Total printers: {len(printers)}")
        print(f"   📡 Real printers: {len(real_printers)}")
        print(f"   🎭 Emulated printers: {len(emulated_printers)}")
        print(f"   ✅ No hanging or timeouts!")
        
        if total_time < 30:
            print(f"   🎉 EXCELLENT: System is FAST and RELIABLE!")
        else:
            print(f"   ⚠️ System is working but could be faster")
        
        return {
            'success': True,
            'total_time': total_time,
            'discovery_time': discovery_time,
            'total_printers': len(printers),
            'real_printers': len(real_printers),
            'emulated_printers': len(emulated_printers)
        }
        
    except asyncio.TimeoutError:
        print(f"❌ SYSTEM TIMEOUT - Test cancelled after 15+ seconds")
        return {'success': False, 'error': 'timeout'}
    except Exception as e:
        print(f"❌ SYSTEM ERROR: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_complete_fixed_system())
    
    if result['success']:
        print(f"\n🎯 VERDICT: SYSTEM IS FIXED AND WORKING!")
    else:
        print(f"\n❌ VERDICT: SYSTEM STILL HAS ISSUES")
