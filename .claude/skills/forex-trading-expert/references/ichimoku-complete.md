# Ichimoku Kinko Hyo - Complete Reference

## History & Philosophy

Ichimoku Kinko Hyo (一目均衡表) was developed by Japanese journalist Goichi Hosoda before WWII. He worked on perfecting it for over 30 years with numerous students before publishing in 1969. The name translates to "one glance equilibrium chart" - a complete trading system visible at a glance.

## Five Lines of Ichimoku

### 1. Tenkan-Sen (転換線) - Conversion/Turning Line
```
Formula: (Highest High + Lowest Low) / 2 for last 9 periods
```
- Fastest line, represents short-term momentum
- Direction indicates immediate price tendency
- **Never trade against Tenkan direction**
- Russians call it "correction line"

### 2. Kijun-Sen (基準線) - Base/Standard Line
```
Formula: (Highest High + Lowest Low) / 2 for last 26 periods
```
- Slower line, represents medium-term trend
- Acts as dynamic support/resistance
- Often used as trailing stop loss
- Flat Kijun attracts price (equilibrium)

### 3. Chikou Span (遅行スパン) - Lagging Span
```
Formula: Current close plotted 26 periods BACK
```
- Confirms trend direction
- Shows momentum relative to past price
- **Key confirmation tool** - don't trade without it
- Used to find support/resistance levels

### 4. Senkou Span A (先行スパン1) - Leading Span A
```
Formula: (Tenkan-Sen + Kijun-Sen) / 2, plotted 26 periods AHEAD
```
- Faster cloud boundary
- Forms one edge of Kumo

### 5. Senkou Span B (先行スパン2) - Leading Span B
```
Formula: (Highest High + Lowest Low) / 2 for last 52 periods, plotted 26 periods AHEAD
```
- Slower cloud boundary
- **Very important** - flat SSB attracts price strongly
- Represents long-term equilibrium

### Kumo (雲) - The Cloud
- Space between Senkou Span A and Senkou Span B
- **Heart of the strategy**
- Bullish cloud: SSA > SSB (green/light)
- Bearish cloud: SSA < SSB (red/dark)
- Cloud thickness = support/resistance strength
- Future cloud shows anticipated market direction

## Standard Settings

| Setting | Value | Meaning |
|---------|-------|---------|
| Tenkan | 9 | ~1.5 weeks |
| Kijun | 26 | ~1 month |
| Senkou Span B | 52 | ~2 months |
| Displacement | 26 | Forward/back offset |

### Alternative Settings
- **7, 28, 119** - Optimized for H4 (tested by automated systems)
- **8, 34, 144** - Fibonacci-based
- **2, 24, 120** - Hourly (1 day = 24h, 1 week = 120h)
- **24, 60, 120** - Daily/weekly focus

## Signal Classification

### Signal Strength
| Strength | Bullish | Bearish |
|----------|---------|---------|
| **Strong** | Cross/break above cloud | Cross/break below cloud |
| **Neutral** | Cross/break inside cloud | Cross/break inside cloud |
| **Weak** | Cross/break below cloud | Cross/break above cloud |

## The 17 Signals of Hosoda

### Group 1: Line-Based Signals

#### 1. TK Cross (Tenkan-Kijun Cross)
- **Golden Cross**: Tenkan crosses Kijun from below → BUY
- **Dead Cross**: Tenkan crosses Kijun from above → SELL
- Stronger with larger crossing angle
- **Strong**: Above cloud (buy) / Below cloud (sell)
- **Weak**: Below cloud (buy) / Above cloud (sell)
- **Neutral**: Inside cloud → NO TRADE

#### 2. Kumo Breakout
- Price breaks through cloud
- Exit through SSA = strong signal
- Exit through SSB = weak signal
- Requires Chikou confirmation

#### 3. Kumo Retest
- After breakout, price returns to test cloud
- Cloud acts as support (bullish) or resistance (bearish)
- Entry on bounce from cloud

#### 4. Edge-to-Edge (E2E)
- Trade from one cloud edge to opposite edge
- Entry when price enters cloud
- Target: opposite side of cloud
- Requires minimum cloud width

#### 5. Price x Kijun Cross
- Price crossing Kijun line
- Stronger than Tenkan signals
- Often indicates medium-term trend change
- Used for stop-loss placement

#### 6. Kijun Bounce
- Price bounces off Kijun line
- Trend continuation signal
- Entry after confirmed bounce

#### 7. Price x Tenkan Cross
- Price crossing Tenkan line
- Weaker signal, used for:
  - Adding to positions
  - Quick scalp entries

#### 8. Tenkan Bounce
- Price bounces off Tenkan line
- Short-term trend continuation
- Good for adding lots to winning positions

### Group 2: Chikou-Based Signals

#### 9. Chikou x Price
- Chikou crossing historical price
- Above price = bullish confirmation
- Below price = bearish confirmation
- **Critical filter for all trades**

#### 10. Chikou x Kumo
- Chikou crossing the cloud (26 periods back)
- Strong trend confirmation
- Cloud acts as support/resistance for Chikou

#### 11. Chikou x Lines
- Chikou crossing Tenkan/Kijun (26 periods back)
- Additional confirmation layer

#### 12. Kumo Twist
- SSA crosses SSB (cloud color change)
- Signals potential long-term trend reversal
- Best on D1 and higher timeframes
- Add lots to existing positions

### Group 3: Structure Signals

#### 13. SSA/SSB Bounce
- Price bounces from cloud edge
- Trend continuation within trend
- Wick touch + close rejection

#### 14. Flat SSB
- Horizontal SSB for extended period
- Strong equilibrium/magnet zone
- Price tends to return to flat SSB
- Wait for breakout of this level

#### 15. TK ReCross
- Second TK cross in same direction
- Confirms trend resumption after pullback

#### 16. Kijun + Chikou Clean
- Kijun signal with clear Chikou path
- No obstacles in Chikou's way

#### 17. TK Pullback
- Price pulls back to Tenkan after TK cross
- Entry on resumption
- Minimum distance: 1x ATR

## Three Lines Signal (Sanyaku Kouten/Gyakuten)

### Bullish Alignment (Top to Bottom)
1. Tenkan
2. Kijun
3. Senkou Span A (above SSB)

### Bearish Alignment (Top to Bottom)
1. Senkou Span A
2. Kijun
3. Tenkan

## Chikou Span Confirmation Rules

| Trade | Chikou Must Be |
|-------|---------------|
| BUY | Above price from 26 bars ago |
| SELL | Below price from 26 bars ago |

**Critical**: If Chikou is on wrong side, DO NOT TRADE or reduce position size.

## Finding Support/Resistance with Chikou

1. Start with Monthly chart
2. Find Chikou turning points (peaks/troughs)
3. Draw horizontal lines at these levels
4. Repeat on Weekly and Daily
5. Color-code by timeframe importance

## Hosoda's Numbers (Time Cycles)

Key numbers for timing analysis:
- 9, 17, 26, 33, 42, 65, 76, 129, 172, 200+

These represent natural cycle lengths in markets.

## Entry Rules

### Standard Entry Checklist
1. ☐ Price position vs Cloud (above/below)
2. ☐ Tenkan vs Kijun relationship
3. ☐ Chikou confirmation
4. ☐ Cloud color (future direction)
5. ☐ No flat Kijun blocking

### Strong BUY Setup
- Price > Cloud
- Tenkan > Kijun
- Chikou > Price (26 back)
- Cloud is bullish (SSA > SSB)
- Cloud is thick

### Strong SELL Setup
- Price < Cloud
- Tenkan < Kijun
- Chikou < Price (26 back)
- Cloud is bearish (SSA < SSB)
- Cloud is thick

## Exit Strategies

### Method 1: Kijun Trailing Stop
- Move stop to Kijun level
- Exit when price closes beyond Kijun

### Method 2: Opposite Signal
- Exit on TK cross in opposite direction
- Or Chikou crossing price

### Method 3: Cloud Touch
- Partial exit at cloud touch
- Full exit on cloud penetration

### Method 4: Support/Resistance Target
- Pre-identified levels from Chikou analysis

## Wave Analysis (ŚWISTAK Method)

### Fibonacci Extensions for Ichimoku
```
Standard levels: 127.2%, 141.4%, 161.8%, 223.2%, 261.8%, 400%, 423.6%
```

### Targets by Signal Type

| Signal | Typical Target |
|--------|---------------|
| TK Cross | 161.8%, 261.8%, 423.6% |
| Kijun Breakout | 161.8%, 261.8% |
| Kijun Retest | 141.4%, 161.8% |
| Cloud Breakout | 127.2%, 141.4%, 161.8% |
| Cloud Retest | 127.2%, 141.4% |

### Pair-Specific Targets
- **CHF/JPY pairs**: 127.2%, 141.4%
- **EUR/USD**: 141.4%, 161.8%
- **Gold/Silver**: 141.4%, 161.8% (volatile: 261.8%)
- **Indices**: 161.8%
- **Crypto (BTC)**: 161.8%
- **Crypto (ALT)**: 141.4%, 161.8%

### Measurement Rules
1. **On breaking candle**: Measure from swing high/low to break candle
2. **After retest**: Measure from swing to retest candle
3. **"Łokietek" method**: Adjust one arm of Fib to wick for precision

## Filters and Confirmations

### Trend Filters
- Price vs Cloud
- HTF (Higher Timeframe) Cloud alignment
- Kijun slope direction
- TK alignment

### Momentum Filters
- Strong candle close (wick filter)
- Breakout buffer (ATR-based)
- Minimum body size

### Structure Filters
- Cloud thickness (min ATR)
- Flat Kijun blocking
- Range detection (avoid consolidation)

### Distance Filters
- Max distance from Kijun (overextended)
- Max distance from Cloud

## Common Mistakes

1. Trading inside flat cloud
2. Ignoring Chikou confirmation
3. Taking TK crosses against cloud
4. Trading in choppy/sideways markets
5. Not testing settings on historical data
6. Using too many filters

## Best Practices

1. **Timeframe**: H4 and D1 are most reliable
2. **Pairs**: Works best on JPY pairs (original design)
3. **Trend markets**: Ichimoku excels in trends, avoid ranging
4. **Confirmation**: Always use at least 3 elements
5. **Patience**: Wait for clean setups

## Trading Sessions (Volatility Windows)

| Session | Time (UTC) | Best Pairs |
|---------|------------|------------|
| Tokyo | 00:00-09:00 | JPY pairs |
| London | 08:00-17:00 | EUR, GBP |
| NY | 13:00-22:00 | USD pairs |
| **London/NY Overlap** | 13:00-17:00 | Highest volatility |

## MQL5 Ichimoku Implementation

```mql5
// Create Ichimoku indicator handle
int ichimokuHandle = iIchimoku(_Symbol, PERIOD_CURRENT, 9, 26, 52);

// Buffers
double tenkan[], kijun[], ssa[], ssb[], chikou[];
ArraySetAsSeries(tenkan, true);
ArraySetAsSeries(kijun, true);
ArraySetAsSeries(ssa, true);
ArraySetAsSeries(ssb, true);
ArraySetAsSeries(chikou, true);

// Copy data
CopyBuffer(ichimokuHandle, 0, 0, 100, tenkan);   // Tenkan-sen
CopyBuffer(ichimokuHandle, 1, 0, 100, kijun);    // Kijun-sen
CopyBuffer(ichimokuHandle, 2, 0, 100, ssa);      // Senkou Span A
CopyBuffer(ichimokuHandle, 3, 0, 100, ssb);      // Senkou Span B
CopyBuffer(ichimokuHandle, 4, 0, 100, chikou);   // Chikou Span

// Check signals
bool bullishTKCross = tenkan[1] > kijun[1] && tenkan[2] <= kijun[2];
bool bearishTKCross = tenkan[1] < kijun[1] && tenkan[2] >= kijun[2];
bool priceAboveCloud = close[0] > MathMax(ssa[0], ssb[0]);
bool priceBelowCloud = close[0] < MathMin(ssa[0], ssb[0]);
bool bullishCloud = ssa[0] > ssb[0];
bool bearishCloud = ssa[0] < ssb[0];

// Chikou confirmation (compare to price 26 bars ago)
bool chikouBullish = close[0] > close[26];
bool chikouBearish = close[0] < close[26];

// Strong buy signal
bool strongBuy = bullishTKCross && priceAboveCloud && bullishCloud && chikouBullish;
```

## Pine Script Ichimoku Implementation

```pinescript
//@version=5
indicator("Ichimoku Kinko Hyo", overlay=true)

// Settings
tenkanPeriod = input.int(9, "Tenkan Period")
kijunPeriod = input.int(26, "Kijun Period")
senkouBPeriod = input.int(52, "Senkou B Period")
displacement = input.int(26, "Displacement")

// Calculations
donchian(len) => math.avg(ta.lowest(len), ta.highest(len))

tenkan = donchian(tenkanPeriod)
kijun = donchian(kijunPeriod)
ssa = math.avg(tenkan, kijun)
ssb = donchian(senkouBPeriod)
chikou = close

// Plotting
plot(tenkan, "Tenkan", color.red, 1)
plot(kijun, "Kijun", color.blue, 2)
plot(chikou, "Chikou", color.green, 1, offset=-displacement)

ssaPlot = plot(ssa, "SSA", color.green, 1, offset=displacement)
ssbPlot = plot(ssb, "SSB", color.red, 1, offset=displacement)
fill(ssaPlot, ssbPlot, color=ssa > ssb ? color.new(color.green, 80) : color.new(color.red, 80))

// Signals
tkCrossBull = ta.crossover(tenkan, kijun)
tkCrossBear = ta.crossunder(tenkan, kijun)

priceAboveCloud = close > math.max(ssa[displacement], ssb[displacement])
priceBelowCloud = close < math.min(ssa[displacement], ssb[displacement])

chikouAbovePrice = close > close[displacement]
chikouBelowPrice = close < close[displacement]

// Strong signals
strongBuy = tkCrossBull and priceAboveCloud and ssa > ssb and chikouAbovePrice
strongSell = tkCrossBear and priceBelowCloud and ssa < ssb and chikouBelowPrice

plotshape(strongBuy, "Strong Buy", shape.triangleup, location.belowbar, color.lime, size=size.normal)
plotshape(strongSell, "Strong Sell", shape.triangledown, location.abovebar, color.red, size=size.normal)

// Alerts
alertcondition(strongBuy, "Strong Buy Signal", "Ichimoku Strong Buy on {{ticker}}")
alertcondition(strongSell, "Strong Sell Signal", "Ichimoku Strong Sell on {{ticker}}")
```

## Complete Ichimoku EA Template (MQL5)

```mql5
#property copyright "Ichimoku EA"
#property version   "1.00"

#include <Trade\Trade.mqh>

input group "=== Ichimoku Settings ==="
input int      InpTenkan       = 9;
input int      InpKijun        = 26;
input int      InpSenkouB      = 52;

input group "=== Trading Settings ==="
input double   InpLotSize      = 0.01;
input int      InpMagic        = 12345;
input bool     InpRequireChikou = true;

CTrade trade;
int ichimokuHandle;

double tenkan[], kijun[], ssa[], ssb[];

int OnInit() {
   trade.SetExpertMagicNumber(InpMagic);
   
   ichimokuHandle = iIchimoku(_Symbol, PERIOD_CURRENT, InpTenkan, InpKijun, InpSenkouB);
   if(ichimokuHandle == INVALID_HANDLE) return(INIT_FAILED);
   
   ArraySetAsSeries(tenkan, true);
   ArraySetAsSeries(kijun, true);
   ArraySetAsSeries(ssa, true);
   ArraySetAsSeries(ssb, true);
   
   return(INIT_SUCCEEDED);
}

void OnTick() {
   if(!IsNewBar()) return;
   if(!UpdateBuffers()) return;
   
   // Get current values
   double close0 = iClose(_Symbol, PERIOD_CURRENT, 0);
   double close26 = iClose(_Symbol, PERIOD_CURRENT, 26);
   
   // Cloud values (current, not displaced)
   double cloudTop = MathMax(ssa[0], ssb[0]);
   double cloudBottom = MathMin(ssa[0], ssb[0]);
   
   // Signals
   bool tkCrossBull = tenkan[1] > kijun[1] && tenkan[2] <= kijun[2];
   bool tkCrossBear = tenkan[1] < kijun[1] && tenkan[2] >= kijun[2];
   
   bool priceAboveCloud = close0 > cloudTop;
   bool priceBelowCloud = close0 < cloudBottom;
   
   bool bullishCloud = ssa[0] > ssb[0];
   bool bearishCloud = ssa[0] < ssb[0];
   
   // Chikou confirmation
   bool chikouBull = !InpRequireChikou || (close0 > close26);
   bool chikouBear = !InpRequireChikou || (close0 < close26);
   
   // Entry logic
   if(PositionsTotal() == 0) {
      // Strong BUY
      if(tkCrossBull && priceAboveCloud && bullishCloud && chikouBull) {
         double sl = kijun[0];
         double tp = close0 + (close0 - sl) * 2; // RR 1:2
         trade.Buy(InpLotSize, _Symbol, 0, sl, tp, "Ichimoku Buy");
      }
      
      // Strong SELL
      if(tkCrossBear && priceBelowCloud && bearishCloud && chikouBear) {
         double sl = kijun[0];
         double tp = close0 - (sl - close0) * 2; // RR 1:2
         trade.Sell(InpLotSize, _Symbol, 0, sl, tp, "Ichimoku Sell");
      }
   }
}

bool UpdateBuffers() {
   if(CopyBuffer(ichimokuHandle, 0, 0, 5, tenkan) < 5) return false;
   if(CopyBuffer(ichimokuHandle, 1, 0, 5, kijun) < 5) return false;
   if(CopyBuffer(ichimokuHandle, 2, 0, 5, ssa) < 5) return false;
   if(CopyBuffer(ichimokuHandle, 3, 0, 5, ssb) < 5) return false;
   return true;
}

bool IsNewBar() {
   static datetime lastBar = 0;
   datetime currentBar = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(lastBar != currentBar) {
      lastBar = currentBar;
      return true;
   }
   return false;
}
```
