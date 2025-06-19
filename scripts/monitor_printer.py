#!/usr/bin/env python3
"""
3D Printer Real-Time Monitoring System

Dieses Script überwacht einen angeschlossenen 3D-Drucker in Echtzeit und verwendet
den echten Drucker (nicht Mock-Modus). Es erkennt automatisch den Drucker und 
stellt eine Live-Überwachung bereit.

Features:
- Automatische Drucker-Erkennung (CH340, Arduino, etc.)
- Echte Serial-Kommunikation (kein Mock-Modus)
- Live-Temperatur-Monitoring
- Drucker-Status-Überwachung
- G-Code-Befehle senden
- Kontinuierliche Überwachung
"""

import asyncio
import time
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Serial communication
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    print("❌ FEHLER: pyserial ist nicht installiert!")
    print("Installiere es mit: pip install pyserial")
    sys.exit(1)

from agents.printer_agent import PrinterAgent, PrinterStatus
from core.logger import get_logger

logger = get_logger(__name__)


class RealPrinterMonitor:
    """Echte 3D-Drucker Überwachung (kein Mock-Modus)."""
    
    def __init__(self):
        self.printer_agent = None
        self.monitoring_active = False
        self.last_status = None
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        
    def detect_printers(self) -> List[Dict[str, Any]]:
        """Erkenne angeschlossene 3D-Drucker."""
        print("🔍 Suche nach angeschlossenen 3D-Druckern...")
        
        detected_printers = []
        ports = serial.tools.list_ports.comports()
        
        print(f"📋 Gefundene USB-Geräte ({len(ports)}):")
        
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port.device}")
            print(f"     - Beschreibung: {port.description}")
            print(f"     - Hersteller: {port.manufacturer}")
            print(f"     - Produkt: {port.product}")
            print(f"     - VID:PID: {port.vid:04x}:{port.pid:04x}" if port.vid and port.pid else "     - VID:PID: Unbekannt")
            
            # Typische 3D-Drucker-Identifikatoren
            description_lower = (port.description or "").lower()
            manufacturer_lower = (port.manufacturer or "").lower()
            
            is_potential_printer = any(keyword in description_lower or keyword in manufacturer_lower 
                                     for keyword in [
                                         'ch340', 'ch341',  # Chinesische USB-Serial-Konverter
                                         'arduino', 'mega',  # Arduino-basierte Drucker
                                         'cp210', 'cp2102',  # Silicon Labs USB-Serial
                                         'ftdi', 'ft232',    # FTDI USB-Serial
                                         'usb-serial', 'serial',
                                         'qinheng',          # QinHeng Electronics (CH340)
                                     ])
            
            if is_potential_printer:
                detected_printers.append({
                    'port': port.device,
                    'description': port.description,
                    'manufacturer': port.manufacturer,
                    'product': port.product,
                    'vid_pid': f"{port.vid:04x}:{port.pid:04x}" if port.vid and port.pid else "unknown"
                })
                print(f"     ✅ Potenzieller 3D-Drucker erkannt!")
            else:
                print(f"     ❌ Kein 3D-Drucker")
            print()
        
        print(f"🎯 {len(detected_printers)} potenzielle 3D-Drucker gefunden")
        return detected_printers
    
    async def connect_to_printer(self, port: Optional[str] = None) -> bool:
        """Verbinde mit dem 3D-Drucker."""
        print("🔗 Verbinde mit 3D-Drucker...")
        
        # Erstelle PrinterAgent mit ECHTEM Modus (kein Mock!)
        config = {
            'mock_mode': False,  # ✅ WICHTIG: Mock-Modus deaktiviert!
            'baudrate': 250000,  # ✅ KORREKTE BAUDRATE für Geeetech I3
            'timeout': 10,
            'reconnect_attempts': 3
        }
        
        self.printer_agent = PrinterAgent("real_printer_monitor", config=config)
        
        if not port:
            # Auto-Erkennung
            detected = self.detect_printers()
            if not detected:
                print("❌ Keine 3D-Drucker gefunden!")
                return False
            
            # Versuche jeden erkannten Drucker
            for printer_info in detected:
                print(f"🔄 Versuche Verbindung mit {printer_info['port']}...")
                if await self._try_connect(printer_info['port']):
                    return True
                self.connection_attempts += 1
                
            print("❌ Verbindung zu allen erkannten Druckern fehlgeschlagen!")
            return False
        else:
            # Spezifischer Port
            return await self._try_connect(port)
    
    async def _try_connect(self, port: str) -> bool:
        """Versuche Verbindung zu einem spezifischen Port."""
        try:
            print(f"  📡 Verbindungsversuch {self.connection_attempts + 1}/{self.max_connection_attempts}")
            print(f"  🔌 Port: {port}")
            print(f"  ⚡ Baudrate: 250000")
            
            # Verbindungsanfrage
            result = await self.printer_agent.execute_task({
                'operation': 'connect_printer',
                'specifications': {
                    'serial_port': port,
                    'baudrate': 250000  # ✅ KORREKTE BAUDRATE für Geeetech I3
                }
            })
            
            if result.get('success', False):
                print(f"  ✅ Erfolgreich verbunden!")
                print(f"  📋 Drucker-ID: {result.get('printer_id', 'unknown')}")
                print(f"  🔧 Firmware: {result.get('firmware', 'unknown')}")
                print(f"  📊 Status: {result.get('status', 'unknown')}")
                print(f"  🎯 Mock-Modus: {result.get('is_mock', 'unknown')}")
                return True
            else:
                print(f"  ❌ Verbindung fehlgeschlagen: {result.get('error_message', 'Unbekannter Fehler')}")
                return False
                
        except Exception as e:
            print(f"  💥 Fehler bei Verbindungsversuch: {e}")
            return False
    
    async def get_printer_status(self) -> Optional[Dict[str, Any]]:
        """Hole aktuellen Drucker-Status."""
        if not self.printer_agent:
            return None
            
        try:
            result = await self.printer_agent.execute_task({
                'operation': 'get_printer_status',
                'specifications': {}
            })
            
            if result.get('success', False):
                return result
            else:
                print(f"❌ Status-Abfrage fehlgeschlagen: {result.get('error_message', 'Unbekannt')}")
                return None
                
        except Exception as e:
            print(f"💥 Fehler bei Status-Abfrage: {e}")
            return None
    
    async def send_gcode_command(self, command: str) -> Optional[str]:
        """Sende G-Code-Befehl an den Drucker."""
        if not self.printer_agent:
            print("❌ Kein Drucker verbunden!")
            return None
            
        try:
            print(f"📤 Sende G-Code: {command}")
            
            result = await self.printer_agent.execute_task({
                'operation': 'send_gcode_command',
                'specifications': {
                    'command': command
                }
            })
            
            if result.get('success', False):
                response = result.get('response', '')
                print(f"📥 Antwort: {response}")
                return response
            else:
                print(f"❌ G-Code fehlgeschlagen: {result.get('error_message', 'Unbekannt')}")
                return None
                
        except Exception as e:
            print(f"💥 Fehler beim G-Code senden: {e}")
            return None
    
    async def monitor_continuously(self, interval: float = 5.0):
        """Kontinuierliche Überwachung des Druckers."""
        print(f"👁️  Starte kontinuierliche Überwachung (alle {interval}s)")
        print("   Drücke Ctrl+C zum Beenden")
        print("=" * 60)
        
        self.monitoring_active = True
        
        try:
            while self.monitoring_active:
                # Status-Update
                status = await self.get_printer_status()
                
                if status:
                    self._display_status(status)
                else:
                    print("❌ Verbindung zum Drucker verloren!")
                    
                    # Versuche Wiederverbindung
                    print("🔄 Versuche Wiederverbindung...")
                    if await self.connect_to_printer():
                        print("✅ Wiederverbindung erfolgreich!")
                    else:
                        print("❌ Wiederverbindung fehlgeschlagen!")
                        break
                
                # Warte bis zur nächsten Aktualisierung
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Überwachung durch Benutzer gestoppt")
            self.monitoring_active = False
    
    def _display_status(self, status: Dict[str, Any]):
        """Zeige aktuellen Status an."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Status-Header
        print(f"\n[{timestamp}] 📊 Drucker-Status:")
        
        # Grundlegende Informationen
        print(f"  Status: {status.get('status', 'unknown')}")
        
        # Temperatur-Informationen
        temp_data = status.get('temperature', {})
        if temp_data:
            hotend_current = temp_data.get('hotend_current', 0)
            hotend_target = temp_data.get('hotend_target', 0)
            bed_current = temp_data.get('bed_current', 0)
            bed_target = temp_data.get('bed_target', 0)
            
            print(f"  🌡️  Hotend: {hotend_current:.1f}°C / {hotend_target:.1f}°C")
            print(f"  🛏️  Bett: {bed_current:.1f}°C / {bed_target:.1f}°C")
        
        # Position (falls verfügbar)
        position = status.get('position', {})
        if position:
            x = position.get('x', 0)
            y = position.get('y', 0)
            z = position.get('z', 0)
            print(f"  📍 Position: X:{x:.2f} Y:{y:.2f} Z:{z:.2f}")
        
        # Drucker-Informationen
        printer_info = status.get('printer_info', {})
        if printer_info:
            print(f"  🏷️  Name: {printer_info.get('name', 'unknown')}")
            print(f"  🔧 Firmware: {printer_info.get('firmware_version', 'unknown')}")
        
        # Verbindungs-Informationen
        connection_info = status.get('connection_info', {})
        if connection_info:
            port = connection_info.get('port', 'unknown')
            baudrate = connection_info.get('baudrate', 'unknown')
            print(f"  🔌 Verbindung: {port} @ {baudrate} baud")
        
        print("-" * 60)
    
    async def interactive_mode(self):
        """Interaktiver Modus für G-Code-Befehle."""
        print("\n🎮 Interaktiver Modus gestartet")
        print("Gebe G-Code-Befehle ein (z.B. M105, M115, G28)")
        print("Spezielle Befehle:")
        print("  'status'  - Zeige detaillierten Status")
        print("  'monitor' - Starte kontinuierliche Überwachung")
        print("  'quit'    - Beenden")
        print()
        
        while True:
            try:
                command = input("G-Code> ").strip()
                
                if command.lower() in ['quit', 'exit', 'q']:
                    break
                elif command.lower() == 'status':
                    status = await self.get_printer_status()
                    if status:
                        self._display_status(status)
                elif command.lower() == 'monitor':
                    await self.monitor_continuously()
                    break
                elif command:
                    await self.send_gcode_command(command)
                
            except KeyboardInterrupt:
                break
    
    async def shutdown(self):
        """Herunterfahren und Aufräumen."""
        print("\n🔽 Fahre System herunter...")
        
        self.monitoring_active = False
        
        if self.printer_agent:
            try:
                # Drucker trennen
                await self.printer_agent.execute_task({
                    'operation': 'disconnect_printer',
                    'specifications': {}
                })
                print("✅ Drucker getrennt")
            except Exception as e:
                print(f"⚠️  Fehler beim Trennen: {e}")
        
        print("✅ System heruntergefahren")


async def main():
    """Hauptfunktion."""
    print("🖨️  3D-Drucker Echtzeit-Überwachung")
    print("===================================")
    print("Dieses System verwendet den ECHTEN Drucker (kein Mock-Modus)")
    print()
    
    monitor = RealPrinterMonitor()
    
    try:
        # Versuche Verbindung zum Drucker
        if await monitor.connect_to_printer():
            print("\n🎉 Erfolgreich mit Drucker verbunden!")
            print()
            
            # Zeige ersten Status
            initial_status = await monitor.get_printer_status()
            if initial_status:
                monitor._display_status(initial_status)
            
            # Starte interaktiven Modus
            await monitor.interactive_mode()
        else:
            print("\n❌ Konnte keine Verbindung zum Drucker herstellen!")
            print("\nMögliche Lösungen:")
            print("1. Überprüfe USB-Verbindung")
            print("2. Stelle sicher, dass der Drucker eingeschaltet ist")
            print("3. Prüfe, ob andere Software den Port verwendet")
            print("4. Überprüfe Berechtigungen für USB-Geräte")
            
    except KeyboardInterrupt:
        print("\n⏹️  Programm durch Benutzer gestoppt")
    
    finally:
        await monitor.shutdown()


if __name__ == "__main__":
    # Prüfe Berechtigungen
    print("🔐 Prüfe System-Berechtigungen...")
    
    # Prüfe USB-Geräte
    try:
        ports = serial.tools.list_ports.comports()
        print(f"✅ USB-Zugriff verfügbar ({len(ports)} Geräte)")
    except Exception as e:
        print(f"❌ USB-Zugriff-Fehler: {e}")
        print("Möglicherweise fehlende Berechtigungen für USB-Geräte")
        print("Versuche: sudo usermod -a -G dialout $USER")
        sys.exit(1)
    
    # Starte Hauptprogramm
    asyncio.run(main())
