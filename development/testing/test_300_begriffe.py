#!/usr/bin/env python3
"""
300 Begriffe Mass-Testing Suite für AI Agent 3D Print System
Testet systematisch die KI-Fähigkeiten mit verschiedenen Objekttypen
"""

import asyncio
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Tuple
import random

# 300 Test-Begriffe kategorisiert
TEST_BEGRIFFE = {
    "einfache_formen": [
        "Würfel", "Kugel", "Zylinder", "Kegel", "Pyramide", "Quader", "Ring", "Torus",
        "Scheibe", "Röhre", "Rohr", "Stab", "Balken", "Platte", "Brett"
    ],
    
    "haushalt": [
        "Tasse", "Schüssel", "Teller", "Gabel", "Löffel", "Messer", "Flasche", "Deckel",
        "Dose", "Topf", "Pfanne", "Sieb", "Korkenzieher", "Flaschenöffner", "Untersetzer",
        "Kerzenhalter", "Vase", "Blumentopf", "Briefbeschwerer", "Seifenschale", "Zahnbürstenhalter",
        "Handtuchhalter", "Haken", "Knopf", "Griff", "Schalter", "Kabelhalter"
    ],
    
    "technik": [
        "Zahnrad", "Schraube", "Mutter", "Unterlegscheibe", "Lager", "Riemenscheibe",
        "Hebel", "Nocken", "Feder", "Kupplung", "Gehäuse", "Halterung", "Adapter",
        "Stecker", "Buchse", "Antenne", "Kühlkörper", "Lüfter", "Propeller",
        "Motor", "Getriebe", "Welle", "Achse", "Klemme", "Klammer"
    ],
    
    "werkzeuge": [
        "Hammer", "Schraubenzieher", "Zange", "Säge", "Bohrer", "Meißel", "Feile",
        "Schlüssel", "Winkel", "Lineal", "Maßband", "Wasserwaage", "Lot", "Zirkel",
        "Spachtel", "Pinsel", "Rolle", "Kelle", "Schaufel", "Rechen"
    ],
    
    "spielzeug": [
        "Würfel", "Ball", "Kreisel", "Puzzle", "Baustein", "Figur", "Auto", "Flugzeug",
        "Schiff", "Roboter", "Tier", "Puppe", "Haus", "Turm", "Brücke", "Leiter",
        "Schaukel", "Rutsche", "Wippe", "Karussell"
    ],
    
    "küche": [
        "Salzstreuer", "Pfefferstreuer", "Zuckerdose", "Teekanne", "Kaffeekanne", "Milchkännchen",
        "Sahnekännchen", "Butterdose", "Marmeladenglas", "Brotkorb", "Obstschale", "Salatschüssel",
        "Schneebesen", "Rührlöffel", "Pfannenwender", "Schöpfkelle", "Nudelholz", "Backform",
        "Kuchenform", "Ausstechform", "Reibe", "Hobel", "Presse", "Mörser"
    ],
    
    "büro": [
        "Stift", "Kugelschreiber", "Bleistift", "Marker", "Textmarker", "Radiergummi",
        "Anspitzer", "Kleber", "Schere", "Locher", "Hefter", "Klammerentferner",
        "Brieföffner", "Briefklemme", "Büroklammer", "Ordner", "Mappe", "Ablage",
        "Stempel", "Stempelkissen", "Etiketten", "Visitenkartenhalter"
    ],
    
    "garten": [
        "Blumentopf", "Gießkanne", "Harke", "Spaten", "Schaufel", "Hacke", "Rechen",
        "Schere", "Säge", "Messer", "Sprüher", "Schlauch", "Düse", "Sprinkler",
        "Pflanzstab", "Rankhilfe", "Vogeltränke", "Vogelhäuschen", "Windrad", "Wetterfahne"
    ],
    
    "elektronik": [
        "Gehäuse", "Platine", "Kondensator", "Widerstand", "LED", "Schalter", "Taster",
        "Potentiometer", "Stecker", "Buchse", "Kabel", "Litze", "Antenne", "Sensor",
        "Display", "Tastatur", "Maus", "Lautsprecher", "Mikrofon", "Kamera"
    ],
    
    "möbel": [
        "Stuhl", "Tisch", "Schrank", "Regal", "Bank", "Hocker", "Liege", "Bett",
        "Sofa", "Sessel", "Kommode", "Sideboard", "Vitrine", "Schreibtisch",
        "Nachttisch", "Garderobe", "Spiegel", "Lampe", "Leuchte"
    ],
    
    "sport": [
        "Ball", "Hantel", "Gewicht", "Stange", "Reck", "Barren", "Ring", "Seil",
        "Sprungseil", "Hula-Hoop", "Frisbee", "Boomerang", "Pfeil", "Bogen",
        "Schläger", "Racket", "Paddel", "Ruder", "Ski", "Snowboard"
    ],
    
    "medizin": [
        "Spritze", "Thermometer", "Stethoskop", "Brille", "Lupe", "Pinzette",
        "Skalpell", "Verbandsmaterial", "Pflaster", "Bandage", "Schiene",
        "Prothese", "Implantat", "Zahnspange", "Zahnersatz"
    ],
    
    "schmuck": [
        "Ring", "Kette", "Armband", "Ohrring", "Anhänger", "Brosche", "Manschettenknopf",
        "Uhr", "Medaillon", "Perle", "Edelstein", "Diamant", "Kreuz", "Herz", "Stern"
    ],
    
    "transport": [
        "Rad", "Reifen", "Felge", "Achse", "Lager", "Bremse", "Lenker", "Sattel",
        "Pedal", "Kette", "Zahnrad", "Schaltung", "Rahmen", "Gabel", "Stoßdämpfer"
    ],
    
    "komplexe_objekte": [
        "Uhr", "Getriebe", "Motor", "Pumpe", "Ventil", "Turbine", "Kompressor",
        "Generator", "Transformator", "Schalter", "Relais", "Sensor", "Aktuator",
        "Roboterarm", "Drohne", "Satellit", "Rakete", "Teleskop", "Mikroskop"
    ]
}

class BegriffeTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        self.erfolgreiche_tests = 0
        self.fehlgeschlagene_tests = 0
        
    def generate_test_list(self, anzahl=300) -> List[str]:
        """Generiere Liste von Test-Begriffen"""
        alle_begriffe = []
        for kategorie, begriffe in TEST_BEGRIFFE.items():
            alle_begriffe.extend(begriffe)
        
        # Shuffle und nehme die ersten 'anzahl' Begriffe
        random.shuffle(alle_begriffe)
        return alle_begriffe[:anzahl]
    
    async def teste_begriff(self, begriff: str, session_id: int) -> Dict:
        """Teste einen einzelnen Begriff"""
        print(f"[{session_id:03d}] Teste: '{begriff}'...")
        
        start_time = time.time()
        
        try:
            # API Request
            response = requests.post(
                f"{self.base_url}/api/print-request",
                json={"user_request": f"Erstelle ein {begriff}"},
                timeout=30
            )
            
            if response.status_code != 201:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            job_data = response.json()
            job_id = job_data["job_id"]
            
            # Warte auf Completion (max 60 Sekunden)
            for i in range(60):
                status_response = requests.get(f"{self.base_url}/api/status/{job_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data["status"] == "completed":
                        end_time = time.time()
                        
                        result = {
                            "begriff": begriff,
                            "success": True,
                            "job_id": job_id,
                            "processing_time": end_time - start_time,
                            "progress": status_data["progress_percentage"],
                            "output_files": status_data.get("output_files"),
                            "error": None
                        }
                        
                        self.erfolgreiche_tests += 1
                        print(f"  ✅ Erfolgreich in {result['processing_time']:.1f}s")
                        return result
                        
                    elif status_data["status"] in ["failed", "cancelled"]:
                        raise Exception(f"Workflow failed: {status_data.get('error_message', 'Unknown error')}")
                
                time.sleep(1)
            
            raise Exception("Timeout nach 60 Sekunden")
            
        except Exception as e:
            end_time = time.time()
            result = {
                "begriff": begriff,
                "success": False,
                "job_id": None,
                "processing_time": end_time - start_time,
                "progress": 0,
                "output_files": None,
                "error": str(e)
            }
            
            self.fehlgeschlagene_tests += 1
            print(f"  ❌ Fehlgeschlagen: {e}")
            return result
    
    async def mass_test(self, anzahl=300):
        """Führe Mass-Test durch"""
        print(f"🧪 Starte Mass-Test mit {anzahl} Begriffen...")
        print(f"📊 API Endpoint: {self.base_url}")
        
        test_begriffe = self.generate_test_list(anzahl)
        
        start_time = datetime.now()
        
        for i, begriff in enumerate(test_begriffe, 1):
            result = await self.teste_begriff(begriff, i)
            self.results[begriff] = result
            
            # Progress Update
            if i % 10 == 0:
                erfolgsrate = (self.erfolgreiche_tests / i) * 100
                print(f"\n📈 Progress: {i}/{anzahl} ({erfolgsrate:.1f}% Erfolgsrate)")
                print(f"   ✅ Erfolgreich: {self.erfolgreiche_tests}")
                print(f"   ❌ Fehlgeschlagen: {self.fehlgeschlagene_tests}\n")
        
        end_time = datetime.now()
        
        # Finaler Report
        self.generate_report(start_time, end_time, anzahl)
    
    def generate_report(self, start_time, end_time, anzahl):
        """Generiere detaillierten Report"""
        total_time = (end_time - start_time).total_seconds()
        erfolgsrate = (self.erfolgreiche_tests / anzahl) * 100
        
        print("\n" + "="*80)
        print(f"🎯 MASS-TEST REPORT - {anzahl} BEGRIFFE")
        print("="*80)
        print(f"📅 Start: {start_time.strftime('%H:%M:%S')}")
        print(f"📅 Ende: {end_time.strftime('%H:%M:%S')}")
        print(f"⏱️  Gesamtzeit: {total_time:.1f} Sekunden ({total_time/60:.1f} Minuten)")
        print(f"⚡ Durchschnitt: {total_time/anzahl:.2f}s pro Begriff")
        print()
        print(f"✅ Erfolgreich: {self.erfolgreiche_tests}/{anzahl} ({erfolgsrate:.1f}%)")
        print(f"❌ Fehlgeschlagen: {self.fehlgeschlagene_tests}/{anzahl} ({100-erfolgsrate:.1f}%)")
        
        # Kategorien-Analyse
        kategorien_stats = {}
        for begriff, result in self.results.items():
            for kategorie, begriffe in TEST_BEGRIFFE.items():
                if begriff in begriffe:
                    if kategorie not in kategorien_stats:
                        kategorien_stats[kategorie] = {"success": 0, "total": 0}
                    kategorien_stats[kategorie]["total"] += 1
                    if result["success"]:
                        kategorien_stats[kategorie]["success"] += 1
        
        print("\n📊 KATEGORIEN-ANALYSE:")
        for kategorie, stats in sorted(kategorien_stats.items()):
            if stats["total"] > 0:
                erfolg_prozent = (stats["success"] / stats["total"]) * 100
                print(f"  {kategorie:20}: {stats['success']:2d}/{stats['total']:2d} ({erfolg_prozent:5.1f}%)")
        
        # Fehlgeschlagene Begriffe
        fehlgeschlagene = [begriff for begriff, result in self.results.items() if not result["success"]]
        if fehlgeschlagene:
            print(f"\n❌ FEHLGESCHLAGENE BEGRIFFE ({len(fehlgeschlagene)}):")
            for begriff in fehlgeschlagene[:20]:  # Nur erste 20 zeigen
                error = self.results[begriff]["error"]
                print(f"  • {begriff}: {error}")
            if len(fehlgeschlagene) > 20:
                print(f"  ... und {len(fehlgeschlagene)-20} weitere")
        
        # Performance-Analyse
        erfolgreiche_zeiten = [r["processing_time"] for r in self.results.values() if r["success"]]
        if erfolgreiche_zeiten:
            avg_time = sum(erfolgreiche_zeiten) / len(erfolgreiche_zeiten)
            min_time = min(erfolgreiche_zeiten)
            max_time = max(erfolgreiche_zeiten)
            
            print(f"\n⚡ PERFORMANCE-ANALYSE (nur erfolgreiche):")
            print(f"  Durchschnitt: {avg_time:.2f}s")
            print(f"  Minimum: {min_time:.2f}s")
            print(f"  Maximum: {max_time:.2f}s")
        
        # Speichere Report als JSON
        report_file = f"mass_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "meta": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "total_time_seconds": total_time,
                    "anzahl_begriffe": anzahl,
                    "erfolgsrate_prozent": erfolgsrate
                },
                "statistics": {
                    "erfolgreich": self.erfolgreiche_tests,
                    "fehlgeschlagen": self.fehlgeschlagene_tests,
                    "kategorien": kategorien_stats
                },
                "results": self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detaillierter Report gespeichert: {report_file}")
        print("="*80)


async def main():
    """Hauptfunktion"""
    tester = BegriffeTester()
    
    # Teste erst Server-Verbindung
    try:
        response = requests.get(f"{tester.base_url}/health", timeout=5)
        if response.status_code != 200:
            raise Exception("Server nicht erreichbar")
        print("✅ Server-Verbindung erfolgreich")
    except Exception as e:
        print(f"❌ Server-Verbindung fehlgeschlagen: {e}")
        print("💡 Stelle sicher, dass das API server läuft (python api/main.py)")
        return
    
    # Frage Benutzer nach Anzahl
    try:
        anzahl = int(input("Anzahl Begriffe zum Testen (1-300, Enter für 50): ") or "50")
        anzahl = max(1, min(300, anzahl))
    except ValueError:
        anzahl = 50
    
    print(f"🚀 Beginne Test mit {anzahl} Begriffen...")
    await tester.mass_test(anzahl)


if __name__ == "__main__":
    asyncio.run(main())
