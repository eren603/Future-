---
name: forex-trading-expert
description: >-
  Trading expert for Forex/CFD, indices (DAX, NASDAQ, S&P500), MQL5, Pine Script v5, 
  MT5 Python API. Use for: trading strategies, technical analysis, risk management, 
  Expert Advisors, custom indicators, backtesting, copy trading, prop trading rules,
  Smart Money Concepts, ICT, Ichimoku Kinko Hyo, ŚWISTAK Fibonacci.
---

# Forex Trading Expert

Trading strategies, bot development, and market analysis.

## Markets

**Forex**: EUR/USD, GBP/USD, USD/JPY, USD/CHF, minors, exotics
**Indices**: DAX40, NASDAQ100, S&P500, US30, US100, Dow Jones
**Commodities**: XAUUSD, XAGUSD, WTI, Brent
**Crypto CFDs**: BTC/USD, ETH/USD

## Sessions (UTC)

| Session | Hours | Best Pairs |
|---------|-------|------------|
| Sydney | 22:00-07:00 | AUD, NZD |
| Tokyo | 00:00-09:00 | JPY |
| London | 08:00-17:00 | EUR, GBP |
| New York | 13:00-22:00 | USD |
| **Overlap** | 13:00-17:00 | Highest volatility |

## Risk Management

```
Position Size = (Account × Risk%) / (Entry - SL) / Point
```

- Max risk/trade: 1-2%
- Min R:R ratio: 1:2 (prefer 1:3)
- Max daily drawdown: 5%
- Max positions: 3-5
- Always use stop-loss

**Prop Firms**: Daily loss 4-5%, max DD 8-10%, no news trading.

## Ichimoku Quick Ref

| Line | Formula | Purpose |
|------|---------|---------|
| Tenkan | (HH+LL)/2 of 9 | Momentum |
| Kijun | (HH+LL)/2 of 26 | Trend, S/R |
| SSA | (T+K)/2 +26 fwd | Cloud edge |
| SSB | (HH+LL)/2 of 52 +26 fwd | Cloud edge |
| Chikou | Close -26 back | Confirmation |

**Signals**: TK Cross, Kumo Breakout, Kumo Twist, Chikou confirmation.
**Strength**: Above cloud = strong buy, below = strong sell.

## Bot Development Workflow

1. Define strategy → precise entry/exit rules
2. Choose platform → MT5 (MQL5) or TradingView (Pine)
3. Code indicator → visual testing first
4. Add order management → EA/Strategy
5. Implement risk → position sizing, SL/TP
6. Backtest → Strategy Tester / TradingView
7. Optimize → walk-forward
8. Forward test → demo 1-3 months
9. Deploy live → start 0.5% risk
10. Monitor & iterate

## Reference Files

- `references/mql5-complete.md` - Full MQL5 API, EA templates, CTrade class
- `references/pine-script-complete.md` - Pine v5 reference, strategy templates
- `references/ichimoku-complete.md` - 17 signals, wave analysis, code
- `references/smart-money-concepts.md` - ICT, order blocks, FVG, liquidity
- `references/indicators-library.md` - Common indicator implementations
- `references/candlestick-patterns.md` - Pattern detection code
