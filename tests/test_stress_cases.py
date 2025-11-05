"""Compatibility stub for the legacy stress test suite."""

import asyncio

from tests.scripts.stress_tests import main as _main


def main() -> int:
    """Execute the relocated stress tests and return the exit code."""
    result = asyncio.run(_main())
    return 0 if result else 1

if __name__ == "__main__":
    raise SystemExit(main())
