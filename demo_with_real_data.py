#!/usr/bin/env python3
"""
Enhanced demo with realistic portfolio data for contest submission.
This simulates the full DVRR Autopilot experience without requiring API keys.
"""

import sys
import json

from scripts.indicators import calculate_trend_score, format_indicator_summary
from scripts.regime import classify_regime, get_sleeve_weights, format_regime_summary
from scripts.sizing import SizingConfig, SizingMethod, calculate_position_size, format_sizing


def _configure_stdout() -> None:
    """Use UTF-8 stdout when the terminal supports it."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def generate_realistic_portfolio():
    """Generate realistic portfolio data for demo."""
    return [
        {
            "symbol": "AAPL",
            "quantity": 50,
            "market_value": 11600.00,
            "instrument_type": "EQUITY"
        },
        {
            "symbol": "MSFT", 
            "quantity": 30,
            "market_value": 10500.00,
            "instrument_type": "EQUITY"
        },
        {
            "symbol": "GOOGL",
            "quantity": 15,
            "market_value": 2450.00,
            "instrument_type": "EQUITY"
        },
        {
            "symbol": "NVDA",
            "quantity": 25,
            "market_value": 22500.00,
            "instrument_type": "EQUITY"
        },
        {
            "symbol": "TSLA",
            "quantity": 40,
            "market_value": 9600.00,
            "instrument_type": "EQUITY"
        }
    ]

def generate_realistic_market_data():
    """Generate realistic market data with current trends."""
    import random
    import math
    
    # SPY data - recent downtrend with high volatility
    spy_base = 450.0
    spy_prices = []
    for i in range(252):
        # Recent downtrend pattern
        trend = -0.001 if i > 200 else 0.0005  # Turn negative recently
        volatility = 0.025 if i > 180 else 0.015  # Increased volatility
        change = random.gauss(trend, volatility)
        spy_base = spy_base * (1 + change)
        spy_prices.append(max(spy_base, 100.0))
    
    # Generate OHLCV for SPY
    spy_data = {
        "open": [spy_prices[0]] + spy_prices[:-1],
        "high": [p * (1 + random.uniform(0.01, 0.03)) for p in spy_prices],
        "low": [p * (1 - random.uniform(0.01, 0.03)) for p in spy_prices],
        "close": spy_prices,
        "volume": [random.randint(80000000, 120000000) for _ in range(252)]
    }
    
    # Individual stock data
    stocks_data = {}
    stock_configs = {
        "AAPL": {"base": 232.0, "trend": 0.001, "vol": 0.02},  # Strong performer
        "MSFT": {"base": 350.0, "trend": 0.0005, "vol": 0.018},  # Moderate
        "GOOGL": {"base": 163.0, "trend": -0.0008, "vol": 0.022},  # Lagging
        "NVDA": {"base": 900.0, "trend": 0.002, "vol": 0.035},  # High momentum
        "TSLA": {"base": 240.0, "trend": -0.0015, "vol": 0.04},  # Volatile, declining
    }
    
    for symbol, config in stock_configs.items():
        prices = []
        base = config["base"]
        for i in range(252):
            change = random.gauss(config["trend"], config["vol"])
            base = base * (1 + change)
            prices.append(max(base, 10.0))
        
        stocks_data[symbol] = {
            "open": [prices[0]] + prices[:-1],
            "high": [p * (1 + random.uniform(0.01, 0.04)) for p in prices],
            "low": [p * (1 - random.uniform(0.01, 0.04)) for p in prices],
            "close": prices,
            "volume": [random.randint(20000000, 100000000) for _ in range(252)]
        }
    
    return spy_data, stocks_data

def main():
    _configure_stdout()
    print("╔══════════════════════════════════════════════╗")
    print("║    DVRR AUTOPILOT - CONTEST DEMO             ║")
    print("║    Realistic Portfolio Analysis               ║")
    print("╚══════════════════════════════════════════════╝")
    
    # Step 1: Load portfolio
    print("\n💼 Loading portfolio from Public.com...")
    portfolio = generate_realistic_portfolio()
    total_equity = sum(pos["market_value"] for pos in portfolio)
    
    print("   Account: DEMO-ACCT-01")
    print(f"   Equity:  ${total_equity:,.2f}")
    print(f"   Cash:    ${(total_equity * 0.1):,.2f}")  # Assume 10% cash
    print(f"   Positions: {len(portfolio)}")
    
    for pos in portfolio:
        print(f"     {pos['symbol']:6}: {pos['quantity']:3} shares @ ${(pos['market_value']/pos['quantity']):.2f} = ${pos['market_value']:,.2f}")
    
    # Step 2: Fetch market data
    print("\n📊 Fetching market data from Polygon.io...")
    spy_data, stocks_data = generate_realistic_market_data()
    
    print(f"   ✓ SPY: {len(spy_data['close'])} bars")
    for symbol in stocks_data:
        print(f"   ✓ {symbol}: {len(stocks_data[symbol]['close'])} bars")
    
    # Step 3: Regime classification
    print("\n🌡️  Classifying market regime on SPY...")
    regime = classify_regime(
        prices=spy_data["close"],
        high=spy_data["high"], 
        low=spy_data["low"],
        close=spy_data["close"]
    )
    
    weights, scale = get_sleeve_weights(regime)
    print(format_regime_summary(regime, weights, scale))
    
    # Step 4: Score positions
    print("\n📈 Scoring positions with technical indicators...")
    scored_positions = []
    
    for pos in portfolio:
        if pos["symbol"] not in stocks_data:
            continue
            
        data = stocks_data[pos["symbol"]]
        indicators = calculate_trend_score(
            prices=data["close"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"]
        )
        indicators.symbol = pos["symbol"]
        scored_positions.append((pos, indicators))
        print(format_indicator_summary(indicators))
    
    # Sort by trend score
    scored_positions.sort(key=lambda x: x[1].trend_score or 0, reverse=True)
    
    # Step 5: Generate trade suggestions
    print("\n⚡ Generating rebalance trade suggestions...")
    sizing_config = SizingConfig(
        method=SizingMethod.HYBRID,
        risk_per_trade_pct=0.02,
        max_position_pct=0.10
    )
    
    trade_intents = []
    min_trend_score = 0.02
    
    for pos, indicators in scored_positions:
        current_weight = pos["market_value"] / total_equity
        
        # SELL suggestions for weak performers
        if indicators.trend_score and indicators.trend_score < min_trend_score:
            sell_qty = pos["quantity"] * 0.5
            sell_notional = sell_qty * indicators.last_close
            trade_intents.append({
                "symbol": pos["symbol"],
                "side": "SELL",
                "quantity": round(sell_qty, 4),
                "notional": round(sell_notional, 2),
                "reason": f"Weak trend score ({indicators.trend_score:+.4f} < {min_trend_score})"
            })
        
        # BUY suggestions for strong performers
        elif indicators.trend_score and indicators.trend_score > min_trend_score * 2:
            if current_weight < 0.05:  # Underweight
                confidence = min(1.0, indicators.trend_score * 3 + 0.3)
                sizing = calculate_position_size(
                    config=sizing_config,
                    portfolio_value=total_equity,
                    symbol=pos["symbol"],
                    entry_price=indicators.last_close,
                    confidence=confidence,
                    atr_14=indicators.atr_14,
                    volatility_regime=regime.volatility.value,
                    existing_position_value=pos["market_value"]
                )
                
                if sizing.suggested_notional > 0:
                    trade_intents.append({
                        "symbol": pos["symbol"],
                        "side": "BUY",
                        "quantity": round(sizing.suggested_shares, 4),
                        "notional": round(sizing.suggested_notional, 2),
                        "reason": f"Strong trend ({indicators.trend_score:+.4f}), underweight ({current_weight:.1%})",
                        "sizing_summary": f"${sizing.suggested_notional:,.2f} ({sizing.suggested_shares:.2f} shares) - Risk: ${sizing.risk_amount:,.2f}"
                    })
    
    # Print trade suggestions
    if trade_intents:
        print(f"\n   📋 {len(trade_intents)} trade(s) proposed:")
        for intent in trade_intents:
            emoji = "🟢" if intent["side"] == "BUY" else "🔴"
            print(f"   {emoji} {intent['side']} {intent['quantity']:.4f} {intent['symbol']} — ${intent['notional']:,.2f}")
            print(f"      Reason: {intent['reason']}")
            if "sizing_summary" in intent:
                print(f"      Sizing: {intent['sizing_summary']}")
    else:
        print("   ✅ Portfolio is balanced. No trades needed.")
    
    # Step 6: Summary
    print("\n" + "=" * 60)
    print("  DVRR AUTOPILOT DEMO COMPLETE")
    print(f"  Market Regime: {regime.trend.value} / {regime.volatility.value}")
    print(f"  Portfolio: ${total_equity:,.2f} across {len(portfolio)} positions")
    print(f"  Trades: {len(trade_intents)} suggested (0 executed)")
    print("=" * 60)
    
    # JSON output for agent consumption
    output = {
        "mode": "SUGGEST",
        "account": {
            "equity": total_equity,
            "cash": total_equity * 0.1,
            "buying_power": total_equity * 1.1,
            "position_count": len(portfolio)
        },
        "regime": {
            "trend": regime.trend.value,
            "trend_confidence": regime.trend_confidence,
            "volatility": regime.volatility.value,
            "volatility_percentile": regime.volatility_percentile,
            "tradability": regime.tradability_score
        },
        "sleeve_weights": weights,
        "scale_factor": scale,
        "positions_scored": len(scored_positions),
        "trades_proposed": len(trade_intents),
        "trades_executed": 0,
        "trade_intents": trade_intents,
        "executed_orders": [],
        "errors": []
    }
    
    print("\n📊 Structured Output (JSON):")
    print(json.dumps(output, indent=2))
    
    return output

if __name__ == "__main__":
    main()
