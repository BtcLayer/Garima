#!/usr/bin/env python3
"""
Backtest strategies 31-50 (Pine scripts) on BNB, ETH, BTC, SOL, LINK — 4h timeframe.
Maps Pine Script indicator logic to the backtester signal functions as closely as possible.
Checks results against ALPHA++ and ALPHA tier criteria.
"""
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_strategies_batch import (
    load_data, calculate_indicators, apply_strategy,
    run_backtest, DATA_FILES, INITIAL_CAPITAL, FEE,
    SIGNAL_FUNCTIONS,
)

# ── Strategy definitions mapped from Pine scripts 31-50 ─────────────
# Signal mapping notes:
#   EMA cross (ema8>ema21)        -> EMA_Cross (persistent: ema8>ema21)
#   Supertrend (close>supertrend) -> Supertrend (persistent)
#   PSAR (close>psar)             -> PSAR_Bull (persistent)
#   ADX>25 / ADX>30               -> ADX_Trend (threshold=25 in code, close enough)
#   Ichimoku above cloud          -> Ichimoku_Bull (persistent)
#   Tenkan > Kijun                -> Ichimoku_Bull (closest match — both indicate bullish cloud)
#   OBV rising                    -> OBV_Rising (persistent)
#   close > EMA50                 -> Trend_MA50 (persistent)
#   close > EMA200                -> Trend_MA50 (approx — only EMA50 available)
#   Volume > Nx avg               -> Volume_Spike
#   DI+ > DI-                     -> ADX_Trend (closest — both measure trend directional strength)
#   EMA stack (8>21>50)           -> EMA_Cross + Trend_MA50
#   close > Keltner mid (EMA20)   -> EMA_Cross (since keltner_mid ~ EMA20 ~ EMA cross zone)
#   Breakout (close > 20-bar high)-> Breakout_20
#   close > close[1]              -> Volume_Spike (bullish candle w/ volume, closest)

STRATEGIES = [
    # 31: EMA + Supertrend + PSAR + ADX — ALL 4
    {
        "id": "S31", "name": "31_Micro_Trend_A",
        "signals": ["EMA_Cross", "Supertrend", "PSAR_Bull", "ADX_Trend"],
        "min_agreement": 4,
        "sl": 0.005, "tp": 0.020, "ts": 0.003,
    },
    # 32: EMA + Ichimoku + PSAR + OBV — ALL 4
    {
        "id": "S32", "name": "32_Micro_Trend_B",
        "signals": ["EMA_Cross", "Ichimoku_Bull", "PSAR_Bull", "OBV_Rising"],
        "min_agreement": 4,
        "sl": 0.006, "tp": 0.025, "ts": 0.003,
    },
    # 33: Supertrend + PSAR + ADX + OBV + Trend_MA50 — ALL 5
    {
        "id": "S33", "name": "33_Micro_Trend_C",
        "signals": ["Supertrend", "PSAR_Bull", "ADX_Trend", "OBV_Rising", "Trend_MA50"],
        "min_agreement": 5,
        "sl": 0.005, "tp": 0.020, "ts": 0.0025,
    },
    # 34: EMA + Supertrend + PSAR + Ichimoku + ADX + Trend_MA50 — ALL 6
    {
        "id": "S34", "name": "34_Nano_Scalp",
        "signals": ["EMA_Cross", "Supertrend", "PSAR_Bull", "Ichimoku_Bull", "ADX_Trend", "Trend_MA50"],
        "min_agreement": 6,
        "sl": 0.004, "tp": 0.015, "ts": 0.002,
    },
    # 35: EMA + Ichimoku + Ichimoku(TK) + PSAR + Supertrend + ADX + OBV — 6 of 7
    #     Tenkan>Kijun mapped to extra Ichimoku_Bull (counted once, so 6 unique signals, need 5)
    {
        "id": "S35", "name": "35_Precision_Entry",
        "signals": ["EMA_Cross", "Ichimoku_Bull", "PSAR_Bull", "Supertrend", "ADX_Trend", "OBV_Rising"],
        "min_agreement": 5,  # 6 of 7 Pine signals -> 5 of 6 backtester signals (TK merged)
        "sl": 0.005, "tp": 0.025, "ts": 0.003,
    },
    # 36: Ichimoku + TK + Supertrend + PSAR + ADX — ALL 5
    #     Ichi + TK merge to Ichimoku_Bull -> 4 unique signals, need all 4
    {
        "id": "S36", "name": "36_Ichi_Super_Combo",
        "signals": ["Ichimoku_Bull", "Supertrend", "PSAR_Bull", "ADX_Trend"],
        "min_agreement": 4,
        "sl": 0.010, "tp": 0.050, "ts": 0.005,
    },
    # 37: EMA8>21 + close>EMA50 + close>EMA200 + Supertrend + PSAR — ALL 5
    #     close>EMA200 ~ Trend_MA50 (best available)
    {
        "id": "S37", "name": "37_Triple_Trend_Filter",
        "signals": ["EMA_Cross", "Trend_MA50", "Supertrend", "PSAR_Bull"],
        "min_agreement": 4,  # 4 unique backtester signals (EMA50 and EMA200 merge to Trend_MA50)
        "sl": 0.010, "tp": 0.040, "ts": 0.005,
    },
    # 38: Ichimoku + TK + PSAR + OBV + Volume — ALL 5
    #     Ichi+TK merge -> 4 unique
    {
        "id": "S38", "name": "38_Cloud_Momentum",
        "signals": ["Ichimoku_Bull", "PSAR_Bull", "OBV_Rising", "Volume_Spike"],
        "min_agreement": 4,
        "sl": 0.012, "tp": 0.050, "ts": 0.006,
    },
    # 39: ADX>30 + DI+>DI- + EMA + Supertrend + PSAR — ALL 5
    #     ADX>30 and DI+>DI- both map to ADX_Trend -> 4 unique
    {
        "id": "S39", "name": "39_ADX_Power_Entry",
        "signals": ["ADX_Trend", "EMA_Cross", "Supertrend", "PSAR_Bull"],
        "min_agreement": 4,
        "sl": 0.010, "tp": 0.050, "ts": 0.005,
    },
    # 40: close>Keltner_mid + Ichimoku + PSAR + ADX — ALL 4
    #     Keltner_mid (EMA20) ~ EMA_Cross
    {
        "id": "S40", "name": "40_Keltner_Ichi_PSAR",
        "signals": ["EMA_Cross", "Ichimoku_Bull", "PSAR_Bull", "ADX_Trend"],
        "min_agreement": 4,
        "sl": 0.010, "tp": 0.040, "ts": 0.005,
    },
    # 41: EMA + PSAR + Supertrend + ADX + Volume + OBV — 5 of 6
    {
        "id": "S41", "name": "41_Momentum_Burst_Pro",
        "signals": ["EMA_Cross", "PSAR_Bull", "Supertrend", "ADX_Trend", "Volume_Spike", "OBV_Rising"],
        "min_agreement": 5,
        "sl": 0.015, "tp": 0.080, "ts": 0.008,
    },
    # 42: Breakout_20 + Volume + ADX + EMA + Supertrend — ALL 5
    {
        "id": "S42", "name": "42_Breakout_Confirm_Max",
        "signals": ["Breakout_20", "Volume_Spike", "ADX_Trend", "EMA_Cross", "Supertrend"],
        "min_agreement": 5,
        "sl": 0.015, "tp": 0.080, "ts": 0.008,
    },
    # 43: Ichimoku + TK + Breakout_20 + ADX + OBV — ALL 5
    #     Ichi+TK merge -> 4 unique
    {
        "id": "S43", "name": "43_Ichi_Breakout_Pro",
        "signals": ["Ichimoku_Bull", "Breakout_20", "ADX_Trend", "OBV_Rising"],
        "min_agreement": 4,
        "sl": 0.015, "tp": 0.070, "ts": 0.007,
    },
    # 44: PSAR + Volume2x + close>prev + EMA + Supertrend — ALL 5
    #     close>prev ~ Volume_Spike (includes bullish candle check)
    {
        "id": "S44", "name": "44_PSAR_Volume_Surge",
        "signals": ["PSAR_Bull", "Volume_Spike", "EMA_Cross", "Supertrend"],
        "min_agreement": 4,
        "sl": 0.015, "tp": 0.060, "ts": 0.007,
    },
    # 45: DI+>DI- + ADX>25 + EMA + PSAR + Ichimoku — ALL 5
    #     DI and ADX merge to ADX_Trend -> 4 unique
    {
        "id": "S45", "name": "45_DI_Crossover_Pro",
        "signals": ["ADX_Trend", "EMA_Cross", "PSAR_Bull", "Ichimoku_Bull"],
        "min_agreement": 4,
        "sl": 0.015, "tp": 0.070, "ts": 0.007,
    },
    # 46: EMA stack (8>21>50) + PSAR + ADX + Supertrend — ALL 4
    #     EMA stack = EMA_Cross + Trend_MA50
    {
        "id": "S46", "name": "46_EMA_Stack_Full",
        "signals": ["EMA_Cross", "Trend_MA50", "PSAR_Bull", "ADX_Trend", "Supertrend"],
        "min_agreement": 5,
        "sl": 0.010, "tp": 0.050, "ts": 0.005,
    },
    # 47: Cloud breakout + Volume 1.5x + ADX + PSAR — ALL 4
    #     Cloud breakout ~ Ichimoku_Bull (persistent above cloud)
    {
        "id": "S47", "name": "47_Cloud_Break_Volume",
        "signals": ["Ichimoku_Bull", "Volume_Spike", "ADX_Trend", "PSAR_Bull"],
        "min_agreement": 4,
        "sl": 0.015, "tp": 0.080, "ts": 0.008,
    },
    # 48: Supertrend flip + EMA + ADX + PSAR — ALL 4
    #     Supertrend flip ~ Supertrend (persistent; flip is initial signal)
    {
        "id": "S48", "name": "48_Supertrend_Flip_Pro",
        "signals": ["Supertrend", "EMA_Cross", "ADX_Trend", "PSAR_Bull"],
        "min_agreement": 4,
        "sl": 0.015, "tp": 0.060, "ts": 0.006,
    },
    # 49: PSAR flip + Ichimoku + ADX + OBV — ALL 4
    #     PSAR flip ~ PSAR_Bull (persistent)
    {
        "id": "S49", "name": "49_PSAR_Flip_Ichi",
        "signals": ["PSAR_Bull", "Ichimoku_Bull", "ADX_Trend", "OBV_Rising"],
        "min_agreement": 4,
        "sl": 0.012, "tp": 0.060, "ts": 0.006,
    },
    # 50: EMA stack + Ichimoku + TK + PSAR + Supertrend + ADX>30 + OBV + DI — 7 of 8
    #     Deduped: EMA_Cross, Trend_MA50, Ichimoku_Bull, PSAR_Bull, Supertrend, ADX_Trend, OBV_Rising = 7
    #     Need 6 of 7 (TK+Ichi merge, DI+ADX merge)
    {
        "id": "S50", "name": "50_Ultimate_Alpha",
        "signals": ["EMA_Cross", "Trend_MA50", "Ichimoku_Bull", "PSAR_Bull", "Supertrend", "ADX_Trend", "OBV_Rising"],
        "min_agreement": 6,
        "sl": 0.010, "tp": 0.050, "ts": 0.005,
    },
]

# ── Assets and timeframe ────────────────────────────────────────────
ASSETS = ["BNBUSDT", "ETHUSDT", "BTCUSDT", "SOLUSDT", "LINKUSDT"]
TIMEFRAME = "4h"

# ── ALPHA tier criteria ─────────────────────────────────────────────
def classify_tier(daily_pct, sharpe, win_rate, gross_dd):
    """Classify result into ALPHA++ / ALPHA / below."""
    if daily_pct >= 0.50 and sharpe >= 3.5 and win_rate >= 45.0 and gross_dd < 35.0:
        return "ALPHA++"
    elif daily_pct >= 0.25 and sharpe >= 2.5 and win_rate >= 45.0 and gross_dd < 45.0:
        return "ALPHA"
    else:
        return "---"


def compute_metrics(trades, years):
    """Compute all required metrics from a trade list."""
    if not trades:
        return None

    equity = INITIAL_CAPITAL
    peak = equity
    max_dd = 0
    min_capital = INITIAL_CAPITAL
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
        min_capital = min(min_capital, equity)

    final_capital = equity
    net_profit = final_capital - INITIAL_CAPITAL
    roi_pct = net_profit / INITIAL_CAPITAL * 100
    roi_annual = ((final_capital / INITIAL_CAPITAL) ** (1 / max(years, 0.01)) - 1) * 100

    # Daily %
    total_days = years * 365.25
    daily_pct = roi_pct / max(total_days, 1)

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0

    total_wins_usd = sum(t["pnl"] for t in wins)
    total_losses_usd = abs(sum(t["pnl"] for t in losses))
    profit_factor = total_wins_usd / total_losses_usd if total_losses_usd > 0 else 0

    # Sharpe (annualized from trade returns)
    returns = [t["return_pct"] for t in trades]
    avg_trade = np.mean(returns) if returns else 0
    std_ret = np.std(returns) if len(returns) > 1 else 1
    sharpe = (avg_trade / std_ret) * np.sqrt(len(trades)) if std_ret > 0 else 0

    net_dd = max(0, (INITIAL_CAPITAL - min_capital) / INITIAL_CAPITAL * 100)

    return {
        "roi_annual": round(roi_annual, 2),
        "daily_pct": round(daily_pct, 4),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe": round(sharpe, 2),
        "gross_dd": round(max_dd, 2),
        "net_dd": round(net_dd, 2),
        "trades": len(trades),
        "final_capital": round(final_capital, 2),
    }


def main():
    print("=" * 100)
    print("  BATCH 31-50 BACKTEST  |  5 assets x 20 strategies  |  4h timeframe")
    print("=" * 100)

    all_results = []

    for asset in ASSETS:
        data_key = f"{asset}_{TIMEFRAME}"
        if data_key not in DATA_FILES:
            print(f"\n[SKIP] No data for {data_key}")
            continue

        df_raw = load_data(data_key)
        if df_raw is None:
            continue

        print(f"Calculating indicators for {asset}...")
        df_ind = calculate_indicators(df_raw)

        # Determine time range
        if "timestamp" in df_ind.columns:
            from datetime import datetime as _dt
            t0 = str(df_ind["timestamp"].min())[:10]
            t1 = str(df_ind["timestamp"].max())[:10]
            try:
                years = max((_dt.fromisoformat(t1) - _dt.fromisoformat(t0)).days / 365.25, 0.01)
            except Exception:
                years = 1.0
        else:
            t0, t1, years = "?", "?", 1.0

        for strat in STRATEGIES:
            df_copy = apply_strategy(
                df_ind.copy(),
                strat["signals"],
                min_agreement=strat["min_agreement"],
            )
            final_cap, trades = run_backtest(
                df_copy,
                stop_loss=strat["sl"],
                take_profit=strat["tp"],
                trailing_stop=strat["ts"],
            )

            m = compute_metrics(trades, years)
            if m is None:
                continue

            tier = classify_tier(m["daily_pct"], m["sharpe"], m["win_rate"], m["gross_dd"])

            all_results.append({
                "Strategy": strat["name"],
                "Asset": asset.replace("USDT", ""),
                "ROI%/yr": m["roi_annual"],
                "Daily%": m["daily_pct"],
                "WR%": m["win_rate"],
                "PF": m["profit_factor"],
                "Sharpe": m["sharpe"],
                "GDD%": m["gross_dd"],
                "NDD%": m["net_dd"],
                "Trades": m["trades"],
                "Tier": tier,
            })

    # ── Print results ────────────────────────────────────────────────
    if not all_results:
        print("\nNo results to show.")
        return

    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values("Sharpe", ascending=False).reset_index(drop=True)

    print("\n")
    print("=" * 130)
    print("  RESULTS — sorted by Sharpe (hardest metric to pass)")
    print("=" * 130)

    # Print header
    fmt = "{:<28s} {:>5s} {:>9s} {:>7s} {:>6s} {:>6s} {:>7s} {:>6s} {:>6s} {:>6s} {:>8s}"
    print(fmt.format("Strategy", "Asset", "ROI%/yr", "Daily%", "WR%", "PF", "Sharpe", "GDD%", "NDD%", "Trds", "Tier"))
    print("-" * 130)

    for _, row in results_df.iterrows():
        tier_str = row["Tier"]
        line = fmt.format(
            row["Strategy"],
            row["Asset"],
            f"{row['ROI%/yr']:.1f}",
            f"{row['Daily%']:.4f}",
            f"{row['WR%']:.1f}",
            f"{row['PF']:.2f}",
            f"{row['Sharpe']:.2f}",
            f"{row['GDD%']:.1f}",
            f"{row['NDD%']:.1f}",
            str(row["Trades"]),
            tier_str,
        )
        print(line)

    # ── Summary ──────────────────────────────────────────────────────
    alpha_pp = results_df[results_df["Tier"] == "ALPHA++"]
    alpha = results_df[results_df["Tier"] == "ALPHA"]
    print("\n" + "=" * 80)
    print(f"  TOTAL RESULTS: {len(results_df)}")
    print(f"  ALPHA++ : {len(alpha_pp)}  (daily>=0.5%, Sharpe>=3.5, WR>=45%, GDD<35%)")
    print(f"  ALPHA   : {len(alpha)}  (daily>=0.25%, Sharpe>=2.5, WR>=45%, GDD<45%)")
    print(f"  Below   : {len(results_df) - len(alpha_pp) - len(alpha)}")
    print("=" * 80)

    # Save to CSV
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "reports", "batch31_50_results.csv")
    results_df.to_csv(csv_path, index=False)
    print(f"\nSaved to {csv_path}")


if __name__ == "__main__":
    main()
