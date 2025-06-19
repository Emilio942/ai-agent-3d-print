# 🏗️ AI Agent 3D Print System - Projekt-Struktur

## 📁 Haupt-Verzeichnisse

### 🎯 **Kern-System**
```
├── main.py                    # Haupt-Einstiegspunkt
├── requirements.txt           # Python Dependencies
├── config.yaml               # Haupt-Konfiguration
├── .env.template             # Environment Template
└── __init__.py               # Package Definition
```

### 🤖 **System-Komponenten**
```
├── agents/                   # AI-Agenten (Research, CAD, Slicer, Printer)
├── api/                     # FastAPI Backend & Endpoints
├── core/                    # Kern-Bibliotheken & Base Classes
├── config/                  # Konfigurationsdateien
├── web/                     # Web Frontend (React)
├── templates/               # HTML Templates
└── static/                  # Statische Web-Assets
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
└── README.md              # Projekt-Übersicht
```

### 🧪 **Testing & Validierung**
```
├── tests/                  # Organisierte Unit & Integration Tests
├── scripts/
│   ├── testing/           # Test-Ausführungs-Skripte
│   ├── validation/        # Task-Validierungs-Skripte
│   ├── demos/             # Demo & Showcase Skripte
│   └── debug/             # Debug & Development Utilities
├── coverage_reports/       # Test Coverage Berichte
└── htmlcov/               # HTML Coverage Reports
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

---

## 🎯 **Schnellstart**

### Entwicklung starten:
```bash
python scripts/start_api_server.py
```

### Tests ausführen:
```bash
python scripts/testing/run_unit_tests.py
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

---

## 🔄 **Workflow**

1. **Research Agent** → Analysiert Benutzer-Input
2. **CAD Agent** → Generiert 3D-Modelle
3. **Slicer Agent** → Konvertiert zu G-Code
4. **Printer Agent** → Steuert 3D-Drucker

**🎉 System ist 98% abgeschlossen und production-ready!**
