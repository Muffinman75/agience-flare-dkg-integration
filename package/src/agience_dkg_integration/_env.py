"""Auto-load `.env` files for CLI and MCP entrypoints.

Looks for `.env` in (in order):
1. Current working directory
2. The integration package root (parent of this module's package dir)
3. Repo root walked up to 4 levels above CWD

The first match wins. Existing environment variables are NOT overridden,
so explicit shell exports / `--token` flags still take precedence.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env() -> Path | None:
    """Load the nearest `.env` file. Returns the path that was loaded, or None."""
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        return None

    candidates: list[Path] = []

    cwd = Path.cwd()
    candidates.append(cwd / ".env")
    for parent in cwd.parents[:4]:
        candidates.append(parent / ".env")

    pkg_root = Path(__file__).resolve().parents[2]
    candidates.append(pkg_root / ".env")

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return candidate

    return None
