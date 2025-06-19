#!/usr/bin/env python3
"""
Einfaches 3D-Drucker Monitoring

Direktes Monitoring ohne komplexe Agent-Struktur.
Überwacht den Geeetech I3 Drucker in Echtzeit.
"""

import serial
import time
import threading
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import re

class SimplePrinterMonitor:
    """Einfaches 3D-Drucker Monitoring ohne Agent-System."""
    
    def __init__(self, port='/dev/ttyUSB0', baudrate=250000):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.monitoring_active = False
        self.last_temperatures = {'hotend': 0, 'bed': 0}
        self.firmware_info = "Unknown"
        
    def connect(self) -> bool:
        """Verbinde direkt mit dem Drucker."""
        try:
            print(f"🔗 Verbinde mit {self.port} @ {self.baudrate} baud...")
            
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2,
                write_timeout=2
            )
            
            print("⏱️  Warte auf Drucker-Initialisierung...")
            time.sleep(3)  # Gib dem Drucker Zeit sich zu initialisieren
            
            # Teste Verbindung mit M115 (Firmware Info)
            print("📡 Teste Verbindung...")
            response = self.send_command("M115")
            
            if response and ("marlin" in response.lower() or "firmware" in response.lower()):
                print(f"✅ Verbindung erfolgreich!")
                print(f"🔧 Firmware: {response[:60]}...")
                self.firmware_info = response
                return True
            else:
                print(f"❌ Unerwartete Antwort: {response}")
                return False
                
        except Exception as e:
            print(f"❌ Verbindungsfehler: {e}")
            return False
    
    def send_command(self, command: str, timeout: float = 3.0) -> Optional[str]:
        """Sende G-Code-Befehl und warte auf Antwort."""
        if not self.serial_connection or not self.serial_connection.is_open:
            return None
            
        try:
            # Sende Befehl
            cmd_with_newline = f"{command}\n"
            self.serial_connection.write(cmd_with_newline.encode('utf-8'))
            self.serial_connection.flush()
            
            # Sammle Antwort
            response_lines = []
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.serial_connection.in_waiting > 0:
                    try:
                        line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            response_lines.append(line)
                            print(f"📥 {line}")  # Debug: zeige alle empfangenen Zeilen
                            
                            # Bei "ok" oder "Error" ist die Antwort komplett
                            if line.startswith('ok') or line.startswith('Error'):
                                break
                    except Exception as e:
                        print(f"⚠️  Dekodierungsfehler: {e}")
                        
                time.sleep(0.01)
            
            return '\n'.join(response_lines) if response_lines else None
            
        except Exception as e:
            print(f"❌ Sende-Fehler: {e}")
            return None
    
    def get_temperature(self) -> Dict[str, float]:
        """Hole aktuelle Temperaturen."""
        response = self.send_command("M105")
        temperatures = {'hotend': 0.0, 'bed': 0.0, 'hotend_target': 0.0, 'bed_target': 0.0}
        
        if response:
            # Parse Temperatur-Response: "ok T:25.0/0.0 B:24.0/0.0"
            temp_match = re.search(r'T:(\d+\.?\d*)/(\d+\.?\d*)', response)
            bed_match = re.search(r'B:(\d+\.?\d*)/(\d+\.?\d*)', response)
            
            if temp_match:
                temperatures['hotend'] = float(temp_match.group(1))
                temperatures['hotend_target'] = float(temp_match.group(2))
            
            if bed_match:
                temperatures['bed'] = float(bed_match.group(1))
                temperatures['bed_target'] = float(bed_match.group(2))
        
        return temperatures
    
    def get_position(self) -> Dict[str, float]:
        """Hole aktuelle Position."""
        response = self.send_command("M114")
        position = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'e': 0.0}
        
        if response:
            # Parse Position: "X:0.00 Y:0.00 Z:0.00 E:0.00"
            x_match = re.search(r'X:(-?\d+\.?\d*)', response)
            y_match = re.search(r'Y:(-?\d+\.?\d*)', response)
            z_match = re.search(r'Z:(-?\d+\.?\d*)', response)
            e_match = re.search(r'E:(-?\d+\.?\d*)', response)
            
            if x_match: position['x'] = float(x_match.group(1))
            if y_match: position['y'] = float(y_match.group(1))
            if z_match: position['z'] = float(z_match.group(1))
            if e_match: position['e'] = float(e_match.group(1))
        
        return position
    
    def display_status(self):
        """Zeige aktuellen Status."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n{'='*60}")
        print(f"[{timestamp}] 📊 3D-Drucker Status (Geeetech I3)")
        print(f"{'='*60}")
        
        # Temperaturen
        temps = self.get_temperature()
        print(f"🌡️  Hotend: {temps['hotend']:.1f}°C / {temps['hotend_target']:.1f}°C")
        print(f"🛏️  Heizbett: {temps['bed']:.1f}°C / {temps['bed_target']:.1f}°C")
        
        # Position
        pos = self.get_position()
        print(f"📍 Position: X:{pos['x']:.2f} Y:{pos['y']:.2f} Z:{pos['z']:.2f} E:{pos['e']:.2f}")
        
        # Verbindung
        print(f"🔌 Verbindung: {self.port} @ {self.baudrate} baud")
        print(f"🔧 Firmware: Marlin (Geeetech I3)")
        
        print(f"{'='*60}")
    
    def continuous_monitoring(self, interval: float = 5.0):
        """Kontinuierliche Überwachung."""
        print(f"👁️  Starte kontinuierliche Überwachung (alle {interval}s)")
        print("Drücke Ctrl+C zum Beenden")
        
        self.monitoring_active = True
        
        try:
            while self.monitoring_active:
                self.display_status()
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Überwachung gestoppt")
            self.monitoring_active = False
    
    def interactive_mode(self):
        """Interaktiver Modus."""
        print("\n🎮 Interaktiver Modus")
        print("Verfügbare Befehle:")
        print("  M105      - Temperaturen abfragen")
        print("  M114      - Position abfragen")
        print("  M115      - Firmware-Info")
        print("  G28       - Home alle Achsen")
        print("  G28 X     - Home X-Achse")
        print("  G28 Y     - Home Y-Achse")  
        print("  G28 Z     - Home Z-Achse")
        print("  monitor   - Kontinuierliche Überwachung")
        print("  status    - Aktueller Status")
        print("  quit      - Beenden")
        print()
        
        while True:
            try:
                command = input("G-Code> ").strip()
                
                if command.lower() in ['quit', 'exit', 'q']:
                    break
                elif command.lower() == 'monitor':
                    self.continuous_monitoring()
                    break
                elif command.lower() == 'status':
                    self.display_status()
                elif command:
                    print(f"📤 Sende: {command}")
                    response = self.send_command(command)
                    if response:
                        print(f"📥 Antwort: {response}")
                    else:
                        print("❌ Keine Antwort oder Timeout")
                
            except KeyboardInterrupt:
                break
    
    def disconnect(self):
        """Trenne Verbindung."""
        self.monitoring_active = False
        
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("✅ Verbindung getrennt")


def main():
    """Hauptfunktion."""
    print("🖨️  Einfaches 3D-Drucker Monitoring")
    print("===================================")
    print("Geeetech I3 mit Marlin Firmware")
    print("Port: /dev/ttyUSB0 @ 250000 baud")
    print()
    
    monitor = SimplePrinterMonitor()
    
    try:
        if monitor.connect():
            print("\n🎉 Bereit für Monitoring!")
            
            # Zeige ersten Status
            monitor.display_status()
            
            # Starte interaktiven Modus
            monitor.interactive_mode()
        else:
            print("\n❌ Verbindung fehlgeschlagen!")
            print("\nTipps:")
            print("1. Ist der Drucker eingeschaltet?")
            print("2. USB-Kabel richtig angeschlossen?")
            print("3. Andere Software schließen (OctoPrint, etc.)")
            
    except KeyboardInterrupt:
        print("\n⏹️  Programm gestoppt")
    
    finally:
        monitor.disconnect()


if __name__ == "__main__":
    main()
