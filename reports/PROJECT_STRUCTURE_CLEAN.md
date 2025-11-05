# 🏗️ AI Agent 3D Print System - Aufgeräumte Projekt-Struktur

## 📁 Haupt-Verzeichnisse

### 🎯 **Kern-System**
```
├── main.py                    # Haupt-Einstiegspunkt
├── requirements.txt           # Python Dependencies
├── config.yaml               # Haupt-Konfiguration
├── .env.template             # Environment Template
├── LICENSE                   # Projekt-Lizenz
├── README.md                 # Projekt-Übersicht
└── __init__.py               # Package Definition
```

### 🤖 **System-Komponenten**
```
├── agents/                   # AI-Agenten (Research, CAD, Slicer, Printer)
├── api/                     # FastAPI Backend & Endpoints
├── core/                    # Kern-Bibliotheken & Base Classes
├── config/                  # Konfigurationsdateien
├── web/                     # Web Frontend (HTML/CSS/JS)
├── templates/               # HTML Templates
├── static/                  # Statische Web-Assets
└── printer_support/         # 🆕 Drucker-Support Module
```

### 📚 **Dokumentation**
```
├── documentation/
│   ├── tasks/              # Task-spezifische Completion Summaries
│   ├── milestones/         # Meilenstein-Dokumentation
│   ├── project-status/     # Projekt-Status Berichte
│   ├── aufgabenliste_mit_status.md  # Haupt-Aufgabenliste
│   ├── tech_stack.md       # Technologie-Entscheidungen
│   └── *.json             # Validierungs- und Report-Dateien
├── docs/                   # API & Developer Documentation
└── PROJECT_STRUCTURE.md   # Diese Datei
```

### 🧪 **Testing & Validierung**
```
├── tests/                  # Organisierte Unit & Integration Tests
│   └── scripts/           # 🆕 Test-Ausführungs-Skripte
├── test_data/             # 🆕 Test-Bilder und Sample-Dateien
├── validation/            # 🆕 Projekt-Validierung & Reports
├── coverage_reports/      # Test Coverage Berichte
└── htmlcov/              # HTML Coverage Reports
```

### 🚀 **Deployment & Produktion**
```
├── deployment/
│   ├── Dockerfile         # Docker Container Definition
│   ├── docker-compose.prod.yml  # Production Docker Compose
│   └── .dockerignore     # Docker Build Ignores
├── scripts/
│   ├── start_api_server.py      # Development Server
│   ├── start_api_production.py  # Production Server
│   └── start_advanced_server.py # Advanced Features Server
└── .venv/                # Virtual Environment (local)
```

### 📊 **Daten & Logs**
```
├── data/                  # STL-Dateien, G-Code, Outputs
├── logs/                  # System & Agent Logs
├── cache/                 # Caching für Performance
├── examples/              # Beispiel-Projekte
└── __pycache__/          # Python Bytecode Cache
```

### 🛠️ **Development & Debug**
```
├── development/           # 🆕 Development Tools & Debug Scripts
│   ├── api_debug.py      # API Debugging
│   ├── auto_web_interface.py  # Web Interface Launcher
│   ├── web_server.py     # Development Server
│   └── *debug*.py        # Debug Utilities
└── android/              # Android App (optional)
```

---

## 🎯 **Schnellstart**

### Entwicklung starten:
```bash
python scripts/start_api_server.py
# oder für Development:
python development/web_server.py
```

### Tests ausführen:
```bash
python -m pytest tests/
# oder einzelne Test-Skripte:
python tests/scripts/test_basic.py
```

### Production deployment:
```bash
docker-compose -f deployment/docker-compose.prod.yml up
```

---

## 📖 **Wichtige Dateien**

| Datei | Beschreibung |
|-------|-------------|
| `documentation/aufgabenliste_mit_status.md` | **Haupt-Projekt-Status** |
| `main.py` | **System-Einstiegspunkt** |
| `README.md` | **Projekt-Übersicht** |
| `tests/` | **Alle Unit & Integration Tests** |
| `agents/parent_agent.py` | **Haupt-Orchestrierung** |
| `api/main.py` | **FastAPI Backend** |
| `web/index.html` | **Web Interface** |
| `printer_support/multi_printer_support.py` | **Drucker-Erkennung** |

---

## 🔄 **Workflow**

1. **Research Agent** → Analysiert Benutzer-Input
2. **CAD Agent** → Generiert 3D-Modelle
3. **Slicer Agent** → Konvertiert zu G-Code
4. **Printer Agent** → Steuert 3D-Drucker

---

## 🆕 **Aufräumung Durchgeführt**

### Neue Ordner-Struktur:
- ✅ `printer_support/` - Alle drucker-bezogenen Module
- ✅ `test_data/` - Test-Bilder und Sample-Dateien
- ✅ `validation/` - Validierungs-Dokumente und Reports
- ✅ `development/` - Development Tools und Debug Scripts
- ✅ `tests/scripts/` - Test-Ausführungs-Skripte

### Aufgeräumt:
- ✅ Root-Verzeichnis bereinigt
- ✅ Test-Skripte organisiert
- ✅ Debug-Tools separiert
- ✅ Validierungs-Dokumente gesammelt
- ✅ README-Dateien für alle neuen Ordner
- ✅ Python Package Structure erstellt

**🎉 System ist sauber organisiert und production-ready!**
