#!/usr/bin/env python3
"""Utility for removing transient development artifacts.

This script keeps the repository tidy by deleting Python bytecode caches,
log files, and other noise that should never be committed.  It is intentionally
non-destructive with respect to source assets and supports a ``--dry-run``
mode so you can preview what would be deleted before doing so.

Examples
--------
Run a dry run to inspect the planned removals::

    python scripts/cleanup_workspace.py --dry-run

Clean everything (default behaviour)::

    python scripts/cleanup_workspace.py

The script focuses on repository-managed locations and skips virtual
environments, build artifacts, and third-party directories.
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

# Directories that we never want to traverse when cleaning.
SKIP_NAME_PARTS = {
    ".git",
    ".venv",
    "env",
    "venv",
    "node_modules",
    "htmlcov",
    "coverage_reports",
    "logs/archive",
}

# Specific relative files that should additionally be removed if present.
EXTRA_FILES = {
    Path("test_input_generated.png"),  # old demo artifact
}


@dataclass
class Candidate:
    """Represents an item slated for removal."""

    path: Path
    reason: str

    @property
    def is_dir(self) -> bool:
        return self.path.is_dir()


def iter_pycache(base: Path) -> Iterator[Candidate]:
    for directory in base.rglob("__pycache__"):
        if _should_skip(directory):
            continue
        yield Candidate(directory, "python bytecode cache")


def iter_compiled_python(base: Path) -> Iterator[Candidate]:
    for suffix in ("*.pyc", "*.pyo", "*.pyd"):
        for file in base.rglob(suffix):
            if _should_skip(file):
                continue
            yield Candidate(file, "compiled python artifact")


def iter_logs(base: Path) -> Iterator[Candidate]:
    logs_dir = base / "logs"
    if not logs_dir.exists():
        return iter(())
    def generate() -> Iterator[Candidate]:
        for pattern in ("*.log", "*.log.*"):
            for file in logs_dir.rglob(pattern):
                if file.is_dir() or file.name.lower().endswith("readme.md"):
                    continue
                yield Candidate(file, "log file")
    return generate()


def iter_extra_files(base: Path) -> Iterator[Candidate]:
    for rel in EXTRA_FILES:
        candidate = base / rel
        if candidate.exists() and not _should_skip(candidate):
            yield Candidate(candidate, "stale artifact")


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_NAME_PARTS for part in path.parts)


def collect_candidates(base: Path, include_logs: bool = True) -> list[Candidate]:
    candidates: list[Candidate] = []
    candidates.extend(iter_pycache(base))
    candidates.extend(iter_compiled_python(base))
    if include_logs:
        candidates.extend(iter_logs(base))
    candidates.extend(iter_extra_files(base))
    # Ensure deterministic ordering for predictable output
    return sorted(candidates, key=lambda c: (len(str(c.path)), str(c.path)))


def remove_candidate(candidate: Candidate) -> None:
    if candidate.path.is_dir():
        shutil.rmtree(candidate.path, ignore_errors=True)
    else:
        try:
            candidate.path.unlink()
        except FileNotFoundError:
            pass


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean transient workspace artifacts.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without deleting anything.",
    )
    parser.add_argument(
        "--skip-logs",
        action="store_true",
        help="Do not remove log files under the logs/ directory.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = Path(__file__).resolve().parent.parent
    candidates = collect_candidates(repo_root, include_logs=not args.skip_logs)

    if not candidates:
        print("✅ Nothing to clean – workspace already tidy.")
        return 0

    action = "Would remove" if args.dry_run else "Removing"
    for candidate in candidates:
        rel_path = candidate.path.relative_to(repo_root)
        print(f"{action}: {rel_path} ({candidate.reason})")
        if not args.dry_run:
            remove_candidate(candidate)

    if args.dry_run:
        print("ℹ️  Dry run complete – no files were deleted.")
    else:
        print(f"🧹 Removed {len(candidates)} items. Workspace looks good!")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
