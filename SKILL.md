---
name: dvrr-autopilot
description: >
  Regime-aware autonomous portfolio rebalancer for Public.com. Classifies market
  conditions (trending, choppy, volatile), scores every holding with 12+ technical
  indicators, computes optimal position sizes using Kelly/ATR/hybrid math, and
  executes rebalance trades through the Public API — all in one agent invocation.
  Use this skill when the user asks to analyze their portfolio, detect the current
  market regime, get smart rebalance suggestions, or run an autonomous trading cycle
  on their Public.com brokerage account.
env:
  PUBLIC_API_SECRET:
    description: "Your Public.com API secret key (Settings → API Keys)"
    required: true
  PUBLIC_ACCOUNT_ID:
    description: "Your Public.com brokerage account ID"
    required: true
  DVRR_MODE:
    description: "Execution mode: ANALYZE (read-only), SUGGEST (show trades), or EXECUTE (place orders)"
    required: false
    default: "SUGGEST"
  DVRR_RISK_PER_TRADE:
    description: "Max risk per trade as decimal (default 0.02 = 2%)"
    required: false
    default: "0.02"
  DVRR_MAX_POSITION_PCT:
    description: "Max single position as % of portfolio (default 0.10 = 10%)"
    required: false
    default: "0.10"
  POLYGON_API_KEY:
    description: "Polygon.io API key for historical OHLCV data (free tier works)"
    required: true
---

# DVRR Autopilot — Regime-Aware Autonomous Rebalancer

A production-grade trading skill that brings institutional-quality regime detection,
multi-factor technical scoring, and intelligent position sizing to any Public.com
portfolio. Derived from a battle-tested autonomous trading agent running the DVRR
(Diversified Volatility-Responsive Rotation) strategy.

## What This Skill Does

1. **Authenticates** with Public.com and loads your portfolio (positions, balances, buying power)
2. **Fetches historical OHLCV** data for SPY (market benchmark) and every holding via Polygon.io
3. **Classifies the market regime** — Trending (strong up/down), Choppy, or Volatile — using MA alignment, slope analysis, and volatility percentile ranking
4. **Computes sleeve weights** — Dynamically allocates between TREND, BREAKOUT, and REVERSION strategies based on the detected regime
5. **Scores every position** with 12+ technical indicators: SMA(50/200), EMA(20), RSI(14), MACD, Ichimoku Cloud, Bollinger Band Squeeze, ATR(14), momentum (3m/6m with recency skip), volume ratio
6. **Sizes trades optimally** using a hybrid engine: ATR-based volatility sizing → Kelly criterion overlay → confidence scaling → loss-streak dampening → regime-based exposure reduction
7. **Generates rebalance orders** — BUY underweight winners, SELL overweight losers, with exact share quantities and dollar amounts
8. **Executes via Public API** — In EXECUTE mode, places real orders through Public.com (market or limit)

## Modes

| Mode | Behavior |
|------|----------|
| `ANALYZE` | Read-only. Shows regime, scores, and risk metrics. No trade suggestions. |
| `SUGGEST` | Default. Shows everything above + specific rebalance trades with sizing. |
| `EXECUTE` | Places the suggested orders through Public.com. **Real money.** Requires explicit user confirmation. |

## How to Use

### Quick Portfolio Analysis
```
Analyze my Public.com portfolio — what's the current market regime and how are my positions scoring?
```

### Get Rebalance Suggestions
```
Run the DVRR autopilot on my portfolio in SUGGEST mode. Show me what trades it recommends and why.
```

### Full Autonomous Cycle
```
Run a full DVRR autopilot cycle in EXECUTE mode. Rebalance my portfolio based on the current regime.
```

### Specific Analysis
```
What regime is the market in right now? Should I be more defensive or aggressive?
```
```
Score AAPL, MSFT, and NVDA — which one has the strongest trend setup right now?
```
```
Calculate optimal position size for buying TSLA given my current portfolio and risk tolerance.
```

## Architecture

```
scripts/
├── public_client.py    # Public.com API client (auth, positions, quotes, orders)
├── indicators.py       # 12+ pure-math technical indicators (zero dependencies)
├── regime.py           # Market regime classifier + sleeve weight allocator
├── sizing.py           # Kelly / ATR / hybrid position sizing engine
└── autopilot.py        # Main orchestrator — ties everything together
```

## Safety & Guardrails

- **No trading required** — ANALYZE and SUGGEST modes are read-only and never place orders. The skill provides full value (regime detection, scoring, sizing math) without any trading activity.
- **Default mode is SUGGEST** — never places trades without explicit opt-in
- **EXECUTE mode requires user confirmation** before every order
- **Position limits enforced** — max 10% per position, max 30% per sector
- **Risk per trade capped** — default 2% of portfolio, configurable
- **Extreme volatility circuit breaker** — reduces exposure to 30% in crisis regimes
- **Loss streak dampening** — halves position sizes after consecutive losses
- **All API keys via env vars** — never hardcoded, never logged

## Technical Indicators Computed

| Indicator | Purpose |
|-----------|---------|
| SMA(50), SMA(200) | Trend identification, golden/death cross |
| EMA(20) | Short-term momentum |
| RSI(14) | Overbought/oversold detection |
| MACD (12/26/9) | Momentum confirmation |
| Ichimoku Cloud | Trend strength + support/resistance |
| ATR(14) | Volatility measurement, stop placement |
| Bollinger Band Squeeze | Breakout detection |
| Momentum (3m, 6m) | Medium-term trend strength |
| Volume Ratio | Conviction confirmation |
| Realized Volatility (20d) | Risk assessment |

## Regime Classifications

| Regime | Sleeve Weights | Exposure |
|--------|---------------|----------|
| **Strong Uptrend** | TREND 70%, BREAKOUT 20%, REVERSION 10% | 100% |
| **Uptrend** | TREND 55%, BREAKOUT 30%, REVERSION 15% | 100% |
| **Choppy** | TREND 20%, BREAKOUT 30%, REVERSION 50% | 100% |
| **High Volatility** | Adjusted weights | 70% (30% cash) |
| **Extreme Volatility** | Reduced all | 30% (70% cash) |

## Position Sizing Methods

| Method | Description |
|--------|-------------|
| **ATR-based** | Position size = (Portfolio × Risk%) / (ATR × Multiple) |
| **Kelly Criterion** | Optimal f based on win rate and payoff ratio (¼ Kelly for safety) |
| **Confidence Scaling** | Scale up/down based on signal confidence (0.4–1.5×) |
| **Loss Streak Dampening** | Halve size after 2+ consecutive losses |
| **Regime Adjustment** | Cut 50% in HIGH vol, 70% in EXTREME vol |

## Dependencies

- Python 3.9+
- `httpx` — HTTP client for Public.com and Polygon APIs
- No other external dependencies. All indicators are pure Python math.

## Setup

```bash
pip install httpx
export PUBLIC_API_SECRET="your-secret-key"
export PUBLIC_ACCOUNT_ID="your-account-id"
export POLYGON_API_KEY="your-polygon-key"
```

Run directly:
```bash
python -m scripts
```
