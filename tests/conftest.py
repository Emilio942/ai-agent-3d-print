"""Root pytest configuration shared across the project."""

from __future__ import annotations

import inspect
from typing import Any

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-dev-tests",
        action="store_true",
        default=False,
        help="Run the development and scripts integration test suites.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "devtest: mark development-only integration tests requiring opt-in",
    )
    config.addinivalue_line(
        "markers",
        "run_dev_test: marker for development tests that remain enabled by default",
    )


def _is_async_test(item: pytest.Item) -> bool:
    """Return True when the collected test function is an async coroutine."""

    test_func: Any | None = getattr(item, "function", None)
    if test_func is None:
        return False

    if not inspect.iscoroutinefunction(test_func):
        return False

    keywords = item.keywords
    if "asyncio" in keywords or "anyio" in keywords:
        return False

    return True


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically mark legacy async tests so pytest-asyncio executes them."""

    for item in items:
        if _is_async_test(item):
            item.add_marker(pytest.mark.asyncio)