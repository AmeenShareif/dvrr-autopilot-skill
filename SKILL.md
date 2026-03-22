---
name: dvrr-autopilot
description: >
  Public.com portfolio copilot for live account analysis, market-regime detection,
  single-ticker deep dives, and safe rebalance suggestions in one run. Use this
  skill when the user wants an account-specific answer about what to trim, hold,
  add, or watch next.
env:
  PUBLIC_API_SECRET:
    description: "Your Public.com API secret key for live mode; if absent, the skill falls back to contest demo analysis"
    required: false
  PUBLIC_ACCOUNT_ID:
    description: "Your Public.com brokerage account ID for live mode; if absent, the skill falls back to contest demo analysis"
    required: false
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
  DVRR_TARGET_SYMBOL:
    description: "Optional single ticker to analyze; when set, the skill fetches SPY plus that symbol only"
    required: false
  POLYGON_API_KEY:
    description: "Polygon.io API key for live historical OHLCV data; if absent, the skill falls back to contest demo analysis"
    required: false
---

# DVRR Autopilot — Public.com Portfolio Copilot

A production-grade trading skill that turns a Public.com account into a live,
regime-aware decision engine. It combines market classification, multi-factor
technical scoring, and risk-aware sizing so an AI agent can answer the question:
“What should I do with my portfolio right now?”

## What This Skill Does

1. **Loads the live portfolio** from Public.com, including balances, positions, cash, and buying power
2. **Classifies the market regime** from SPY so the agent knows whether to lean trend, breakout, or reversion
3. **Scores holdings or one focused ticker** with 12+ technical indicators
4. **Sizes trades intelligently** with ATR, Kelly, confidence scaling, and regime overlays
5. **Generates clear rebalance ideas** with exact share counts and dollar amounts
6. **Executes only when asked** in `EXECUTE` mode, with confirmation and guardrails

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

If the user wants the fastest proof that the skill works, use the single-ticker path:

```bash
python -m scripts --symbol NVDA
```

That mode fetches `SPY` plus only the requested ticker, which is ideal for large
accounts or short live demos.

If live Public or Polygon credentials are unavailable, `python -m scripts` automatically falls back to the contest demo analysis so the skill still returns a structured result.

Environment loading precedence:
- `DVRR_ENV_FILE` if set
- `scripts/.env` if present
- repo-root `.env`

Single-ticker mode:
- Set `DVRR_TARGET_SYMBOL=NVDA` or run `python -m scripts --symbol NVDA`
- The skill will fetch `SPY` plus that ticker only, instead of walking the entire holdings list
- This is the recommended mode when the user asks about one symbol or the account has many holdings

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
Analyze NVDA only and tell me whether it is a buy, hold, or sell candidate.
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

Offline demos:
```bash
python demo.py
python demo_with_real_data.py
```
