"""Asynchronous diagnostics for the ParentAgent startup sequence."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import pytest
import pytest_asyncio


class ParentAgentProtocol(Protocol):
    """Subset of ParentAgent behaviour needed for the diagnostics."""

    async def initialize(self) -> None:  # pragma: no cover - protocol definition
        ...

    def get_status(self) -> dict[str, Any]:  # pragma: no cover - protocol definition
        ...

    async def execute_research_workflow(self, payload: dict[str, Any]) -> Any:  # pragma: no cover - protocol definition
        ...

    async def shutdown(self) -> None:  # pragma: no cover - protocol definition
        ...


@dataclass
class WorkflowStubResult:
    success: bool


@dataclass
class DiagnosticResult:
    """Outcome of the ParentAgent diagnostics run."""

    success: bool
    steps: list[str] = field(default_factory=list)
    status: dict[str, Any] | None = None
    workflow_success: bool | None = None
    error: str | None = None


async def run_parent_agent_diagnostics(
    agent_factory: Callable[[], ParentAgentProtocol],
) -> DiagnosticResult:
    """Execute the legacy debug steps against an agent factory."""

    result = DiagnosticResult(success=False)
    agent: ParentAgentProtocol | None = None

    try:
        result.steps.append("import_parent_agent")
        agent = agent_factory()
        result.steps.append("create_instance")

        await agent.initialize()
        result.steps.append("initialize")

        status = agent.get_status()
        result.status = status
        result.steps.append("get_status")

        workflow = await agent.execute_research_workflow(
            {
                "user_request": "simple cube",
                "requirements": "small test object",
            }
        )
        result.workflow_success = bool(getattr(workflow, "success", False))
        result.steps.append("execute_research_workflow")

        await agent.shutdown()
        result.steps.append("shutdown")

        result.success = result.workflow_success is True
        return result
    except Exception as exc:  # pragma: no cover - error pathway validated via tests
        result.error = str(exc)
        result.steps.append("error")
        if agent is not None:
            try:
                await agent.shutdown()
                result.steps.append("shutdown")
            except Exception:
                result.steps.append("shutdown_failed")
        return result


@dataclass
class StubParentAgent:
    """Minimal ParentAgent replacement for deterministic diagnostics."""

    initialized: bool = False
    shutdown_called: bool = False
    workflow_payloads: list[dict[str, Any]] = field(default_factory=list)

    async def initialize(self) -> None:
        self.initialized = True

    def get_status(self) -> dict[str, Any]:
        return {
            "state": "RUNNING" if self.initialized else "IDLE",
            "active_workflows": len(self.workflow_payloads),
        }

    async def execute_research_workflow(self, payload: dict[str, Any]) -> WorkflowStubResult:
        if not self.initialized:
            raise RuntimeError("Agent not initialized")
        self.workflow_payloads.append(payload)
        return WorkflowStubResult(success=True)

    async def shutdown(self) -> None:
        self.shutdown_called = True


@dataclass
class FailingParentAgent(StubParentAgent):
    """ParentAgent stub that raises during initialization."""

    failure_message: str = "Initialization failed"

    async def initialize(self) -> None:  # pragma: no cover - exercised in tests
        raise RuntimeError(self.failure_message)


@pytest_asyncio.fixture
async def stub_agent() -> StubParentAgent:
    return StubParentAgent()


@pytest.mark.asyncio
async def test_diagnostics_complete_successfully_with_stub(stub_agent: StubParentAgent) -> None:
    result = await run_parent_agent_diagnostics(lambda: stub_agent)

    assert result.success is True
    assert result.status == {"state": "RUNNING", "active_workflows": 0}
    assert result.workflow_success is True
    assert stub_agent.shutdown_called is True
    assert stub_agent.workflow_payloads == [
        {"user_request": "simple cube", "requirements": "small test object"}
    ]
    assert result.steps == [
        "import_parent_agent",
        "create_instance",
        "initialize",
        "get_status",
        "execute_research_workflow",
        "shutdown",
    ]


@pytest.mark.asyncio
async def test_diagnostics_capture_initialization_failure() -> None:
    failing_agent = FailingParentAgent()
    result = await run_parent_agent_diagnostics(lambda: failing_agent)

    assert result.success is False
    assert result.workflow_success is None
    assert result.error == "Initialization failed"
    assert failing_agent.shutdown_called is True
    assert "error" in result.steps


if __name__ == "__main__":  # pragma: no cover - manual debugging helper
    from core.parent_agent import ParentAgent

    async def _main() -> None:
        diagnostics = await run_parent_agent_diagnostics(ParentAgent)
        if diagnostics.success:
            print("=== All tests passed! ===")
        else:
            print("✗ Diagnostics failed:", diagnostics.error)

    asyncio.run(_main())
