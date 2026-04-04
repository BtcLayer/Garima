"""Feed April 4 TV validation results into ML + dashboard."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ml_online import add_tv_result, train_online_model
import pandas as pd
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

results = [
    # Strategy, Asset, CAGR%, WR%, PF, GDD%, Trades, Tier
    ("EMA_Ribbon", "ETHUSDT", "1h", 3066, 83.45, 3.88, 9.05, 2159, "TIER_1"),
    ("EMA_Ribbon", "BTCUSDT", "1h", 991, 76.28, 7.09, 12.0, 1659, "TIER_2"),
    ("CCI_Donchian_Fusion", "ETHUSDT", "1h", 2480, 84.25, 5.55, 7.0, 1022, "TIER_1"),
    ("EMA_Ribbon", "LDOUSDT", "1h", 3410, 97.83, 9.79, 7.72, 741, "TIER_1_DEPLOY"),
    ("EMA_Ribbon", "SUIUSDT", "4h", 1350, 84.94, 8.94, 10.22, 1658, "TIER_1"),
    ("Triple_Confirm", "BTCUSDT", "4h", 3826, 84.01, 8.84, 2.46, 744, "TIER_1"),
    ("CCI_Donchian_Fusion", "BTCUSDT", "4h", 3277, 80.84, 8.84, 2.46, 604, "TIER_1"),
    ("CCI_Donchian_Fusion", "LDOUSDT", "4h", 2104, 83.91, 9.17, 6.27, 604, "TIER_2"),
    ("Triple_Confirm", "LDOUSDT", "4h", 3122, 83.52, 9.05, 3.53, 744, "TIER_1"),
    ("Supertrend_CCI", "BTCUSDT", "4h", 1005, 83.91, 9.17, 2.47, 604, "TIER_1"),
    ("Supertrend_CCI", "SUIUSDT", "4h", 1793, 82.78, 7.69, 4.24, 270, "TIER_1"),
    ("Triple_Confirm", "SUIUSDT", "4h", 1703, 83.72, 9.05, 2.73, 744, "TIER_1"),
    ("CCI_Donchian_Fusion", "SUIUSDT", "4h", 1703, 83.72, 12.05, 1.11, 226, "TIER_1"),
    ("Stoch_RSI_Trend", "BTCUSDT", "4h", 806, 81.19, 6.69, 12.48, 270, "TIER_2"),
    ("Stoch_RSI_Trend", "SUIUSDT", "4h", 1338, 81.8, 8.44, 9.5, 270, "TIER_1"),
    ("Stoch_RSI_Trend", "LDOUSDT", "4h", 1338, 82.22, 8.72, 3.21, 270, "TIER_1"),
    ("MACD_Zero_Cross", "ETHUSDT", "4h", 805, 83.83, 11.61, 2.97, 266, "TIER_2"),
    ("MACD_Zero_Cross", "BTCUSDT", "4h", 506, 77.07, 8.49, 4.67, 266, "TIER_2"),
    ("MACD_Zero_Cross", "LDOUSDT", "4h", 404, 83.78, 8.19, 3.19, 111, "TIER_2"),
    ("MACD_Zero_Cross", "SUIUSDT", "4h", 1268, 85.41, 10.76, 3.59, 270, "TIER_1"),
    ("Supertrend_CCI", "ETHUSDT", "4h", 6431, 82.95, 8.66, 2.66, 900, "TIER_1"),
    ("Supertrend_CCI", "LDOUSDT", "4h", 3301, 83.49, 8.66, 3.06, 604, "TIER_1"),
]

print(f"Feeding {len(results)} new TV results...\n")

# Feed to online ML
for strat, asset, tf, cagr, wr, pf, gdd, trades, tier in results:
    params = {"signals": strat.lower().replace("_", "+"), "tp": 12.0, "sl": 1.5, "trail": 4.0}
    tv_result = {
        "net_profit_pct": cagr, "win_rate": wr, "profit_factor": pf,
        "trades": trades, "max_drawdown": -gdd, "profitable": True, "sharpe": 0,
    }
    try:
        add_tv_result(strat, asset, tf, params, tv_result)
    except Exception as e:
        print(f"  Warning: {strat} {asset} — {e}")

# Retrain
print("\nRetraining online model...")
try:
    model = train_online_model()
    print("Model trained!" if model else "Training skipped")
except Exception as e:
    print(f"Training error: {e}")

# Append to dashboard CSV
csv_path = os.path.join(ROOT, "storage", "tv_cagr_results.csv")
new_rows = []
for strat, asset, tf, cagr, wr, pf, gdd, trades, tier in results:
    roi_day = round(((1 + cagr/100)**(1/365.25) - 1) * 100, 4)
    new_rows.append({
        "Strategy": strat, "Asset": asset.replace("USDT", ""),
        "Timeframe": tf,
        "Net_Profit_USD": 0, "ROI_Percent": 0, "ROI": 0,
        "CAGR_Percent": cagr, "ROI_Per_Day_Pct": roi_day,
        "Win_Rate_Percent": wr, "Win_Rate_Adjusted": wr,
        "Profit_Factor": pf, "Sharpe_Ratio": 0,
        "Avg_Win_USD": 0, "Avg_Loss_USD": 0, "Win_Loss_Ratio": 0,
        "Trades_Per_Year": trades / 5,
        "Max_Drawdown_USD": 0, "Max_Drawdown_Percent": 0,
        "Gross_Drawdown_USD": 0, "Gross_Drawdown_Percent": -gdd,
        "Net_Drawdown_USD": 0, "Net_Drawdown_Percent": 0,
        "Current_Drawdown_USD": 0, "Current_Drawdown_Percent": 0,
        "WR_Flag": "HIGH_WR" if wr > 80 else "",
        "Performance_Grade": "EXCEPTIONAL" if tier == "TIER_1_DEPLOY" else "STRONG" if tier == "TIER_1" else "PROMISING",
        "Deployment_Status": tier,
        "Rank": 0, "Initial_Capital_USD": 10000, "Final_Capital_USD": 0,
        "Time_period_checked": "", "Time_start": "", "time_end": "",
        "fees_exchnage": "0.06%", "Total_Trades": trades,
        "Data_Source": "tv_apr4",
    })

df_new = pd.DataFrame(new_rows)
if os.path.exists(csv_path):
    df_existing = pd.read_csv(csv_path)
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
else:
    df_combined = df_new

df_combined = df_combined.sort_values("CAGR_Percent", ascending=False)
df_combined["Rank"] = range(1, len(df_combined) + 1)
df_combined.to_csv(csv_path, index=False)
print(f"\nDashboard CSV updated: {len(df_combined)} total strategies")

# Update top10
top10 = []
top_df = df_combined[df_combined["CAGR_Percent"] > 0].head(10)
for i, (_, row) in enumerate(top_df.iterrows(), 1):
    top10.append({
        "rank": i, "strategy": str(row.get("Strategy", "")),
        "asset": str(row.get("Asset", "")), "timeframe": str(row.get("Timeframe", "4h")),
        "cagr_pct": round(float(row.get("CAGR_Percent", 0)), 2),
        "roi_per_day_pct": round(float(row.get("ROI_Per_Day_Pct", 0)), 4),
        "win_rate": round(float(row.get("Win_Rate_Percent", 0)), 2),
        "profit_factor": round(float(row.get("Profit_Factor", 0)), 2),
        "sharpe": round(float(row.get("Sharpe_Ratio", 0)), 2),
        "max_dd_pct": round(abs(float(row.get("Max_Drawdown_Percent", 0))), 2),
        "gdd_pct": round(abs(float(row.get("Gross_Drawdown_Percent", 0))), 2),
        "trades": int(row.get("Total_Trades", 0)),
        "tier": str(row.get("Deployment_Status", "")),
        "params": {"sl_pct": 1.5, "tp_pct": 12.0, "trail_pct": 4.0,
                   "adx_filter": 20, "volume_filter": True, "max_trades_day": 3},
    })
json.dump(top10, open(os.path.join(ROOT, "storage", "top10_strategies.json"), "w"), indent=2)
print(f"Top 10 updated")

print("\nNew Top 10:")
for s in top10:
    print(f"  #{s['rank']} {s['strategy']} {s['asset']} {s['timeframe']} — CAGR {s['cagr_pct']}% GDD {s['gdd_pct']}% | {s['tier']}")
