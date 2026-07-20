# Candlestick Patterns Detection

## MQL5 Candlestick Pattern Functions

```mql5
// Helper functions
double Body(int bar) {
   return MathAbs(iClose(_Symbol, PERIOD_CURRENT, bar) - iOpen(_Symbol, PERIOD_CURRENT, bar));
}

double UpperWick(int bar) {
   return iHigh(_Symbol, PERIOD_CURRENT, bar) - MathMax(iOpen(_Symbol, PERIOD_CURRENT, bar), iClose(_Symbol, PERIOD_CURRENT, bar));
}

double LowerWick(int bar) {
   return MathMin(iOpen(_Symbol, PERIOD_CURRENT, bar), iClose(_Symbol, PERIOD_CURRENT, bar)) - iLow(_Symbol, PERIOD_CURRENT, bar);
}

double Range(int bar) {
   return iHigh(_Symbol, PERIOD_CURRENT, bar) - iLow(_Symbol, PERIOD_CURRENT, bar);
}

bool IsBullish(int bar) {
   return iClose(_Symbol, PERIOD_CURRENT, bar) > iOpen(_Symbol, PERIOD_CURRENT, bar);
}

bool IsBearish(int bar) {
   return iClose(_Symbol, PERIOD_CURRENT, bar) < iOpen(_Symbol, PERIOD_CURRENT, bar);
}

double AvgBody(int period = 10) {
   double sum = 0;
   for(int i = 1; i <= period; i++) {
      sum += Body(i);
   }
   return sum / period;
}

// DOJI
bool IsDoji(int bar = 1, double threshold = 0.1) {
   return Body(bar) <= Range(bar) * threshold;
}

// HAMMER (bullish reversal at bottom)
bool IsHammer(int bar = 1) {
   double body = Body(bar);
   double lowerWick = LowerWick(bar);
   double upperWick = UpperWick(bar);
   
   return lowerWick >= body * 2 && 
          upperWick <= body * 0.3 && 
          body > 0;
}

// INVERTED HAMMER (bullish reversal at bottom)
bool IsInvertedHammer(int bar = 1) {
   double body = Body(bar);
   double lowerWick = LowerWick(bar);
   double upperWick = UpperWick(bar);
   
   return upperWick >= body * 2 && 
          lowerWick <= body * 0.3 && 
          body > 0;
}

// HANGING MAN (bearish reversal at top)
bool IsHangingMan(int bar = 1) {
   return IsHammer(bar) && IsBearish(bar);
}

// SHOOTING STAR (bearish reversal at top)
bool IsShootingStar(int bar = 1) {
   double body = Body(bar);
   double lowerWick = LowerWick(bar);
   double upperWick = UpperWick(bar);
   
   return upperWick >= body * 2 && 
          lowerWick <= body * 0.3 && 
          IsBearish(bar);
}

// ENGULFING PATTERNS
bool IsBullishEngulfing(int bar = 1) {
   return IsBearish(bar + 1) && 
          IsBullish(bar) && 
          iOpen(_Symbol, PERIOD_CURRENT, bar) < iClose(_Symbol, PERIOD_CURRENT, bar + 1) &&
          iClose(_Symbol, PERIOD_CURRENT, bar) > iOpen(_Symbol, PERIOD_CURRENT, bar + 1) &&
          Body(bar) > Body(bar + 1);
}

bool IsBearishEngulfing(int bar = 1) {
   return IsBullish(bar + 1) && 
          IsBearish(bar) && 
          iOpen(_Symbol, PERIOD_CURRENT, bar) > iClose(_Symbol, PERIOD_CURRENT, bar + 1) &&
          iClose(_Symbol, PERIOD_CURRENT, bar) < iOpen(_Symbol, PERIOD_CURRENT, bar + 1) &&
          Body(bar) > Body(bar + 1);
}

// MORNING STAR (bullish reversal)
bool IsMorningStar(int bar = 1) {
   bool firstBearish = IsBearish(bar + 2) && Body(bar + 2) > AvgBody();
   bool secondSmall = Body(bar + 1) < Body(bar + 2) * 0.3;
   bool thirdBullish = IsBullish(bar) && Body(bar) > AvgBody();
   bool gapDown = MathMax(iOpen(_Symbol, PERIOD_CURRENT, bar + 1), iClose(_Symbol, PERIOD_CURRENT, bar + 1)) < iClose(_Symbol, PERIOD_CURRENT, bar + 2);
   bool closesAbove = iClose(_Symbol, PERIOD_CURRENT, bar) > (iOpen(_Symbol, PERIOD_CURRENT, bar + 2) + iClose(_Symbol, PERIOD_CURRENT, bar + 2)) / 2;
   
   return firstBearish && secondSmall && thirdBullish && closesAbove;
}

// EVENING STAR (bearish reversal)
bool IsEveningStar(int bar = 1) {
   bool firstBullish = IsBullish(bar + 2) && Body(bar + 2) > AvgBody();
   bool secondSmall = Body(bar + 1) < Body(bar + 2) * 0.3;
   bool thirdBearish = IsBearish(bar) && Body(bar) > AvgBody();
   bool gapUp = MathMin(iOpen(_Symbol, PERIOD_CURRENT, bar + 1), iClose(_Symbol, PERIOD_CURRENT, bar + 1)) > iClose(_Symbol, PERIOD_CURRENT, bar + 2);
   bool closesBelow = iClose(_Symbol, PERIOD_CURRENT, bar) < (iOpen(_Symbol, PERIOD_CURRENT, bar + 2) + iClose(_Symbol, PERIOD_CURRENT, bar + 2)) / 2;
   
   return firstBullish && secondSmall && thirdBearish && closesBelow;
}

// THREE WHITE SOLDIERS (bullish continuation)
bool IsThreeWhiteSoldiers(int bar = 1) {
   bool allBullish = IsBullish(bar) && IsBullish(bar + 1) && IsBullish(bar + 2);
   bool higherCloses = iClose(_Symbol, PERIOD_CURRENT, bar) > iClose(_Symbol, PERIOD_CURRENT, bar + 1) && 
                       iClose(_Symbol, PERIOD_CURRENT, bar + 1) > iClose(_Symbol, PERIOD_CURRENT, bar + 2);
   bool smallWicks = UpperWick(bar) < Body(bar) * 0.3 && 
                     UpperWick(bar + 1) < Body(bar + 1) * 0.3;
   bool openInPrevBody = iOpen(_Symbol, PERIOD_CURRENT, bar) > iOpen(_Symbol, PERIOD_CURRENT, bar + 1) &&
                         iOpen(_Symbol, PERIOD_CURRENT, bar) < iClose(_Symbol, PERIOD_CURRENT, bar + 1);
   
   return allBullish && higherCloses && smallWicks && openInPrevBody;
}

// THREE BLACK CROWS (bearish continuation)
bool IsThreeBlackCrows(int bar = 1) {
   bool allBearish = IsBearish(bar) && IsBearish(bar + 1) && IsBearish(bar + 2);
   bool lowerCloses = iClose(_Symbol, PERIOD_CURRENT, bar) < iClose(_Symbol, PERIOD_CURRENT, bar + 1) && 
                      iClose(_Symbol, PERIOD_CURRENT, bar + 1) < iClose(_Symbol, PERIOD_CURRENT, bar + 2);
   bool smallWicks = LowerWick(bar) < Body(bar) * 0.3 && 
                     LowerWick(bar + 1) < Body(bar + 1) * 0.3;
   bool openInPrevBody = iOpen(_Symbol, PERIOD_CURRENT, bar) < iOpen(_Symbol, PERIOD_CURRENT, bar + 1) &&
                         iOpen(_Symbol, PERIOD_CURRENT, bar) > iClose(_Symbol, PERIOD_CURRENT, bar + 1);
   
   return allBearish && lowerCloses && smallWicks && openInPrevBody;
}

// PIERCING LINE (bullish reversal)
bool IsPiercingLine(int bar = 1) {
   bool prevBearish = IsBearish(bar + 1) && Body(bar + 1) > AvgBody();
   bool currBullish = IsBullish(bar) && Body(bar) > AvgBody();
   bool opensBelowPrevLow = iOpen(_Symbol, PERIOD_CURRENT, bar) < iLow(_Symbol, PERIOD_CURRENT, bar + 1);
   double midpoint = (iOpen(_Symbol, PERIOD_CURRENT, bar + 1) + iClose(_Symbol, PERIOD_CURRENT, bar + 1)) / 2;
   bool closesAboveMid = iClose(_Symbol, PERIOD_CURRENT, bar) > midpoint;
   bool closesBelowOpen = iClose(_Symbol, PERIOD_CURRENT, bar) < iOpen(_Symbol, PERIOD_CURRENT, bar + 1);
   
   return prevBearish && currBullish && opensBelowPrevLow && closesAboveMid && closesBelowOpen;
}

// DARK CLOUD COVER (bearish reversal)
bool IsDarkCloudCover(int bar = 1) {
   bool prevBullish = IsBullish(bar + 1) && Body(bar + 1) > AvgBody();
   bool currBearish = IsBearish(bar) && Body(bar) > AvgBody();
   bool opensAbovePrevHigh = iOpen(_Symbol, PERIOD_CURRENT, bar) > iHigh(_Symbol, PERIOD_CURRENT, bar + 1);
   double midpoint = (iOpen(_Symbol, PERIOD_CURRENT, bar + 1) + iClose(_Symbol, PERIOD_CURRENT, bar + 1)) / 2;
   bool closesBelowMid = iClose(_Symbol, PERIOD_CURRENT, bar) < midpoint;
   bool closesAboveOpen = iClose(_Symbol, PERIOD_CURRENT, bar) > iOpen(_Symbol, PERIOD_CURRENT, bar + 1);
   
   return prevBullish && currBearish && opensAbovePrevHigh && closesBelowMid && closesAboveOpen;
}

// HARAMI (inside bar)
bool IsBullishHarami(int bar = 1) {
   return IsBearish(bar + 1) && 
          IsBullish(bar) && 
          Body(bar + 1) > AvgBody() &&
          iOpen(_Symbol, PERIOD_CURRENT, bar) > iClose(_Symbol, PERIOD_CURRENT, bar + 1) &&
          iClose(_Symbol, PERIOD_CURRENT, bar) < iOpen(_Symbol, PERIOD_CURRENT, bar + 1) &&
          Body(bar) < Body(bar + 1) * 0.5;
}

bool IsBearishHarami(int bar = 1) {
   return IsBullish(bar + 1) && 
          IsBearish(bar) && 
          Body(bar + 1) > AvgBody() &&
          iOpen(_Symbol, PERIOD_CURRENT, bar) < iClose(_Symbol, PERIOD_CURRENT, bar + 1) &&
          iClose(_Symbol, PERIOD_CURRENT, bar) > iOpen(_Symbol, PERIOD_CURRENT, bar + 1) &&
          Body(bar) < Body(bar + 1) * 0.5;
}

// TWEEZER TOPS/BOTTOMS
bool IsTweezerTop(int bar = 1, double tolerance = 2) {
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   return IsBullish(bar + 1) && 
          IsBearish(bar) &&
          MathAbs(iHigh(_Symbol, PERIOD_CURRENT, bar) - iHigh(_Symbol, PERIOD_CURRENT, bar + 1)) <= tolerance * point;
}

bool IsTweezerBottom(int bar = 1, double tolerance = 2) {
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   return IsBearish(bar + 1) && 
          IsBullish(bar) &&
          MathAbs(iLow(_Symbol, PERIOD_CURRENT, bar) - iLow(_Symbol, PERIOD_CURRENT, bar + 1)) <= tolerance * point;
}
```

## Pine Script Candlestick Pattern Functions

```pinescript
//@version=5
indicator("Candlestick Patterns", overlay=true)

// Helper functions
body = math.abs(close - open)
upperWick = high - math.max(open, close)
lowerWick = math.min(open, close) - low
range_hl = high - low
isBullish = close > open
isBearish = close < open
avgBody = ta.sma(body, 10)

// Doji
doji = body <= range_hl * 0.1

// Hammer
hammer = lowerWick >= body * 2 and upperWick <= body * 0.3 and body > 0

// Inverted Hammer
invertedHammer = upperWick >= body * 2 and lowerWick <= body * 0.3 and body > 0

// Shooting Star
shootingStar = upperWick >= body * 2 and lowerWick <= body * 0.3 and isBearish

// Engulfing
bullishEngulfing = isBearish[1] and isBullish and open < close[1] and close > open[1] and body > body[1]
bearishEngulfing = isBullish[1] and isBearish and open > close[1] and close < open[1] and body > body[1]

// Morning Star
morningStar = isBearish[2] and body[2] > avgBody and body[1] < body[2] * 0.3 and isBullish and body > avgBody and close > (open[2] + close[2]) / 2

// Evening Star
eveningStar = isBullish[2] and body[2] > avgBody and body[1] < body[2] * 0.3 and isBearish and body > avgBody and close < (open[2] + close[2]) / 2

// Three White Soldiers
threeWhiteSoldiers = isBullish and isBullish[1] and isBullish[2] and close > close[1] and close[1] > close[2] and upperWick < body * 0.3 and upperWick[1] < body[1] * 0.3

// Three Black Crows
threeBlackCrows = isBearish and isBearish[1] and isBearish[2] and close < close[1] and close[1] < close[2] and lowerWick < body * 0.3 and lowerWick[1] < body[1] * 0.3

// Piercing Line
piercingLine = isBearish[1] and body[1] > avgBody and isBullish and body > avgBody and open < low[1] and close > (open[1] + close[1]) / 2 and close < open[1]

// Dark Cloud Cover
darkCloudCover = isBullish[1] and body[1] > avgBody and isBearish and body > avgBody and open > high[1] and close < (open[1] + close[1]) / 2 and close > open[1]

// Harami
bullishHarami = isBearish[1] and isBullish and body[1] > avgBody and open > close[1] and close < open[1] and body < body[1] * 0.5
bearishHarami = isBullish[1] and isBearish and body[1] > avgBody and open < close[1] and close > open[1] and body < body[1] * 0.5

// Tweezer
tweezerTop = isBullish[1] and isBearish and math.abs(high - high[1]) <= syminfo.mintick * 2
tweezerBottom = isBearish[1] and isBullish and math.abs(low - low[1]) <= syminfo.mintick * 2

// Plotting
plotshape(bullishEngulfing, "Bullish Engulfing", shape.triangleup, location.belowbar, color.green, size=size.small)
plotshape(bearishEngulfing, "Bearish Engulfing", shape.triangledown, location.abovebar, color.red, size=size.small)
plotshape(hammer, "Hammer", shape.circle, location.belowbar, color.blue, size=size.tiny)
plotshape(shootingStar, "Shooting Star", shape.circle, location.abovebar, color.orange, size=size.tiny)
plotshape(morningStar, "Morning Star", shape.diamond, location.belowbar, color.lime, size=size.small)
plotshape(eveningStar, "Evening Star", shape.diamond, location.abovebar, color.maroon, size=size.small)
plotshape(doji, "Doji", shape.cross, location.abovebar, color.gray, size=size.tiny)

// Alerts
alertcondition(bullishEngulfing, "Bullish Engulfing", "Bullish Engulfing pattern on {{ticker}}")
alertcondition(bearishEngulfing, "Bearish Engulfing", "Bearish Engulfing pattern on {{ticker}}")
alertcondition(morningStar, "Morning Star", "Morning Star pattern on {{ticker}}")
alertcondition(eveningStar, "Evening Star", "Evening Star pattern on {{ticker}}")
```
