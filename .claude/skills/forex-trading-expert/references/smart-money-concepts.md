# Smart Money Concepts (SMC) / ICT Methodology

## Order Blocks (OB)

Order Blocks are areas where institutional orders were placed. They often act as support/resistance.

### Bullish Order Block
- Last bearish candle before a significant bullish move
- Price often returns to test this zone before continuing higher

### Bearish Order Block  
- Last bullish candle before a significant bearish move
- Price often returns to test this zone before continuing lower

### MQL5 Order Block Detection
```mql5
struct OrderBlock {
   double highPrice;
   double lowPrice;
   datetime time;
   bool isBullish;
   bool isValid;
};

OrderBlock FindBullishOB(int lookback = 50, int minMove = 20) {
   OrderBlock ob = {0, 0, 0, true, false};
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   
   for(int i = 2; i < lookback; i++) {
      // Bearish candle followed by strong bullish move
      if(iClose(_Symbol, PERIOD_CURRENT, i) < iOpen(_Symbol, PERIOD_CURRENT, i)) {
         double moveUp = iHigh(_Symbol, PERIOD_CURRENT, i-1) - iLow(_Symbol, PERIOD_CURRENT, i);
         if(moveUp >= minMove * point) {
            ob.highPrice = iHigh(_Symbol, PERIOD_CURRENT, i);
            ob.lowPrice = iLow(_Symbol, PERIOD_CURRENT, i);
            ob.time = iTime(_Symbol, PERIOD_CURRENT, i);
            ob.isBullish = true;
            ob.isValid = true;
            break;
         }
      }
   }
   return ob;
}

OrderBlock FindBearishOB(int lookback = 50, int minMove = 20) {
   OrderBlock ob = {0, 0, 0, false, false};
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   
   for(int i = 2; i < lookback; i++) {
      // Bullish candle followed by strong bearish move
      if(iClose(_Symbol, PERIOD_CURRENT, i) > iOpen(_Symbol, PERIOD_CURRENT, i)) {
         double moveDown = iHigh(_Symbol, PERIOD_CURRENT, i) - iLow(_Symbol, PERIOD_CURRENT, i-1);
         if(moveDown >= minMove * point) {
            ob.highPrice = iHigh(_Symbol, PERIOD_CURRENT, i);
            ob.lowPrice = iLow(_Symbol, PERIOD_CURRENT, i);
            ob.time = iTime(_Symbol, PERIOD_CURRENT, i);
            ob.isBullish = false;
            ob.isValid = true;
            break;
         }
      }
   }
   return ob;
}

bool IsPriceInOB(OrderBlock &ob, double price) {
   return price >= ob.lowPrice && price <= ob.highPrice;
}
```

### Pine Script Order Block
```pinescript
//@version=5
indicator("Order Blocks", overlay=true, max_boxes_count=500)

// Settings
lookback = input.int(50, "Lookback Period")
obLength = input.int(20, "OB Extension Bars")
showBullOB = input.bool(true, "Show Bullish OB")
showBearOB = input.bool(true, "Show Bearish OB")

// Detect swing points
swingHigh = ta.pivothigh(high, 5, 5)
swingLow = ta.pivotlow(low, 5, 5)

// Bullish Order Block - last bearish candle before swing low
bullishOB = close[6] < open[6] and not na(swingLow)
bearishOB = close[6] > open[6] and not na(swingHigh)

// Draw boxes
if bullishOB and showBullOB
    box.new(bar_index[6], high[6], bar_index + obLength, low[6], 
            bgcolor=color.new(color.green, 80), border_color=color.green)

if bearishOB and showBearOB
    box.new(bar_index[6], high[6], bar_index + obLength, low[6], 
            bgcolor=color.new(color.red, 80), border_color=color.red)
```

## Fair Value Gaps (FVG) / Imbalance

FVG is a gap between candle wicks indicating fast price movement. Price tends to return to fill these gaps.

### Bullish FVG
- Low of current candle is higher than high of 2 candles ago
- Gap between high[2] and low[0]

### Bearish FVG
- High of current candle is lower than low of 2 candles ago  
- Gap between low[2] and high[0]

### MQL5 FVG Detection
```mql5
struct FVG {
   double top;
   double bottom;
   datetime time;
   bool isBullish;
   bool isFilled;
};

bool DetectBullishFVG(int bar, FVG &fvg) {
   double high2 = iHigh(_Symbol, PERIOD_CURRENT, bar + 2);
   double low0 = iLow(_Symbol, PERIOD_CURRENT, bar);
   
   if(low0 > high2) {
      fvg.top = low0;
      fvg.bottom = high2;
      fvg.time = iTime(_Symbol, PERIOD_CURRENT, bar + 1);
      fvg.isBullish = true;
      fvg.isFilled = false;
      return true;
   }
   return false;
}

bool DetectBearishFVG(int bar, FVG &fvg) {
   double low2 = iLow(_Symbol, PERIOD_CURRENT, bar + 2);
   double high0 = iHigh(_Symbol, PERIOD_CURRENT, bar);
   
   if(high0 < low2) {
      fvg.top = low2;
      fvg.bottom = high0;
      fvg.time = iTime(_Symbol, PERIOD_CURRENT, bar + 1);
      fvg.isBullish = false;
      fvg.isFilled = false;
      return true;
   }
   return false;
}

bool IsFVGFilled(FVG &fvg) {
   double currentHigh = iHigh(_Symbol, PERIOD_CURRENT, 0);
   double currentLow = iLow(_Symbol, PERIOD_CURRENT, 0);
   
   if(fvg.isBullish && currentLow <= fvg.bottom) return true;
   if(!fvg.isBullish && currentHigh >= fvg.top) return true;
   
   return false;
}
```

### Pine Script FVG
```pinescript
//@version=5
indicator("Fair Value Gaps", overlay=true, max_boxes_count=500)

// Settings
showBullFVG = input.bool(true, "Show Bullish FVG")
showBearFVG = input.bool(true, "Show Bearish FVG")
extendBars = input.int(50, "Extend Bars")

// FVG Detection
bullishFVG = low > high[2]
bearishFVG = high < low[2]

// Draw FVG boxes
if bullishFVG and showBullFVG
    fvgTop = low
    fvgBottom = high[2]
    box.new(bar_index[1], fvgTop, bar_index + extendBars, fvgBottom,
            bgcolor=color.new(color.teal, 80), border_color=color.teal)

if bearishFVG and showBearFVG
    fvgTop = low[2]
    fvgBottom = high
    box.new(bar_index[1], fvgTop, bar_index + extendBars, fvgBottom,
            bgcolor=color.new(color.maroon, 80), border_color=color.maroon)
```

## Liquidity Concepts

### Buy-Side Liquidity (BSL)
- Stop losses above swing highs
- Equal highs (EQH)
- Price often sweeps these levels before reversing

### Sell-Side Liquidity (SSL)
- Stop losses below swing lows
- Equal lows (EQL)
- Price often sweeps these levels before reversing

### Pine Script Liquidity Levels
```pinescript
//@version=5
indicator("Liquidity Levels", overlay=true, max_lines_count=500)

// Swing detection
swingLength = input.int(5, "Swing Length")

swingHigh = ta.pivothigh(high, swingLength, swingLength)
swingLow = ta.pivotlow(low, swingLength, swingLength)

// Draw liquidity levels
if not na(swingHigh)
    line.new(bar_index[swingLength], swingHigh, bar_index + 50, swingHigh, 
             color=color.red, style=line.style_dashed, width=1)
    label.new(bar_index[swingLength], swingHigh, "BSL", 
              style=label.style_label_down, color=color.red, textcolor=color.white, size=size.tiny)

if not na(swingLow)
    line.new(bar_index[swingLength], swingLow, bar_index + 50, swingLow, 
             color=color.green, style=line.style_dashed, width=1)
    label.new(bar_index[swingLength], swingLow, "SSL", 
              style=label.style_label_up, color=color.green, textcolor=color.white, size=size.tiny)
```

## Break of Structure (BOS) & Change of Character (CHoCH)

### BOS (Break of Structure)
- Continuation pattern
- Bullish BOS: Price breaks above previous swing high
- Bearish BOS: Price breaks below previous swing low

### CHoCH (Change of Character)
- Reversal pattern
- Bullish CHoCH: Price breaks above swing high after downtrend
- Bearish CHoCH: Price breaks below swing low after uptrend

### Pine Script BOS/CHoCH
```pinescript
//@version=5
indicator("BOS & CHoCH", overlay=true)

swingLen = input.int(5, "Swing Length")

var float lastSwingHigh = na
var float lastSwingLow = na
var int trend = 0  // 1 = up, -1 = down, 0 = neutral

swingHigh = ta.pivothigh(high, swingLen, swingLen)
swingLow = ta.pivotlow(low, swingLen, swingLen)

// Update swing levels
if not na(swingHigh)
    lastSwingHigh := swingHigh
if not na(swingLow)
    lastSwingLow := swingLow

// Detect BOS and CHoCH
bullishBreak = ta.crossover(close, lastSwingHigh)
bearishBreak = ta.crossunder(close, lastSwingLow)

// Determine if BOS or CHoCH
bullishBOS = bullishBreak and trend == 1
bullishCHoCH = bullishBreak and trend == -1
bearishBOS = bearishBreak and trend == -1
bearishCHoCH = bearishBreak and trend == 1

// Update trend
if bullishBreak
    trend := 1
if bearishBreak
    trend := -1

// Labels
if bullishBOS
    label.new(bar_index, high, "BOS", style=label.style_label_down, color=color.blue, textcolor=color.white)
if bullishCHoCH
    label.new(bar_index, high, "CHoCH", style=label.style_label_down, color=color.lime, textcolor=color.black)
if bearishBOS
    label.new(bar_index, low, "BOS", style=label.style_label_up, color=color.orange, textcolor=color.black)
if bearishCHoCH
    label.new(bar_index, low, "CHoCH", style=label.style_label_up, color=color.red, textcolor=color.white)
```

## Kill Zones (High Probability Trading Times)

### ICT Kill Zones (New York Time)
| Session | Time (ET) | Description |
|---------|-----------|-------------|
| Asian | 20:00-00:00 | Accumulation phase |
| London | 02:00-05:00 | High volatility, trend starts |
| NY AM | 07:00-10:00 | Highest volume, reversals |
| NY PM | 13:30-16:00 | Continuation or reversal |

### Pine Script Kill Zone Filter
```pinescript
//@version=5
indicator("Kill Zones", overlay=true)

// Input times (in exchange timezone)
londonStart = input.int(2, "London Start (hour)")
londonEnd = input.int(5, "London End (hour)")
nyStart = input.int(7, "NY AM Start (hour)")
nyEnd = input.int(10, "NY AM End (hour)")

// Check if in kill zone
inLondonKZ = hour >= londonStart and hour < londonEnd
inNYKZ = hour >= nyStart and hour < nyEnd
inKillZone = inLondonKZ or inNYKZ

// Background color
bgcolor(inLondonKZ ? color.new(color.blue, 90) : na, title="London KZ")
bgcolor(inNYKZ ? color.new(color.orange, 90) : na, title="NY KZ")

// Can be used as filter in strategy
// if longCondition and inKillZone
//     strategy.entry("Long", strategy.long)
```

## Optimal Trade Entry (OTE)

OTE is the 62-79% Fibonacci retracement zone of an impulse move.

### Pine Script OTE Zone
```pinescript
//@version=5
indicator("OTE Zone", overlay=true)

lookback = input.int(20, "Lookback")
oteHigh = input.float(0.79, "OTE High Level")
oteLow = input.float(0.62, "OTE Low Level")

// Find recent swing high and low
highestHigh = ta.highest(high, lookback)
lowestLow = ta.lowest(low, lookback)
range_val = highestHigh - lowestLow

// Calculate OTE zone for bullish setup (retracement in uptrend)
oteTop = highestHigh - range_val * oteLow
oteBottom = highestHigh - range_val * oteHigh

// Draw OTE zone
var box oteBox = na
box.delete(oteBox)
oteBox := box.new(bar_index - lookback, oteTop, bar_index, oteBottom,
                   bgcolor=color.new(color.purple, 80), border_color=color.purple)
```
