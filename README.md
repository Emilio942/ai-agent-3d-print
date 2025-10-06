# AI Agent 3D Print System

Ein KI-gesteuertes System zur automatischen Generierung und zum Druck von 3D-Objekten basierend auf natürlichsprachlichen Beschreibungen.

## Projektübersicht

Dieses System ermöglicht es Benutzern, 3D-Objekte durch einfache Textbeschreibungen zu erstellen und zu drucken. Das System verwendet verschiedene KI-Agenten, die zusammenarbeiten, um den gesamten Workflow von der Texteingabe bis zum fertigen 3D-Druck zu automatisieren.

## Architektur

```
Text Input → Research Agent → CAD Agent → Slicer Agent → Printer Agent → 3D Print
```

### Komponenten

- **Research Agent**: NLP-basierte Intent-Erkennung und Web-Recherche
- **CAD Agent**: 3D-Modellgenerierung mit FreeCAD Python API
- **Slicer Agent**: G-Code-Generierung mit PrusaSlicer CLI
- **Printer Agent**: Druckersteuerung über serielle Kommunikation

## Technologie-Stack

- **Sprache**: Python 3.12
- **Framework**: FastAPI + WebSocket
- **CAD**: FreeCAD Python API
- **Slicer**: PrusaSlicer CLI
- **NLP**: spaCy + Transformers (Hybrid)
- **Hardware**: pyserial für Druckerkommunikation

## Projektstruktur

```
project/
├── agents/               # Spezialiserte Agenten (Research, CAD, Slicer, Printer, …)
├── api/                  # FastAPI-Endpunkte und Middleware
├── core/                 # Basis-Klassen, Schemas & Infrastruktur
├── printer_support/      # Emulator, Multi-Printer-Support & Utilities
├── tests/                # Unit-, Integrations- und Strukturtests
│   ├── unit/             # Klassische Unittests
│   ├── integration/      # Cross-Agent-Szenarien
│   └── scripts/          # Frühere Demos (werden via Kompatibilitäts-Stubs aufgerufen)
├── documentation/        # Fortschrittsberichte & Status-Dokumente
├── development/          # Werkzeuge & Hilfsskripte für Dev-Umgebungen
├── data/                 # Artefakte (z. B. STL, G-Code, Caches)
├── scripts/              # Hilfsskripte & CLI-Utilities
├── config/               # Konfigurationsdateien & YAML-Vorlagen
├── logs/                 # Laufzeit- und Diagnose-Logs
└── web/                  # Frontend-Assets
```

> **Hinweis:** Im Projektwurzelverzeichnis verbleiben nur wenige "Compatibility Stubs" (z. B. `test_printer_functions.py` oder `printer_emulator.py`). Diese dünnen Adapter verweisen auf die neuen Module in `tests/` bzw. `printer_support/` und halten Legacy-Importpfade funktionsfähig.

## Installation

1. **Repository klonen**
   ```bash
   git clone <repository-url>
   cd ai-agent-3d-print
   ```

2. **Python-Umgebung einrichten**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # oder
   .venv\Scripts\activate     # Windows
   ```

3. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

4. **FreeCAD installieren** (falls nicht über pip verfügbar)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install freecad python3-freecad
   
   # Mit Conda
   conda install -c conda-forge freecad
   ```

5. **PrusaSlicer installieren**
   - Download von [PrusaSlicer Website](https://www.prusa3d.com/prusaslicer/)
   - Pfad in `config/settings.yaml` konfigurieren

## Konfiguration

Die Hauptkonfiguration befindet sich in `config/settings.yaml`. Wichtige Einstellungen:

```yaml
# Drucker-Konfiguration
printer:
  mock_mode: true  # Für Tests ohne echten Drucker
  serial:
    port: "/dev/ttyUSB0"  # Anpassen für Ihr System
    baudrate: 115200

# Slicer-Konfiguration
slicer:
  executable_path: "/usr/bin/prusa-slicer"  # Anpassen für Ihr System
```

## Nutzung

### Entwicklungsmodus
```bash
python main.py
```

### API-Server starten
```bash
uvicorn api.main:app --reload
```

### Beispiel-Request
```bash
curl -X POST "http://localhost:8000/api/print-request" \
     -H "Content-Type: application/json" \
     -d '{"text": "Erstelle einen 2cm Würfel aus PLA"}'
```

### End-to-End Demo im Mock-Modus
```bash
python scripts/demos/cat_text_to_print_demo.py --prompt "Erstelle eine Katze"
```
Der Ablauf nutzt die vorhandenen Agenten vollständig lokal: Der Research Agent erstellt Anforderungen aus dem Textprompt, die Demo generiert nun automatisch eine stylisierte Katzen-Heightmap (`core/cat_heightmap.py`), der CAD Agent wandelt sie in ein STL um, der Slicer Agent erzeugt Mock-G-Code und der Printer Agent streamt den Job an den integrierten Mock-Drucker. Alle Artefakte landen unter `output/cat_demo/`.

## Wartung & Aufräumen

Laufzeit-Logs und Python-Cache-Dateien können das Repository leicht aufblähen. Mit dem Skript
`scripts/cleanup_workspace.py` entfernst du diese Artefakte schnell:

```bash
python scripts/cleanup_workspace.py --dry-run  # zeigt, was gelöscht würde
python scripts/cleanup_workspace.py            # löscht die Artefakte
```

Das Skript löscht standardmäßig `__pycache__/`, `*.pyc` und Log-Dateien aus `logs/`. Mit
`--skip-logs` kannst du Log-Dateien behalten.

## Entwicklungsstand

### ✅ Abgeschlossene Aufgaben
- [x] Task 0.1: Tech-Stack-Analyse & Entscheidung
- [x] Task 0.2: Projekt-Struktur & Konfiguration

### 🚧 In Bearbeitung
- [ ] Task 0.3: Logging & Error Handling Framework

### 📋 Geplant
- [ ] Task 1.1: BaseAgent mit Error Handling
- [ ] Task 1.2: Message Queue mit Prioritäten
- [ ] Task 1.3: ParentAgent mit Orchestrierung
- [ ] Task 1.4: API-Schema Definition

## Tests ausführen

```bash
# Ganze Test-Suite (empfohlen)
pytest tests

# Mit Coverage
pytest --cov=core --cov=agents --cov-report=html

# Einzelne Dateien oder Ordner
pytest tests/test_printer_agent.py
```

## Dokumentation

- [Tech Stack Analyse](tech_stack.md)
- [API Dokumentation](docs/api.md) (geplant)
- [Agent Spezifikationen](docs/agents.md) (geplant)

## Beitragen

1. Fork des Repositories erstellen
2. Feature-Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Änderungen committen (`git commit -m 'Add some AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request erstellen

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe `LICENSE` Datei für Details.

## Kontakt

- Projektmanagement: [Issue Tracker](https://github.com/user/repo/issues)
- Dokumentation: [Wiki](https://github.com/user/repo/wiki)

## Acknowledgments

- FreeCAD Community für die ausgezeichnete Python API
- PrusaResearch für den robusten Slicer
- spaCy Team für die NLP-Bibliothek
