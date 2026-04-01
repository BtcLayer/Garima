#!/usr/bin/env python3
"""Backtest all 10 Pine Script strategies on our 4h data."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from datetime import datetime

FEE = 0.001

def backtest_signal(df, bull, bear, tp=0.03, sl=0.015, horizon=12):
    cap = INITIAL_CAPITAL; trades = []; i = 0
    while i < len(df) - horizon - 1:
        side = None
        if bull.iloc[i]: side = "long"
        elif bear.iloc[i]: side = "short"
        if side:
            entry = df.iloc[i+1]["open"] * (1 + FEE if side=="long" else 1 - FEE)
            tp_p = entry*(1+tp) if side=="long" else entry*(1-tp)
            sl_p = entry*(1-sl) if side=="long" else entry*(1+sl)
            ex = None
            for j in range(i+2, min(i+horizon+2, len(df))):
                if side=="long":
                    if df.iloc[j]["low"] <= sl_p: ex=sl_p*(1-FEE); break
                    if df.iloc[j]["high"] >= tp_p: ex=tp_p*(1-FEE); break
                else:
                    if df.iloc[j]["high"] >= sl_p: ex=sl_p*(1+FEE); break
                    if df.iloc[j]["low"] <= tp_p: ex=tp_p*(1+FEE); break
            if ex is None:
                ex = df.iloc[min(i+horizon+1,len(df)-1)]["close"]*(1-FEE if side=="long" else 1+FEE)
                j = min(i+horizon+1,len(df)-1)
            pnl = (ex-entry)*cap*0.95/entry if side=="long" else (entry-ex)*cap*0.95/entry
            cap += pnl
            trades.append({"pnl":pnl,"side":side})
            i = j+1
        else:
            i += 1
    return cap, trades

ASSETS = ["ETHUSDT","BTCUSDT","ADAUSDT","SOLUSDT","LINKUSDT"]
TP_SL = [(0.02,0.01,8),(0.03,0.015,10),(0.04,0.02,12),(0.06,0.03,12),(0.08,0.04,15)]
all_results = []

for asset in ASSETS:
    df = load_data(f"{asset}_4h")
    if df is None: continue
    df = calculate_indicators(df)
    yrs = max((datetime.fromisoformat(str(df["timestamp"].iloc[-1])[:10])-datetime.fromisoformat(str(df["timestamp"].iloc[0])[:10])).days/365.25, 0.01)
    ema200 = df["close"].ewm(200).mean()
    obv = (np.sign(df["close"].diff())*df["volume"]).fillna(0).cumsum()
    obv_ema = obv.rolling(11).mean()
    cloud_top = df[["senkou_span_a","senkou_span_b"]].max(axis=1)
    cloud_bot = df[["senkou_span_a","senkou_span_b"]].min(axis=1)
    st_upper = (df["high"]+df["low"])/2 + 2.0*df["atr"]
    st_lower = (df["high"]+df["low"])/2 - 2.0*df["atr"]
    dip_count = ((df["rsi"]<35).astype(int)+(df["stoch_k"]<25).astype(int)+(df["close"]<df["bb_lower"]).astype(int)+(df["cci"]<-80).astype(int)+(df["mfi"]<25).astype(int)+(df["williams_r"]<-75).astype(int))
    ob_count = ((df["rsi"]>65).astype(int)+(df["stoch_k"]>75).astype(int)+(df["close"]>df["bb_upper"]).astype(int)+(df["cci"]>80).astype(int)+(df["mfi"]>75).astype(int)+(df["williams_r"]>-25).astype(int))
    trend_up = (df["close"]>df["ema50"])&(df["ema50"]>ema200)
    trend_down = (df["close"]<df["ema50"])&(df["ema50"]<ema200)
    st_above = df["close"]>df["supertrend"]
    is_bull_r = (df["ema50"]>ema200)&(df["adx"]>25)
    is_bear_r = (df["ema50"]<ema200)&(df["adx"]>25)
    is_side = df["adx"]<20

    strategies = {
        "01_MACD_Momentum": (
            ((df["macd"]>df["macd_signal"])&(df["macd"].shift(1)<=df["macd_signal"].shift(1))&(df["close"]>ema200)&(df["adx"]>20)).astype(int),
            ((df["macd"]<df["macd_signal"])&(df["macd"].shift(1)>=df["macd_signal"].shift(1))&(df["close"]<ema200)&(df["adx"]>20)).astype(int)),
        "02_Keltner_RSI": (
            ((df["close"]>df["keltner_upper"])&(df["close"].shift(1)<=df["keltner_upper"].shift(1))&(df["rsi"]>55)&(df["adx"]>20)).astype(int),
            ((df["close"]<df["keltner_lower"])&(df["close"].shift(1)>=df["keltner_lower"].shift(1))&(df["rsi"]<45)&(df["adx"]>20)).astype(int)),
        "03_EMA_Volume": (
            ((df["ema8"]>df["ema21"])&(df["ema8"].shift(1)<=df["ema21"].shift(1))&(df["rsi"]>50)&(df["vol_ratio"]>1.5)&(df["adx"]>20)).astype(int),
            ((df["ema8"]<df["ema21"])&(df["ema8"].shift(1)>=df["ema21"].shift(1))&(df["rsi"]<50)&(df["vol_ratio"]>1.5)&(df["adx"]>20)).astype(int)),
        "04_Ichimoku_Cloud": (
            ((df["close"]>cloud_top)&(df["tenkan_sen"]>df["kijun_sen"])&(df["tenkan_sen"].shift(1)<=df["kijun_sen"].shift(1))&(df["adx"]>20)).astype(int),
            ((df["close"]<cloud_bot)&(df["tenkan_sen"]<df["kijun_sen"])&(df["tenkan_sen"].shift(1)>=df["kijun_sen"].shift(1))&(df["adx"]>20)).astype(int)),
        "05_Supertrend_ADX": (
            (st_above & ~st_above.shift(1).fillna(False) & (df["rsi"]>45) & (df["adx"]>20)).astype(int),
            (~st_above & st_above.shift(1).fillna(True) & (df["rsi"]<55) & (df["adx"]>20)).astype(int)),
        "06_OBV_Momentum": (
            (((obv>obv_ema)&(df["close"]>ema200)&(df["adx"]>20)) & ~((obv.shift(1)>obv_ema.shift(1))&(df["close"].shift(1)>ema200.shift(1)))).astype(int),
            (((obv<obv_ema)&(df["close"]<ema200)&(df["adx"]>20)) & ~((obv.shift(1)<obv_ema.shift(1))&(df["close"].shift(1)<ema200.shift(1)))).astype(int)),
        "07_Lookback_Mom": (
            (((df["close"]>df["close"].shift(9))&(df["adx"]>20)) & ~((df["close"].shift(1)>df["close"].shift(10))&(df["adx"].shift(1)>20))).astype(int),
            (((df["close"]<df["close"].shift(9))&(df["adx"]>20)) & ~((df["close"].shift(1)<df["close"].shift(10))&(df["adx"].shift(1)>20))).astype(int)),
        "08_Supertrend_Lvl": (
            ((df["close"]>st_upper.shift(1))&(df["close"]>ema200)&(df["adx"]>20) & ~((df["close"].shift(1)>st_upper.shift(2))&(df["close"].shift(1)>ema200.shift(1)))).astype(int),
            ((df["close"]<st_lower.shift(1))&(df["close"]<ema200)&(df["adx"]>20) & ~((df["close"].shift(1)<st_lower.shift(2))&(df["close"].shift(1)<ema200.shift(1)))).astype(int)),
        "09_Regime_Adaptive": (
            (((df["close"]>df["high_20"].shift(1))&(df["vol_ratio"]>1.3)&is_bull_r) | ((df["close"]<df["bb_lower"])&(df["rsi"]<35)&(df["rsi"]>df["rsi"].shift(1))&is_side)).astype(int),
            (((df["close"]<df["low_20"].shift(1))&(df["vol_ratio"]>1.3)&is_bear_r) | ((df["close"]>df["bb_upper"])&(df["rsi"]>65)&(df["rsi"]<df["rsi"].shift(1))&is_side)).astype(int)),
        "10_Multi_Dip_Trend": (
            (trend_up & (dip_count>=3) & (df["rsi"]>df["rsi"].shift(1))).astype(int),
            (trend_down & (ob_count>=3) & (df["rsi"]<df["rsi"].shift(1))).astype(int)),
    }

    for sname, (bull, bear) in strategies.items():
        best = None
        for tp, sl, hz in TP_SL:
            cap, trades = backtest_signal(df, bull, bear, tp, sl, hz)
            if len(trades) < 3: continue
            roi = ((cap/INITIAL_CAPITAL)**(1/yrs)-1)*100 if cap > 0 else -100
            daily = roi/365
            w = [t for t in trades if t["pnl"]>0]
            wr = len(w)/len(trades)*100
            tw = sum(t["pnl"] for t in trades if t["pnl"]>0)
            tl = abs(sum(t["pnl"] for t in trades if t["pnl"]<=0))
            pf = tw/tl if tl>0 else 0
            eq=INITIAL_CAPITAL;pk=eq;gdd=0
            for t in trades:
                eq+=t["pnl"];pk=max(pk,eq);dd=(pk-eq)/pk*100;gdd=max(gdd,dd)
            if best is None or daily > best["daily"]:
                best = {"asset":asset,"strategy":sname,"daily":round(daily,4),"roi_yr":round(roi,1),
                        "pf":round(pf,2),"wr":round(wr,1),"gdd":round(gdd,1),
                        "trades":len(trades),"longs":len([t for t in trades if t["side"]=="long"]),
                        "shorts":len([t for t in trades if t["side"]=="short"]),
                        "tp":tp*100,"sl":sl*100,"cap":round(cap,0)}
        if best and best["daily"] > -0.5:
            all_results.append(best)
    print(f"  {asset} done", flush=True)

all_results.sort(key=lambda x: -x["daily"])
print(f"\n{'='*110}")
print(f"  ALL 10 STRATEGIES — BEST PARAMS PER ASSET (4h)")
print(f"{'='*110}")
print(f"{'#':<3} {'ROI/d':>7} {'ROI/yr':>7} {'Asset':<10} {'Strategy':<25} {'PF':>5} {'WR%':>5} {'GDD%':>5} {'Trd':>5} {'L':>4} {'S':>4} {'TP%':>4} {'SL%':>4} {'Final$':>8}")
print("-"*110)
for i, r in enumerate(all_results):
    tag = " <<<" if r["daily"] >= 0.1 else ""
    print(f"{i+1:<3} {r['daily']:>6.3f}% {r['roi_yr']:>6.1f}% {r['asset']:<10} {r['strategy']:<25} {r['pf']:>5.2f} {r['wr']:>5.1f} {r['gdd']:>5.1f} {r['trades']:>5} {r['longs']:>4} {r['shorts']:>4} {r['tp']:>4} {r['sl']:>4} ${r['cap']:>7,.0f}{tag}")
above_01 = len([r for r in all_results if r["daily"]>=0.1])
above_005 = len([r for r in all_results if r["daily"]>=0.05])
print(f"\n>= 0.1%/day: {above_01} | >= 0.05%/day: {above_005} | Total: {len(all_results)}")
print("DONE")
