"""Pytest configuration for development integration test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

# Tests in this directory are high-level development/integration scenarios that
# typically rely on running external services or user interaction. They are
# skipped by default unless explicitly requested via --run-dev-tests. Specific
# files can be whitelisted to continue running in the standard suite.
_ALLOWED_DEFAULT_FILES = {
    "test_advanced_features.py",
    "test_api_minimal.py",
    "test_api_debug.py",
}


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "devtest: mark development integration tests that require explicit opt-in",
    )
    config.addinivalue_line(
        "markers",
        "run_dev_test: opt-in marker to keep a development test active by default",
    )

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-dev-tests"):
        return

    skip_marker = pytest.mark.skip(
        reason="Development integration test (use --run-dev-tests to enable)",
    )

    for item in items:
        path = Path(str(item.fspath))
        if path.parent.name != "testing" or path.parent.parent.name != "development":
            continue

        if "run_dev_test" in item.keywords:
            continue

        if path.name in _ALLOWED_DEFAULT_FILES:
            item.add_marker(pytest.mark.run_dev_test)
            continue

        item.add_marker(skip_marker)