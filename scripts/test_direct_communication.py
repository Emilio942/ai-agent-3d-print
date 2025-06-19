#!/usr/bin/env python3
"""
Direkter 3D-Drucker Kommunikations-Test

Testet die serielle Kommunikation direkt ohne das komplexe System.
"""

import serial
import time
import sys

def test_printer_communication(port='/dev/ttyUSB0', baudrate=115200):
    """Teste direkte Kommunikation mit dem 3D-Drucker."""
    print(f"🔧 Teste direkte Kommunikation mit {port}")
    print(f"⚡ Baudrate: {baudrate}")
    
    try:
        # Öffne serielle Verbindung
        print("🔗 Öffne serielle Verbindung...")
        ser = serial.Serial(port, baudrate, timeout=5)
        time.sleep(2)  # Warte auf Drucker-Initialisierung
        
        print("✅ Verbindung hergestellt")
        print("📡 Warte auf spontane Nachrichten vom Drucker...")
        
        # Höre 5 Sekunden auf spontane Nachrichten
        for i in range(50):  # 5 Sekunden, 0.1s pro Iteration
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"📥 Empfangen (spontan): {line}")
            time.sleep(0.1)
        
        # Teste bekannte G-Code-Befehle
        test_commands = [
            "M115",  # Firmware-Info
            "M105",  # Temperatur
            "G28",   # Home
            "M114",  # Position
        ]
        
        for cmd in test_commands:
            print(f"\n📤 Sende: {cmd}")
            ser.write(f"{cmd}\n".encode('utf-8'))
            ser.flush()
            
            # Warte auf Antwort
            start_time = time.time()
            response_received = False
            
            while time.time() - start_time < 3:  # 3 Sekunden Timeout
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"📥 Antwort: {line}")
                        response_received = True
                        if line.startswith('ok') or 'Error' in line:
                            break
                time.sleep(0.01)
            
            if not response_received:
                print("❌ Keine Antwort erhalten")
        
        ser.close()
        print("\n✅ Test abgeschlossen")
        
    except serial.SerialException as e:
        print(f"❌ Serieller Fehler: {e}")
    except Exception as e:
        print(f"💥 Unerwarteter Fehler: {e}")

def test_different_baudrates(port='/dev/ttyUSB0'):
    """Teste verschiedene Baudraten."""
    baudrates = [115200, 250000, 9600, 57600, 38400, 19200]
    
    print(f"🎯 Teste verschiedene Baudraten für {port}")
    
    for baudrate in baudrates:
        print(f"\n{'='*50}")
        print(f"🔧 Teste Baudrate: {baudrate}")
        
        try:
            ser = serial.Serial(port, baudrate, timeout=2)
            time.sleep(1)
            
            # Sende einfachen Test-Befehl
            ser.write(b"M115\n")
            ser.flush()
            
            response = ""
            start_time = time.time()
            
            while time.time() - start_time < 2:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response += line + " "
                        if 'ok' in line.lower() or 'firmware' in line.lower():
                            break
                time.sleep(0.01)
            
            ser.close()
            
            if response:
                print(f"✅ Antwort bei {baudrate}: {response}")
                return baudrate  # Erfolgreiche Baudrate gefunden
            else:
                print(f"❌ Keine Antwort bei {baudrate}")
                
        except Exception as e:
            print(f"❌ Fehler bei {baudrate}: {e}")
    
    print("\n❌ Keine funktionierende Baudrate gefunden")
    return None

if __name__ == "__main__":
    port = '/dev/ttyUSB0'
    
    print("🖨️  Direkter 3D-Drucker Kommunikations-Test")
    print("===========================================")
    
    # Prüfe ob Port existiert
    try:
        import os
        if not os.path.exists(port):
            print(f"❌ Port {port} existiert nicht!")
            sys.exit(1)
        
        # Teste zuerst mit Standard-Baudrate
        print("Phase 1: Standard-Kommunikationstest")
        test_printer_communication(port, 115200)
        
        print("\n" + "="*60)
        print("Phase 2: Baudrate-Scan")
        working_baudrate = test_different_baudrates(port)
        
        if working_baudrate:
            print(f"\n🎉 Funktionierende Baudrate gefunden: {working_baudrate}")
            print("\nPhase 3: Erweiterte Tests mit funktionierender Baudrate")
            test_printer_communication(port, working_baudrate)
        
    except KeyboardInterrupt:
        print("\n⏹️  Test durch Benutzer gestoppt")
    except Exception as e:
        print(f"💥 Allgemeiner Fehler: {e}")
