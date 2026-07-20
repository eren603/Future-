# MQL5 Complete Reference

## Trade Operations (CTrade class)

```mql5
#include <Trade\Trade.mqh>
CTrade trade;

// Setup
trade.SetExpertMagicNumber(123456);
trade.SetDeviationInPoints(10);
trade.SetTypeFilling(ORDER_FILLING_IOC);     // or ORDER_FILLING_FOK, ORDER_FILLING_RETURN
trade.SetMarginMode();

// Market Orders
trade.Buy(volume, symbol, price, sl, tp, comment);
trade.Sell(volume, symbol, price, sl, tp, comment);

// Pending Orders
trade.BuyLimit(volume, price, symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
trade.SellLimit(volume, price, symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
trade.BuyStop(volume, price, symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
trade.SellStop(volume, price, symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
trade.BuyStopLimit(volume, price, priceStopLimit, symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
trade.SellStopLimit(volume, price, priceStopLimit, symbol, sl, tp, ORDER_TIME_GTC, 0, comment);

// Position Management
trade.PositionClose(symbol);               // Close by symbol
trade.PositionClose(ticket);               // Close by ticket
trade.PositionClosePartial(ticket, volume);
trade.PositionModify(ticket, sl, tp);

// Order Management  
trade.OrderDelete(ticket);
trade.OrderModify(ticket, price, sl, tp, ORDER_TIME_GTC, 0, priceStopLimit);

// Results
trade.ResultRetcode();     // Return code
trade.ResultDeal();        // Deal ticket
trade.ResultOrder();       // Order ticket
trade.ResultVolume();      // Volume
trade.ResultPrice();       // Price
trade.ResultComment();     // Comment
```

## Position Info (CPositionInfo class)

```mql5
#include <Trade\PositionInfo.mqh>
CPositionInfo posInfo;

// Selection
posInfo.Select(symbol);
posInfo.SelectByIndex(index);
posInfo.SelectByTicket(ticket);

// Properties
posInfo.Symbol();
posInfo.Magic();
posInfo.Ticket();
posInfo.Time();
posInfo.TimeUpdate();
posInfo.PositionType();      // POSITION_TYPE_BUY or POSITION_TYPE_SELL
posInfo.Volume();
posInfo.PriceOpen();
posInfo.PriceCurrent();
posInfo.StopLoss();
posInfo.TakeProfit();
posInfo.Swap();
posInfo.Profit();
posInfo.Commission();
posInfo.Comment();
posInfo.Identifier();

// Helper
posInfo.TypeDescription();   // "buy" or "sell"
```

## Symbol Info (CSymbolInfo class)

```mql5
#include <Trade\SymbolInfo.mqh>
CSymbolInfo symbolInfo;

symbolInfo.Name(_Symbol);
symbolInfo.RefreshRates();

// Prices
symbolInfo.Ask();
symbolInfo.Bid();
symbolInfo.Last();

// Symbol properties
symbolInfo.Point();
symbolInfo.Digits();
symbolInfo.Spread();
symbolInfo.SpreadFloat();
symbolInfo.TickValue();
symbolInfo.TickSize();
symbolInfo.ContractSize();
symbolInfo.LotsMin();
symbolInfo.LotsMax();
symbolInfo.LotsStep();
symbolInfo.VolumeMin();
symbolInfo.VolumeMax();
symbolInfo.VolumeStep();
symbolInfo.StopsLevel();     // Minimum SL/TP distance
symbolInfo.FreezeLevel();    // Freeze distance

// Session
symbolInfo.SessionOpen();
symbolInfo.SessionClose();

// Trading
symbolInfo.TradeMode();      // SYMBOL_TRADE_MODE_FULL, etc.
symbolInfo.IsSynced();
```

## Technical Indicators

### Creating Indicator Handles
```mql5
// Moving Averages
int handleMA = iMA(symbol, timeframe, period, shift, method, applied_price);
// method: MODE_SMA, MODE_EMA, MODE_SMMA, MODE_LWMA
// applied_price: PRICE_CLOSE, PRICE_OPEN, PRICE_HIGH, PRICE_LOW, PRICE_MEDIAN, PRICE_TYPICAL, PRICE_WEIGHTED

int handleRSI = iRSI(symbol, timeframe, period, applied_price);

int handleMACD = iMACD(symbol, timeframe, fast_ema, slow_ema, signal, applied_price);

int handleBands = iBands(symbol, timeframe, period, shift, deviation, applied_price);

int handleATR = iATR(symbol, timeframe, period);

int handleStoch = iStochastic(symbol, timeframe, k_period, d_period, slowing, method, price_field);

int handleADX = iADX(symbol, timeframe, period);

int handleCCI = iCCI(symbol, timeframe, period, applied_price);

int handleIchimoku = iIchimoku(symbol, timeframe, tenkan_sen, kijun_sen, senkou_span_b);

int handleSAR = iSAR(symbol, timeframe, step, maximum);

int handleAO = iAO(symbol, timeframe);

int handleAC = iAC(symbol, timeframe);

int handleVolumes = iVolumes(symbol, timeframe, applied_volume);

int handleOBV = iOBV(symbol, timeframe, applied_volume);

int handleMFI = iMFI(symbol, timeframe, period, applied_volume);

int handleFractals = iFractals(symbol, timeframe);

int handleAlligator = iAlligator(symbol, timeframe, jaw_period, jaw_shift, teeth_period, teeth_shift, lips_period, lips_shift, method, applied_price);
```

### Reading Indicator Values
```mql5
double buffer[];
ArraySetAsSeries(buffer, true);

// Copy indicator buffer data
int copied = CopyBuffer(handle, buffer_index, start_pos, count, buffer);

// Example: Get last 3 MA values
CopyBuffer(handleMA, 0, 0, 3, buffer);
double currentMA = buffer[0];
double previousMA = buffer[1];
double twoBarsAgo = buffer[2];

// MACD has 3 buffers: 0=main, 1=signal
double macdMain[], macdSignal[];
CopyBuffer(handleMACD, 0, 0, 3, macdMain);    // Main line
CopyBuffer(handleMACD, 1, 0, 3, macdSignal);  // Signal line

// Bollinger Bands: 0=middle, 1=upper, 2=lower
double bbMiddle[], bbUpper[], bbLower[];
CopyBuffer(handleBands, 0, 0, 3, bbMiddle);
CopyBuffer(handleBands, 1, 0, 3, bbUpper);
CopyBuffer(handleBands, 2, 0, 3, bbLower);

// Stochastic: 0=main, 1=signal
double stochMain[], stochSignal[];
CopyBuffer(handleStoch, 0, 0, 3, stochMain);
CopyBuffer(handleStoch, 1, 0, 3, stochSignal);
```

## Time Functions

```mql5
datetime TimeCurrent();              // Server time
datetime TimeLocal();                // Local time
datetime TimeGMT();                  // GMT time
int      TimeGMTOffset();            // Offset from GMT

// Time components
MqlDateTime dt;
TimeToStruct(TimeCurrent(), dt);
dt.year;
dt.mon;
dt.day;
dt.day_of_week;   // 0=Sunday
dt.day_of_year;
dt.hour;
dt.min;
dt.sec;

// Bar time
datetime iTime(symbol, timeframe, bar_index);

// Time conversion
datetime StringToTime("2024.01.01 00:00");
string   TimeToString(time, TIME_DATE|TIME_MINUTES|TIME_SECONDS);
```

## Price Data Functions

```mql5
// Copy price data
double close[];
ArraySetAsSeries(close, true);
CopyClose(symbol, timeframe, start_pos, count, close);

CopyOpen(symbol, timeframe, start_pos, count, open);
CopyHigh(symbol, timeframe, start_pos, count, high);
CopyLow(symbol, timeframe, start_pos, count, low);
CopyTime(symbol, timeframe, start_pos, count, time);
CopyTickVolume(symbol, timeframe, start_pos, count, volume);
CopyRealVolume(symbol, timeframe, start_pos, count, real_volume);
CopySpread(symbol, timeframe, start_pos, count, spread);

// MqlRates structure
MqlRates rates[];
ArraySetAsSeries(rates, true);
CopyRates(symbol, timeframe, start_pos, count, rates);
// rates[0].open, rates[0].high, rates[0].low, rates[0].close, rates[0].time, rates[0].tick_volume
```

## Timeframes

```mql5
PERIOD_M1     // 1 minute
PERIOD_M2     // 2 minutes
PERIOD_M3     // 3 minutes
PERIOD_M4     // 4 minutes
PERIOD_M5     // 5 minutes
PERIOD_M6     // 6 minutes
PERIOD_M10    // 10 minutes
PERIOD_M12    // 12 minutes
PERIOD_M15    // 15 minutes
PERIOD_M20    // 20 minutes
PERIOD_M30    // 30 minutes
PERIOD_H1     // 1 hour
PERIOD_H2     // 2 hours
PERIOD_H3     // 3 hours
PERIOD_H4     // 4 hours
PERIOD_H6     // 6 hours
PERIOD_H8     // 8 hours
PERIOD_H12    // 12 hours
PERIOD_D1     // 1 day
PERIOD_W1     // 1 week
PERIOD_MN1    // 1 month
PERIOD_CURRENT // Current chart timeframe
```

## Account Information

```mql5
AccountInfoString(ACCOUNT_COMPANY);
AccountInfoString(ACCOUNT_NAME);
AccountInfoString(ACCOUNT_SERVER);
AccountInfoString(ACCOUNT_CURRENCY);

AccountInfoInteger(ACCOUNT_LOGIN);
AccountInfoInteger(ACCOUNT_LEVERAGE);
AccountInfoInteger(ACCOUNT_TRADE_MODE);      // ACCOUNT_TRADE_MODE_DEMO, ACCOUNT_TRADE_MODE_REAL
AccountInfoInteger(ACCOUNT_TRADE_ALLOWED);
AccountInfoInteger(ACCOUNT_TRADE_EXPERT);

AccountInfoDouble(ACCOUNT_BALANCE);
AccountInfoDouble(ACCOUNT_EQUITY);
AccountInfoDouble(ACCOUNT_MARGIN);
AccountInfoDouble(ACCOUNT_MARGIN_FREE);
AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
AccountInfoDouble(ACCOUNT_PROFIT);
```

## Order Types

```mql5
ORDER_TYPE_BUY              // Market buy
ORDER_TYPE_SELL             // Market sell
ORDER_TYPE_BUY_LIMIT        // Buy limit
ORDER_TYPE_SELL_LIMIT       // Sell limit
ORDER_TYPE_BUY_STOP         // Buy stop
ORDER_TYPE_SELL_STOP        // Sell stop
ORDER_TYPE_BUY_STOP_LIMIT   // Buy stop limit
ORDER_TYPE_SELL_STOP_LIMIT  // Sell stop limit
ORDER_TYPE_CLOSE_BY         // Close by opposite position
```

## Common Patterns

### New Bar Detection
```mql5
bool IsNewBar(ENUM_TIMEFRAMES timeframe = PERIOD_CURRENT) {
   static datetime lastBar = 0;
   datetime currentBar = iTime(_Symbol, timeframe, 0);
   if(lastBar != currentBar) {
      lastBar = currentBar;
      return true;
   }
   return false;
}
```

### Normalize Volume
```mql5
double NormalizeVolume(string symbol, double volume) {
   double minVol = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxVol = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double stepVol = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   
   volume = MathMax(minVol, volume);
   volume = MathMin(maxVol, volume);
   volume = MathFloor(volume / stepVol) * stepVol;
   
   return NormalizeDouble(volume, 2);
}
```

### Calculate Lot Size by Risk
```mql5
double CalculateLotSize(string symbol, double riskPercent, double slPoints) {
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * riskPercent / 100.0;
   
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   
   double slValue = slPoints * point;
   double lotSize = riskAmount / (slValue / tickSize * tickValue);
   
   return NormalizeVolume(symbol, lotSize);
}
```

### Trailing Stop
```mql5
void TrailingStop(int trailingPoints, int minimumProfit) {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(!positionInfo.SelectByIndex(i)) continue;
      if(positionInfo.Symbol() != _Symbol) continue;
      if(positionInfo.Magic() != InpMagicNumber) continue;
      
      double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      double currentPrice = positionInfo.PriceCurrent();
      double openPrice = positionInfo.PriceOpen();
      double currentSL = positionInfo.StopLoss();
      double newSL;
      
      if(positionInfo.PositionType() == POSITION_TYPE_BUY) {
         if(currentPrice - openPrice > minimumProfit * point) {
            newSL = currentPrice - trailingPoints * point;
            if(newSL > currentSL) {
               trade.PositionModify(positionInfo.Ticket(), newSL, positionInfo.TakeProfit());
            }
         }
      }
      else if(positionInfo.PositionType() == POSITION_TYPE_SELL) {
         if(openPrice - currentPrice > minimumProfit * point) {
            newSL = currentPrice + trailingPoints * point;
            if(newSL < currentSL || currentSL == 0) {
               trade.PositionModify(positionInfo.Ticket(), newSL, positionInfo.TakeProfit());
            }
         }
      }
   }
}
```

### Move to Breakeven
```mql5
void MoveToBreakeven(int triggerPoints, int lockPoints) {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(!positionInfo.SelectByIndex(i)) continue;
      if(positionInfo.Symbol() != _Symbol) continue;
      if(positionInfo.Magic() != InpMagicNumber) continue;
      
      double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      double openPrice = positionInfo.PriceOpen();
      double currentPrice = positionInfo.PriceCurrent();
      double currentSL = positionInfo.StopLoss();
      
      if(positionInfo.PositionType() == POSITION_TYPE_BUY) {
         double newSL = openPrice + lockPoints * point;
         if(currentPrice >= openPrice + triggerPoints * point && currentSL < newSL) {
            trade.PositionModify(positionInfo.Ticket(), newSL, positionInfo.TakeProfit());
         }
      }
      else if(positionInfo.PositionType() == POSITION_TYPE_SELL) {
         double newSL = openPrice - lockPoints * point;
         if(currentPrice <= openPrice - triggerPoints * point && (currentSL > newSL || currentSL == 0)) {
            trade.PositionModify(positionInfo.Ticket(), newSL, positionInfo.TakeProfit());
         }
      }
   }
}
```
