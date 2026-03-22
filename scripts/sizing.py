"""
Position Sizing Engine — Kelly, ATR, Hybrid, with regime-aware adjustments.

Implements five sizing strategies from a production trading agent:
1. FIXED_RISK: Risk fixed % of portfolio per trade
2. KELLY: Kelly criterion for optimal sizing (¼ Kelly for safety)
3. VOLATILITY: ATR-based volatility sizing
4. CONFIDENCE: Scale by signal confidence score
5. HYBRID: Combine all factors (default)
"""

from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum


class SizingMethod(Enum):
    FIXED_RISK = "fixed_risk"
    KELLY = "kelly"
    VOLATILITY = "volatility"
    CONFIDENCE = "confidence"
    HYBRID = "hybrid"


@dataclass
class SizingConfig:
    """Position sizing configuration."""
    method: SizingMethod = SizingMethod.HYBRID
    risk_per_trade_pct: float = 0.02
    max_position_pct: float = 0.10
    min_position_pct: float = 0.005
    kelly_fraction: float = 0.25
    atr_multiple: float = 2.0
    target_risk_pct: float = 0.02
    min_confidence: float = 0.4
    max_confidence_boost: float = 1.5
    reduce_after_losses: int = 2
    reduction_factor: float = 0.5
    volatile_market_reduction: float = 0.5


@dataclass
class SizingResult:
    """Result of position sizing calculation."""
    symbol: str
    suggested_notional: float
    suggested_shares: float
    risk_amount: float
    risk_pct: float
    stop_price: Optional[float]
    target_price: Optional[float]
    sizing_breakdown: Dict[str, float]
    reasoning: str


# ============================================================================
# COMPONENT FUNCTIONS
# ============================================================================

def calculate_kelly_size(
    win_rate: float, avg_win: float, avg_loss: float, kelly_fraction: float = 0.25,
) -> float:
    """
    Kelly Criterion: f* = (p*b - q) / b where p=win_rate, b=avg_win/avg_loss.
    Uses fractional Kelly (default ¼) for safety.
    """
    if avg_win <= 0:
        return 0.0
    loss_rate = 1 - win_rate
    edge = (win_rate * avg_win) - (loss_rate * abs(avg_loss))
    if edge <= 0:
        return 0.0
    full_kelly = edge / avg_win
    return full_kelly * kelly_fraction


def calculate_atr_stop(entry_price: float, atr_14: float, atr_multiple: float = 2.0) -> float:
    """ATR-based stop price."""
    return entry_price - (atr_14 * atr_multiple)


def calculate_volatility_size(
    portfolio_value: float, entry_price: float, atr_14: float,
    risk_per_trade_pct: float = 0.02, atr_multiple: float = 2.0,
) -> tuple:
    """
    ATR-based position sizing.
    Shares = (Portfolio × Risk%) / (ATR × Multiple)
    Returns: (notional, shares, stop_price)
    """
    if atr_14 <= 0 or entry_price <= 0:
        return 0, 0, None
    risk_amount = portfolio_value * risk_per_trade_pct
    stop_distance = atr_14 * atr_multiple
    shares = risk_amount / stop_distance
    notional = shares * entry_price
    stop_price = entry_price - stop_distance
    return notional, shares, stop_price


def calculate_fixed_risk_size(
    portfolio_value: float, entry_price: float, stop_price: float,
    risk_per_trade_pct: float = 0.02,
) -> tuple:
    """Fixed risk sizing. Returns: (notional, shares, risk_amount)."""
    if stop_price >= entry_price or entry_price <= 0:
        return 0, 0, 0
    risk_amount = portfolio_value * risk_per_trade_pct
    risk_per_share = entry_price - stop_price
    shares = risk_amount / risk_per_share
    notional = shares * entry_price
    return notional, shares, risk_amount


def apply_confidence_scaling(
    base_size: float, confidence: float,
    min_confidence: float = 0.4, max_boost: float = 1.5,
) -> float:
    """Scale position size by signal confidence (0–1)."""
    if confidence < min_confidence:
        return 0.0
    if min_confidence >= 1.0:
        return base_size
    clamped = min(confidence, 1.0)
    factor = (clamped - min_confidence) / (1.0 - min_confidence)
    scale = 1.0 + (factor * (max_boost - 1.0))
    return base_size * scale


def apply_loss_streak_adjustment(
    base_size: float, consecutive_losses: int,
    reduce_after: int = 2, reduction_factor: float = 0.5,
) -> float:
    """Reduce size after consecutive losses."""
    if consecutive_losses < reduce_after:
        return base_size
    reductions = consecutive_losses - reduce_after + 1
    return base_size * (reduction_factor ** reductions)


def apply_volatility_regime_adjustment(
    base_size: float, volatility_regime: str, volatile_reduction: float = 0.5,
) -> float:
    """Cut size in high/extreme volatility."""
    if volatility_regime in ("HIGH", "EXTREME"):
        return base_size * volatile_reduction
    return base_size


# ============================================================================
# MAIN SIZING FUNCTION
# ============================================================================

def calculate_position_size(
    config: SizingConfig,
    portfolio_value: float,
    symbol: str,
    entry_price: float,
    confidence: float = 0.5,
    atr_14: Optional[float] = None,
    win_rate: Optional[float] = None,
    avg_win: Optional[float] = None,
    avg_loss: Optional[float] = None,
    consecutive_losses: int = 0,
    volatility_regime: str = "MEDIUM",
    existing_position_value: float = 0.0,
) -> SizingResult:
    """
    Calculate optimal position size using configured method.

    This is the main entry point. It applies:
    1. Base sizing (ATR / Kelly / Fixed / Hybrid)
    2. Confidence scaling
    3. Loss streak dampening
    4. Volatility regime adjustment
    5. Position limit capping
    """
    breakdown = {}
    parts = []
    max_position = portfolio_value * config.max_position_pct
    min_position = portfolio_value * config.min_position_pct
    stop_price = None

    # --- Base sizing ---
    if config.method == SizingMethod.FIXED_RISK:
        base_notional = portfolio_value * config.risk_per_trade_pct
        stop_price = entry_price * 0.95
        breakdown["base_method"] = "fixed_risk"
        parts.append(f"Fixed risk: {config.risk_per_trade_pct:.1%}")

    elif config.method == SizingMethod.KELLY:
        if win_rate is not None and avg_win is not None and avg_loss is not None:
            kelly_pct = calculate_kelly_size(win_rate, avg_win, avg_loss, config.kelly_fraction)
            base_notional = portfolio_value * kelly_pct
            breakdown["kelly_pct"] = kelly_pct
            parts.append(f"Kelly: {kelly_pct:.2%} (¼ Kelly)")
        else:
            base_notional = portfolio_value * config.risk_per_trade_pct
            stop_price = entry_price * 0.95
            parts.append("Kelly: insufficient data → fixed risk fallback")

    elif config.method == SizingMethod.VOLATILITY:
        if atr_14 and atr_14 > 0:
            base_notional, _, stop_price = calculate_volatility_size(
                portfolio_value, entry_price, atr_14,
                config.risk_per_trade_pct, config.atr_multiple,
            )
            breakdown["atr_14"] = atr_14
            parts.append(f"ATR-based: {atr_14:.2f} ATR, {config.atr_multiple}× multiple")
        else:
            base_notional = portfolio_value * config.risk_per_trade_pct
            stop_price = entry_price * 0.95
            parts.append("Volatility: no ATR → fixed risk fallback")

    elif config.method == SizingMethod.CONFIDENCE:
        base = portfolio_value * config.risk_per_trade_pct
        base_notional = apply_confidence_scaling(base, confidence, config.min_confidence, config.max_confidence_boost)
        stop_price = entry_price * 0.95
        parts.append(f"Confidence: {confidence:.2f}")

    else:  # HYBRID
        if atr_14 and atr_14 > 0:
            base_notional, _, stop_price = calculate_volatility_size(
                portfolio_value, entry_price, atr_14,
                config.risk_per_trade_pct, config.atr_multiple,
            )
            parts.append(f"Base: ATR sizing ({atr_14:.2f})")
        else:
            base_notional = portfolio_value * config.risk_per_trade_pct
            stop_price = entry_price * 0.95
            parts.append(f"Base: Fixed risk ({config.risk_per_trade_pct:.1%})")

        confidence_scaled = apply_confidence_scaling(
            base_notional, confidence, config.min_confidence, config.max_confidence_boost,
        )
        if confidence < config.min_confidence:
            parts.append(f"Confidence too low ({confidence:.2f} < {config.min_confidence})")
            return SizingResult(
                symbol=symbol, suggested_notional=0, suggested_shares=0,
                risk_amount=0, risk_pct=0, stop_price=None, target_price=None,
                sizing_breakdown=breakdown, reasoning="; ".join(parts),
            )
        breakdown["confidence_scale"] = confidence_scaled / base_notional if base_notional > 0 else 1.0
        base_notional = confidence_scaled
        parts.append(f"Confidence scaled: {confidence:.2f}")

    # --- Adjustments ---
    loss_adj = apply_loss_streak_adjustment(
        base_notional, consecutive_losses, config.reduce_after_losses, config.reduction_factor,
    )
    if loss_adj < base_notional:
        breakdown["loss_reduction"] = loss_adj / base_notional
        parts.append(f"Loss streak: {consecutive_losses} losses")
    base_notional = loss_adj

    vol_adj = apply_volatility_regime_adjustment(
        base_notional, volatility_regime, config.volatile_market_reduction,
    )
    if vol_adj < base_notional:
        breakdown["vol_reduction"] = vol_adj / base_notional
        parts.append(f"Vol regime: {volatility_regime}")
    base_notional = vol_adj

    # --- Position limits ---
    potential_total = existing_position_value + base_notional
    if potential_total > max_position:
        base_notional = max(0, max_position - existing_position_value)
        parts.append(f"Max position cap: ${max_position:,.0f}")
    if 0 < base_notional < min_position:
        base_notional = 0
        parts.append(f"Below min size (${min_position:,.0f})")

    final_shares = base_notional / entry_price if entry_price > 0 else 0

    if stop_price and stop_price < entry_price:
        risk_per_share = entry_price - stop_price
        risk_amount = final_shares * risk_per_share
        risk_pct = risk_amount / portfolio_value if portfolio_value > 0 else 0
    else:
        risk_amount = base_notional * 0.05
        risk_pct = risk_amount / portfolio_value if portfolio_value > 0 else 0

    target_price = (entry_price + (entry_price - stop_price) * 2) if stop_price else entry_price * 1.05

    return SizingResult(
        symbol=symbol,
        suggested_notional=round(base_notional, 2),
        suggested_shares=round(final_shares, 4),
        risk_amount=round(risk_amount, 2),
        risk_pct=round(risk_pct, 4),
        stop_price=round(stop_price, 2) if stop_price else None,
        target_price=round(target_price, 2),
        sizing_breakdown=breakdown,
        reasoning="; ".join(parts),
    )


def format_sizing(result: SizingResult) -> str:
    """Human-readable sizing result."""
    lines = [
        f"  Position Sizing for {result.symbol}:",
        f"    Notional:  ${result.suggested_notional:,.2f} ({result.suggested_shares:.4f} shares)",
        f"    Risk:      ${result.risk_amount:,.2f} ({result.risk_pct:.2%} of portfolio)",
    ]
    if result.stop_price:
        lines.append(f"    Stop:      ${result.stop_price:,.2f}")
    if result.target_price:
        lines.append(f"    Target:    ${result.target_price:,.2f}")
    lines.append(f"    Reasoning: {result.reasoning}")
    return "\n".join(lines)
