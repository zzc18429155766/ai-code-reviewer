"""File scanning and filtering utilities."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from .languages import detect_language


def scan_directory(
    directory: str | Path,
    ignore_patterns: list[str] | None = None,
    extensions: list[str] | None = None,
) -> list[Path]:
    """Scan a directory for reviewable source files."""
    root = Path(directory)
    ignore = ignore_patterns or []
    found = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        rel = str(path.relative_to(root))

        # Check ignore patterns
        if any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(path.name, p) for p in ignore):
            continue

        # Check if it's a supported language
        lang = detect_language(str(path))
        if not lang:
            continue

        # Check extensions filter
        if extensions:
            if not any(path.name.endswith(ext) or path.name == ext for ext in extensions):
                continue

        found.append(path)

    return found


def filter_changed_files(files: list[str], ignore_patterns: list[str] | None = None) -> list[str]:
    """Filter a list of changed files to only reviewable ones."""
    ignore = ignore_patterns or []
    result = []

    for f in files:
        if any(fnmatch.fnmatch(f, p) for p in ignore):
            continue
        if detect_language(f):
            result.append(f)

    return result
