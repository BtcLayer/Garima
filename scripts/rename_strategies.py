"""Rename messy strategy names in tournament_winners.csv"""
import csv
from collections import Counter

CSV_PATH = "/home/ubuntu/tradingview_webhook_bot/storage/reports/tournament_winners.csv"

RENAME = {
    "03 ema break momentum": "EMA_Break_Momentum",
    "07 macd breakout": "MACD_Breakout",
    "10 aggressive entry": "Aggressive_Entry",
    "21 full momentum": "Full_Momentum",
    "22 ichimoku trend pro": "Ichimoku_Trend_Pro",
    "23 ichimoku macd pro": "Ichimoku_MACD_Pro",
    "24 keltner breakout": "Keltner_Breakout",
    "44 psar volume surge 4h": "PSAR_Volume_Surge",
    "ATR Supertrend [QuantAlgo]": "ATR_Supertrend",
    "BB Squeeze Break": "BB_Squeeze_Break",
    "EMA 9by15 Strategy": "EMA_9x15_Cross",
    "EMA-SMA Crossover": "EMA_SMA_Crossover",
    "Enhanced ATR Supertrend": "Enhanced_ATR_Supertrend",
    "Hackathon V3 FIXED - Institutional Matrix": "Institutional_Matrix",
    "Hybrid SMC [MarkitTick]": "Hybrid_SMC",
    "Hybrid Smart Money Concepts [MarkitTick]": "Hybrid_SMC_Pro",
    "ML Lorentzian Classification": "ML_Lorentzian",
    "Machine Learning Lorentzian Classification": "ML_Lorentzian",
    "Madrid Ribbon": "Madrid_Ribbon",
    "Mean Reversion Scalper Hybrid": "Mean_Reversion_Scalper",
    "Oppsite SMA": "Opposite_SMA",
    "REVERSE_44 psar volume surge 4h": "REV_PSAR_Volume_Surge",
    "REVERSE_reversed barupdn strategy": "REV_BarUpDn",
    "REVERSE_vwap break entry": "REV_VWAP_Break",
    "Reverse Madrid Ribbon Strategy": "REV_Madrid_Ribbon",
    "Reverse SMA 9 Cross": "REV_SMA9_Cross",
    "Reverse SMA Cross Backtest - ETH 1H": "REV_SMA_Cross_ETH",
    "Reverse SuperTrend - ETH 4h": "REV_SuperTrend",
    "Reverse SuperTrend ETH 4h": "REV_SuperTrend",
    "Reverse SuperTrend Strategy": "REV_SuperTrend",
    "Smart Money Concept - Uncle Sam": "SMC_UncleSam",
    "Smart Money Concepts [LuxAlgo]": "SMC_LuxAlgo",
    "Squeeze Go Momentum Pro": "Squeeze_Momentum_Pro",
    "Squeeze Go Pro": "Squeeze_Go_Pro",
    "Squeeze Momentum": "Squeeze_Momentum",
    "Squeeze Momentum Indicator [LazyBear]": "Squeeze_LazyBear",
    "Squeeze Momentum [LazyBear]": "Squeeze_LazyBear",
    "Squeeze vX [DGT]": "Squeeze_DGT",
    "Squeeze-Flow Expansion Hybrid": "Squeeze_Flow_Hybrid",
    "SuperTrend BTC 4h - Webhook": "SuperTrend_BTC",
    "SuperTrend Fusion \u2014 ATP": "SuperTrend_Fusion",
    "Supertrend": "SuperTrend",
    "reverse liquidity trap": "REV_Liquidity_Trap",
    "reversed barupdn strategy": "REV_BarUpDn",
    "vwap break entry": "VWAP_Break_Entry",
    "tv_12_PSAR_EMA_Vol": "PSAR_EMA_Vol",
}


def clean_name(name):
    name = name.strip().strip("'").strip('"')
    if name in RENAME:
        return RENAME[name]
    for old, new in RENAME.items():
        if old in name:
            return new
    if "SMC Strategy" in name or "Smart Money Concepts" in name:
        if "Webhook" in name:
            return "SMC_LuxAlgo_WH"
        return "SMC_LuxAlgo"
    return name


rows = []
with open(CSV_PATH, "r") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows.append(header)
    for row in reader:
        if len(row) >= 2:
            row[1] = clean_name(row[1])
        rows.append(row)

with open(CSV_PATH, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

names = Counter(row[1] for row in rows[1:])
print(f"Renamed {len(rows)-1} strategies")
print(f"Unique names: {len(names)}")
for n, c in names.most_common(15):
    print(f"  {n}: {c}")
