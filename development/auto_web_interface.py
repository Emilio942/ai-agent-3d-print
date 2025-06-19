#!/usr/bin/env python3
"""
Automatisches Web-Interface mit 3D-Drucker Integration
Startet das Web-Interface und verbindet automatisch den angeschlossenen Drucker
"""

import os
import sys
import time
import requests
import subprocess
import webbrowser
import asyncio
from datetime import datetime

class AutoWebInterface:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.server_process = None
        self.printer_connected = False
        
    def start_server(self):
        """Starte den API Server"""
        print("🚀 Starte AI Agent 3D Print System API Server...")
        
        try:
            # Prüfe ob Server bereits läuft
            response = requests.get(f"{self.base_url}/health", timeout=2)
            print("✅ Server bereits aktiv")
            return True
        except:
            pass
        
        # Starte neuen Server
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, "api/main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            # Warte bis Server bereit ist
            for i in range(30):
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=1)
                    if response.status_code == 200:
                        print("✅ Server erfolgreich gestartet")
                        return True
                except:
                    pass
                time.sleep(1)
                print(f"  Warte auf Server... ({i+1}/30)")
            
            print("❌ Server-Start fehlgeschlagen")
            return False
            
        except Exception as e:
            print(f"❌ Fehler beim Server-Start: {e}")
            return False
    
    def detect_printer(self):
        """Erkenne angeschlossenen 3D-Drucker"""
        print("🔍 Suche nach angeschlossenem 3D-Drucker...")
        
        try:
            # Prüfe verfügbare serielle Ports
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            
            printer_ports = []
            for port in ports:
                if port.device.startswith('/dev/ttyUSB') or port.device.startswith('/dev/ttyACM'):
                    printer_ports.append(port)
                    print(f"  📡 Gefunden: {port.device} - {port.description}")
            
            if not printer_ports:
                print("⚠️ Kein 3D-Drucker gefunden (USB/ACM Ports)")
                return None
            
            return printer_ports[0].device
            
        except Exception as e:
            print(f"❌ Drucker-Erkennung fehlgeschlagen: {e}")
            return None
    
    def connect_printer(self, port):
        """Verbinde mit 3D-Drucker über API"""
        print(f"🔌 Verbinde mit Drucker an {port}...")
        
        try:
            # Drucker-Verbindung über API
            response = requests.post(
                f"{self.base_url}/api/printer/connect",
                json={
                    "port": port,
                    "baudrate": 115200,
                    "mock_mode": False
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.printer_connected = True
                    print("✅ Drucker erfolgreich verbunden")
                    print(f"   📊 Status: {result.get('status')}")
                    print(f"   🏷️ Typ: {result.get('printer_info', {}).get('name', 'Unbekannt')}")
                    return True
                else:
                    print(f"❌ Verbindung fehlgeschlagen: {result.get('error')}")
            else:
                print(f"❌ API-Fehler: {response.status_code}")
                # Fallback: Verwende Mock-Mode
                print("🎭 Fallback zu Mock-Mode...")
                return self.connect_mock_printer()
            
        except Exception as e:
            print(f"❌ Verbindungsfehler: {e}")
            # Fallback: Verwende Mock-Mode
            print("🎭 Fallback zu Mock-Mode...")
            return self.connect_mock_printer()
        
        return False
    
    def connect_mock_printer(self):
        """Verbinde Mock-Drucker für Demo"""
        try:
            # Mock-Drucker über API verbinden
            response = requests.post(
                f"{self.base_url}/api/printer/connect",
                json={"mock_mode": True},
                timeout=5
            )
            
            if response.status_code == 200:
                self.printer_connected = True
                print("✅ Mock-Drucker verbunden (Demo-Mode)")
                return True
            
        except Exception as e:
            print(f"❌ Mock-Drucker Fehler: {e}")
        
        return False
    
    def open_browser(self):
        """Öffne Web-Browser mit Interface"""
        print("🌐 Öffne Web-Interface im Browser...")
        
        try:
            # Öffne Browser
            webbrowser.open(self.base_url)
            print(f"✅ Browser geöffnet: {self.base_url}")
            return True
            
        except Exception as e:
            print(f"❌ Browser-Start fehlgeschlagen: {e}")
            print(f"💡 Öffne manuell: {self.base_url}")
            return False
    
    def show_system_status(self):
        """Zeige aktuellen System-Status"""
        print("\n" + "="*60)
        print("📊 SYSTEM STATUS")
        print("="*60)
        
        try:
            # Health Check
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                print(f"🚀 System Status: {health['status']}")
                print(f"⏱️ Uptime: {health['uptime_seconds']:.1f}s")
                print(f"📋 Aktive Workflows: {health['active_workflows']}")
                print(f"✅ Abgeschlossene Jobs: {health['total_completed']}")
                
                # Agenten Status
                print("\n🤖 AGENTEN STATUS:")
                for agent, status in health['agents_status'].items():
                    status_icon = "✅" if status == "healthy" else "⚠️"
                    print(f"  {status_icon} {agent.capitalize()}: {status}")
                
                # System Metriken
                metrics = health.get('system_metrics', {})
                if metrics:
                    print("\n📈 SYSTEM METRIKEN:")
                    print(f"  💾 CPU: {metrics.get('cpu_usage_percent', 0):.1f}%")
                    print(f"  🧠 Memory: {metrics.get('memory_usage_percent', 0):.1f}%")
                    print(f"  💽 Disk: {metrics.get('disk_usage_percent', 0):.1f}%")
                
            else:
                print("❌ System Status nicht verfügbar")
                
        except Exception as e:
            print(f"❌ Status-Abfrage fehlgeschlagen: {e}")
        
        # Drucker Status
        print(f"\n🖨️ DRUCKER STATUS:")
        if self.printer_connected:
            try:
                response = requests.get(f"{self.base_url}/api/printer/status", timeout=5)
                if response.status_code == 200:
                    printer_status = response.json()
                    print(f"  🔌 Verbindung: ✅ Aktiv")
                    print(f"  🌡️ Hotend: {printer_status.get('temperature', {}).get('hotend_current', 0):.1f}°C")
                    print(f"  🛏️ Bett: {printer_status.get('temperature', {}).get('bed_current', 0):.1f}°C")
                    
                    pos = printer_status.get('position', {})
                    print(f"  📍 Position: X:{pos.get('x', 0):.1f} Y:{pos.get('y', 0):.1f} Z:{pos.get('z', 0):.1f}")
                else:
                    print("  ⚠️ Status nicht verfügbar")
            except Exception as e:
                print(f"  ❌ Drucker-Status Fehler: {e}")
        else:
            print("  🔌 Verbindung: ❌ Nicht verbunden")
        
        print("="*60)
    
    def demo_workflow(self):
        """Führe Demo-Workflow durch"""
        print("\n🎯 DEMO: Automatischer 3D-Druck Workflow")
        print("="*50)
        
        demo_objects = [
            "kleiner Würfel 2cm",
            "Smartphone-Halter",
            "Zahnrad mit 8 Zähnen"
        ]
        
        for i, obj in enumerate(demo_objects, 1):
            print(f"\n[{i}/{len(demo_objects)}] Erstelle: {obj}")
            
            try:
                # Workflow starten
                response = requests.post(
                    f"{self.base_url}/api/print-request",
                    json={"user_request": f"Erstelle ein {obj}"},
                    timeout=10
                )
                
                if response.status_code == 201:
                    job_data = response.json()
                    job_id = job_data["job_id"]
                    print(f"  📋 Job erstellt: {job_id[:8]}...")
                    
                    # Warte auf Completion
                    for j in range(30):
                        status_response = requests.get(f"{self.base_url}/api/status/{job_id}")
                        if status_response.status_code == 200:
                            status = status_response.json()
                            progress = status["progress_percentage"]
                            step = status["current_step"]
                            
                            print(f"  🔄 {progress:3.0f}% - {step}")
                            
                            if status["status"] == "completed":
                                print(f"  ✅ Erfolgreich abgeschlossen!")
                                if status.get("output_files"):
                                    print(f"     📄 STL: {os.path.basename(status['output_files'].get('stl', ''))}")
                                    print(f"     📄 G-Code: {os.path.basename(status['output_files'].get('gcode', ''))}")
                                break
                            elif status["status"] in ["failed", "cancelled"]:
                                print(f"  ❌ Fehlgeschlagen: {status.get('error_message')}")
                                break
                        
                        time.sleep(1)
                    
                else:
                    print(f"  ❌ Workflow-Start fehlgeschlagen: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Demo-Fehler: {e}")
            
            time.sleep(2)  # Kurze Pause zwischen Jobs
    
    def interactive_menu(self):
        """Interaktives Menü"""
        while True:
            print("\n" + "="*50)
            print("🎮 AI AGENT 3D PRINT - INTERACTIVE MENU")
            print("="*50)
            print("1. 📊 System Status anzeigen")
            print("2. 🎯 Demo Workflow ausführen")
            print("3. 🖨️ Drucker neu verbinden")
            print("4. 🌐 Browser öffnen")
            print("5. 🧪 Test Suite ausführen")
            print("6. ❌ Beenden")
            print("="*50)
            
            try:
                choice = input("Wähle Option (1-6): ").strip()
                
                if choice == "1":
                    self.show_system_status()
                elif choice == "2":
                    self.demo_workflow()
                elif choice == "3":
                    port = self.detect_printer()
                    if port:
                        self.connect_printer(port)
                    else:
                        self.connect_mock_printer()
                elif choice == "4":
                    self.open_browser()
                elif choice == "5":
                    self.run_test_suites()
                elif choice == "6":
                    break
                else:
                    print("❌ Ungültige Option!")
                    
            except KeyboardInterrupt:
                break
    
    def run_test_suites(self):
        """Führe Test-Suites aus"""
        print("\n🧪 TEST SUITES")
        print("1. 📝 300 Begriffe Test (Klein: 20)")
        print("2. 📷 Bild-Erkennung Test")
        print("3. 🚀 Beide Tests")
        
        choice = input("Wähle Test (1-3): ").strip()
        
        if choice in ["1", "3"]:
            print("🚀 Starte 300-Begriffe Test...")
            os.system(f"{sys.executable} test_300_begriffe.py")
        
        if choice in ["2", "3"]:
            print("🚀 Starte Bild-Erkennung Test...")
            os.system(f"{sys.executable} test_bilderkennnung.py")
    
    def cleanup(self):
        """Cleanup beim Beenden"""
        print("\n🧹 System wird heruntergefahren...")
        
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print("✅ Server beendet")
            except:
                try:
                    self.server_process.kill()
                    print("⚠️ Server forciert beendet")
                except:
                    pass
    
    def run(self):
        """Hauptfunktion"""
        print("🚀 AI AGENT 3D PRINT - AUTO WEB INTERFACE")
        print("="*60)
        
        try:
            # 1. Server starten
            if not self.start_server():
                return
            
            # 2. Drucker erkennen und verbinden
            printer_port = self.detect_printer()
            if printer_port:
                self.connect_printer(printer_port)
            else:
                self.connect_mock_printer()
            
            # 3. Browser öffnen
            self.open_browser()
            
            # 4. System Status anzeigen
            time.sleep(2)
            self.show_system_status()
            
            # 5. Interaktives Menü
            self.interactive_menu()
            
        except KeyboardInterrupt:
            print("\n⚠️ Benutzer-Unterbrechung")
        except Exception as e:
            print(f"\n❌ Unerwarteter Fehler: {e}")
        finally:
            self.cleanup()


def main():
    """Hauptfunktion"""
    interface = AutoWebInterface()
    interface.run()


if __name__ == "__main__":
    main()
