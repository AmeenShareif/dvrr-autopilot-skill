"""
DVRR Autopilot — Regime-Aware Autonomous Portfolio Rebalancer.

This is the main orchestrator. It:
1. Connects to Public.com and loads your portfolio
2. Fetches historical OHLCV from Polygon.io for SPY + all holdings
3. Classifies the market regime (trend + volatility)
4. Scores every position with 12+ technical indicators
5. Computes optimal position sizes with hybrid Kelly/ATR/confidence engine
6. Generates rebalance trade intents (BUY underweight winners, SELL losers)
7. Optionally executes trades through Public.com API

Modes: ANALYZE | SUGGEST | EXECUTE
"""

import os
import sys
import json
import time
import logging
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, try manual loading
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Run: pip install httpx")
    sys.exit(1)

from .public_client import PublicClient, Position, AccountInfo
from .indicators import calculate_trend_score, IndicatorSet, format_indicator_summary
from .regime import (
    classify_regime, get_sleeve_weights, should_trade, RegimeState,
    TrendRegime, VolatilityRegime, format_regime_summary,
)
from .sizing import (
    SizingConfig, SizingMethod, calculate_position_size, format_sizing, SizingResult,
)

logger = logging.getLogger(__name__)
_POLYGON_REQUEST_TIMESTAMPS = deque()


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------


def _configure_stdout() -> None:
    """Use UTF-8 stdout when the terminal supports it."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _configure_logging() -> None:
    """Keep noisy HTTP client logs out of normal output."""
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _wait_for_polygon_slot() -> None:
    """Throttle Polygon calls to avoid free-tier 429s."""
    max_calls = max(1, int(os.environ.get("POLYGON_MAX_REQUESTS_PER_MINUTE", "5")))
    window_seconds = 60.0
    now = time.monotonic()

    while _POLYGON_REQUEST_TIMESTAMPS and now - _POLYGON_REQUEST_TIMESTAMPS[0] >= window_seconds:
        _POLYGON_REQUEST_TIMESTAMPS.popleft()

    if len(_POLYGON_REQUEST_TIMESTAMPS) >= max_calls:
        sleep_for = window_seconds - (now - _POLYGON_REQUEST_TIMESTAMPS[0]) + 0.1
        if sleep_for > 0:
            print(f"   Waiting {sleep_for:.1f}s for Polygon rate limit...", flush=True)
            time.sleep(sleep_for)

    now = time.monotonic()
    while _POLYGON_REQUEST_TIMESTAMPS and now - _POLYGON_REQUEST_TIMESTAMPS[0] >= window_seconds:
        _POLYGON_REQUEST_TIMESTAMPS.popleft()
    _POLYGON_REQUEST_TIMESTAMPS.append(time.monotonic())


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class AutopilotConfig:
    """Autopilot configuration — all from env vars with safe defaults."""
    mode: str = "SUGGEST"  # ANALYZE, SUGGEST, EXECUTE
    risk_per_trade: float = 0.02
    max_position_pct: float = 0.10
    max_sector_pct: float = 0.30
    min_trend_score: float = 0.02
    rebalance_threshold: float = 0.20
    polygon_api_key: str = ""

    @classmethod
    def from_env(cls) -> "AutopilotConfig":
        return cls(
            mode=os.environ.get("DVRR_MODE", "SUGGEST").upper(),
            risk_per_trade=float(os.environ.get("DVRR_RISK_PER_TRADE", "0.02")),
            max_position_pct=float(os.environ.get("DVRR_MAX_POSITION_PCT", "0.10")),
            polygon_api_key=os.environ.get("POLYGON_API_KEY", ""),
        )


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TradeIntent:
    """A proposed trade action."""
    symbol: str
    side: str
    quantity: float
    notional: float
    reason: str
    sizing: Optional[SizingResult] = None


@dataclass
class AutopilotResult:
    """Full result of an autopilot cycle."""
    account: AccountInfo
    regime: RegimeState
    sleeve_weights: Dict[str, float]
    scale_factor: float
    scored_positions: List[Tuple[Position, IndicatorSet]]
    trade_intents: List[TradeIntent]
    executed_orders: List[Dict[str, Any]]
    mode: str
    errors: List[str] = field(default_factory=list)


# ============================================================================
# POLYGON DATA FETCHER
# ============================================================================

def fetch_ohlcv(
    symbol: str, api_key: str, days: int = 300,
) -> Optional[Dict[str, List[float]]]:
    """
    Fetch historical OHLCV from Polygon.io.
    Returns: {"open": [...], "high": [...], "low": [...], "close": [...], "volume": [...]}
    """
    if not api_key:
        logger.warning(f"No Polygon API key — skipping {symbol}")
        return None

    from datetime import datetime, timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 5000,
        "apiKey": api_key,
    }

    try:
        for attempt in range(3):
            _wait_for_polygon_slot()
            with httpx.Client(timeout=15) as http:
                resp = http.get(url, params=params)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        try:
                            delay = max(1.0, float(retry_after))
                        except ValueError:
                            delay = 5.0 * (attempt + 1)
                    else:
                        delay = 5.0 * (attempt + 1)
                    logger.warning(
                        "Polygon rate limit for %s; retrying in %.1fs",
                        symbol,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                data = resp.json()

            results = data.get("results", [])
            if not results:
                logger.warning(f"No OHLCV data for {symbol}")
                return None

            return {
                "open": [r["o"] for r in results],
                "high": [r["h"] for r in results],
                "low": [r["l"] for r in results],
                "close": [r["c"] for r in results],
                "volume": [r["v"] for r in results],
            }
        logger.warning(f"Polygon fetch failed for {symbol}: rate limit exhausted")
        return None
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        logger.error(f"Polygon fetch failed for {symbol}: HTTP {status}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Polygon fetch failed for {symbol}: {e.__class__.__name__}")
        return None
    except Exception as e:
        logger.error(f"Polygon fetch failed for {symbol}: {e.__class__.__name__}")
        return None


# ============================================================================
# SECTOR MAPPING (simplified S&P sector classification)
# ============================================================================

SECTOR_MAP = {
    "XLK": "TECH", "AAPL": "TECH", "MSFT": "TECH", "NVDA": "TECH", "GOOG": "TECH",
    "GOOGL": "TECH", "META": "TECH", "AVGO": "TECH", "ADBE": "TECH", "CRM": "TECH",
    "AMD": "TECH", "INTC": "TECH", "CSCO": "TECH", "ORCL": "TECH", "NOW": "TECH",
    "XLF": "FINANCIALS", "JPM": "FINANCIALS", "BAC": "FINANCIALS", "WFC": "FINANCIALS",
    "GS": "FINANCIALS", "MS": "FINANCIALS", "BLK": "FINANCIALS", "SCHW": "FINANCIALS",
    "XLV": "HEALTH", "UNH": "HEALTH", "JNJ": "HEALTH", "LLY": "HEALTH", "PFE": "HEALTH",
    "ABBV": "HEALTH", "MRK": "HEALTH", "TMO": "HEALTH", "ABT": "HEALTH",
    "XLE": "ENERGY", "XOM": "ENERGY", "CVX": "ENERGY", "COP": "ENERGY", "SLB": "ENERGY",
    "XLY": "CONSUMER_DISC", "AMZN": "CONSUMER_DISC", "TSLA": "CONSUMER_DISC",
    "HD": "CONSUMER_DISC", "NKE": "CONSUMER_DISC", "MCD": "CONSUMER_DISC",
    "XLP": "CONSUMER_STAPLES", "PG": "CONSUMER_STAPLES", "KO": "CONSUMER_STAPLES",
    "PEP": "CONSUMER_STAPLES", "COST": "CONSUMER_STAPLES", "WMT": "CONSUMER_STAPLES",
    "XLI": "INDUSTRIALS", "CAT": "INDUSTRIALS", "BA": "INDUSTRIALS", "UPS": "INDUSTRIALS",
    "HON": "INDUSTRIALS", "GE": "INDUSTRIALS", "RTX": "INDUSTRIALS",
    "XLU": "UTILITIES", "NEE": "UTILITIES", "DUK": "UTILITIES", "SO": "UTILITIES",
    "XLRE": "REAL_ESTATE", "AMT": "REAL_ESTATE", "PLD": "REAL_ESTATE",
    "XLB": "MATERIALS", "LIN": "MATERIALS", "APD": "MATERIALS",
    "XLC": "COMMUNICATIONS", "DIS": "COMMUNICATIONS", "NFLX": "COMMUNICATIONS",
    "SPY": "BROAD_MARKET", "QQQ": "BROAD_MARKET", "IWM": "BROAD_MARKET",
    "VOO": "BROAD_MARKET", "VTI": "BROAD_MARKET",
}


def get_sector(symbol: str) -> str:
    return SECTOR_MAP.get(symbol.upper(), "OTHER")


# ============================================================================
# CORE AUTOPILOT LOGIC
# ============================================================================

def run_autopilot(config: Optional[AutopilotConfig] = None) -> AutopilotResult:
    """
    Execute a full DVRR autopilot cycle.

    1. Load portfolio from Public.com
    2. Fetch historical data from Polygon
    3. Classify market regime on SPY
    4. Score every position
    5. Generate rebalance trades
    6. Optionally execute
    """
    _configure_stdout()
    _configure_logging()
    cfg = config or AutopilotConfig.from_env()
    errors: List[str] = []

    # ── Step 1: Connect to Public.com ──
    print("\n🔐 Connecting to Public.com...")
    try:
        client = PublicClient()
        account = client.get_account()
        positions = account.positions or client.get_positions()
        account.positions = positions
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        raise

    print(f"   Account: {account.account_id}")
    print(f"   Equity:  ${account.equity:,.2f}")
    print(f"   Cash:    ${account.cash:,.2f}")
    print(f"   Positions: {len(positions)}")

    # ── Step 2: Fetch market data ──
    print("\n📊 Fetching historical data from Polygon.io...")
    symbols = ["SPY"] + [p.symbol for p in positions if p.instrument_type == "EQUITY"]
    symbols = list(dict.fromkeys(symbols))  # deduplicate, preserve order

    ohlcv_cache: Dict[str, Dict[str, List[float]]] = {}
    for sym in symbols:
        data = fetch_ohlcv(sym, cfg.polygon_api_key)
        if data:
            ohlcv_cache[sym] = data
            print(f"   ✓ {sym}: {len(data['close'])} bars")
        else:
            errors.append(f"No data for {sym}")
            print(f"   ✗ {sym}: no data")
        time.sleep(0.25)  # rate limit courtesy

    # ── Step 3: Classify market regime on SPY ──
    print("\n🌡️  Classifying market regime...")
    spy_data = ohlcv_cache.get("SPY")
    if spy_data:
        regime = classify_regime(
            prices=spy_data["close"],
            high=spy_data["high"],
            low=spy_data["low"],
            close=spy_data["close"],
        )
    else:
        regime = RegimeState(
            trend=TrendRegime.CHOPPY, trend_confidence=0.5,
            volatility=VolatilityRegime.MEDIUM, volatility_percentile=0.5,
            tradability_score=0.5, details={"fallback": True},
        )
        errors.append("SPY data unavailable — using fallback regime")

    weights, scale = get_sleeve_weights(regime)
    print(format_regime_summary(regime, weights, scale))

    # ── Step 4: Score every position ──
    print("\n📈 Scoring positions...")
    scored: List[Tuple[Position, IndicatorSet]] = []

    for pos in positions:
        if pos.instrument_type != "EQUITY":
            continue
        data = ohlcv_cache.get(pos.symbol)
        if not data or len(data["close"]) < 200:
            scored.append((pos, IndicatorSet(symbol=pos.symbol)))
            continue

        indicators = calculate_trend_score(
            prices=data["close"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"],
        )
        indicators.symbol = pos.symbol
        scored.append((pos, indicators))
        print(format_indicator_summary(indicators))

    # Sort by trend score (strongest first)
    scored.sort(key=lambda x: x[1].trend_score or 0, reverse=True)

    # ── Step 5: Generate rebalance trades ──
    trade_intents: List[TradeIntent] = []

    if cfg.mode in ("SUGGEST", "EXECUTE"):
        print("\n⚡ Generating rebalance trades...")
        can_trade, gate_reason = should_trade(regime)

        if not can_trade:
            print(f"   🚫 Trade gate blocked: {gate_reason}")
            print("   No trades will be generated.")
        else:
            sizing_config = SizingConfig(
                method=SizingMethod.HYBRID,
                risk_per_trade_pct=cfg.risk_per_trade,
                max_position_pct=cfg.max_position_pct,
            )

            # Track sector exposure
            sector_exposure: Dict[str, float] = {}
            for pos, ind in scored:
                sector = get_sector(pos.symbol)
                sector_exposure[sector] = sector_exposure.get(sector, 0) + pos.market_value

            for pos, ind in scored:
                if ind.trend_score is None:
                    continue

                current_weight = pos.market_value / account.equity if account.equity > 0 else 0
                sector = get_sector(pos.symbol)
                sector_weight = sector_exposure.get(sector, 0) / account.equity if account.equity > 0 else 0

                # SELL: trend score below threshold or negative
                if ind.trend_score < cfg.min_trend_score and current_weight > 0.005:
                    sell_qty = pos.quantity * 0.5  # sell half
                    sell_notional = sell_qty * (ind.last_close or pos.market_value / max(pos.quantity, 1))
                    trade_intents.append(TradeIntent(
                        symbol=pos.symbol,
                        side="SELL",
                        quantity=round(sell_qty, 4),
                        notional=round(sell_notional, 2),
                        reason=f"Weak trend score ({ind.trend_score:+.4f} < {cfg.min_trend_score})",
                    ))

                # BUY: strong trend, underweight, sector not maxed
                elif ind.trend_score > cfg.min_trend_score * 2:
                    # Compute target weight based on sleeve allocation
                    trend_weight = weights.get("TREND", 0)
                    target_weight = trend_weight * min(ind.trend_score * 5, 1.0) / max(len(scored), 1)
                    target_weight = min(target_weight, cfg.max_position_pct)

                    if current_weight < target_weight * (1 - cfg.rebalance_threshold):
                        # Underweight — size the buy
                        if sector_weight >= cfg.max_sector_pct:
                            continue  # sector maxed

                        confidence = min(1.0, ind.trend_score * 3 + 0.3)
                        sizing = calculate_position_size(
                            config=sizing_config,
                            portfolio_value=account.equity,
                            symbol=pos.symbol,
                            entry_price=ind.last_close or (pos.market_value / max(pos.quantity, 1)),
                            confidence=confidence,
                            atr_14=ind.atr_14,
                            volatility_regime=regime.volatility.value,
                            existing_position_value=pos.market_value,
                        )

                        if sizing.suggested_notional > 0:
                            trade_intents.append(TradeIntent(
                                symbol=pos.symbol,
                                side="BUY",
                                quantity=round(sizing.suggested_shares, 4),
                                notional=round(sizing.suggested_notional, 2),
                                reason=f"Strong trend ({ind.trend_score:+.4f}), underweight ({current_weight:.1%} vs {target_weight:.1%})",
                                sizing=sizing,
                            ))

            # Print trade summary
            if trade_intents:
                print(f"\n   📋 {len(trade_intents)} trade(s) proposed:")
                for intent in trade_intents:
                    emoji = "🟢" if intent.side == "BUY" else "🔴"
                    print(f"   {emoji} {intent.side} {intent.quantity:.4f} {intent.symbol} — ${intent.notional:,.2f}")
                    print(f"      Reason: {intent.reason}")
                    if intent.sizing:
                        print(format_sizing(intent.sizing))
            else:
                print("   ✅ Portfolio is balanced. No trades needed.")

    # ── Step 6: Execute (if mode is EXECUTE) ──
    executed_orders: List[Dict[str, Any]] = []

    if cfg.mode == "EXECUTE" and trade_intents:
        print("\n🚀 EXECUTING TRADES...")
        print("   ⚠️  This will place REAL orders on your Public.com account.")
        confirmation = input("   Type 'CONFIRM' to proceed: ").strip()

        if confirmation == "CONFIRM":
            for intent in trade_intents:
                try:
                    print(f"   Placing {intent.side} {intent.quantity} {intent.symbol}...")
                    result = client.place_order(
                        symbol=intent.symbol,
                        side=intent.side,
                        quantity=intent.quantity,
                    )
                    executed_orders.append({
                        "symbol": intent.symbol,
                        "side": intent.side,
                        "quantity": intent.quantity,
                        "order_id": result.order_id,
                        "status": result.status,
                    })
                    print(f"   ✓ {result.order_id} — {result.status}")
                except Exception as e:
                    errors.append(f"Order failed for {intent.symbol}: {e}")
                    print(f"   ✗ {intent.symbol}: {e}")
        else:
            print("   ❌ Execution cancelled by user.")

    # ── Summary ──
    print("\n" + "=" * 50)
    print(f"  DVRR Autopilot Cycle Complete ({cfg.mode})")
    print(f"  Regime:    {regime.trend.value} / {regime.volatility.value}")
    print(f"  Positions: {len(scored)} scored")
    print(f"  Trades:    {len(trade_intents)} proposed, {len(executed_orders)} executed")
    if errors:
        print(f"  Warnings:  {len(errors)}")
        for e in errors:
            print(f"    ⚠ {e}")
    print("=" * 50)

    return AutopilotResult(
        account=account,
        regime=regime,
        sleeve_weights=weights,
        scale_factor=scale,
        scored_positions=scored,
        trade_intents=trade_intents,
        executed_orders=executed_orders,
        mode=cfg.mode,
        errors=errors,
    )


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    """Run the autopilot from the command line."""
    _configure_stdout()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s", force=True)
    _configure_logging()

    print("╔══════════════════════════════════════════════╗")
    print("║    DVRR AUTOPILOT — Regime-Aware Rebalancer  ║")
    print("║    Powered by Public.com API + Polygon.io    ║")
    print("╚══════════════════════════════════════════════╝")

    config = AutopilotConfig.from_env()
    print(f"\n  Mode:           {config.mode}")
    print(f"  Risk/Trade:     {config.risk_per_trade:.1%}")
    print(f"  Max Position:   {config.max_position_pct:.0%}")

    result = run_autopilot(config)

    # Output structured JSON for agent consumption
    output = {
        "mode": result.mode,
        "account": {
            "equity": result.account.equity,
            "cash": result.account.cash,
            "buying_power": result.account.buying_power,
            "position_count": len(result.account.positions),
        },
        "regime": {
            "trend": result.regime.trend.value,
            "trend_confidence": result.regime.trend_confidence,
            "volatility": result.regime.volatility.value,
            "volatility_percentile": result.regime.volatility_percentile,
            "tradability": result.regime.tradability_score,
        },
        "sleeve_weights": result.sleeve_weights,
        "scale_factor": result.scale_factor,
        "positions_scored": len(result.scored_positions),
        "trades_proposed": len(result.trade_intents),
        "trades_executed": len(result.executed_orders),
        "trade_intents": [
            {
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "notional": t.notional,
                "reason": t.reason,
            }
            for t in result.trade_intents
        ],
        "executed_orders": result.executed_orders,
        "errors": result.errors,
    }

    print("\n📊 Structured Output (JSON):")
    print(json.dumps(output, indent=2))

    return output


if __name__ == "__main__":
    main()
