#!/usr/bin/env python3
"""
Demo script for DVRR Autopilot - Shows functionality without API keys.
Demonstrates indicators, regime classification, and position sizing with sample data.
"""

import sys

from scripts.indicators import calculate_trend_score, format_indicator_summary
from scripts.regime import classify_regime, get_sleeve_weights, format_regime_summary
from scripts.sizing import SizingConfig, SizingMethod, calculate_position_size, format_sizing


def _configure_stdout() -> None:
    """Use UTF-8 stdout when the terminal supports it."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def generate_sample_data(symbol="AAPL", days=252):
    """Generate realistic sample OHLCV data for demonstration."""
    import random
    import math
    
    # Start with base price
    base_price = 150.0
    prices = [base_price]
    
    # Generate realistic price movement
    for i in range(days - 1):
        # Random walk with slight upward trend
        change = random.gauss(0.0005, 0.02)  # 0.05% daily drift, 2% volatility
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1.0))  # Ensure positive price
    
    # Generate OHLCV from prices
    high = []
    low = []
    close = prices[:]
    volume = []
    
    for i, price in enumerate(prices):
        # Add some intraday variation
        intraday_vol = random.uniform(0.005, 0.03)
        high.append(price * (1 + intraday_vol))
        low.append(price * (1 - intraday_vol))
        volume.append(random.randint(50000000, 150000000))  # 50M-150M shares
    
    # Open is previous close (except first day)
    open_price = [prices[0]] + prices[:-1]
    
    return {
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }

def main():
    _configure_stdout()
    print("╔══════════════════════════════════════════════╗")
    print("║    DVRR AUTOPILOT DEMO (No API Keys)       ║")
    print("║    Demonstrating core functionality        ║")
    print("╚══════════════════════════════════════════════╝")
    
    print("\n📊 Generating sample market data...")
    spy_data = generate_sample_data("SPY", 252)
    aapl_data = generate_sample_data("AAPL", 252)
    msft_data = generate_sample_data("MSFT", 252)
    
    print("   ✓ SPY: 252 trading days")
    print("   ✓ AAPL: 252 trading days") 
    print("   ✓ MSFT: 252 trading days")
    
    # Step 1: Regime Classification
    print("\n🌡️  Classifying market regime on SPY...")
    regime = classify_regime(
        prices=spy_data["close"],
        high=spy_data["high"],
        low=spy_data["low"],
        close=spy_data["close"]
    )
    
    weights, scale = get_sleeve_weights(regime)
    print(format_regime_summary(regime, weights, scale))
    
    # Step 2: Technical Analysis
    print("\n📈 Computing technical indicators...")
    symbols_data = [("AAPL", aapl_data), ("MSFT", msft_data)]
    
    for symbol, data in symbols_data:
        indicators = calculate_trend_score(
            prices=data["close"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"]
        )
        indicators.symbol = symbol
        print(format_indicator_summary(indicators))
    
    # Step 3: Position Sizing Demo
    print("\n💰 Position sizing demonstration...")
    sizing_config = SizingConfig(
        method=SizingMethod.HYBRID,
        risk_per_trade_pct=0.02,
        max_position_pct=0.10
    )
    
    # Demo sizing for AAPL
    aapl_indicators = calculate_trend_score(
        prices=aapl_data["close"],
        high=aapl_data["high"],
        low=aapl_data["low"],
        close=aapl_data["close"],
        volume=aapl_data["volume"]
    )
    
    sizing_result = calculate_position_size(
        config=sizing_config,
        portfolio_value=100000,  # $100k portfolio
        symbol="AAPL",
        entry_price=aapl_data["close"][-1],
        confidence=0.7,
        atr_14=aapl_indicators.atr_14,
        volatility_regime=regime.volatility.value
    )
    
    print(format_sizing(sizing_result))
    
    # Step 4: Summary
    print("\n" + "=" * 50)
    print("  DEMO COMPLETE")
    print(f"  Market Regime: {regime.trend.value} / {regime.volatility.value}")
    print(f"  Recommended Allocation: {weights.get('TREND', 0):.0%} Trend, {weights.get('BREAKOUT', 0):.0%} Breakout, {weights.get('REVERSION', 0):.0%} Reversion")
    print(f"  Cash Reserve: {1.0 - scale:.0%}")
    print("=" * 50)
    
    print("\n✅ To use with real data:")
    print("   1. Set environment variables:")
    print("      export PUBLIC_API_SECRET='your-secret'")
    print("      export PUBLIC_ACCOUNT_ID='your-account'")
    print("      export POLYGON_API_KEY='your-polygon-key'")
    print("   2. Run: python -m scripts")
    print("   3. Choose mode: ANALYZE | SUGGEST | EXECUTE")

if __name__ == "__main__":
    main()
