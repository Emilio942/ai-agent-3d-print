# 🔌 AI 3D Backend Plugin System

## Übersicht

Dieses System ermöglicht **einfaches Austauschen** verschiedener KI-Backends für 3D-Generierung. Du kannst zwischen lokalen Modellen, Cloud-APIs und eigenen Implementierungen wechseln **ohne den Rest des Codes zu ändern**.

## 🎯 Features

- ✅ **Plug & Play**: Einfaches Austauschen von KI-Backends
- ✅ **Konfigurierbar**: Backends per YAML-Datei umschalten
- ✅ **Erweiterbar**: Eigene Backends einfach hinzufügen
- ✅ **Fallback**: Automatischer Fallback bei Fehlern
- ✅ **Multi-Provider**: Lokale Modelle, OpenAI, Replicate, Meshy.ai, etc.

## 📁 Struktur

```
core/ai_backends/
├── __init__.py                  # Package init
├── base_backend.py              # Abstract base class
├── backend_registry.py          # Plugin registry
├── backend_manager.py           # Central manager
├── local_depth_backend.py       # Default backend (lokal, kostenlos)
└── mock_cloud_backend.py        # Template für Cloud-APIs

config/
└── ai_backends.yaml             # Konfiguration

examples/
└── ai_backend_usage.py          # Verwendungsbeispiele
```

## 🚀 Quick Start

### 1. Backend auswählen

Editiere `config/ai_backends.yaml`:

```yaml
ai_3d_backend:
  active: "local_depth"  # Ändere hier den Backend-Namen
  fallback: "local_depth"
```

### 2. Im Code verwenden

```python
from core.ai_backends.backend_manager import get_ai_backend_manager

# Manager holen
manager = get_ai_backend_manager()
await manager.initialize()

# Text zu 3D
result = await manager.text_to_3d("ein cooler Würfel")
if result['success']:
    mesh = result['mesh']
    mesh.export("output.stl")

# Bild zu 3D
result = await manager.image_to_3d("mein_bild.jpg")

# Mesh verbessern
result = await manager.enhance_mesh(my_mesh)
```

### 3. Backend wechseln (zur Laufzeit)

```python
# Zu anderem Backend wechseln
await manager.switch_backend('replicate_shap_e')

# Jetzt wird Replicate verwendet
result = await manager.text_to_3d("sphere")
```

## 🔧 Verfügbare Backends

### 1. **local_depth** (Default)
- **Typ**: Lokal, kostenlos
- **Gut für**: Testing, einfache Projekte
- **Features**: Depth estimation, heightmap-based
- **Kosten**: $0
- **GPU**: Nicht erforderlich

```yaml
active: "local_depth"
```

### 2. **mock_cloud** (Template)
- **Typ**: Cloud API Template
- **Gut für**: Als Vorlage für echte APIs
- **Status**: ⚠️ MOCK - ersetzen mit echter API

```yaml
active: "mock_cloud"
backends:
  mock_cloud:
    config:
      api_key: "dein-api-key"
```

### 3. **Replicate Shap-E** (Beispiel - implementieren)
- **Typ**: Cloud API
- **Gut für**: Hochwertige text-to-3D
- **Kosten**: ~$0.0023 pro Generation
- **Docs**: https://replicate.com/cjwbw/shap-e

```yaml
active: "replicate_shap_e"
backends:
  replicate_shap_e:
    config:
      api_token: "r8_..."  # Von replicate.com
```

### 4. **Meshy.ai** (Beispiel - implementieren)
- **Typ**: Cloud API
- **Gut für**: Text/Bild zu 3D, hohe Qualität
- **Kosten**: Ab $0.10 pro Generation
- **Docs**: https://docs.meshy.ai

```yaml
active: "meshy_ai"
backends:
  meshy_ai:
    config:
      api_key: "msy_..."
      art_style: "realistic"
```

## 🎨 Eigenes Backend erstellen

### Schritt 1: Backend-Klasse erstellen

```python
# core/ai_backends/my_backend.py

from core.ai_backends.base_backend import BaseAI3DBackend
from core.ai_backends.backend_registry import register_backend

@register_backend('my_backend')
class MyBackend(BaseAI3DBackend):
    
    async def initialize(self) -> bool:
        # Lade dein Modell / verbinde mit API
        self.is_initialized = True
        return True
    
    async def image_to_3d(self, image_path, params=None):
        # Deine Implementierung
        # ... generiere mesh ...
        return {
            'mesh': mesh,
            'metadata': {...},
            'success': True
        }
    
    async def text_to_3d(self, prompt, params=None):
        # Deine Implementierung
        return {'mesh': mesh, 'success': True, 'metadata': {}}
    
    async def enhance_mesh(self, mesh, params=None):
        # Optional: Mesh-Verbesserung
        return {'mesh': enhanced_mesh, 'success': True, 'metadata': {}}
    
    def get_capabilities(self):
        return {
            'supports_image_to_3d': True,
            'supports_text_to_3d': True,
            'supports_mesh_enhancement': False,
            'runs_locally': True,
            'cost_info': {'cost_per_generation': 0.0}
        }
    
    def get_backend_info(self):
        return {
            'name': 'My Backend',
            'version': '1.0.0',
            'provider': 'custom',
            'description': 'Mein eigenes Backend'
        }
```

### Schritt 2: Config hinzufügen

```yaml
# config/ai_backends.yaml

ai_3d_backend:
  active: "my_backend"
  
  backends:
    my_backend:
      enabled: true
      config:
        custom_param: "wert"
```

### Schritt 3: Verwenden

```python
manager = get_ai_backend_manager()
await manager.initialize()

# Dein Backend wird automatisch geladen!
result = await manager.text_to_3d("test")
```

## 📊 Backend Capabilities prüfen

```python
# Was kann das aktuelle Backend?
caps = manager.get_active_backend_capabilities()

print(f"Image to 3D: {caps['supports_image_to_3d']}")
print(f"Text to 3D: {caps['supports_text_to_3d']}")
print(f"Runs Locally: {caps['runs_locally']}")
print(f"Cost: ${caps['cost_info']['cost_per_generation']}")
```

## 🔄 Fallback-System

Wenn das primäre Backend fehlschlägt, wird automatisch das Fallback-Backend versucht:

```yaml
ai_3d_backend:
  active: "replicate_shap_e"  # Primär
  fallback: "local_depth"     # Fallback
```

```python
# Automatischer Fallback bei Fehler
result = await manager.text_to_3d(
    "complex object",
    use_fallback_on_error=True  # Standard: True
)
```

## 🌐 Cloud APIs einbinden

### Beispiel: Replicate Shap-E

```python
# core/ai_backends/replicate_backend.py

import replicate
from core.ai_backends.base_backend import BaseAI3DBackend
from core.ai_backends.backend_registry import register_backend

@register_backend('replicate_shap_e')
class ReplicateShapEBackend(BaseAI3DBackend):
    
    async def text_to_3d(self, prompt, params=None):
        output = await replicate.async_run(
            "cjwbw/shap-e:8e6460f0e4a6...",
            input={"prompt": prompt}
        )
        
        # Download mesh
        mesh_url = output['model_url']
        mesh = trimesh.load(mesh_url)
        
        return {'mesh': mesh, 'success': True, 'metadata': {}}
```

## 📚 Vollständiges Beispiel

Siehe `examples/ai_backend_usage.py` für komplette Beispiele:

```bash
python examples/ai_backend_usage.py
```

## 🛠️ Troubleshooting

### Backend nicht gefunden

```
KeyError: Backend 'my_backend' not found
```

**Lösung**: 
1. Prüfe ob Backend registriert: `@register_backend('my_backend')`
2. Prüfe Dateinamen: `*_backend.py`
3. Auto-discovery aktiviert in Config

### API Key fehlt

```
⚠️ No API key provided
```

**Lösung**: Setze API Key in `config/ai_backends.yaml`:

```yaml
backends:
  replicate_shap_e:
    config:
      api_token: "r8_dein_token_hier"
```

## 📖 API Referenz

### BaseAI3DBackend

Alle Backends müssen diese Methoden implementieren:

- `async initialize() -> bool` - Backend initialisieren
- `async image_to_3d(image_path, params) -> Dict` - Bild → 3D
- `async text_to_3d(prompt, params) -> Dict` - Text → 3D  
- `async enhance_mesh(mesh, params) -> Dict` - Mesh verbessern
- `get_capabilities() -> Dict` - Backend-Fähigkeiten
- `get_backend_info() -> Dict` - Backend-Info

### AI3DBackendManager

Manager-Methoden:

- `await initialize()` - Manager initialisieren
- `await switch_backend(name)` - Backend wechseln
- `await image_to_3d(path, params)` - Bild zu 3D
- `await text_to_3d(prompt, params)` - Text zu 3D
- `await enhance_mesh(mesh, params)` - Mesh optimieren
- `list_available_backends()` - Liste aller Backends
- `get_active_backend_info()` - Info über aktives Backend

## 💡 Best Practices

1. **Immer Fallback setzen**: Mindestens `local_depth` als Fallback
2. **API Keys sicher**: Nie im Code, immer in Config
3. **Capabilities prüfen**: Vor Nutzung prüfen ob Feature supported
4. **Error Handling**: `if result['success']` immer prüfen
5. **Cleanup**: `await manager.cleanup()` am Ende aufrufen

## 🎯 Nächste Schritte

1. ✅ Aktuelles `local_depth` Backend testen
2. 🔧 Eigenes Backend für deine KI implementieren
3. 🌐 Optional: Cloud-Backend (Replicate, Meshy, etc.) hinzufügen
4. 📝 Config anpassen für deine Needs
5. 🚀 In Production deployen

## 📞 Support

Bei Fragen zum Plugin-System:
1. Siehe `examples/ai_backend_usage.py` für Beispiele
2. Prüfe `config/ai_backends.yaml` für Konfiguration
3. Schaue in `mock_cloud_backend.py` für API-Templates
