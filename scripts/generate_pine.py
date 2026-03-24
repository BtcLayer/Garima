"""
Pine Script Generator
=====================
Generates TradingView Pine Script v5 from bot strategy parameters.

Usage:
  python generate_pine.py EMA_Cloud_Strength 3.0 5.0 2.5
  python generate_pine.py <strategy_name> <SL%> <TP%> <TS%>

Or run without args to generate for all elite_ranking.json strategies.
"""

import sys
import os
import json

ROOT = os.path.dirname(os.path.abspath(__file__))

# ── Signal → Pine Script condition mapping ──────────────────────────────
# Matches exactly what run_strategies_batch.py uses
SIGNAL_PINE = {
    "EMA_Cross":    "ema8 > ema21",
    "RSI_Oversold": "rsi14 < 30 and rsi14 > rsi14[1]",
    "MACD_Cross":   "ta.crossover(macdLine, signalLine)",
    "BB_Lower":     "close < bbLower",
    "BB_Upper":     "close > bbUpper",
    "Volume_Spike": "volume / volMA > 1.5 and close > close[1]",
    "Breakout_20":  "close > ta.highest(high, 20)[1]",
    "Stochastic":   "stochK < 20 and stochK > stochK[1]",
    "Supertrend":   "close > supertrend",
    "VWAP":         "close > ta.vwap",
    "ADX_Trend":    "adxVal > 25",
    "Trend_MA50":   "close > ema50",
}

# ── Strategy name → signal list mapping ─────────────────────────────────
# Top strategies from the bot
STRATEGY_SIGNALS = {
    "EMA_Cloud_Strength":      ["EMA_Cross", "Trend_MA50", "ADX_Trend"],
    "EMA_RSI_Momentum":        ["EMA_Cross", "RSI_Oversold", "Trend_MA50"],
    "Supertrend_BB_Entry":     ["Supertrend", "BB_Lower", "EMA_Cross", "MACD_Cross", "RSI_Oversold"],
    "Supertrend_Multi_Entry":  ["Supertrend", "EMA_Cross", "VWAP", "ADX_Trend", "Volume_Spike"],
    "Volume_Breakout_Pro":     ["Volume_Spike", "Breakout_20", "VWAP"],
    "Mean_Reversion_Pro":      ["BB_Lower", "RSI_Oversold", "Stochastic", "VWAP"],
    "RSI_Recovery":            ["RSI_Oversold", "Stochastic", "Trend_MA50"],
    "ADX_Stochastic_VWAP":    ["ADX_Trend", "Stochastic", "VWAP", "BB_Lower", "Volume_Spike"],
    "VWAP_Break_Entry":        ["VWAP", "Breakout_20", "ADX_Trend", "RSI_Oversold"],
    "RSI_Extreme_Reversal":    ["RSI_Oversold", "Stochastic", "BB_Lower", "VWAP"],
    "Breakout_Retest":         ["Breakout_20", "RSI_Oversold", "BB_Lower"],
    "RSI_Stochastic_VWAP_ADX": ["RSI_Oversold", "Stochastic", "VWAP", "ADX_Trend", "MACD_Cross"],
    "RSI_BB_MACD_Stochastic":  ["RSI_Oversold", "BB_Lower", "MACD_Cross", "Stochastic"],
    "Scalp_Trade":             ["RSI_Oversold", "BB_Lower", "VWAP", "Stochastic"],
    "Oversold_Recovery":       ["RSI_Oversold", "Stochastic", "BB_Lower", "VWAP"],
    "Double_Bottom_Formation": ["BB_Lower", "RSI_Oversold", "Stochastic", "VWAP"],
    "BB_Stochastic_Trade":     ["BB_Lower", "Stochastic", "RSI_Oversold", "VWAP"],
    "RSI_Confirmation":        ["RSI_Oversold", "Stochastic", "BB_Lower", "VWAP"],
    "RSI_Stochastic_Pro":      ["RSI_Oversold", "Stochastic", "BB_Lower", "MACD_Cross"],
    "ADX_Stochastic_BB":       ["ADX_Trend", "Stochastic", "BB_Lower", "RSI_Oversold"],
}


def _lookup_min_agreement(strategy_name):
    """Look up min_agreement from batch strategy definitions."""
    try:
        sys.path.insert(0, ROOT)
        from strategies import get_all_strategies
        for s in get_all_strategies():
            if s["name"].lower() == strategy_name.lower():
                return s.get("min_agreement", 1)
    except Exception:
        pass
    return 1


def generate_pine(strategy_name, sl_pct, tp_pct, ts_pct, min_agreement=None):
    """Generate Pine Script v5 code for a strategy."""
    signals = STRATEGY_SIGNALS.get(strategy_name)
    if not signals:
        # Try to find by partial match
        for name, sigs in STRATEGY_SIGNALS.items():
            if strategy_name.lower().replace("_", "") in name.lower().replace("_", ""):
                signals = sigs
                strategy_name = name
                break
    if not signals:
        return f"// Unknown strategy: {strategy_name}\n// Available: {', '.join(STRATEGY_SIGNALS.keys())}"

    # Auto-lookup min_agreement from batch definition
    if min_agreement is None:
        min_agreement = _lookup_min_agreement(strategy_name)

    # Build signal conditions
    signal_vars = []
    signal_conditions = []
    for sig in signals:
        pine_cond = SIGNAL_PINE.get(sig, f"// UNKNOWN: {sig}")
        var_name = f"sig_{sig.lower().replace('_', '')}"
        signal_vars.append(f"{var_name} = {pine_cond}")
        signal_conditions.append(var_name)

    # Combine signals
    if min_agreement == 1:
        entry_logic = " and ".join(signal_conditions)
        entry_comment = "// All signals must agree"
    else:
        sum_expr = " + ".join([f"({s} ? 1 : 0)" for s in signal_conditions])
        entry_logic = f"({sum_expr}) >= {min_agreement}"
        entry_comment = f"// At least {min_agreement} of {len(signals)} signals must agree"

    # Exit: when fewer than 1 signal active (matches bot logic)
    exit_sum = " + ".join([f"({s} ? 1 : 0)" for s in signal_conditions])
    exit_logic = f"({exit_sum}) < 1"

    pine = f"""//@version=5
strategy("{strategy_name} [Bot Verification]", overlay=true, initial_capital=10000,
         default_qty_type=strategy.cash, default_qty_value=9500,
         commission_type=strategy.commission.percent, commission_value=0.1,
         slippage=0)

// ===========================================================
// Strategy: {strategy_name}
// Signals: {', '.join(signals)}
// Parameters: SL={sl_pct}% | TP={tp_pct}% | TS={ts_pct}%
// Generated for cross-verification with Garima bot
// ===========================================================

// -- Indicator Parameters --
ema8   = ta.ema(close, 8)
ema21  = ta.ema(close, 21)
ema50  = ta.ema(close, 50)
sma20  = ta.sma(close, 20)

// Bollinger Bands (20, 2)
bbBasis = sma20
bbDev   = 2.0 * ta.stdev(close, 20)
bbUpper = bbBasis + bbDev
bbLower = bbBasis - bbDev

// RSI (14)
rsi14 = ta.rsi(close, 14)

// MACD (21, 50, 9) — matches bot: ema21 - ema50
macdLine   = ema21 - ema50
signalLine = ta.ema(macdLine, 9)
macdHist   = macdLine - signalLine

// Stochastic (14, 3)
stochK = ta.stoch(close, high, low, 14)
stochD = ta.sma(stochK, 3)

// Volume
volMA = ta.sma(volume, 20)

// ATR (14)
atr14 = ta.atr(14)

// Supertrend (multiplier=3, ATR=14)
hlAvg      = (high + low) / 2.0
supertrend = hlAvg - 3.0 * atr14

// ADX (14)
[diPlus, diMinus, adxVal] = ta.dmi(14, 14)

// -- Signal Conditions --
// Matching run_strategies_batch.py exactly:
{chr(10).join(signal_vars)}

// -- Entry / Exit Logic --
{entry_comment}
entryCondition = {entry_logic}
exitCondition  = {exit_logic}

// -- Risk Parameters --
sl_pct = {sl_pct} / 100.0
tp_pct = {tp_pct} / 100.0
ts_pct = {ts_pct} / 100.0

// -- Strategy Execution --
canTrade = strategy.equity > 0

if entryCondition and strategy.position_size == 0 and canTrade
    qty = math.max(1, math.floor(strategy.equity * 0.95 / close))
    strategy.entry("Long", strategy.long, qty=qty)

if strategy.position_size > 0
    entryPx = strategy.position_avg_price
    slPrice = entryPx * (1 - sl_pct)
    tpPrice = entryPx * (1 + tp_pct)
    strategy.exit("Exit", "Long", stop=slPrice, limit=tpPrice, trail_price=entryPx, trail_offset=entryPx * ts_pct / syminfo.mintick)

if exitCondition and strategy.position_size > 0
    strategy.close("Long", comment="Signal Exit")

// -- Plots --
plot(ema8,  "EMA 8",  color=color.new(color.blue, 0), linewidth=1)
plot(ema21, "EMA 21", color=color.new(color.orange, 0), linewidth=1)
plot(ema50, "EMA 50", color=color.new(color.red, 0), linewidth=2)
plot(bbUpper, "BB Upper", color=color.new(color.gray, 60))
plot(bbLower, "BB Lower", color=color.new(color.gray, 60))
plot(supertrend, "Supertrend", color=color.new(color.green, 0), linewidth=1)

// Entry markers
plotshape(entryCondition and strategy.position_size == 0 and canTrade, "Entry", shape.triangleup, location.belowbar, color.green, size=size.small)
"""
    return pine


def generate_from_elite_ranking():
    """Generate Pine Scripts for all strategies in elite_ranking.json."""
    elite_path = os.path.join(ROOT, "storage", "elite_ranking.json")
    if not os.path.exists(elite_path):
        print("elite_ranking.json not found")
        return

    with open(elite_path) as f:
        data = json.load(f)

    out_dir = os.path.join(ROOT, "pine_scripts")
    os.makedirs(out_dir, exist_ok=True)

    for r in data.get("results", []):
        name = r.get("name", "unknown")
        sl = r.get("sl", 0.03) * 100
        tp = r.get("tp", 0.05) * 100
        ts = r.get("ts", 0.025) * 100

        pine = generate_pine(name, sl, tp, ts)
        if pine.startswith("// Unknown"):
            print(f"  SKIP: {name} — not in signal mapping")
            continue

        filename = f"{name}_SL{sl:.0f}_TP{tp:.0f}_TS{ts:.0f}.pine"
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w") as f:
            f.write(pine)
        print(f"  OK: {filepath}")

    print(f"\nAll scripts saved to: {out_dir}/")
    print("Copy-paste any .pine file into TradingView Pine Editor → Add to Chart")


def main():
    if len(sys.argv) >= 4:
        name = sys.argv[1]
        sl = float(sys.argv[2])
        tp = float(sys.argv[3])
        ts = float(sys.argv[4]) if len(sys.argv) > 4 else 2.5
        pine = generate_pine(name, sl, tp, ts)
        print(pine)

        out_dir = os.path.join(ROOT, "pine_scripts")
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, f"{name}_SL{sl:.0f}_TP{tp:.0f}_TS{ts:.0f}.pine")
        with open(filepath, "w") as f:
            f.write(pine)
        print(f"\nSaved to: {filepath}")
    else:
        print("Generating Pine Scripts for all elite_ranking.json strategies...\n")
        generate_from_elite_ranking()


if __name__ == "__main__":
    main()
