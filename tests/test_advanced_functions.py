"""Compatibility stub plus smoke tests for the legacy advanced pause/resume demo."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable

import pytest

from tests.scripts.advanced_pause_resume_demo import main as _main


def _run_async(coro: Awaitable[Any]) -> Any:
    """Run an async coroutine, accommodating existing event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()

    return asyncio.run(coro)


def run_demo() -> bool:
    """Execute the advanced demo coroutine and surface its boolean result."""
    return _run_async(_main())


def main() -> int:
    """Legacy CLI entry point for backwards compatibility."""
    return 0 if run_demo() else 1


@pytest.mark.parametrize("demo_result", [True, False], ids=["success", "failure"])
def test_main_exit_codes(monkeypatch: pytest.MonkeyPatch, demo_result: bool) -> None:
    """Ensure ``main`` maps coroutine outcomes onto traditional exit codes."""

    async def fake_demo() -> bool:
        return demo_result

    monkeypatch.setattr("test_advanced_functions._main", fake_demo)
    assert (main() == 0) is demo_result


def test_run_demo_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard that ``run_demo`` awaits the advanced coroutine exactly once."""

    calls = []

    async def fake_demo() -> bool:  # pragma: no cover - helper
        calls.append(True)
        return True

    monkeypatch.setattr("test_advanced_functions._main", fake_demo)
    assert run_demo() is True
    assert calls == [True]


if __name__ == "__main__":  # pragma: no cover - manual execution path
    raise SystemExit(main())
