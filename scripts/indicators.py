"""
Technical Indicators — Pure Python, zero external dependencies.

All functions expect price series as lists with oldest-first ordering.
Extracted and refined from a production autonomous trading agent.
"""

import math
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class IchimokuCloud:
    tenkan_sen: float
    kijun_sen: float
    senkou_span_a: float
    senkou_span_b: float
    chikou_span: float


@dataclass
class IndicatorSet:
    """Full technical indicator snapshot for a symbol."""
    symbol: str
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_20: Optional[float] = None
    atr_14: Optional[float] = None
    momentum_3m: Optional[float] = None
    momentum_6m: Optional[float] = None
    volatility_20d: Optional[float] = None
    trend_score: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_val: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    cloud_color: Optional[str] = None
    price_vs_cloud: Optional[str] = None
    volume_ratio: Optional[float] = None
    bb_squeeze: Optional[bool] = None
    bb_squeeze_intensity: Optional[float] = None
    bb_bandwidth: Optional[float] = None
    last_close: Optional[float] = None


# ============================================================================
# SIMPLE MOVING AVERAGE
# ============================================================================

def sma(prices: List[float], period: int) -> List[float]:
    """Simple Moving Average with rolling window optimization."""
    if len(prices) < period:
        return [float('nan')] * len(prices)
    result = [float('nan')] * (period - 1)
    window_sum = sum(prices[:period])
    result.append(window_sum / period)
    for i in range(period, len(prices)):
        window_sum = window_sum - prices[i - period] + prices[i]
        result.append(window_sum / period)
    return result


def sma_slope(sma_values: List[float], lookback: int = 5) -> float:
    """Slope of SMA over lookback period (positive = uptrend)."""
    valid = [x for x in sma_values[-lookback:] if not math.isnan(x)]
    if len(valid) < 2:
        return 0.0
    return (valid[-1] - valid[0]) / len(valid)


# ============================================================================
# EXPONENTIAL MOVING AVERAGE
# ============================================================================

def ema(prices: List[float], period: int, smoothing: float = 2.0) -> List[float]:
    """Exponential Moving Average."""
    if len(prices) < period:
        return [float('nan')] * len(prices)
    result = [float('nan')] * (period - 1)
    sma_start = sum(prices[:period]) / period
    result.append(sma_start)
    multiplier = smoothing / (period + 1)
    current_ema = sma_start
    for i in range(period, len(prices)):
        current_ema = (prices[i] - current_ema) * multiplier + current_ema
        result.append(current_ema)
    return result


# ============================================================================
# TRUE RANGE & ATR
# ============================================================================

def true_range(high: List[float], low: List[float], close: List[float]) -> List[float]:
    """True Range: max(H-L, |H-Cp|, |L-Cp|)."""
    if len(high) < 2:
        return [high[0] - low[0]] if high else []
    tr = [high[0] - low[0]]
    for i in range(1, len(high)):
        prev_close = close[i - 1]
        tr.append(max(
            high[i] - low[i],
            abs(high[i] - prev_close),
            abs(low[i] - prev_close),
        ))
    return tr


def atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[float]:
    """Average True Range using Wilder's smoothing."""
    tr = true_range(high, low, close)
    if len(tr) < period:
        return [float('nan')] * len(tr)
    result = [float('nan')] * (period - 1)
    current_atr = sum(tr[:period]) / period
    result.append(current_atr)
    alpha = 1 / period
    for i in range(period, len(tr)):
        current_atr = (1 - alpha) * current_atr + alpha * tr[i]
        result.append(current_atr)
    return result


# ============================================================================
# RSI
# ============================================================================

def rsi(prices: List[float], period: int = 14) -> List[float]:
    """Relative Strength Index with Wilder's smoothing."""
    if len(prices) < period + 1:
        return [float('nan')] * len(prices)
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(0, c) for c in changes]
    losses = [abs(min(0, c)) for c in changes]
    result = [float('nan')] * period
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100 - (100 / (1 + rs)))
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))
    return result


# ============================================================================
# MACD
# ============================================================================

def macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Tuple[List[float], List[float], List[float]]:
    """MACD Line, Signal Line, Histogram."""
    if len(prices) < slow_period:
        nan_list = [float('nan')] * len(prices)
        return nan_list, nan_list, nan_list
    ema_fast = ema(prices, fast_period)
    ema_slow = ema(prices, slow_period)
    macd_line = []
    for f, s in zip(ema_fast, ema_slow):
        if math.isnan(f) or math.isnan(s):
            macd_line.append(float('nan'))
        else:
            macd_line.append(f - s)
    valid_start = 0
    while valid_start < len(macd_line) and math.isnan(macd_line[valid_start]):
        valid_start += 1
    valid_slice = macd_line[valid_start:]
    if len(valid_slice) < signal_period:
        signal_line = [float('nan')] * len(prices)
    else:
        signal_slice = ema(valid_slice, signal_period)
        signal_line = [float('nan')] * valid_start + signal_slice
    histogram = []
    for m, s in zip(macd_line, signal_line):
        if math.isnan(m) or math.isnan(s):
            histogram.append(float('nan'))
        else:
            histogram.append(m - s)
    return macd_line, signal_line, histogram


# ============================================================================
# BOLLINGER BANDS & SQUEEZE
# ============================================================================

def bollinger_bands(
    prices: List[float], period: int = 20, num_std: float = 2.0
) -> Tuple[List[float], List[float], List[float]]:
    """Bollinger Bands: (middle, upper, lower)."""
    if len(prices) < period:
        nan_list = [float('nan')] * len(prices)
        return nan_list, nan_list, nan_list
    middle = sma(prices, period)
    upper, lower = [], []
    for i in range(len(prices)):
        if i < period - 1:
            upper.append(float('nan'))
            lower.append(float('nan'))
        else:
            window = prices[i - period + 1: i + 1]
            mean = sum(window) / period
            variance = sum((p - mean) ** 2 for p in window) / period
            std_dev = math.sqrt(variance)
            upper.append(mean + num_std * std_dev)
            lower.append(mean - num_std * std_dev)
    return middle, upper, lower


def bb_bandwidth(middle: float, upper: float, lower: float) -> float:
    """Normalized Bollinger Band width."""
    if middle <= 0:
        return 0.0
    return (upper - lower) / middle


def keltner_channel(
    high: List[float], low: List[float], close: List[float],
    ema_period: int = 20, atr_period: int = 10, atr_mult: float = 1.5,
) -> Tuple[List[float], List[float], List[float]]:
    """Keltner Channel: EMA ± multiplier × ATR."""
    mid = ema(close, ema_period)
    atr_vals = atr(high, low, close, atr_period)
    upper_ch, lower_ch = [], []
    for m, a in zip(mid, atr_vals):
        if math.isnan(m) or math.isnan(a):
            upper_ch.append(float('nan'))
            lower_ch.append(float('nan'))
        else:
            upper_ch.append(m + atr_mult * a)
            lower_ch.append(m - atr_mult * a)
    return mid, upper_ch, lower_ch


def bb_squeeze_detect(
    high: List[float], low: List[float], close: List[float],
) -> Tuple[bool, float]:
    """Detect Bollinger Band squeeze (BB inside Keltner Channel)."""
    n = len(close)
    if n < 25:
        return False, 0.0
    _, bb_upper, bb_lower = bollinger_bands(close, 20, 2.0)
    _, kc_upper, kc_lower = keltner_channel(high, low, close, 20, 10, 1.5)
    bbu, bbl = bb_upper[-1], bb_lower[-1]
    kcu, kcl = kc_upper[-1], kc_lower[-1]
    if any(math.isnan(v) for v in (bbu, bbl, kcu, kcl)):
        return False, 0.0
    is_squeeze = bbu < kcu and bbl > kcl
    kc_width = kcu - kcl
    bb_width = bbu - bbl
    if kc_width <= 0:
        return is_squeeze, 0.0
    intensity = max(0.0, min(1.0, 1.0 - (bb_width / kc_width)))
    return is_squeeze, intensity


# ============================================================================
# ICHIMOKU CLOUD
# ============================================================================

def ichimoku(
    high: List[float], low: List[float], close: List[float],
) -> List[Optional[IchimokuCloud]]:
    """Ichimoku Cloud components."""
    if len(high) < 52:
        return [None] * len(high)
    result: List[Optional[IchimokuCloud]] = []
    for i in range(len(high)):
        if i < 52:
            result.append(None)
            continue
        h9 = max(high[i - 8: i + 1])
        l9 = min(low[i - 8: i + 1])
        tenkan = (h9 + l9) / 2
        h26 = max(high[i - 25: i + 1])
        l26 = min(low[i - 25: i + 1])
        kijun = (h26 + l26) / 2
        if i >= 26:
            prev_h9 = max(high[i - 26 - 8: i - 26 + 1])
            prev_l9 = min(low[i - 26 - 8: i - 26 + 1])
            prev_tenkan = (prev_h9 + prev_l9) / 2
            prev_h26 = max(high[i - 26 - 25: i - 26 + 1])
            prev_l26 = min(low[i - 26 - 25: i - 26 + 1])
            prev_kijun = (prev_h26 + prev_l26) / 2
            span_a = (prev_tenkan + prev_kijun) / 2
        else:
            span_a = float('nan')
        if i >= 52 + 26:
            prev_h52 = max(high[i - 26 - 51: i - 26 + 1])
            prev_l52 = min(low[i - 26 - 51: i - 26 + 1])
            span_b = (prev_h52 + prev_l52) / 2
        else:
            span_b = float('nan')
        chikou = close[i]
        result.append(IchimokuCloud(
            tenkan_sen=tenkan, kijun_sen=kijun,
            senkou_span_a=span_a, senkou_span_b=span_b,
            chikou_span=chikou,
        ))
    return result


# ============================================================================
# MOMENTUM & VOLATILITY
# ============================================================================

def momentum(prices: List[float], period: int) -> float:
    """Percentage return over period."""
    if len(prices) <= period:
        return 0.0
    old = prices[-(period + 1)]
    if old <= 0:
        return 0.0
    return (prices[-1] / old) - 1


def momentum_skip_recent(prices: List[float], period: int, skip: int = 5) -> float:
    """Momentum skipping recent N days to avoid chasing peaks."""
    if len(prices) <= period + skip:
        return 0.0
    old = prices[-(period + skip + 1)]
    recent = prices[-(skip + 1)]
    if old <= 0:
        return 0.0
    return (recent / old) - 1


def daily_returns(prices: List[float]) -> List[float]:
    """Daily percentage returns."""
    if len(prices) < 2:
        return []
    return [
        ((prices[i] / prices[i - 1]) - 1) if prices[i - 1] != 0 else 0.0
        for i in range(1, len(prices))
    ]


def realized_volatility(returns: List[float], period: int = 20) -> float:
    """Annualized realized volatility (std dev of returns × √252)."""
    if len(returns) < period:
        return float('nan')
    recent = returns[-period:]
    n = len(recent)
    mean = sum(recent) / n
    variance = sum((r - mean) ** 2 for r in recent) / max(n - 1, 1)
    return math.sqrt(variance) * math.sqrt(252)


# ============================================================================
# TREND SCORING
# ============================================================================

def trend_on(price: float, sma_50_val: float, sma_200_val: float) -> bool:
    """Check if trend is ON: Price > SMA200 and SMA50 > SMA200."""
    if math.isnan(sma_50_val) or math.isnan(sma_200_val):
        return False
    return price > sma_200_val and sma_50_val > sma_200_val


def calculate_trend_score(
    prices: List[float],
    high: List[float],
    low: List[float],
    close: List[float],
    volume: Optional[List[float]] = None,
) -> IndicatorSet:
    """
    Calculate full indicator set with composite trend score.

    This is the main scoring function — it computes 12+ indicators and
    produces a single trend_score that synthesizes momentum, MACD,
    Ichimoku, RSI, and volume signals.
    """
    result = IndicatorSet(symbol="")
    if len(prices) < 200:
        return result

    # Moving averages
    sma_50_vals = sma(prices, 50)
    sma_200_vals = sma(prices, 200)
    ema_20_vals = ema(prices, 20)
    result.sma_50 = sma_50_vals[-1] if sma_50_vals else None
    result.sma_200 = sma_200_vals[-1] if sma_200_vals else None
    result.ema_20 = ema_20_vals[-1] if ema_20_vals else None
    result.last_close = prices[-1]

    # MACD
    macd_l, signal_l, hist_l = macd(prices)
    result.macd_val = macd_l[-1] if macd_l else None
    result.macd_signal = signal_l[-1] if signal_l else None
    result.macd_hist = hist_l[-1] if hist_l else None

    # RSI
    rsi_vals = rsi(prices, 14)
    result.rsi_14 = rsi_vals[-1] if rsi_vals else None

    # Ichimoku
    clouds = ichimoku(high, low, close)
    cloud = clouds[-1] if clouds else None
    if cloud and not math.isnan(cloud.senkou_span_a) and not math.isnan(cloud.senkou_span_b):
        if cloud.senkou_span_a > cloud.senkou_span_b:
            result.cloud_color = "GREEN"
            top, bottom = cloud.senkou_span_a, cloud.senkou_span_b
        else:
            result.cloud_color = "RED"
            top, bottom = cloud.senkou_span_b, cloud.senkou_span_a
        cp = prices[-1]
        if cp > top:
            result.price_vs_cloud = "ABOVE"
        elif cp < bottom:
            result.price_vs_cloud = "BELOW"
        else:
            result.price_vs_cloud = "INSIDE"

    # ATR
    atr_vals = atr(high, low, close, 14)
    result.atr_14 = atr_vals[-1] if atr_vals else None

    # Momentum (skip last 5 days to avoid chasing)
    result.momentum_3m = momentum_skip_recent(prices, 63, skip=5)
    result.momentum_6m = momentum_skip_recent(prices, 126, skip=5)

    # Volatility
    rets = daily_returns(prices)
    result.volatility_20d = realized_volatility(rets, 20)

    # Volume ratio
    if volume and len(volume) >= 20:
        avg_vol = sum(volume[-20:]) / 20
        result.volume_ratio = volume[-1] / avg_vol if avg_vol > 0 else 1.0

    # Bollinger Band Squeeze
    if len(close) >= 25:
        squeeze, intensity = bb_squeeze_detect(high, low, close)
        result.bb_squeeze = squeeze
        result.bb_squeeze_intensity = intensity
        _, bb_up, bb_lo = bollinger_bands(close, 20, 2.0)
        bb_mid = sma(close, 20)
        if bb_mid and not math.isnan(bb_mid[-1]) and not math.isnan(bb_up[-1]):
            result.bb_bandwidth = bb_bandwidth(bb_mid[-1], bb_up[-1], bb_lo[-1])

    # Composite trend score
    cp = prices[-1]
    if trend_on(cp, result.sma_50, result.sma_200):
        base = (result.momentum_3m + result.momentum_6m) / 2

        # MACD boost/drag
        if result.macd_hist is not None:
            base += 0.05 if result.macd_hist > 0 else -0.05

        # Ichimoku boost/drag
        if result.price_vs_cloud == "ABOVE" and result.cloud_color == "GREEN":
            base += 0.05
        elif result.price_vs_cloud == "BELOW":
            base -= 0.20

        # RSI mean-reversion
        if result.rsi_14 is not None:
            if result.rsi_14 > 75:
                base -= 0.10
            elif result.rsi_14 < 30:
                base += 0.08

        # Volume confirmation
        if result.volume_ratio is not None:
            if result.volume_ratio > 1.5:
                base += 0.05
            elif result.volume_ratio < 0.5:
                base -= 0.03

        # SMA cross
        if result.sma_50 is not None and result.sma_200 is not None:
            if result.sma_50 > result.sma_200:
                base += 0.03
            else:
                base -= 0.05

        result.trend_score = base
    else:
        result.trend_score = 0.0

    return result


def format_indicator_summary(ind: IndicatorSet) -> str:
    """Human-readable indicator summary."""
    lines = [f"── {ind.symbol} Technical Snapshot ──"]
    if ind.last_close is not None:
        lines.append(f"  Price:        ${ind.last_close:,.2f}")
    if ind.sma_50 is not None:
        lines.append(f"  SMA(50):      ${ind.sma_50:,.2f}")
    if ind.sma_200 is not None:
        lines.append(f"  SMA(200):     ${ind.sma_200:,.2f}")
    if ind.rsi_14 is not None:
        lines.append(f"  RSI(14):      {ind.rsi_14:.1f}")
    if ind.macd_hist is not None:
        lines.append(f"  MACD Hist:    {ind.macd_hist:+.4f}")
    if ind.atr_14 is not None:
        lines.append(f"  ATR(14):      ${ind.atr_14:.2f}")
    if ind.cloud_color:
        lines.append(f"  Ichimoku:     {ind.price_vs_cloud} cloud ({ind.cloud_color})")
    if ind.bb_squeeze is not None:
        sq = "YES" if ind.bb_squeeze else "no"
        lines.append(f"  BB Squeeze:   {sq}" + (f" (intensity {ind.bb_squeeze_intensity:.2f})" if ind.bb_squeeze else ""))
    if ind.momentum_3m is not None:
        lines.append(f"  Mom (3m):     {ind.momentum_3m:+.2%}")
    if ind.momentum_6m is not None:
        lines.append(f"  Mom (6m):     {ind.momentum_6m:+.2%}")
    if ind.volatility_20d is not None:
        lines.append(f"  Vol (20d):    {ind.volatility_20d:.1%} ann.")
    if ind.trend_score is not None:
        lines.append(f"  Trend Score:  {ind.trend_score:+.4f}")
    return "\n".join(lines)
