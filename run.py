"""Repo-root launcher for the DVRR Autopilot skill."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
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
        if key and value:
            values[key] = value
    return values


def _load_workspace_env(skill_root: Path) -> None:
    workspace_env = skill_root / "workspace.env"
    if not workspace_env.is_file():
        return

    pointer_values = _parse_env_file(workspace_env)
    env_path = pointer_values.get("DVRR_ENV_FILE")
    if env_path:
        os.environ.setdefault("DVRR_ENV_FILE", env_path)
        for key, value in _parse_env_file(Path(env_path)).items():
            os.environ.setdefault(key, value)


def main() -> object:
    skill_root = Path(__file__).resolve().parent
    _load_workspace_env(skill_root)
    if str(skill_root) not in sys.path:
        sys.path.insert(0, str(skill_root))

    from scripts.__main__ import main as skill_main

    return skill_main()


if __name__ == "__main__":
    main()
