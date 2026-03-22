"""
Market Regime Classifier — Trend, Volatility, and Sleeve Weight Allocation.

Classifies the current market environment and determines how capital should
be allocated across TREND, BREAKOUT, and REVERSION strategy sleeves.

Part of the DVRR (Diversified Volatility-Responsive Rotation) public skill
implementation.
"""

import math
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from .indicators import sma, atr, daily_returns, realized_volatility


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class TrendRegime(Enum):
    STRONG_UPTREND = "STRONG_UPTREND"
    UPTREND = "UPTREND"
    CHOPPY = "CHOPPY"
    DOWNTREND = "DOWNTREND"
    STRONG_DOWNTREND = "STRONG_DOWNTREND"


class VolatilityRegime(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass
class RegimeState:
    """Full regime classification result."""
    trend: TrendRegime
    trend_confidence: float
    volatility: VolatilityRegime
    volatility_percentile: float
    tradability_score: float
    details: Dict[str, Any]


# ============================================================================
# TREND CLASSIFICATION
# ============================================================================

def classify_trend(
    prices: List[float],
    sma_short: int = 20,
    sma_medium: int = 50,
    sma_long: int = 200,
) -> Tuple[TrendRegime, float]:
    """
    Classify trend regime based on MA alignment and slope.

    Uses 5 bullish/bearish signals:
    - Price vs SMA(20), SMA(50), SMA(200)
    - SMA(20) vs SMA(50)
    - SMA(50) vs SMA(200)

    Plus SMA(50) slope over last 10 days for strong trend confirmation.

    Returns: (regime, confidence 0–1)
    """
    if len(prices) < sma_long:
        return TrendRegime.CHOPPY, 0.5

    current = prices[-1]
    sma_20 = sma(prices, sma_short)[-1]
    sma_50 = sma(prices, sma_medium)[-1]
    sma_200 = sma(prices, sma_long)[-1]

    if any(math.isnan(x) for x in [sma_20, sma_50, sma_200]):
        return TrendRegime.CHOPPY, 0.5

    above_20 = current > sma_20
    above_50 = current > sma_50
    above_200 = current > sma_200
    ma_20_above_50 = sma_20 > sma_50
    ma_50_above_200 = sma_50 > sma_200

    # SMA(50) slope over last 10 days
    sma_50_vals = sma(prices, sma_medium)
    slope_50 = 0.0
    if len(sma_50_vals) >= 10 and not math.isnan(sma_50_vals[-10]) and sma_50_vals[-10] != 0:
        slope_50 = (sma_50_vals[-1] - sma_50_vals[-10]) / sma_50_vals[-10]

    bullish_signals = sum([above_20, above_50, above_200, ma_20_above_50, ma_50_above_200])
    bearish_signals = 5 - bullish_signals

    if bullish_signals >= 4 and slope_50 > 0.01:
        confidence = min(1.0, 0.6 + slope_50 * 10)
        return TrendRegime.STRONG_UPTREND, confidence
    elif bullish_signals >= 3:
        confidence = 0.5 + (bullish_signals - 2) * 0.15
        return TrendRegime.UPTREND, confidence
    elif bearish_signals >= 4 and slope_50 < -0.01:
        confidence = min(1.0, 0.6 + abs(slope_50) * 10)
        return TrendRegime.STRONG_DOWNTREND, confidence
    elif bearish_signals >= 3:
        confidence = 0.5 + (bearish_signals - 2) * 0.15
        return TrendRegime.DOWNTREND, confidence
    else:
        return TrendRegime.CHOPPY, 0.5


# ============================================================================
# VOLATILITY CLASSIFICATION
# ============================================================================

def classify_volatility(
    prices: List[float],
    lookback: int = 20,
    historical_lookback: int = 252,
) -> Tuple[VolatilityRegime, float]:
    """
    Classify volatility regime based on current vs historical vol percentile.

    Computes rolling 20-day realized vol over the last year, then ranks
    where the current vol sits in that distribution.

    Returns: (regime, percentile 0–1)
    """
    if len(prices) < historical_lookback:
        return VolatilityRegime.MEDIUM, 0.5

    returns = daily_returns(prices)
    current_vol = realized_volatility(returns, lookback)

    historical_vols = []
    for i in range(historical_lookback - lookback):
        end_idx = len(returns) - i
        start_idx = end_idx - lookback
        if start_idx >= 0:
            vol = realized_volatility(returns[start_idx:end_idx], lookback)
            if not math.isnan(vol):
                historical_vols.append(vol)

    if not historical_vols:
        return VolatilityRegime.MEDIUM, 0.5

    below_count = sum(1 for v in historical_vols if v < current_vol)
    percentile = below_count / len(historical_vols)

    if percentile >= 0.95:
        return VolatilityRegime.EXTREME, percentile
    elif percentile >= 0.75:
        return VolatilityRegime.HIGH, percentile
    elif percentile >= 0.25:
        return VolatilityRegime.MEDIUM, percentile
    else:
        return VolatilityRegime.LOW, percentile


# ============================================================================
# TRADABILITY
# ============================================================================

def calculate_tradability(
    bid: float, ask: float, last_price: float,
    volume: int, avg_volume: int, current_atr: float,
) -> float:
    """
    Tradability score (0–1). Higher = better conditions.
    Factors: bid-ask spread, relative volume, ATR reasonableness.
    """
    # Spread score
    if last_price > 0:
        spread_bps = (ask - bid) / last_price * 10000
    else:
        spread_bps = 100
    if spread_bps <= 5:
        spread_score = 1.0
    elif spread_bps <= 10:
        spread_score = 0.9
    elif spread_bps <= 20:
        spread_score = 0.7
    elif spread_bps <= 50:
        spread_score = 0.4
    else:
        spread_score = 0.1

    # Volume score
    volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
    if volume_ratio >= 1.5:
        volume_score = 1.0
    elif volume_ratio >= 1.0:
        volume_score = 0.9
    elif volume_ratio >= 0.5:
        volume_score = 0.6
    else:
        volume_score = 0.3

    # ATR reasonableness
    if last_price > 0 and current_atr > 0:
        atr_pct = current_atr / last_price
        if atr_pct <= 0.02:
            atr_score = 1.0
        elif atr_pct <= 0.03:
            atr_score = 0.8
        elif atr_pct <= 0.05:
            atr_score = 0.5
        else:
            atr_score = 0.2
    else:
        atr_score = 0.5

    return round(spread_score * 0.4 + volume_score * 0.3 + atr_score * 0.3, 3)


# ============================================================================
# FULL REGIME CLASSIFIER
# ============================================================================

def classify_regime(
    prices: List[float],
    high: List[float],
    low: List[float],
    close: List[float],
    quote: Optional[Dict[str, Any]] = None,
    avg_volume: int = 0,
) -> RegimeState:
    """
    Full regime classification for a symbol or market benchmark.
    Combines trend, volatility, and tradability into a single RegimeState.
    """
    trend, trend_conf = classify_trend(prices)
    vol_regime, vol_pct = classify_volatility(prices)

    if quote:
        try:
            def _sf(val, default=0.0):
                try:
                    return float(val) if val is not None else default
                except (ValueError, TypeError):
                    return default

            atr_vals = atr(high, low, close, 14)
            cur_atr = atr_vals[-1] if atr_vals else 0
            tradability = calculate_tradability(
                bid=_sf(quote.get("bid"), 0),
                ask=_sf(quote.get("ask"), 0),
                last_price=_sf(quote.get("last"), prices[-1]),
                volume=int(_sf(quote.get("volume"), avg_volume)),
                avg_volume=avg_volume,
                current_atr=cur_atr,
            )
        except Exception:
            tradability = 0.5
    else:
        tradability = 0.5

    return RegimeState(
        trend=trend,
        trend_confidence=trend_conf,
        volatility=vol_regime,
        volatility_percentile=vol_pct,
        tradability_score=tradability,
        details={
            "price": prices[-1] if prices else 0,
            "trend_name": trend.value,
            "vol_name": vol_regime.value,
        },
    )


# ============================================================================
# SLEEVE WEIGHTS
# ============================================================================

def get_sleeve_weights(regime: RegimeState) -> Tuple[Dict[str, float], float]:
    """
    Recommended capital allocation across strategy sleeves.

    Returns: ({TREND: w, BREAKOUT: w, REVERSION: w}, scale_factor)
        scale_factor (0.0–1.0): fraction of capital to deploy.
        1.0 = fully invested, 0.30 = 30% invested (70% cash reserve).
    """
    weights = {"TREND": 0.0, "BREAKOUT": 0.0, "REVERSION": 0.0}
    scale_factor = 1.0

    if regime.trend in (TrendRegime.STRONG_UPTREND, TrendRegime.STRONG_DOWNTREND):
        weights["TREND"] = 0.70
        weights["BREAKOUT"] = 0.20
        weights["REVERSION"] = 0.10
    elif regime.trend in (TrendRegime.UPTREND, TrendRegime.DOWNTREND):
        weights["TREND"] = 0.55
        weights["BREAKOUT"] = 0.30
        weights["REVERSION"] = 0.15
    elif regime.trend == TrendRegime.CHOPPY:
        weights["TREND"] = 0.20
        weights["BREAKOUT"] = 0.30
        weights["REVERSION"] = 0.50

    if regime.volatility == VolatilityRegime.EXTREME:
        scale_factor = 0.30
    elif regime.volatility == VolatilityRegime.HIGH:
        weights["TREND"] *= 0.8
        weights["BREAKOUT"] *= 1.2
        scale_factor = 0.70

    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    if scale_factor < 1.0:
        weights = {k: v * scale_factor for k, v in weights.items()}

    return weights, scale_factor


def should_trade(regime: RegimeState, min_tradability: float = 0.4) -> Tuple[bool, str]:
    """Gate: should we trade in this regime?"""
    if regime.tradability_score < min_tradability:
        return False, f"tradability {regime.tradability_score:.2f} < {min_tradability}"
    if regime.volatility == VolatilityRegime.EXTREME:
        return False, "extreme volatility regime"
    return True, "ok"


def format_regime_summary(regime: RegimeState, weights: Dict[str, float], scale: float) -> str:
    """Human-readable regime summary."""
    lines = [
        "══════════════════════════════════════",
        "       MARKET REGIME ANALYSIS         ",
        "══════════════════════════════════════",
        f"  Trend:       {regime.trend.value} (confidence {regime.trend_confidence:.0%})",
        f"  Volatility:  {regime.volatility.value} (percentile {regime.volatility_percentile:.0%})",
        f"  Tradability: {regime.tradability_score:.2f}",
        "",
        "  Sleeve Allocation:",
        f"    TREND:     {weights.get('TREND', 0):.0%}",
        f"    BREAKOUT:  {weights.get('BREAKOUT', 0):.0%}",
        f"    REVERSION: {weights.get('REVERSION', 0):.0%}",
        f"    Cash:      {1.0 - scale:.0%}",
        "══════════════════════════════════════",
    ]
    can_trade, reason = should_trade(regime)
    lines.append(f"  Trade Gate:  {'✅ OPEN' if can_trade else '🚫 BLOCKED — ' + reason}")
    return "\n".join(lines)
