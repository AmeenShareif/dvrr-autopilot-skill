# DVRR Autopilot — Public.com Portfolio Copilot

> Turn a Public.com account into a regime-aware decision engine in one command.

DVRR Autopilot is built for one job: give an AI agent a real portfolio, a current market regime, and a clear answer about what to do next.

It combines live Public.com account data, Polygon market data, technical scoring, and risk-aware sizing so users can get a portfolio-specific answer instead of a generic market explanation.

---

## Why Use This Instead of Google?

Google can explain RSI, moving averages, or market regimes.

It cannot see:
- your live Public.com holdings
- your cash and buying power
- your current position sizes
- your preferred risk limits
- whether one specific ticker should be trimmed, held, or added to

DVRR Autopilot answers the question Google cannot:

> “Given my actual account and the current market regime, what should I do now?”

---

## What You Get In One Run

| Capability | What it means for the user |
|------------|----------------------------|
| Load portfolio | Pulls account balance, positions, cash, and buying power |
| Detect regime | Classifies the market as trending, choppy, or volatile |
| Score holdings | Computes 12+ technical indicators on each holding or one focused ticker |
| Size trades | Uses ATR, Kelly, confidence, and regime overlays to size suggestions |
| Generate orders | Produces exact buy/sell quantities and dollar amounts |
| Execute safely | Keeps `SUGGEST` as the default so nothing trades by accident |

---

## Best First Demo

If you want the fastest, cleanest proof that the skill works, run it on one ticker:

```bash
python -m scripts --symbol NVDA
```

That path fetches `SPY` plus only the requested symbol, which makes the demo fast and avoids scanning every holding in a large account.

---

## Quick Start

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
export DVRR_TARGET_SYMBOL="NVDA"    # optional: analyze one ticker only
```

Env-file precedence:
- `DVRR_ENV_FILE` if set
- `scripts/.env` if present
- OpenClaw secure files from the official Public Agent Skill if present
- repo-root `.env`

Credential names:
- `PUBLIC_API_SECRET` or `PUBLIC_COM_SECRET`
- `PUBLIC_ACCOUNT_ID` or `PUBLIC_COM_ACCOUNT_ID`
- the skill normalizes both sets automatically

### 3. Run

```bash
# Full portfolio analysis
python -m scripts

# Focus on one ticker only
python -m scripts --symbol NVDA
```

If live Public.com or Polygon credentials are unavailable, `python -m scripts`
falls back to the contest demo analysis so it still returns a structured result.

If you are already using the official Public.com OpenClaw skill, you can keep the
same Public credentials there. DVRR Autopilot reads the same secure-file layout and
accepts the same Public credential aliases.

### 4. Optional demos

```bash
python demo.py
python demo_with_real_data.py
```

---

## What It Looks Like

The output is designed to be readable by humans and downstream agents:

- account summary
- market regime
- sleeve allocation
- per-symbol technical snapshot
- trade intents with reasons
- structured JSON for automation

That makes it useful both as a portfolio copilot and as a machine-readable skill.

---

## Why It Is Useful

- It gives a portfolio-specific answer, not a market article.
- It works safely in `SUGGEST` mode by default.
- It supports single-ticker focus for large accounts.
- It produces structured output that another agent can consume.
- It is built around live account context, not generic education.

---

## Technical Edge

| Area | Strength |
|------|----------|
| Market regime | SPY-based trend and volatility classification |
| Indicators | 12+ pure-Python technical indicators |
| Position sizing | Hybrid ATR / Kelly / confidence sizing |
| Scale control | `DVRR_TARGET_SYMBOL` for one-symbol analysis |
| Safety | Read-only default, explicit execute gate |
| Integration | Works as a local skill, not a hosted service |

---

## Usage with AI Agents

Tell your agent something like:

```text
Analyze my Public.com portfolio using the DVRR Autopilot skill.
Tell me the current market regime, which positions are weak, and whether I should trim or hold them.
```

For a single name:

```text
Analyze NVDA only and tell me if it looks like a buy, hold, or sell candidate.
```

---

## File Structure

```
dvrr-autopilot/
├── SKILL.md               # Agent skill manifest
├── README.md              # Public-facing overview
├── .env.example           # Safe template for local secrets
├── requirements.txt       # Python dependencies
├── demo.py                # Offline demo with synthetic data
├── demo_with_real_data.py # Richer offline demo with synthetic portfolio data
└── scripts/
    ├── __init__.py
    ├── __main__.py        # CLI entry point
    ├── autopilot.py       # Main orchestrator
    ├── public_client.py   # Public.com API wrapper
    ├── indicators.py     # Technical indicators
    ├── regime.py         # Market regime classifier
    └── sizing.py         # Position sizing engine
```

---

## Safety

- `SUGGEST` is the default mode
- `EXECUTE` requires explicit confirmation
- all secrets come from env vars
- no hardcoded API keys
- no trade execution is required to get value from the skill

---

## Disclaimer

This skill is for educational and informational purposes only. `SUGGEST` and `ANALYZE`
are read-only. If you choose `EXECUTE`, trades must comply with Public's Terms of Service
and should only be placed after careful review.

Nothing in this project constitutes investment advice or a recommendation to buy or sell
securities. Trading involves risk of loss.

Brokerage services are provided by Open to the Public Investing, Inc., Member FINRA / SIPC.
