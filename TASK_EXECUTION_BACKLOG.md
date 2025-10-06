# Task Execution Backlog

*Erstellt: 04.10.2025*

Dieses Dokument unterteilt die offenen Arbeiten in kleine, ausführbare Schritte. Jedes Paket ist so geschnürt, dass es sich in einer Session oder einem kurzen Arbeitsblock erledigen lässt. Hake Aufgaben nach und nach ab, um die Gesamtintegration zuverlässig voranzutreiben.

---

## Phase 0 · Vorbereitung
- [x] **P0-01 | Fehler-Snapshot & Kategorisierung**  
  Relevante Tests (`pytest test_project_structure.py`, `pytest test_printer_functions.py`, `pytest tests/test_research_agent.py`) erneut laufen lassen und jedes Scheitern den vier Bereichen zuordnen: *Projektstruktur*, *Konfiguration/Abhängigkeiten*, *Logik*, *Monitoring/Threads*. Ergebnisse kurz im Report ergänzen.
  - Ergebnis 2025-10-04:
    - `pytest test_project_structure.py` ❌ – Root enthält noch `test_*.py`-Files und `printer_emulator.py` → Kategorie: **Projektstruktur**.
    - `pytest test_printer_functions.py` ❌ – Async-Tests brechen ab, weil kein passender Pytest-Async-Support aktiv ist → Kategorie: **Konfiguration/Abhängigkeiten**.
    - `pytest tests/test_research_agent.py` ❌ – Mehrere Methoden liefern Coroutines statt synchroner Ergebnisse, außerdem instabiles Web-Research-Caching → Hauptursache: **Logik** (Sync-API-Vertrag) mit Nebenwirkung **Monitoring/Threads** (nicht wartende Coroutines).
  - Ergebnis 2025-10-05:
    - `pytest tests/test_project_structure.py` ✅ – Nach Aufräumen des Root-Verzeichnisses nur noch erlaubte Stubs; Projektstruktur-Thema abgeschlossen.
- [x] **P0-02 | Kritische Abhängigkeits-Blocker identifizieren**  
  Auf Basis der Fehlermeldungen (z. B. NumPy <-> Python 3.12) festhalten, welche Paket-Pins akut ein Update oder Ersatz brauchen, damit nachfolgende Fixes überhaupt testbar sind. Nur blocker notieren, keine vollständige Doku.
  - Blocker 2025-10-04: `pytest-asyncio>=0.23` (oder vergleichbares Plugin) fehlt, sodass Async-Tests nicht lauffähig sind → **Konfiguration/Abhängigkeiten**.
  - Update 2025-10-05: `pytest-asyncio>=1.0.0` nun im `requirements.txt`, Tests (`pytest tests/test_printer_agent.py`, `pytest tests/test_research_agent.py`) laufen ohne Import-/Pluginfehler; verbleibende Fehlschläge sind Logikthemen (Coroutines) und keine Paket-Blocker.

- [ ] **P1-01 | NumPy-Kompatibilität herstellen**  
  `requirements.txt` so anpassen, dass `numpy>=1.26` (Python-3.12-kompatibel) installiert wird; Verträglichkeit mit Torch & spaCy prüfen.
  - Update 2025-10-04: Pins auf `numpy>=1.26,<2`, `torch>=2.7,<3`, `spacy>=3.8,<4` gesetzt; `pytest-asyncio>=1.0` für Python-3.12-Kompatibilität ergänzt.
- [x] **P1-02 | Requirements neu installieren**  
  Nach Anpassung: `pip install -r requirements.txt` ausführen; Fehler protokollieren und ggf. weitere Pins aktualisieren.
  - Update 2025-10-05: Installation erneut durchgeführt; alle Pakete erfolgreich, `click` jetzt bei 8.3.0.
- [ ] **P1-03 | Installationsprotokoll ergänzen**  
  Kurzen Abschnitt im README oder separater Notiz ergänzen, welche Schritte zur Installation nötig sind.

- [x] **P2-01 | Async-Teststrategie festlegen**  
  Entscheidung 2025-10-05: Agents behalten asynchrone Kernmethoden (`*_async`), synchroner Vertrag wird über `_run_async`-Wrapper bereitgestellt. Pytest nutzt `pytest.mark.asyncio` nur für dedizierte Async-Szenarien.
- [x] **P2-02 | Printer-Async-Tests korrigieren**  
  Update 2025-10-05: Legacy Stubs besitzen jetzt `_run_async`-Wrapper und schlanke Smoke-Tests (`pytest test_printer_functions.py`, `pytest test_advanced_functions.py`) laufen grün.
- [x] **P2-03 | Research-Agent-Tests anpassen**  
  Update 2025-10-05: `tests/test_research_agent.py` erwartet weiterhin Sync-Aufrufe; neue Wrapper liefern sofortige Ergebnisse, Async-Varianten werden separat getestet (`tests/test_multi_ai_integration.py`). Suite läuft grün.

## Phase 3 · Core-Module reparieren
- [ ] **P3-01 | AIModelConfig erweitern**  
  Felder `enabled`, `api_url`, `config_path` (inkl. Defaults) ergänzen; Tests sollen keine `TypeError` mehr werfen.
- [ ] **P3-02 | AIModelManager anpassen**  
  Konstruktor & Methoden so erweitern, dass `config_path` akzeptiert wird und `analyze_request` verfügbar ist.
- [x] **P3-03 | ResearchAgent Sync-Vertrag**  
  Update 2025-10-05: `execute_task` & `extract_intent` rufen interne Async-Implementierungen über `_run_async` auf; Leereingaben liefern jetzt Low-Confidence-Fallback. `pytest tests/test_research_agent.py` & `pytest tests/test_multi_ai_integration.py` grün.
- [x] **P3-04 | PrinterAgent Attribute & Methoden**  
  Fehlende Properties/Methoden (`connection_status`, `is_connected`, `stream_gcode`, `_validate_gcode_file`, …) implementieren oder alternative API definieren.
  - Update 2025-10-05: Implementiert neue Public-Wrapper (stream/pause/resume), Validierungen und Statistikfunktionen; `pytest tests/test_printer_agent.py` jetzt grün (35 / 35).
- [x] **P3-05 | PrinterAgent Thread-Steuerung härten**  
  `stop_monitoring` konsequent als `threading.Event` verwenden; Setter/Resetter einbauen, damit Tests kein `bool` injizieren.
  - Update 2025-10-05: Event-basierte Steuerung wiederhergestellt (`set()/clear()` in connect/disconnect/cleanup); keine Thread-Warnungen mehr im Printer-Agent-Testlauf.
- [ ] **P3-06 | SlicerAgent Signaturen korrigieren**  
  `_build_prusaslicer_command` & verwandte Methoden an Tests ausrichten (Parameter `gcode_path`, `slicer_input`, `effective_settings`).
- [ ] **P3-07 | BaseAgent Fehlerverhalten**  
  Sicherstellen, dass Validierungsfehler als standardisierte Antwort statt als Exception zurückkommen (Tests in `test_base_agent.py`).

## Phase 4 · Struktur & Doku
- [x] **P4-01 | Root-Verzeichnis bereinigen**  
  `printer_emulator.py` & Einzeltests in passende Unterordner verschieben; Root auf Kernfiles beschränken.
  - Update 2025-10-05: Vollständige Implementationen nach `tests/scripts/` bzw. `printer_support/` verschoben, Root enthält nur noch schlanke Kompatibilitäts-Stubs; neue Strukturtests bestätigt.
- [ ] **P4-02 | Backup-Dateien archivieren**  
  `*.backup`, `*.corrupted` in Archivordner verschieben oder entfernen; README/Hinweise aktualisieren.
- [ ] **P4-03 | Runbook ergänzen**  
  Schritt-für-Schritt-Anleitung (Venv, Install, Tests, Beispiel-Workflow) im README oder separater Doku-Datei hinterlegen.
- [ ] **P4-04 | Logging-Setup vereinheitlichen**  
  Gemeinsame `logging`-Konfiguration erstellen (z. B. `logging.yaml` oder Modul), damit alle Agents konsistent schreiben.

## Phase 5 · Integration & Validierung
- [ ] **P5-01 | Granulare Tests erneut ausführen**  
  Nach jeder Modulreparatur: relevante Einzeltests (z. B. `pytest tests/test_research_agent.py`).
- [ ] **P5-02 | Gesamtsuite prüfen**  
  `pytest tests` komplett laufen lassen; verbleibende Fehler dokumentieren.
- [ ] **P5-03 | End-to-End-Workflow testen**  
  Beispiel-Flow (Research → CAD → Slicer → Printer → Emulator) mit Mock-Daten durchspielen; Ergebnisse dokumentieren.
- [ ] **P5-04 | CI-Check einrichten**  
  GitHub Actions oder ähnlichen Workflow einrichten, der Lint & Tests automatisiert.

---

### Hinweise zur Abarbeitung
- Nach Abschluss eines Tasks bitte Ergebnis (z. B. Log-Auszug, Commit) im Projekt protokollieren.
- Wo Unsicherheiten bestehen, gerne Zwischenfragen stellen oder Unteraufgaben ergänzen.
- Aufgaben lassen sich flexibel in Sprints/Blöcke bündeln; Reihenfolge orientiert sich an Abhängigkeiten (oben priorisiert).





Bereich	Beobachtung	Auswirkung
Test-Suite	pytest bricht bereits beim Import ab (ModuleNotFoundError: No module named 'web'). Danach folgen diverse Assertion-Fehler (z. B. fehlende printer_emulator-Funktionalitäten, unvollständige API-Routen).	Ohne grüne Tests fehlt ein Objektivmaß für Funktionsfähigkeit. Die Importfehler zeigen, dass das Paket-Layout nicht sauber aufbereitet oder sys.path falsch konfiguriert ist.
Projektstruktur	Mehrfach vorhandene Dateien (slicer_agent.py, slicer_agent_fixed.py, .backup-Varianten), alte Server-Dateien (main.py.backup_before_clean, .corrupted_backup)	Erhöht Integrationsrisiko: unklar, welche Fassung produktiv sein soll. Versionierung wirkt unsauber.
Konfig/Abhängigkeiten	requirements.txt existiert, aber nicht geprüft, ob sie aktuelle Module abdeckt (z. B. WebSocket, FastAPI, Bildverarbeitung).	Fehlende Libraries führen beim Start von API-/Agentenprozessen zu Laufzeitfehlern.
Agenten-Koordination	Agents (slicer, image_processing, printer) koexistieren, aber Schnittstellen (z. B. gemeinsame Datenformate, Message-Bus) sind nicht sichtbar verknüpft.	Gefahr, dass einzelne Komponenten zwar funktionieren, aber keine End-to-End-Pipeline entsteht.
Logging/Monitoring	Keine klaren Hinweise auf zentralisiertes Logging oder Fehler-Handling-Strategie.	Schwierigkeiten beim Debugging komplexer Abläufe.
Dokumentation	Viele Berichte, aber keine aktuelle Schritt-für-Schritt-Anleitung zum Starten des Systems.	Erschwert Tests und Übergabe.