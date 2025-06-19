#!/usr/bin/env python3
"""
Quick-Start: 3D-Drucker Überwachung

Einfaches Script zum schnellen Starten der Drucker-Überwachung.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.monitor_printer import RealPrinterMonitor


async def quick_monitor():
    """Quick-Start Überwachung."""
    print("🚀 Quick-Start: 3D-Drucker Überwachung")
    print("=====================================")
    
    monitor = RealPrinterMonitor()
    
    try:
        # Auto-Connect
        print("🔍 Suche und verbinde automatisch mit 3D-Drucker...")
        if await monitor.connect_to_printer():
            print("✅ Verbunden! Starte Überwachung...")
            await monitor.monitor_continuously(interval=3.0)
        else:
            print("❌ Kein Drucker gefunden oder Verbindung fehlgeschlagen!")
    
    except KeyboardInterrupt:
        print("\n⏹️  Gestoppt")
    
    finally:
        await monitor.shutdown()


if __name__ == "__main__":
    asyncio.run(quick_monitor())
