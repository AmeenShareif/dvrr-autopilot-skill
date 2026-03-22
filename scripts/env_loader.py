"""Helpers for loading DVRR runtime environment files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover - optional dependency
    dotenv_values = None  # type: ignore[assignment]


_PUBLIC_CREDENTIAL_ALIASES = {
    "PUBLIC_API_SECRET": "PUBLIC_COM_SECRET",
    "PUBLIC_ACCOUNT_ID": "PUBLIC_COM_ACCOUNT_ID",
}
_OPENCLAW_SECRET_DIR = Path.home() / ".openclaw" / "workspace" / ".secrets"
_OPENCLAW_SECRET_FILES = {
    "public_com_secret.txt": ("PUBLIC_API_SECRET", "PUBLIC_COM_SECRET"),
    "public_com_account.txt": ("PUBLIC_ACCOUNT_ID", "PUBLIC_COM_ACCOUNT_ID"),
}


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
    candidates.extend(_candidate_openclaw_secret_files())
    candidates.append(repo_root / ".env")
    return candidates


def _candidate_openclaw_secret_files() -> List[Path]:
    """Return supported OpenClaw secure-file credential paths."""
    return [
        _OPENCLAW_SECRET_DIR / filename
        for filename in _OPENCLAW_SECRET_FILES
    ]


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


def _load_openclaw_secret_file(path: Path) -> bool:
    """Load a plaintext OpenClaw secure-file credential if present."""
    if not path.is_file():
        return False

    names = _OPENCLAW_SECRET_FILES.get(path.name)
    if not names:
        return False

    value = path.read_text(encoding="utf-8").strip()
    if not value:
        return False

    for key in names:
        if key not in os.environ:
            os.environ[key] = value
    return True


def _sync_public_credential_aliases() -> None:
    """Mirror the Public/OpenClaw credential names in both directions."""
    for canonical, alias in _PUBLIC_CREDENTIAL_ALIASES.items():
        canonical_value = os.environ.get(canonical)
        alias_value = os.environ.get(alias)

        if canonical_value:
            os.environ[alias] = canonical_value
        elif alias_value:
            os.environ[canonical] = alias_value


def load_runtime_env() -> List[Path]:
    """
    Load runtime env files for the skill.

    Preference order:
    1. DVRR_ENV_FILE if set
    2. scripts/.env
    3. OpenClaw secure-file credentials
    4. repo-root .env
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
        if candidate.name in _OPENCLAW_SECRET_FILES:
            loaded_flag = _load_openclaw_secret_file(candidate)
        else:
            loaded_flag = _load_env_file(candidate)
        if loaded_flag:
            loaded.append(candidate)
            _sync_public_credential_aliases()

    return loaded


def format_env_sources(paths: List[Path]) -> str:
    """Format loaded env sources relative to the skill root when possible."""
    if not paths:
        return "none"

    repo_root = Path(__file__).resolve().parent.parent
    labels: List[str] = []
    for path in paths:
        try:
            resolved = path.resolve()
            if resolved.is_relative_to(_OPENCLAW_SECRET_DIR):
                labels.append(f"openclaw:{resolved.name}")
            else:
                labels.append(str(resolved.relative_to(repo_root)))
        except Exception:
            labels.append(str(path))
    return ", ".join(labels)
