#!/usr/bin/env python3
"""One-command bootstrap for the public DVRR Autopilot skill."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

VALID_MODES = ("ANALYZE", "SUGGEST", "EXECUTE")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python bootstrap.py",
        description="Install dependencies, prepare local env files, and launch DVRR Autopilot.",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="ANALYZE",
        help="Run mode for this bootstrap launch. Default: ANALYZE.",
    )
    parser.add_argument(
        "--symbol",
        help="Optional single ticker to analyze instead of the full portfolio.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Install dependencies and prepare env files without launching the skill.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip pip install if dependencies are already present.",
    )
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _ensure_local_env(repo_root: Path, mode: str) -> Path:
    env_path = repo_root / ".env"
    example_path = repo_root / ".env.example"

    if not env_path.exists():
        if example_path.exists():
            lines = example_path.read_text(encoding="utf-8").splitlines()
            updated: list[str] = []
            saw_mode = False
            for line in lines:
                if line.startswith("DVRR_MODE="):
                    updated.append(f"DVRR_MODE={mode}")
                    saw_mode = True
                elif line.startswith("PUBLIC_API_SECRET="):
                    updated.append("PUBLIC_API_SECRET=")
                elif line.startswith("PUBLIC_ACCOUNT_ID="):
                    updated.append("PUBLIC_ACCOUNT_ID=")
                elif line.startswith("POLYGON_API_KEY="):
                    updated.append("POLYGON_API_KEY=")
                else:
                    updated.append(line)
            if not saw_mode:
                updated.append(f"DVRR_MODE={mode}")
            env_path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
        else:
            env_path.write_text(
                "\n".join(
                    [
                        "# Local DVRR environment",
                        f"DVRR_MODE={mode}",
                        "PUBLIC_API_SECRET=your-secret-key-here",
                        "PUBLIC_ACCOUNT_ID=your-account-id-here",
                        "POLYGON_API_KEY=your-polygon-key-here",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

    workspace_env = repo_root / "workspace.env"
    if not workspace_env.exists():
        workspace_env.write_text(f"DVRR_ENV_FILE={env_path.resolve()}\n", encoding="utf-8")

    return env_path


def _install_dependencies(repo_root: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(repo_root / "requirements.txt")],
        check=True,
    )


def main() -> int:
    args = _parse_args()
    repo_root = _repo_root()

    print("== DVRR Autopilot bootstrap ==")
    print(f"Repository: {repo_root}")

    if not args.skip_install:
        print("Installing dependencies...")
        _install_dependencies(repo_root)
    else:
        print("Skipping dependency install.")

    env_path = _ensure_local_env(repo_root, args.mode)
    print(f"Prepared env: {env_path}")
    print(f"Launch mode: {args.mode}")

    if args.prepare_only:
        print("Bootstrap preparation complete.")
        return 0

    env = os.environ.copy()
    env["DVRR_MODE"] = args.mode
    if args.symbol:
        env["DVRR_TARGET_SYMBOL"] = args.symbol.strip().upper()

    run_cmd = [sys.executable, str(repo_root / "run.py")]
    if args.symbol:
        run_cmd.extend(["--symbol", args.symbol.strip().upper()])

    print("Launching skill...")
    completed = subprocess.run(run_cmd, cwd=repo_root, env=env)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
