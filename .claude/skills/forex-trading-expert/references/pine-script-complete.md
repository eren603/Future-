# Pine Script v5 Complete Reference

## Basic Structure

```pinescript
//@version=5
indicator("Name", overlay=true/false)  // or strategy()

// Inputs
// Calculations
// Plotting
// Alerts
```

## Input Types

```pinescript
// Boolean
showSignals = input.bool(true, "Show Signals", group="Display")

// Integer
period = input.int(14, "Period", minval=1, maxval=500, step=1, group="Settings")

// Float
multiplier = input.float(2.0, "Multiplier", minval=0.1, maxval=10.0, step=0.1, group="Settings")

// String
maType = input.string("EMA", "MA Type", options=["SMA", "EMA", "WMA", "VWMA"], group="Settings")

// Source
source = input.source(close, "Source", group="Settings")

// Color
bullColor = input.color(color.green, "Bull Color", group="Colors")

// Timeframe
htf = input.timeframe("D", "Higher Timeframe", group="MTF")

// Time
startTime = input.time(timestamp("01 Jan 2020"), "Start Date", group="Backtest")

// Session
tradingSession = input.session("0800-1600", "Trading Session", group="Time")

// Symbol
symbol = input.symbol("BTCUSD", "Symbol", group="Settings")
```

## Technical Analysis Functions

### Moving Averages
```pinescript
ta.sma(source, length)           // Simple MA
ta.ema(source, length)           // Exponential MA
ta.wma(source, length)           // Weighted MA
ta.vwma(source, length)          // Volume Weighted MA
ta.rma(source, length)           // Running/Wilder MA
ta.swma(source)                  // Symmetric Weighted MA
ta.hma(source, length)           // Hull MA
ta.alma(source, length, offset, sigma)  // Arnaud Legoux MA
ta.dema(source, length)          // Double EMA (custom)
ta.tema(source, length)          // Triple EMA (custom)
```

### Oscillators
```pinescript
ta.rsi(source, length)           // RSI
ta.stoch(close, high, low, length)  // Stochastic %K
ta.cci(source, length)           // CCI
ta.mfi(hlc3, volume, length)     // Money Flow Index
ta.cmo(source, length)           // Chande Momentum Oscillator
ta.roc(source, length)           // Rate of Change
ta.mom(source, length)           // Momentum
```

### MACD
```pinescript
[macdLine, signalLine, histogram] = ta.macd(source, fastLength, slowLength, signalLength)
```

### Bollinger Bands
```pinescript
[middle, upper, lower] = ta.bb(source, length, mult)
basis = ta.sma(close, 20)
dev = ta.stdev(close, 20) * 2
upper = basis + dev
lower = basis - dev
```

### Supertrend
```pinescript
[supertrend, direction] = ta.supertrend(factor, atrPeriod)
// direction: 1 = bearish, -1 = bullish
```

### ATR & Volatility
```pinescript
ta.atr(length)                   // Average True Range
ta.tr                            // True Range (current bar)
ta.tr(true)                      // True Range with gaps
ta.stdev(source, length)         // Standard Deviation
ta.variance(source, length)      // Variance
```

### DMI / ADX
```pinescript
[diPlus, diMinus, adx] = ta.dmi(diLength, adxSmoothing)
```

### Ichimoku
```pinescript
donchian(len) => math.avg(ta.lowest(len), ta.highest(len))
tenkanSen = donchian(9)
kijunSen = donchian(26)
senkouSpanA = math.avg(tenkanSen, kijunSen)
senkouSpanB = donchian(52)
chikouSpan = close
```

### Pivot Points
```pinescript
ta.pivothigh(source, leftbars, rightbars)
ta.pivotlow(source, leftbars, rightbars)
```

### Crossovers
```pinescript
ta.crossover(source1, source2)   // source1 crosses above source2
ta.crossunder(source1, source2)  // source1 crosses below source2
ta.cross(source1, source2)       // any cross
```

### Highest/Lowest
```pinescript
ta.highest(source, length)       // Highest value
ta.lowest(source, length)        // Lowest value
ta.highestbars(source, length)   // Bars since highest
ta.lowestbars(source, length)    // Bars since lowest
```

### Change Functions
```pinescript
ta.change(source)                // source - source[1]
ta.change(source, length)        // source - source[length]
ta.rising(source, length)        // source > source[1] for last length bars
ta.falling(source, length)       // source < source[1] for last length bars
```

### Cumulative
```pinescript
ta.cum(source)                   // Cumulative sum
ta.barssince(condition)          // Bars since condition was true
```

### Volume
```pinescript
ta.vwap(source)                  // VWAP
ta.obv                           // On Balance Volume
```

## Plotting

### Basic Plots
```pinescript
plot(series, title, color, linewidth, style, trackprice, histbase, offset, join, editable, show_last, display)

// Styles
plot.style_line
plot.style_linebr        // Line with breaks
plot.style_stepline      // Step line
plot.style_steplinebr    // Step line with breaks
plot.style_histogram
plot.style_cross
plot.style_circles
plot.style_columns
plot.style_area
plot.style_areabr
```

### Fill Between Plots
```pinescript
p1 = plot(upper, color=color.green)
p2 = plot(lower, color=color.red)
fill(p1, p2, color=color.new(color.gray, 80))
```

### Plot Shapes
```pinescript
plotshape(condition, title, style, location, color, offset, text, textcolor, editable, size, show_last, display)

// Styles
shape.xcross, shape.cross, shape.triangleup, shape.triangledown
shape.flag, shape.circle, shape.arrowup, shape.arrowdown
shape.labelup, shape.labeldown, shape.square, shape.diamond

// Locations
location.abovebar, location.belowbar, location.top, location.bottom, location.absolute

// Sizes
size.auto, size.tiny, size.small, size.normal, size.large, size.huge
```

### Plot Characters
```pinescript
plotchar(condition, title, char, location, color, offset, text, textcolor, editable, size, show_last, display)
```

### Plot Arrows
```pinescript
plotarrow(series, title, colorup, colordown, offset, minheight, maxheight, editable, show_last, display)
```

### Background Color
```pinescript
bgcolor(condition ? color.new(color.green, 90) : na)
```

### Bar Color
```pinescript
barcolor(condition ? color.green : color.red)
```

### Candle Colors
```pinescript
plotcandle(open, high, low, close, title, color, wickcolor, bordercolor, editable, show_last, display)
```

### Horizontal Lines
```pinescript
hline(price, title, color, linestyle, linewidth, editable)
// linestyle: hline.style_solid, hline.style_dashed, hline.style_dotted
```

### Lines (Dynamic)
```pinescript
line.new(x1, y1, x2, y2, xloc, extend, color, style, width)
// xloc: xloc.bar_index, xloc.bar_time
// extend: extend.none, extend.left, extend.right, extend.both
// style: line.style_solid, line.style_dashed, line.style_dotted
```

### Boxes
```pinescript
box.new(left, top, right, bottom, border_color, border_width, border_style, extend, xloc, bgcolor, text, text_size, text_color, text_halign, text_valign, text_wrap, text_font_family)
```

### Labels
```pinescript
label.new(x, y, text, xloc, yloc, color, style, textcolor, size, textalign, tooltip, text_font_family)
```

### Tables
```pinescript
var table t = table.new(position.top_right, columns, rows, bgcolor, frame_color, frame_width, border_color, border_width)
table.cell(t, column, row, text, width, height, text_color, text_halign, text_valign, text_size, bgcolor, tooltip, text_font_family)
```

## Strategy Functions

### Strategy Settings
```pinescript
strategy(title, shorttitle, overlay, format, precision, scale, pyramiding, calc_on_order_fills, calc_on_every_tick, max_bars_back, backtest_fill_limits_assumption, default_qty_type, default_qty_value, initial_capital, currency, slippage, commission_type, commission_value, process_orders_on_close, close_entries_rule, margin_long, margin_short, explicit_plot_zorder, max_lines_count, max_labels_count, max_boxes_count, risk_free_rate, use_bar_magnifier, fill_orders_on_standard_ohlc, max_polylines_count)

// default_qty_type
strategy.fixed, strategy.cash, strategy.percent_of_equity

// commission_type
strategy.commission.percent, strategy.commission.cash_per_contract, strategy.commission.cash_per_order

// close_entries_rule
"FIFO", "ANY"
```

### Entry/Exit
```pinescript
strategy.entry(id, direction, qty, limit, stop, oca_name, oca_type, comment, alert_message)
// direction: strategy.long, strategy.short

strategy.close(id, comment, qty, qty_percent, alert_message, immediately)
strategy.close_all(comment, alert_message, immediately)

strategy.exit(id, from_entry, qty, qty_percent, profit, limit, loss, stop, trail_price, trail_points, trail_offset, oca_name, comment, comment_profit, comment_loss, comment_trailing, alert_message, alert_profit, alert_loss, alert_trailing)

strategy.cancel(id)
strategy.cancel_all()

strategy.order(id, direction, qty, limit, stop, oca_name, oca_type, comment, alert_message)
```

### Position Info
```pinescript
strategy.position_size        // Current position size (+ for long, - for short)
strategy.position_avg_price   // Average entry price
strategy.opentrades           // Number of open trades
strategy.closedtrades         // Number of closed trades
strategy.wintrades           // Number of winning trades
strategy.losstrades          // Number of losing trades
strategy.eventrades          // Number of break-even trades
strategy.netprofit           // Net profit
strategy.grossprofit         // Gross profit
strategy.grossloss           // Gross loss
strategy.max_drawdown        // Maximum drawdown
strategy.equity              // Current equity
strategy.initial_capital     // Initial capital
```

### Trade Info Functions
```pinescript
// Open trades
strategy.opentrades.entry_price(trade_num)
strategy.opentrades.entry_bar_index(trade_num)
strategy.opentrades.entry_time(trade_num)
strategy.opentrades.entry_id(trade_num)
strategy.opentrades.size(trade_num)
strategy.opentrades.profit(trade_num)
strategy.opentrades.max_runup(trade_num)
strategy.opentrades.max_drawdown(trade_num)
strategy.opentrades.commission(trade_num)

// Closed trades
strategy.closedtrades.entry_price(trade_num)
strategy.closedtrades.exit_price(trade_num)
strategy.closedtrades.entry_bar_index(trade_num)
strategy.closedtrades.exit_bar_index(trade_num)
strategy.closedtrades.entry_time(trade_num)
strategy.closedtrades.exit_time(trade_num)
strategy.closedtrades.profit(trade_num)
strategy.closedtrades.profit_percent(trade_num)
strategy.closedtrades.size(trade_num)
strategy.closedtrades.entry_id(trade_num)
strategy.closedtrades.exit_id(trade_num)
strategy.closedtrades.max_runup(trade_num)
strategy.closedtrades.max_runup_percent(trade_num)
strategy.closedtrades.max_drawdown(trade_num)
strategy.closedtrades.max_drawdown_percent(trade_num)
strategy.closedtrades.commission(trade_num)
```

## Time & Session

```pinescript
// Current bar time
time                         // Bar open time (unix ms)
time_close                   // Bar close time
time_tradingday              // Trading day start time

// Time functions
year, month, weekofyear, dayofmonth, dayofweek, hour, minute, second

// Session check
time(timeframe, session)     // Returns time if bar is in session, else na
time(timeframe, session, timezone)

// Time comparison
timestamp(year, month, day, hour, minute, second)
timestamp(timezone, year, month, day, hour, minute, second)

// Example: Trading session filter
inSession = not na(time(timeframe.period, "0930-1600", "America/New_York"))
```

## Alerts

```pinescript
// Alert conditions
alertcondition(condition, title, message)

// Dynamic alerts in strategy
strategy.entry("Long", strategy.long, alert_message="Long entry at {{close}}")

// Alert placeholders
// {{ticker}}, {{exchange}}, {{close}}, {{open}}, {{high}}, {{low}}, {{volume}}
// {{time}}, {{timenow}}, {{interval}}, {{plot_0}}, {{plot("Plot Name")}}
```

## Request Functions (MTF)

```pinescript
// Higher timeframe data
request.security(symbol, timeframe, expression, gaps, lookahead, ignore_invalid_symbol, currency)

// Example
htfClose = request.security(syminfo.tickerid, "D", close)

// Lookahead
barmerge.lookahead_on   // Use current incomplete bar (repainting!)
barmerge.lookahead_off  // Wait for bar close (default, non-repainting)

// Gaps
barmerge.gaps_on        // Show na on missing data
barmerge.gaps_off       // Fill gaps with last value (default)

// Multiple values
[htfOpen, htfHigh, htfLow, htfClose] = request.security(syminfo.tickerid, "D", [open, high, low, close])
```

## Math Functions

```pinescript
math.abs(x)              // Absolute value
math.sign(x)             // Sign (-1, 0, 1)
math.max(x, y)           // Maximum
math.min(x, y)           // Minimum
math.avg(x, y)           // Average
math.round(x)            // Round
math.round(x, precision) // Round to precision
math.floor(x)            // Floor
math.ceil(x)             // Ceiling
math.pow(base, exp)      // Power
math.sqrt(x)             // Square root
math.log(x)              // Natural log
math.log10(x)            // Log base 10
math.exp(x)              // e^x
math.sin(x), math.cos(x), math.tan(x)  // Trigonometry
math.asin(x), math.acos(x), math.atan(x)
math.random(min, max)    // Random number
math.sum(source, length) // Sum over period
math.todegrees(x)        // Radians to degrees
math.toradians(x)        // Degrees to radians
```

## Arrays

```pinescript
// Create
var arr = array.new_float(size, initial_value)
var arr = array.new_int(size, initial_value)
var arr = array.new_bool(size, initial_value)
var arr = array.new_string(size, initial_value)
var arr = array.new_color(size, initial_value)
var arr = array.new_line(size)
var arr = array.new_label(size)
var arr = array.new_box(size)

// Operations
array.push(arr, value)           // Add to end
array.pop(arr)                   // Remove from end
array.unshift(arr, value)        // Add to start
array.shift(arr)                 // Remove from start
array.insert(arr, index, value)  // Insert at index
array.remove(arr, index)         // Remove at index
array.set(arr, index, value)     // Set value at index
array.get(arr, index)            // Get value at index
array.size(arr)                  // Array size
array.clear(arr)                 // Clear array
array.copy(arr)                  // Copy array
array.slice(arr, start, end)     // Slice array

// Search
array.includes(arr, value)       // Contains value
array.indexof(arr, value)        // First index of value
array.lastindexof(arr, value)    // Last index of value
array.binary_search(arr, value)  // Binary search (sorted arrays)
array.binary_search_leftmost(arr, value)
array.binary_search_rightmost(arr, value)

// Sort
array.sort(arr)                  // Sort ascending
array.sort(arr, order.descending)// Sort descending
array.reverse(arr)               // Reverse order

// Math on arrays
array.sum(arr)
array.avg(arr)
array.median(arr)
array.mode(arr)
array.min(arr)
array.max(arr)
array.stdev(arr)
array.variance(arr)
array.range(arr)
array.covariance(arr1, arr2)
array.percentile_linear_interpolation(arr, percentage)
array.percentile_nearest_rank(arr, percentage)
array.percentrank(arr, value)

// Join arrays
array.concat(arr1, arr2)
array.join(arr, separator)
```

## Colors

```pinescript
// Predefined colors
color.aqua, color.black, color.blue, color.fuchsia, color.gray
color.green, color.lime, color.maroon, color.navy, color.olive
color.orange, color.purple, color.red, color.silver, color.teal
color.white, color.yellow

// Create with transparency
color.new(color, transp)         // transp: 0-100 (0=opaque, 100=invisible)
color.rgb(red, green, blue, transp)

// Color functions
color.r(color)                   // Red component (0-255)
color.g(color)                   // Green component
color.b(color)                   // Blue component
color.t(color)                   // Transparency

// Gradient
color.from_gradient(value, bottom_value, top_value, bottom_color, top_color)
```

## Strings

```pinescript
str.contains(source, str)
str.startswith(source, str)
str.endswith(source, str)
str.length(source)
str.lower(source)
str.upper(source)
str.replace(source, target, replacement, occurrence)
str.replace_all(source, target, replacement)
str.split(string, separator)
str.substring(source, begin_pos, end_pos)
str.tonumber(source)
str.tostring(value, format)
str.format(formatString, arg0, arg1, ...)
str.match(source, regex)
str.pos(source, str)
```

## Symbol Info

```pinescript
syminfo.ticker               // Ticker without exchange
syminfo.tickerid             // Full ticker with exchange
syminfo.root                 // Root symbol (without expiration)
syminfo.prefix               // Exchange prefix
syminfo.session              // Session type
syminfo.timezone             // Timezone
syminfo.currency             // Currency
syminfo.basecurrency         // Base currency (for forex)
syminfo.description          // Symbol description
syminfo.type                 // Symbol type (stock, forex, crypto, etc.)
syminfo.pointvalue           // Point value
syminfo.mintick              // Minimum price change
syminfo.volumetype           // Volume type
```
