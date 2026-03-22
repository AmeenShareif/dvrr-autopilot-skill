"""Helpers for loading DVRR runtime environment files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover - optional dependency
    dotenv_values = None  # type: ignore[assignment]


def _parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a simple KEY=VALUE env file without requiring python-dotenv."""
    values: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                values[key] = value
    return values


def _candidate_env_files() -> List[Path]:
    """Return env files in precedence order."""
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    explicit = os.environ.get("DVRR_ENV_FILE")
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.append(script_dir / ".env")
    candidates.append(repo_root / ".env")
    return candidates


def _load_env_file(path: Path) -> bool:
    """Load keys from a single env file without overwriting process env."""
    if not path.is_file():
        return False

    if dotenv_values is not None:
        raw_values = dotenv_values(path)
        values = {k: v for k, v in raw_values.items() if k and v is not None}
    else:
        values = _parse_env_file(path)

    for key, value in values.items():
        if key not in os.environ:
            os.environ[key] = value

    return True


def load_runtime_env() -> List[Path]:
    """
    Load runtime env files for the skill.

    Preference order:
    1. DVRR_ENV_FILE if set
    2. scripts/.env
    3. repo-root .env
    """
    loaded: List[Path] = []
    seen: set[str] = set()

    for candidate in _candidate_env_files():
        try:
            resolved = str(candidate.resolve())
        except FileNotFoundError:
            resolved = str(candidate)
        if resolved in seen:
            continue
        seen.add(resolved)
        if _load_env_file(candidate):
            loaded.append(candidate)

    return loaded


def format_env_sources(paths: List[Path]) -> str:
    """Format loaded env sources relative to the skill root when possible."""
    if not paths:
        return "none"

    repo_root = Path(__file__).resolve().parent.parent
    labels: List[str] = []
    for path in paths:
        try:
            labels.append(str(path.resolve().relative_to(repo_root)))
        except Exception:
            labels.append(str(path))
    return ", ".join(labels)
