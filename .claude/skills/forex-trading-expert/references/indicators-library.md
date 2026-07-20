# Indicators Library

## Custom Indicators - MQL5

### Heiken Ashi Smoothed
```mql5
double HeikenAshiClose(int bar) {
   return (iOpen(_Symbol, PERIOD_CURRENT, bar) + 
           iHigh(_Symbol, PERIOD_CURRENT, bar) + 
           iLow(_Symbol, PERIOD_CURRENT, bar) + 
           iClose(_Symbol, PERIOD_CURRENT, bar)) / 4;
}

double HeikenAshiOpen(int bar, double prevHAOpen) {
   if(bar == iBars(_Symbol, PERIOD_CURRENT) - 1) {
      return (iOpen(_Symbol, PERIOD_CURRENT, bar) + iClose(_Symbol, PERIOD_CURRENT, bar)) / 2;
   }
   return (prevHAOpen + HeikenAshiClose(bar + 1)) / 2;
}

double HeikenAshiHigh(int bar, double haOpen, double haClose) {
   return MathMax(iHigh(_Symbol, PERIOD_CURRENT, bar), MathMax(haOpen, haClose));
}

double HeikenAshiLow(int bar, double haOpen, double haClose) {
   return MathMin(iLow(_Symbol, PERIOD_CURRENT, bar), MathMin(haOpen, haClose));
}
```

### Range Filter
```mql5
double RangeFilter(int period = 100, double multiplier = 2.6) {
   double smoothRange = 0;
   double filter = 0;
   double prevFilter = 0;
   
   for(int i = 0; i < period; i++) {
      double range = iHigh(_Symbol, PERIOD_CURRENT, i) - iLow(_Symbol, PERIOD_CURRENT, i);
      smoothRange += range;
   }
   smoothRange = smoothRange / period * multiplier;
   
   double close0 = iClose(_Symbol, PERIOD_CURRENT, 0);
   
   if(close0 > prevFilter) {
      if(close0 - smoothRange > prevFilter) filter = close0 - smoothRange;
      else filter = prevFilter;
   }
   else {
      if(close0 + smoothRange < prevFilter) filter = close0 + smoothRange;
      else filter = prevFilter;
   }
   
   return filter;
}
```

### Chandelier Exit
```mql5
void ChandelierExit(int period, double multiplier, double &longStop, double &shortStop) {
   double atr = 0;
   int atrHandle = iATR(_Symbol, PERIOD_CURRENT, period);
   double atrBuffer[];
   ArraySetAsSeries(atrBuffer, true);
   CopyBuffer(atrHandle, 0, 0, 1, atrBuffer);
   atr = atrBuffer[0];
   
   double highest = iHigh(_Symbol, PERIOD_CURRENT, iHighest(_Symbol, PERIOD_CURRENT, MODE_HIGH, period, 0));
   double lowest = iLow(_Symbol, PERIOD_CURRENT, iLowest(_Symbol, PERIOD_CURRENT, MODE_LOW, period, 0));
   
   longStop = highest - atr * multiplier;
   shortStop = lowest + atr * multiplier;
   
   IndicatorRelease(atrHandle);
}
```

### Squeeze Momentum
```mql5
struct SqueezeData {
   double momentum;
   bool sqzOn;
   bool sqzOff;
   bool noSqz;
};

SqueezeData SqueezeMomentum(int bbLength = 20, double bbMult = 2.0, int kcLength = 20, double kcMult = 1.5) {
   SqueezeData data;
   
   // Bollinger Bands
   int bbHandle = iBands(_Symbol, PERIOD_CURRENT, bbLength, 0, bbMult, PRICE_CLOSE);
   double bbUpper[], bbLower[];
   ArraySetAsSeries(bbUpper, true);
   ArraySetAsSeries(bbLower, true);
   CopyBuffer(bbHandle, 1, 0, 1, bbUpper);  // Upper band
   CopyBuffer(bbHandle, 2, 0, 1, bbLower);  // Lower band
   
   // Keltner Channel (using ATR)
   int atrHandle = iATR(_Symbol, PERIOD_CURRENT, kcLength);
   double atr[];
   ArraySetAsSeries(atr, true);
   CopyBuffer(atrHandle, 0, 0, 1, atr);
   
   double close0 = iClose(_Symbol, PERIOD_CURRENT, 0);
   double ema = 0;
   int emaHandle = iMA(_Symbol, PERIOD_CURRENT, kcLength, 0, MODE_EMA, PRICE_CLOSE);
   double emaBuffer[];
   ArraySetAsSeries(emaBuffer, true);
   CopyBuffer(emaHandle, 0, 0, 1, emaBuffer);
   ema = emaBuffer[0];
   
   double kcUpper = ema + atr[0] * kcMult;
   double kcLower = ema - atr[0] * kcMult;
   
   // Squeeze conditions
   data.sqzOn = bbLower[0] > kcLower && bbUpper[0] < kcUpper;
   data.sqzOff = bbLower[0] < kcLower && bbUpper[0] > kcUpper;
   data.noSqz = !data.sqzOn && !data.sqzOff;
   
   // Momentum (simplified linear regression)
   double highest = iHigh(_Symbol, PERIOD_CURRENT, iHighest(_Symbol, PERIOD_CURRENT, MODE_HIGH, kcLength, 0));
   double lowest = iLow(_Symbol, PERIOD_CURRENT, iLowest(_Symbol, PERIOD_CURRENT, MODE_LOW, kcLength, 0));
   double midline = (highest + lowest) / 2;
   data.momentum = close0 - (midline + ema) / 2;
   
   IndicatorRelease(bbHandle);
   IndicatorRelease(atrHandle);
   IndicatorRelease(emaHandle);
   
   return data;
}
```

## Custom Indicators - Pine Script

### Heiken Ashi Smoothed
```pinescript
//@version=5
indicator("Heiken Ashi Smoothed", overlay=true)

len = input.int(10, "Smoothing Length")

haClose = (open + high + low + close) / 4
haOpen = float(na)
haOpen := na(haOpen[1]) ? (open + close) / 2 : (nz(haOpen[1]) + nz(haClose[1])) / 2
haHigh = math.max(high, math.max(haOpen, haClose))
haLow = math.min(low, math.min(haOpen, haClose))

// Smooth
smaClose = ta.sma(haClose, len)
smaOpen = ta.sma(haOpen, len)
smaHigh = ta.sma(haHigh, len)
smaLow = ta.sma(haLow, len)

plotcandle(smaOpen, smaHigh, smaLow, smaClose, 
           color=smaClose >= smaOpen ? color.green : color.red,
           wickcolor=smaClose >= smaOpen ? color.green : color.red,
           bordercolor=smaClose >= smaOpen ? color.green : color.red)
```

### Range Filter
```pinescript
//@version=5
indicator("Range Filter", overlay=true)

src = input.source(close, "Source")
period = input.int(100, "Period")
mult = input.float(2.6, "Multiplier")

smoothRange = ta.ema(ta.tr, period) * mult

var float filter = 0.0
var float prevFilter = 0.0

if src > prevFilter
    if src - smoothRange > prevFilter
        filter := src - smoothRange
    else
        filter := prevFilter
else
    if src + smoothRange < prevFilter
        filter := src + smoothRange
    else
        filter := prevFilter

prevFilter := filter

upward = filter > filter[1]
downward = filter < filter[1]

plot(filter, "Range Filter", color=upward ? color.lime : color.red, linewidth=2)

// Signals
longCond = src > filter and src[1] <= filter[1]
shortCond = src < filter and src[1] >= filter[1]

plotshape(longCond, "Long", shape.triangleup, location.belowbar, color.lime, size=size.small)
plotshape(shortCond, "Short", shape.triangledown, location.abovebar, color.red, size=size.small)
```

### Chandelier Exit
```pinescript
//@version=5
indicator("Chandelier Exit", overlay=true)

length = input.int(22, "ATR Period")
mult = input.float(3.0, "ATR Multiplier")
useClose = input.bool(true, "Use Close for Extremes")

atr = ta.atr(length)

highestHigh = ta.highest(useClose ? close : high, length)
lowestLow = ta.lowest(useClose ? close : low, length)

longStop = highestHigh - atr * mult
shortStop = lowestLow + atr * mult

var int dir = 1

dir := close > shortStop[1] ? 1 : close < longStop[1] ? -1 : dir

buySignal = dir == 1 and dir[1] == -1
sellSignal = dir == -1 and dir[1] == 1

plot(dir == 1 ? longStop : na, "Long Stop", color.green, linewidth=2, style=plot.style_linebr)
plot(dir == -1 ? shortStop : na, "Short Stop", color.red, linewidth=2, style=plot.style_linebr)

plotshape(buySignal, "Buy", shape.labelup, location.belowbar, color.green, text="Buy", textcolor=color.white)
plotshape(sellSignal, "Sell", shape.labeldown, location.abovebar, color.red, text="Sell", textcolor=color.white)
```

### Squeeze Momentum Indicator
```pinescript
//@version=5
indicator("Squeeze Momentum", overlay=false)

length = input.int(20, "BB Length")
mult = input.float(2.0, "BB MultFactor")
lengthKC = input.int(20, "KC Length")
multKC = input.float(1.5, "KC MultFactor")
useTrueRange = input.bool(true, "Use TrueRange (KC)")

// Bollinger Bands
basis = ta.sma(close, length)
dev = mult * ta.stdev(close, length)
upperBB = basis + dev
lowerBB = basis - dev

// Keltner Channel
ma = ta.sma(close, lengthKC)
range_1 = useTrueRange ? ta.tr : high - low
rangema = ta.sma(range_1, lengthKC)
upperKC = ma + rangema * multKC
lowerKC = ma - rangema * multKC

// Squeeze
sqzOn = lowerBB > lowerKC and upperBB < upperKC
sqzOff = lowerBB < lowerKC and upperBB > upperKC
noSqz = not sqzOn and not sqzOff

// Momentum
val = ta.linreg(close - math.avg(ta.highest(high, lengthKC), ta.lowest(low, lengthKC)), lengthKC, 0)

// Colors
bcolor = val > 0 ? (val > val[1] ? color.lime : color.green) : (val < val[1] ? color.red : color.maroon)
scolor = noSqz ? color.blue : sqzOn ? color.black : color.gray

plot(val, "Momentum", bcolor, 4, plot.style_columns)
plot(0, "Squeeze", scolor, 2, plot.style_circles)
```

### Hull Moving Average
```pinescript
//@version=5
indicator("Hull MA", overlay=true)

length = input.int(20, "Length")
src = input.source(close, "Source")

hma = ta.wma(2 * ta.wma(src, length / 2) - ta.wma(src, length), math.round(math.sqrt(length)))

plot(hma, "HMA", color=hma > hma[1] ? color.green : color.red, linewidth=2)
```

### VWAP with Standard Deviation Bands
```pinescript
//@version=5
indicator("VWAP Bands", overlay=true)

showBands = input.bool(true, "Show Bands")
mult1 = input.float(1.0, "Band 1 Mult")
mult2 = input.float(2.0, "Band 2 Mult")

vwapValue = ta.vwap(hlc3)

// Calculate standard deviation
sumSrcSrc = ta.cum(hlc3 * hlc3 * volume)
sumSrc = ta.cum(hlc3 * volume)
sumVol = ta.cum(volume)

vwapStdev = math.sqrt(math.max(sumSrcSrc/sumVol - math.pow(sumSrc/sumVol, 2), 0))

upper1 = vwapValue + vwapStdev * mult1
lower1 = vwapValue - vwapStdev * mult1
upper2 = vwapValue + vwapStdev * mult2
lower2 = vwapValue - vwapStdev * mult2

plot(vwapValue, "VWAP", color.orange, 2)
plot(showBands ? upper1 : na, "Upper 1", color.blue)
plot(showBands ? lower1 : na, "Lower 1", color.blue)
plot(showBands ? upper2 : na, "Upper 2", color.purple)
plot(showBands ? lower2 : na, "Lower 2", color.purple)
```

### Volume Profile (Simplified)
```pinescript
//@version=5
indicator("Volume Profile Simple", overlay=true)

length = input.int(100, "Lookback")
rows = input.int(24, "Rows")

var float[] volArray = array.new_float(rows, 0)
var float[] priceArray = array.new_float(rows, 0)

if barstate.islast
    highestH = ta.highest(high, length)
    lowestL = ta.lowest(low, length)
    step = (highestH - lowestL) / rows
    
    // Reset arrays
    for i = 0 to rows - 1
        array.set(volArray, i, 0)
        array.set(priceArray, i, lowestL + step * i)
    
    // Accumulate volume
    for j = 0 to length - 1
        priceLevel = math.floor((close[j] - lowestL) / step)
        priceLevel := math.max(0, math.min(rows - 1, priceLevel))
        array.set(volArray, int(priceLevel), array.get(volArray, int(priceLevel)) + volume[j])
    
    // Find POC (Point of Control)
    maxVol = array.max(volArray)
    pocIndex = array.indexof(volArray, maxVol)
    pocPrice = array.get(priceArray, pocIndex) + step / 2
    
    // Draw POC line
    line.new(bar_index - length, pocPrice, bar_index, pocPrice, color=color.yellow, width=2)
```

### Multi-Timeframe Dashboard
```pinescript
//@version=5
indicator("MTF Dashboard", overlay=true)

// Timeframes to analyze
tf1 = "15"
tf2 = "60"
tf3 = "240"
tf4 = "D"

// Get trend for each timeframe
getTrend(tf) =>
    ema20 = request.security(syminfo.tickerid, tf, ta.ema(close, 20))
    ema50 = request.security(syminfo.tickerid, tf, ta.ema(close, 50))
    ema20 > ema50 ? 1 : -1

trend1 = getTrend(tf1)
trend2 = getTrend(tf2)
trend3 = getTrend(tf3)
trend4 = getTrend(tf4)

// Dashboard table
var table dashboard = table.new(position.top_right, 2, 5, bgcolor=color.black, border_width=1)

if barstate.islast
    table.cell(dashboard, 0, 0, "TF", text_color=color.white)
    table.cell(dashboard, 1, 0, "Trend", text_color=color.white)
    
    table.cell(dashboard, 0, 1, tf1, text_color=color.white)
    table.cell(dashboard, 1, 1, trend1 == 1 ? "▲" : "▼", text_color=trend1 == 1 ? color.green : color.red)
    
    table.cell(dashboard, 0, 2, tf2, text_color=color.white)
    table.cell(dashboard, 1, 2, trend2 == 1 ? "▲" : "▼", text_color=trend2 == 1 ? color.green : color.red)
    
    table.cell(dashboard, 0, 3, tf3, text_color=color.white)
    table.cell(dashboard, 1, 3, trend3 == 1 ? "▲" : "▼", text_color=trend3 == 1 ? color.green : color.red)
    
    table.cell(dashboard, 0, 4, tf4, text_color=color.white)
    table.cell(dashboard, 1, 4, trend4 == 1 ? "▲" : "▼", text_color=trend4 == 1 ? color.green : color.red)
```
