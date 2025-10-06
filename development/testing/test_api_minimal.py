"""Minimal FastAPI surface tests for high-level feature integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import AsyncClient

from core.voice_control import VoiceCommand


class VoiceControlInterface(Protocol):
    async def get_status(self) -> dict[str, Any]:
        """Return the current status summary for the voice control system."""

    async def process_text_command(self, text: str) -> VoiceCommand:
        """Process a text command and produce a structured voice command."""


class AnalyticsDashboardInterface(Protocol):
    async def get_overview(self) -> dict[str, Any]:
        """Return a snapshot of analytics metrics."""

    async def get_system_health(self) -> dict[str, Any]:
        """Return system health indicators."""


class TemplateLibraryInterface(Protocol):
    async def list_templates(self) -> list[dict[str, Any]]:  # pragma: no cover - protocol
        """List available templates."""

    async def get_categories(self) -> list[str]:  # pragma: no cover - protocol
        """List available template categories."""

    async def search_templates(self, *, category: str) -> list[dict[str, Any]]:  # pragma: no cover - protocol
        """Search templates by category."""


def create_minimal_app(
    voice_control: VoiceControlInterface,
    analytics_dashboard: AnalyticsDashboardInterface,
    template_library: TemplateLibraryInterface,
) -> FastAPI:
    """Create the minimal FastAPI application used for the development tests."""

    app = FastAPI(title="AI Agent 3D Print - New Features Test API")

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {"message": "AI Agent 3D Print - New Features Test API"}

    @app.get("/voice/status")
    async def get_voice_control_status() -> JSONResponse:
        status = await voice_control.get_status()
        return JSONResponse({"success": True, "status": status})

    @app.post("/voice/command/test")
    async def test_voice_command() -> JSONResponse:
        command = await voice_control.process_text_command("print a small gear")
        return JSONResponse(
            {
                "success": True,
                "command": {
                    "intent": command.intent,
                    "parameters": command.parameters,
                    "confidence": command.confidence,
                    "recognized_text": command.command,
                },
            }
        )

    @app.get("/analytics/overview")
    async def get_analytics_overview() -> JSONResponse:
        overview = await analytics_dashboard.get_overview()
        return JSONResponse({"success": True, "overview": overview})

    @app.get("/analytics/health")
    async def get_system_health() -> JSONResponse:
        health = await analytics_dashboard.get_system_health()
        return JSONResponse({"success": True, "health": health})

    @app.get("/templates")
    async def list_templates() -> JSONResponse:
        templates = await template_library.list_templates()
        return JSONResponse({"success": True, "templates": templates})

    @app.get("/templates/categories")
    async def get_template_categories() -> JSONResponse:
        categories = await template_library.get_categories()
        return JSONResponse({"success": True, "categories": categories})

    @app.post("/templates/search")
    async def search_templates() -> JSONResponse:
        templates = await template_library.search_templates(category="mechanical")
        return JSONResponse({"success": True, "templates": templates})

    return app


@dataclass
class StubVoiceControlManager:
    """Lightweight stand-in for the real voice control manager."""

    status_calls: int = 0
    last_command_text: str | None = None

    async def get_status(self) -> dict[str, Any]:
        self.status_calls += 1
        return {"listening": True, "commands_processed": 3}

    async def process_text_command(self, text: str) -> VoiceCommand:
        self.last_command_text = text
        return VoiceCommand(
            command=text,
            intent="print_request",
            parameters={"object_description": "small gear"},
            confidence=0.91,
            timestamp=datetime.now(),
        )


@dataclass
class StubAnalyticsDashboard:
    """Minimal analytics dashboard stub with deterministic responses."""

    overview_calls: int = 0
    health_calls: int = 0

    async def get_overview(self) -> dict[str, Any]:
        self.overview_calls += 1
        return {
            "prints_total": 12,
            "prints_successful": 11,
            "uptime_percent": 98.7,
        }

    async def get_system_health(self) -> dict[str, Any]:
        self.health_calls += 1
        return {
            "printer_status": "online",
            "queue_depth": 2,
            "active_alerts": [],
        }


@dataclass
class StubTemplateLibrary:
    """Template library stub returning canned template data."""

    list_calls: int = 0
    category_calls: int = 0
    last_search_category: str | None = None

    async def list_templates(self) -> list[dict[str, Any]]:
        self.list_calls += 1
        return [
            {"id": "gear_v1", "name": "Precision Gear", "category": "mechanical"},
            {"id": "enclosure_v2", "name": "Control Enclosure", "category": "electronics"},
        ]

    async def get_categories(self) -> list[str]:
        self.category_calls += 1
        return ["mechanical", "electronics", "decorative"]

    async def search_templates(self, *, category: str) -> list[dict[str, Any]]:
        self.last_search_category = category
        return [
            {"id": "gear_v1", "name": "Precision Gear", "category": category},
        ]


@pytest.fixture
def minimal_app() -> tuple[FastAPI, StubVoiceControlManager, StubAnalyticsDashboard, StubTemplateLibrary]:
    voice_control = StubVoiceControlManager()
    analytics_dashboard = StubAnalyticsDashboard()
    template_library = StubTemplateLibrary()
    app = create_minimal_app(voice_control, analytics_dashboard, template_library)
    return app, voice_control, analytics_dashboard, template_library


@pytest_asyncio.fixture
async def api_client(minimal_app: tuple[FastAPI, StubVoiceControlManager, StubAnalyticsDashboard, StubTemplateLibrary]):
    app, *_ = minimal_app
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_root_endpoint_returns_greeting(api_client: AsyncClient) -> None:
    response = await api_client.get("/")
    payload = response.json()

    assert response.status_code == 200
    assert payload == {"message": "AI Agent 3D Print - New Features Test API"}


@pytest.mark.asyncio
async def test_voice_status_endpoint_reports_stub_state(
    api_client: AsyncClient, minimal_app: tuple[FastAPI, StubVoiceControlManager, StubAnalyticsDashboard, StubTemplateLibrary]
) -> None:
    _, voice_control, _, _ = minimal_app

    response = await api_client.get("/voice/status")
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["status"] == {"listening": True, "commands_processed": 3}
    assert voice_control.status_calls == 1


@pytest.mark.asyncio
async def test_voice_command_endpoint_returns_structured_command(
    api_client: AsyncClient, minimal_app: tuple[FastAPI, StubVoiceControlManager, StubAnalyticsDashboard, StubTemplateLibrary]
) -> None:
    _, voice_control, _, _ = minimal_app

    response = await api_client.post("/voice/command/test")
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["command"]["intent"] == "print_request"
    assert payload["command"]["parameters"] == {"object_description": "small gear"}
    assert voice_control.last_command_text == "print a small gear"


@pytest.mark.asyncio
async def test_analytics_endpoints_surface_expected_metrics(
    api_client: AsyncClient, minimal_app: tuple[FastAPI, StubVoiceControlManager, StubAnalyticsDashboard, StubTemplateLibrary]
) -> None:
    _, _, analytics_dashboard, _ = minimal_app

    overview_response = await api_client.get("/analytics/overview")
    overview_payload = overview_response.json()
    health_response = await api_client.get("/analytics/health")
    health_payload = health_response.json()

    assert overview_response.status_code == 200
    assert health_response.status_code == 200
    assert overview_payload["success"] is True
    assert health_payload["success"] is True
    assert "prints_total" in overview_payload["overview"]
    assert "uptime_percent" in overview_payload["overview"]
    assert analytics_dashboard.overview_calls == 1
    assert analytics_dashboard.health_calls == 1
    assert health_payload["health"]["printer_status"] == "online"


@pytest.mark.asyncio
async def test_template_endpoints_return_canned_library_data(
    api_client: AsyncClient, minimal_app: tuple[FastAPI, StubVoiceControlManager, StubAnalyticsDashboard, StubTemplateLibrary]
) -> None:
    _, _, _, template_library = minimal_app

    list_response = await api_client.get("/templates")
    categories_response = await api_client.get("/templates/categories")
    search_response = await api_client.post("/templates/search")

    list_payload = list_response.json()
    categories_payload = categories_response.json()
    search_payload = search_response.json()

    assert list_response.status_code == 200
    assert categories_response.status_code == 200
    assert search_response.status_code == 200

    assert list_payload["success"] is True
    assert categories_payload["success"] is True
    assert search_payload["success"] is True

    assert len(list_payload["templates"]) == 2
    assert categories_payload["categories"] == ["mechanical", "electronics", "decorative"]
    assert template_library.last_search_category == "mechanical"
    assert search_payload["templates"][0]["category"] == "mechanical"


if __name__ == "__main__":  # pragma: no cover - manual launch helper
    from core.analytics_dashboard import AnalyticsDashboard
    from core.template_library import TemplateLibrary
    from core.voice_control import VoiceControlManager
    import uvicorn

    app = create_minimal_app(
        VoiceControlManager(),
        AnalyticsDashboard(),
        TemplateLibrary(),
    )
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
