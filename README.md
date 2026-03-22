# DVRR Autopilot — Regime-Aware Autonomous Rebalancer

> **A production-grade Agent Skill that turns any AI agent into an autonomous portfolio manager for Public.com.**

Built from a battle-tested trading agent running the **DVRR (Diversified Volatility-Responsive Rotation)** strategy. This skill chains 5+ Public API capabilities into a regime-aware trading pipeline — from market analysis to order execution.

---

## 🎯 What It Does

| Step | Description | Public API Used |
|------|-------------|-----------------|
| 1. **Load Portfolio** | Fetches account balance, positions, P&L | Account, Positions |
| 2. **Classify Regime** | Detects trending/choppy/volatile market using SPY | (Polygon.io for OHLCV) |
| 3. **Score Holdings** | Computes 12+ technical indicators per position | Quotes |
| 4. **Size Trades** | Hybrid Kelly/ATR/confidence position sizing | — |
| 5. **Generate Orders** | BUY underweight winners, SELL weak positions | Preflight |
| 6. **Execute** | Places real orders through Public.com | Orders |

## ⚡ Quick Start

### 1. Install

```bash
pip install httpx
```

### 2. Configure

```bash
export PUBLIC_API_SECRET="your-public-api-secret"
export PUBLIC_ACCOUNT_ID="your-account-id"
export POLYGON_API_KEY="your-polygon-key"
export DVRR_MODE="SUGGEST"          # ANALYZE | SUGGEST | EXECUTE
```

### 3. Run

```bash
# From this directory
python -m scripts

# Or ask your AI agent:
# "Run the DVRR autopilot on my portfolio"
```

## 🤖 Usage with AI Agents

### Claude / Claude Code
Upload this skill folder, or point Claude to `SKILL.md`:
```
Analyze my Public.com portfolio using the DVRR autopilot skill.
What regime is the market in? What trades should I make?
```

### Perplexity Computer
Upload as a skill ZIP:
```
Run a full DVRR autopilot cycle in SUGGEST mode on my Public.com account.
```

### OpenClaw / Any Agent
Point the agent to read `SKILL.md` for instructions, then:
```
Execute the DVRR rebalancer. Show me the regime analysis and trade suggestions.
```

## 🔒 Safety

- **Default mode is SUGGEST** — read-only analysis + trade recommendations, no execution
- **EXECUTE requires typing "CONFIRM"** — human-in-the-loop gate
- **Position limits enforced** — max 10% per position, 30% per sector
- **Risk capped** — 2% portfolio risk per trade (configurable)
- **Circuit breaker** — extreme volatility → 70% cash reserve
- **Loss dampening** — halves sizes after consecutive losses
- **No hardcoded secrets** — all keys via env vars

## 📊 What Gets Analyzed

### Market Regime (via SPY)
| Regime | Description | Capital Deployed |
|--------|-------------|-----------------|
| Strong Uptrend | All MAs aligned bullish, positive slope | 100% |
| Uptrend | Majority bullish signals | 100% |
| Choppy | Mixed signals, no clear direction | 100% (reversion-heavy) |
| High Volatility | Vol > 75th percentile | 70% |
| Extreme Volatility | Vol > 95th percentile | 30% |

### Technical Indicators (per position)
- **SMA(50), SMA(200)** — Golden/death cross, trend filter
- **EMA(20)** — Short-term momentum
- **RSI(14)** — Overbought/oversold
- **MACD (12/26/9)** — Momentum confirmation
- **Ichimoku Cloud** — Trend strength + support/resistance levels
- **ATR(14)** — Volatility for stop placement
- **Bollinger Band Squeeze** — Breakout detection (BB inside Keltner)
- **Momentum (3m, 6m)** — Medium-term trend with recency skip
- **Volume Ratio** — Current vs 20-day average
- **Realized Volatility** — Annualized 20-day

### Position Sizing Engine
- **ATR-based**: `Shares = (Portfolio × Risk%) / (ATR × 2)`
- **Kelly Criterion**: Optimal f* with ¼ fractional Kelly
- **Confidence Scaling**: 0.4–1.5× based on signal strength
- **Loss Streak**: Halve size after 2+ consecutive losses
- **Regime Overlay**: -50% in HIGH vol, -70% in EXTREME

## 📁 File Structure

```
dvrr-autopilot/
├── SKILL.md                 # Agent skill manifest (read this first)
├── README.md                # This file
├── requirements.txt         # Python dependencies
└── scripts/
    ├── __init__.py
    ├── __main__.py          # CLI entry point
    ├── autopilot.py         # Main orchestrator
    ├── public_client.py     # Public.com API wrapper
    ├── indicators.py        # 12+ technical indicators (pure math)
    ├── regime.py            # Market regime classifier
    └── sizing.py            # Position sizing engine
```

## 🧪 Example Output

```
╔══════════════════════════════════════════════╗
║    DVRR AUTOPILOT — Regime-Aware Rebalancer  ║
║    Powered by Public.com API + Polygon.io    ║
╚══════════════════════════════════════════════╝

🔐 Connecting to Public.com...
   Account: ABC123
   Equity:  $25,420.00
   Cash:    $3,200.00
   Positions: 12

📊 Fetching historical data from Polygon.io...
   ✓ SPY: 252 bars
   ✓ AAPL: 252 bars
   ✓ NVDA: 252 bars
   ...

══════════════════════════════════════
       MARKET REGIME ANALYSIS
══════════════════════════════════════
  Trend:       UPTREND (confidence 65%)
  Volatility:  MEDIUM (percentile 45%)
  Tradability: 0.87

  Sleeve Allocation:
    TREND:     55%
    BREAKOUT:  30%
    REVERSION: 15%
    Cash:      0%
══════════════════════════════════════
  Trade Gate:  ✅ OPEN

📈 Scoring positions...
── NVDA Technical Snapshot ──
  Price:        $875.50
  SMA(50):      $842.30
  SMA(200):     $715.60
  RSI(14):      62.3
  MACD Hist:    +3.2100
  ATR(14):      $18.45
  Ichimoku:     ABOVE cloud (GREEN)
  Mom (3m):     +18.52%
  Trend Score:  +0.1850

⚡ Generating rebalance trades...
   📋 3 trade(s) proposed:
   🟢 BUY 5.2300 NVDA — $4,582.65
      Reason: Strong trend (+0.1850), underweight (3.2% vs 5.5%)
   🔴 SELL 10.0000 INTC — $312.50
      Reason: Weak trend score (-0.0320 < 0.02)
   🟢 BUY 12.5000 AAPL — $2,187.50
      Reason: Strong trend (+0.0920), underweight (2.1% vs 4.2%)
```

## 🏗️ Architecture

This skill is **self-contained** — no database, no external services beyond Public.com and Polygon.io. All technical analysis is computed with pure Python math (no numpy/pandas required). The entire indicator library, regime classifier, and sizing engine are zero-dependency.

The design is intentionally modular so agents can call individual components:
- Just want regime? Call `regime.classify_regime()`
- Just want indicators? Call `indicators.calculate_trend_score()`
- Just want sizing? Call `sizing.calculate_position_size()`

## 📜 License

MIT — Use freely, trade responsibly.

## ⚠️ Disclaimer

This skill is for educational and informational purposes only. **No trading activity is required** to use this skill — the default SUGGEST mode and ANALYZE mode are fully read-only and never place orders. If you choose to use EXECUTE mode, trades must comply with Public's Terms of Service and must be executed in good faith.

Nothing in this project constitutes investment advice or a recommendation to buy or sell securities. Trading involves risk of loss. Always review trade suggestions before execution. The authors are not responsible for any financial losses. Participants should only trade if consistent with their own investment objectives and financial circumstances.

Brokerage services are provided by Open to the Public Investing, Inc., Member FINRA / SIPC.
