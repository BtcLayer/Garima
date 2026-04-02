#!/usr/bin/env python3
"""Generate 30+ BB Squeeze V2 variations with different params.
Each variation = different BB/KC/SL/TP/Trail combo.
Output: Pine Scripts ready for TV testing."""
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pine")

TEMPLATE = '''//@version=5
strategy("{name}", overlay=true, initial_capital=10000,
     default_qty_type=strategy.percent_of_equity, default_qty_value=95,
     commission_type=strategy.commission.percent, commission_value=0.1)

bb_len = {bb_len}
bb_mult = {bb_mult}
kc_mult = {kc_mult}
sl_pct = {sl} / 100
tp_pct = {tp} / 100
trail_pct = {trail} / 100

bb_basis = ta.sma(close, bb_len)
bb_dev = ta.stdev(close, bb_len) * bb_mult
bb_upper = bb_basis + bb_dev
bb_lower = bb_basis - bb_dev
kc_basis = ta.ema(close, bb_len)
kc_range = ta.atr(bb_len)
kc_upper = kc_basis + kc_mult * kc_range
kc_lower = kc_basis - kc_mult * kc_range

squeeze_on = bb_upper < kc_upper and bb_lower > kc_lower
squeeze_release = not squeeze_on and squeeze_on[1]

highest_high = ta.highest(high, bb_len)
lowest_low = ta.lowest(low, bb_len)
delta = close - math.avg(math.avg(highest_high, lowest_low), bb_basis)
momentum = ta.linreg(delta, bb_len, 0)

[diplus, diminus, adx] = ta.dmi(14, 14)
adx_ok = adx > 20
atr14 = ta.atr(14)
atr_ma = ta.sma(atr14, 100)
vol_ok = atr14 < atr_ma * 2
vol_confirm = volume > ta.sma(volume, 20) * 1.2
ema50 = ta.ema(close, 50)
ema200 = ta.ema(close, 200)
trend_up = ema50 > ema200
trend_down = ema50 < ema200

long_signal = squeeze_release and momentum > 0 and adx_ok and vol_ok
short_signal = squeeze_release and momentum < 0 and adx_ok and vol_ok
long_entry = (long_signal and trend_up and vol_confirm) or (long_signal and momentum > momentum[1])
short_entry = (short_signal and trend_down and vol_confirm) or (short_signal and momentum < momentum[1])

var int trades_today = 0
var int consec_losses = 0
var int cooldown = 0
var float day_equity = strategy.equity
is_new_day = ta.change(time("D")) != 0
if is_new_day
    trades_today := 0
    day_equity := strategy.equity
if cooldown > 0
    cooldown -= 1
was_closed = strategy.position_size[1] != 0 and strategy.position_size == 0
if was_closed
    trades_today += 1
    if strategy.netprofit < strategy.netprofit[1]
        consec_losses += 1
        if consec_losses >= 3
            cooldown := 6
            consec_losses := 0
    else
        consec_losses := 0
daily_pnl = (strategy.equity - day_equity) / day_equity
can_trade = trades_today < 3 and cooldown == 0 and daily_pnl > -0.03

if long_entry and can_trade and strategy.position_size <= 0
    strategy.entry("Long", strategy.long)
    strategy.exit("L_Exit", "Long", stop=close * (1 - sl_pct), limit=close * (1 + tp_pct), trail_points=close * trail_pct / 100 / syminfo.mintick, trail_offset=close * trail_pct / 100 / syminfo.mintick)
if short_entry and can_trade and strategy.position_size >= 0
    strategy.entry("Short", strategy.short)
    strategy.exit("S_Exit", "Short", stop=close * (1 + sl_pct), limit=close * (1 - tp_pct), trail_points=close * trail_pct / 100 / syminfo.mintick, trail_offset=close * trail_pct / 100 / syminfo.mintick)
if momentum < 0 and strategy.position_size > 0
    strategy.close("Long")
if momentum > 0 and strategy.position_size < 0
    strategy.close("Short")

barcolor(squeeze_on ? color.red : color.new(color.green, 60))
bgcolor(squeeze_release ? color.new(color.yellow, 88) : na)
plotshape(long_entry and can_trade, "Buy", shape.triangleup, location.belowbar, color.lime, size=size.small)
plotshape(short_entry and can_trade, "Sell", shape.triangledown, location.abovebar, color.red, size=size.small)
'''

# Parameter grid — each combo becomes a Pine Script
VARIATIONS = [
    # (name_suffix, bb_len, bb_mult, kc_mult, sl, tp, trail)
    # Original winning combo
    ("Default", 20, 2.0, 1.5, 1.5, 4.5, 2.0),
    # TP variations (keep winning base)
    ("TP6", 20, 2.0, 1.5, 1.5, 6.0, 2.5),
    ("TP8", 20, 2.0, 1.5, 1.5, 8.0, 3.0),
    ("TP10", 20, 2.0, 1.5, 1.5, 10.0, 3.5),
    ("TP12", 20, 2.0, 1.5, 1.5, 12.0, 4.0),
    ("TP15", 20, 2.0, 1.5, 1.5, 15.0, 5.0),
    ("TP20", 20, 2.0, 1.5, 1.5, 20.0, 6.0),
    # SL variations
    ("SL1_TP8", 20, 2.0, 1.5, 1.0, 8.0, 3.0),
    ("SL2_TP8", 20, 2.0, 1.5, 2.0, 8.0, 3.0),
    ("SL2_TP10", 20, 2.0, 1.5, 2.0, 10.0, 3.5),
    ("SL1_TP10", 20, 2.0, 1.5, 1.0, 10.0, 3.5),
    # BB Length variations
    ("BB14_TP10", 14, 2.0, 1.5, 1.5, 10.0, 3.5),
    ("BB30_TP10", 30, 2.0, 1.5, 1.5, 10.0, 3.5),
    # BB Mult variations
    ("BBM1.5_TP10", 20, 1.5, 1.5, 1.5, 10.0, 3.5),
    ("BBM2.5_TP10", 20, 2.5, 1.5, 1.5, 10.0, 3.5),
    # KC Mult variations
    ("KC1.0_TP10", 20, 2.0, 1.0, 1.5, 10.0, 3.5),
    ("KC2.0_TP10", 20, 2.0, 2.0, 1.5, 10.0, 3.5),
    # Aggressive combos
    ("Aggro1", 14, 1.5, 1.0, 1.0, 15.0, 4.0),
    ("Aggro2", 20, 1.5, 1.0, 1.0, 20.0, 5.0),
    ("Aggro3", 14, 2.0, 1.5, 1.0, 12.0, 4.0),
    # Conservative combos
    ("Safe1", 30, 2.5, 2.0, 2.0, 6.0, 2.0),
    ("Safe2", 20, 2.0, 1.5, 2.0, 5.0, 2.0),
    # Tight squeeze (KC closer to BB = fewer but stronger signals)
    ("TightSQ", 20, 2.0, 1.8, 1.5, 10.0, 3.5),
    # Wide squeeze (more signals but weaker)
    ("WideSQ", 20, 2.0, 1.2, 1.5, 10.0, 3.5),
    # High trail (lock profits fast)
    ("HighTrail", 20, 2.0, 1.5, 1.5, 10.0, 5.0),
    # No trail (let TP/SL decide)
    ("NoTrail", 20, 2.0, 1.5, 1.5, 10.0, 0.3),
]

count = 0
for suffix, bb_len, bb_mult, kc_mult, sl, tp, trail in VARIATIONS:
    count += 1
    name = f"SQ_{suffix}"
    script = TEMPLATE.format(
        name=name, bb_len=bb_len, bb_mult=bb_mult,
        kc_mult=kc_mult, sl=sl, tp=tp, trail=trail
    )
    filename = f"sq_{count:02d}_{suffix}.pine"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w") as f:
        f.write(script)
    print(f"  {count}. {filename} — BB={bb_len} BBM={bb_mult} KC={kc_mult} SL={sl}% TP={tp}% Trail={trail}%")

print(f"\nGenerated {count} Pine Scripts in pine/ folder")
print("Test each on ETHUSDT and DOTUSDT 4h (top 2 winners)")
