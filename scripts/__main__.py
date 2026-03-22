"""Allow running as: python -m scripts"""

from __future__ import annotations

import argparse
import os

from .env_loader import format_env_sources, load_runtime_env

_LIVE_ENV_VARS = ("PUBLIC_API_SECRET", "PUBLIC_ACCOUNT_ID", "POLYGON_API_KEY")


def _missing_live_env_vars() -> list[str]:
    return [name for name in _LIVE_ENV_VARS if not os.environ.get(name)]


def _parse_args() -> argparse.Namespace:
    """Parse the small CLI surface exposed by the skill entrypoint."""
    parser = argparse.ArgumentParser(
        prog="python -m scripts",
        description="Run the DVRR Autopilot skill.",
    )
    parser.add_argument(
        "--symbol",
        dest="symbol",
        help="Analyze only one ticker instead of the full portfolio.",
    )
    return parser.parse_args()


def main() -> object:
    """Run live analysis when possible, otherwise fall back to the contest demo."""
    args = _parse_args()
    if args.symbol:
        os.environ["DVRR_TARGET_SYMBOL"] = args.symbol.strip().upper()

    loaded_env = load_runtime_env()
    if loaded_env:
        print(f"Env source: {format_env_sources(loaded_env)}")

    missing = _missing_live_env_vars()
    if missing:
        print(
            "WARNING: Live credentials unavailable - running contest demo analysis instead.",
            flush=True,
        )
        from demo_with_real_data import main as demo_main

        return demo_main()

    from .autopilot import main as live_main

    try:
        return live_main()
    except Exception as exc:
        print(
            f"WARNING: Live portfolio analysis unavailable ({exc.__class__.__name__}) - "
            "running contest demo analysis instead.",
            flush=True,
        )
        from demo_with_real_data import main as demo_main

        return demo_main()


if __name__ == "__main__":
    main()
