"""Allow running as: python -m scripts"""

from __future__ import annotations

import os

_LIVE_ENV_VARS = ("PUBLIC_API_SECRET", "PUBLIC_ACCOUNT_ID", "POLYGON_API_KEY")


def _missing_live_env_vars() -> list[str]:
    return [name for name in _LIVE_ENV_VARS if not os.environ.get(name)]


def main() -> object:
    """Run live analysis when possible, otherwise fall back to the contest demo."""
    missing = _missing_live_env_vars()
    if missing:
        print(
            "WARNING: Live credentials unavailable - running contest demo analysis instead.",
            flush=True,
        )
        from demo_with_real_data import main as demo_main

        return demo_main()

    from .autopilot import main as live_main

    return live_main()


if __name__ == "__main__":
    main()
