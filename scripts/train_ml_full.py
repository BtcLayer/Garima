"""Train ML on full 290 CAGR-validated results + extract top 10 for bot deployment."""
import sys, os, json
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import pickle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE = os.path.join(ROOT, "storage")

# ── Load full results ──
csv_path = os.path.join(ROOT, "storage", "tv_cagr_results.csv")
if not os.path.exists(csv_path):
    # Try the user's desktop path
    csv_path = r"C:\Users\hp\Desktop\Internship\Garima\storage\tv_cagr_results.csv"

# Also load the full CSV from user's desktop
full_csv = r"C:\Users\hp\Desktop\Internship\combo_strategy_results_cagr.csv"
if os.path.exists(full_csv):
    df = pd.read_csv(full_csv)
    print(f"Loaded {len(df)} strategies from CAGR results")
else:
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} strategies from storage")

# ── Clean data ──
df = df.dropna(subset=["CAGR_Percent", "Win_Rate_Percent", "Profit_Factor"])
df = df[df["CAGR_Percent"] > -100]  # remove total losses

# ── Feature Engineering ──
def extract_strategy_type(name):
    """Map strategy name to numeric type."""
    name = str(name).lower()
    types = {
        "donchian": 1, "cci": 2, "ha trend": 3, "heikin": 3,
        "kc breakout": 4, "keltner": 4, "psar": 5, "aroon": 6,
        "momentum v2": 7, "breakout retest": 8, "williams": 9,
        "adx di": 10, "chandelier": 11, "trix": 12, "engulfing": 13,
        "bb squeeze": 14, "ensemble": 15, "vwap": 16, "ichimoku v2": 17,
        "ichimoku pure": 18, "momentum rotation": 19, "dca grid": 20,
        "supertrend macd": 21, "liquidity sweep": 22, "fair value": 23,
        "engulfing volume": 24,
    }
    for key, val in types.items():
        if key in name:
            return val
    return 0

def extract_asset_type(asset):
    """Map asset to numeric."""
    assets = {"ETH": 1, "BTC": 2, "DOT": 3, "LDO": 4, "SOL": 5,
              "LINK": 6, "AVAX": 7, "ADA": 8, "XRP": 9, "SUI": 10,
              "BNB": 11, "LTC": 12, "NEAR": 13}
    return assets.get(str(asset).upper(), 0)

df["strategy_type"] = df["Strategy"].apply(extract_strategy_type)
df["asset_type"] = df["Asset"].apply(extract_asset_type)
df["is_perpetual"] = df["Strategy"].str.contains("\.P|Perpetual", case=False, na=False).astype(int)
df["has_trailing"] = (df["strategy_type"].isin([1,2,3,4,5,6,7,8,9,10,11,12,14])).astype(int)
df["trades_per_year"] = pd.to_numeric(df["Trades_Per_Year"], errors="coerce").fillna(0)
df["max_dd_pct"] = pd.to_numeric(df["Max_Drawdown_Percent"], errors="coerce").fillna(0).abs()
df["gdd_pct"] = pd.to_numeric(df["Gross_Drawdown_Percent"], errors="coerce").fillna(0).abs()
df["win_loss_ratio"] = pd.to_numeric(df["Win_Loss_Ratio"], errors="coerce").fillna(0)

# ── Build features ──
feature_cols = ["strategy_type", "asset_type", "is_perpetual", "has_trailing",
                "Win_Rate_Percent", "Profit_Factor", "Sharpe_Ratio",
                "trades_per_year", "max_dd_pct", "gdd_pct", "win_loss_ratio"]

X = df[feature_cols].fillna(0).values
y = df["CAGR_Percent"].values

# ── Train Models ──
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print("\n" + "="*60)
print("TRAINING ML ON", len(X), "TV-VALIDATED STRATEGIES")
print("="*60)

# Gradient Boosting
gbm = GradientBoostingRegressor(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)
gbm_scores = cross_val_score(gbm, X_scaled, y, cv=5, scoring="r2")
print(f"\nGBM Cross-Val R²: {gbm_scores.mean():.3f} ± {gbm_scores.std():.3f}")

# Random Forest
rf = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
rf_scores = cross_val_score(rf, X_scaled, y, cv=5, scoring="r2")
print(f"RF  Cross-Val R²: {rf_scores.mean():.3f} ± {rf_scores.std():.3f}")

# Train final model on all data
gbm.fit(X_scaled, y)
rf.fit(X_scaled, y)

# Feature importance
print("\nFeature Importance (GBM):")
for feat, imp in sorted(zip(feature_cols, gbm.feature_importances_), key=lambda x: -x[1]):
    print(f"  {imp:.3f}  {feat}")

# ── Save models ──
pickle.dump(gbm, open(os.path.join(STORAGE, "ml_cagr_gbm.pkl"), "wb"))
pickle.dump(rf, open(os.path.join(STORAGE, "ml_cagr_rf.pkl"), "wb"))
pickle.dump(scaler, open(os.path.join(STORAGE, "ml_cagr_scaler.pkl"), "wb"))
pickle.dump(feature_cols, open(os.path.join(STORAGE, "ml_cagr_cols.pkl"), "wb"))
print("\nModels saved to storage/")

# ── TOP 10 STRATEGIES ──
print("\n" + "="*60)
print("TOP 10 STRATEGIES FOR LIVE DEPLOYMENT")
print("="*60)

# Filter: only profitable, TIER_1 or TIER_1_DEPLOY or strong TIER_2
top = df[df["Deployment_Status"].isin(["TIER_1", "TIER_1_DEPLOY", "TIER_2"])].copy()
top = top.sort_values("CAGR_Percent", ascending=False)

# Remove duplicates (same strategy on same asset)
top = top.drop_duplicates(subset=["strategy_type", "asset_type"], keep="first")

# Take top 10
top10 = top.head(10)

print(f"\n{'Rank':<5} {'Strategy':<25} {'Asset':<8} {'CAGR%':<10} {'ROI/day%':<10} {'WR%':<8} {'PF':<8} {'Sharpe':<8} {'MaxDD%':<8} {'GDD%':<8} {'Trades':<8} {'Tier':<15}")
print("-" * 130)

for i, (_, row) in enumerate(top10.iterrows(), 1):
    print(f"{i:<5} {str(row['Strategy'])[:24]:<25} {row['Asset']:<8} {row['CAGR_Percent']:<10.1f} {row['ROI_Per_Day_Pct']:<10.4f} {row['Win_Rate_Percent']:<8.1f} {row['Profit_Factor']:<8.2f} {row['Sharpe_Ratio']:<8.2f} {abs(row['Max_Drawdown_Percent']):<8.2f} {row['gdd_pct']:<8.2f} {row['Total_Trades']:<8} {row['Deployment_Status']:<15}")

# ── Save top 10 as JSON for bot ──
top10_list = []
for i, (_, row) in enumerate(top10.iterrows(), 1):
    top10_list.append({
        "rank": i,
        "strategy": row["Strategy"],
        "asset": row["Asset"],
        "timeframe": "4h",
        "cagr_pct": round(row["CAGR_Percent"], 2),
        "roi_per_day_pct": round(row["ROI_Per_Day_Pct"], 4),
        "win_rate": round(row["Win_Rate_Percent"], 2),
        "profit_factor": round(row["Profit_Factor"], 2),
        "sharpe": round(row["Sharpe_Ratio"], 2),
        "max_dd_pct": round(abs(row["Max_Drawdown_Percent"]), 2),
        "gdd_pct": round(row["gdd_pct"], 2),
        "trades": int(row["Total_Trades"]),
        "tier": row["Deployment_Status"],
        "params": {
            "sl_pct": 1.5,
            "tp_pct": 12.0,
            "trail_pct": 4.0,
            "entry_type": "crossover",
            "adx_filter": 20,
            "volume_filter": True,
            "max_trades_day": 3,
            "cooldown_bars": 6,
            "circuit_breaker_pct": -3.0,
        }
    })

json.dump(top10_list, open(os.path.join(STORAGE, "top10_strategies.json"), "w"), indent=2)
print(f"\nTop 10 saved to storage/top10_strategies.json")

# ── Print bot-ready format ──
print("\n" + "="*60)
print("BOT-READY FORMAT (copy to alert bot)")
print("="*60)
for s in top10_list:
    print(f"""
--- #{s['rank']} {s['strategy']} on {s['asset']} ---
Asset: {s['asset']}USDT | TF: 4h
CAGR: {s['cagr_pct']}%/yr | ROI/day: {s['roi_per_day_pct']}%
WR: {s['win_rate']}% | PF: {s['profit_factor']} | Sharpe: {s['sharpe']}
MaxDD: {s['max_dd_pct']}% | GDD: {s['gdd_pct']}%
Params: SL={s['params']['sl_pct']}% TP={s['params']['tp_pct']}% Trail={s['params']['trail_pct']}%
Filters: ADX>{s['params']['adx_filter']}, Volume>SMA20*1.2, Max 3 trades/day
Tier: {s['tier']}""")
