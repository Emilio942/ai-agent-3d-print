"""Compatibility stub plus smoke tests for the legacy pause/resume demo."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Any, Callable

import pytest

from tests.scripts.printer_pause_resume_demo import main as _main


def _run_async(coro: Awaitable[Any]) -> Any:
    """Run an async coroutine, even if a loop is already running."""
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
    """Execute the async demo and return its boolean success state."""
    return _run_async(_main())


def main() -> int:
    """Legacy CLI entry point compatible with ``python test_printer_functions.py``."""
    return 0 if run_demo() else 1


@pytest.mark.parametrize(
    "demo_result",
    [True, False],
    ids=["success", "failure"],
)
def test_main_exit_codes(monkeypatch: pytest.MonkeyPatch, demo_result: bool) -> None:
    """Ensure the compatibility wrapper translates boolean results into exit codes."""

    async def fake_demo() -> bool:
        return demo_result

    monkeypatch.setattr("test_printer_functions._main", fake_demo)
    assert (main() == 0) is demo_result


def test_run_demo_invokes_async_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that ``run_demo`` awaits the relocated coroutine exactly once."""

    calls = []

    async def fake_demo() -> bool:  # pragma: no cover - tiny helper
        calls.append(True)
        return True

    monkeypatch.setattr("test_printer_functions._main", fake_demo)
    assert run_demo() is True
    assert calls == [True]


if __name__ == "__main__":  # pragma: no cover - manual compatibility path
    raise SystemExit(main())
