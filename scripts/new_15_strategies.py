#!/usr/bin/env python3
"""15 completely NEW strategy ideas — never tested before."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from datetime import datetime

FEE = 0.001

def bt(df, bull, bear, tp, sl, hz=12):
    cap=INITIAL_CAPITAL; trades=[]; i=0
    while i<len(df)-hz-1:
        s=None
        if bull.iloc[i]: s="long"
        elif bear.iloc[i]: s="short"
        if s:
            e=df.iloc[i+1]["open"]*(1+FEE if s=="long" else 1-FEE)
            tp_p=e*(1+tp) if s=="long" else e*(1-tp)
            sl_p=e*(1-sl) if s=="long" else e*(1+sl)
            ex=None
            for j in range(i+2,min(i+hz+2,len(df))):
                if s=="long":
                    if df.iloc[j]["low"]<=sl_p: ex=sl_p*(1-FEE); break
                    if df.iloc[j]["high"]>=tp_p: ex=tp_p*(1-FEE); break
                else:
                    if df.iloc[j]["high"]>=sl_p: ex=sl_p*(1+FEE); break
                    if df.iloc[j]["low"]<=tp_p: ex=tp_p*(1+FEE); break
            if ex is None:
                ex=df.iloc[min(i+hz+1,len(df)-1)]["close"]*(1-FEE if s=="long" else 1+FEE)
                j=min(i+hz+1,len(df)-1)
            pnl=(ex-e)*cap*0.95/e if s=="long" else (e-ex)*cap*0.95/e
            cap+=pnl; trades.append({"pnl":pnl,"side":s})
            i=j+1
        else: i+=1
    return cap, trades

ASSETS = ["ETHUSDT","BTCUSDT","ADAUSDT","SOLUSDT","LINKUSDT","BNBUSDT","XRPUSDT","AVAXUSDT","DOTUSDT","LTCUSDT"]
results = []

for asset in ASSETS:
    df = load_data(f"{asset}_4h")
    if df is None: continue
    df = calculate_indicators(df)
    yrs = max((datetime.fromisoformat(str(df["timestamp"].iloc[-1])[:10])-datetime.fromisoformat(str(df["timestamp"].iloc[0])[:10])).days/365.25, 0.01)
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    ema200 = c.ewm(200).mean()
    obv = (np.sign(c.diff())*v).fillna(0).cumsum()

    strats = {}

    # 1. Fast EMA Cross 5/13
    fc = c.ewm(5).mean(); sc = c.ewm(13).mean()
    strats["FastEMA_5_13"] = ((fc>sc)&(fc.shift(1)<=sc.shift(1))&(df["ema8"]>df["ema21"])&(df["adx"]>20), (fc<sc)&(fc.shift(1)>=sc.shift(1))&(df["ema8"]<df["ema21"])&(df["adx"]>20))

    # 2. RSI Divergence
    strats["RSI_Divergence"] = ((l<l.rolling(10).min().shift(1))&(df["rsi"]>df["rsi"].rolling(10).min().shift(1))&(df["rsi"]<40), pd.Series(False,index=df.index))

    # 3. Volume Climax Reversal
    bv = df["vol_ratio"]>2.5
    llw = (pd.concat([c,df["open"]],axis=1).min(axis=1)-l) > (h-l)*0.6
    luw = (h-pd.concat([c,df["open"]],axis=1).max(axis=1)) > (h-l)*0.6
    strats["VolClimax"] = (bv&llw, bv&luw)

    # 4. EMA Ribbon Expansion
    rb = (c.ewm(5).mean()>c.ewm(8).mean())&(c.ewm(8).mean()>c.ewm(13).mean())&(c.ewm(13).mean()>c.ewm(21).mean())
    rs = ((c.ewm(5).mean()-c.ewm(21).mean())/c)>((c.ewm(5).mean()-c.ewm(21).mean())/c).shift(1)
    strats["EMA_Ribbon"] = (rb&rs&~(rb.shift(1)&rs.shift(1)), pd.Series(False,index=df.index))

    # 5. Hammer + Trend
    body = abs(c-df["open"]); tr = h-l
    hammer = llw & (body<tr*0.3) & (c>df["open"])
    strats["Hammer_Trend"] = (hammer&(c>df["ema50"])&(df["adx"]>20), pd.Series(False,index=df.index))

    # 6. Engulfing + Trend
    eng = (c>df["open"])&(df["open"]<c.shift(1))&(c>df["open"].shift(1))&(c.shift(1)<df["open"].shift(1))
    strats["Engulfing_Trend"] = (eng&(c>df["ema50"])&(df["adx"]>20), pd.Series(False,index=df.index))

    # 7. Squeeze Release
    sq = (df["bb_upper"]<df["keltner_upper"])&(df["bb_lower"]>df["keltner_lower"])
    sr = ~sq & sq.shift(1).fillna(False)
    strats["Squeeze_Release"] = (sr&(c.pct_change(10)>0)&(df["adx"]>15), sr&(c.pct_change(10)<0)&(df["adx"]>15))

    # 8. Triple Flip (2 of 3: EMA+ST+PSAR flip same time)
    ef = (df["ema8"]>df["ema21"])&(df["ema8"].shift(1)<=df["ema21"].shift(1))
    sf = (c>df["supertrend"])&(c.shift(1)<=df["supertrend"].shift(1))
    pf2 = (c>df["psar"])&(c.shift(1)<=df["psar"].shift(1))
    strats["Triple_Flip"] = ((ef.astype(int)+sf.astype(int)+pf2.astype(int))>=2, pd.Series(False,index=df.index))

    # 9. Fibonacci Pullback
    sh = h.rolling(20).max(); sl2 = l.rolling(20).min()
    f38 = sh-(sh-sl2)*0.382; f62 = sh-(sh-sl2)*0.618
    strats["Fib_Pullback"] = ((c>=f62)&(c<=f38)&(c>c.shift(1))&(c>df["ema50"]), pd.Series(False,index=df.index))

    # 10. ADX Explosion
    strats["ADX_Explosion"] = ((df["adx"]>30)&(df["adx"].shift(1)<=30)&(c>df["ema50"]), (df["adx"]>30)&(df["adx"].shift(1)<=30)&(c<df["ema50"]))

    # 11. OBV Breakout
    ob_hi = obv.rolling(20).max()
    strats["OBV_Breakout"] = ((obv>ob_hi.shift(1))&(obv.shift(1)<=ob_hi.shift(2))&(c>df["ema21"])&(df["adx"]>20), pd.Series(False,index=df.index))

    # 12. Stoch+RSI Double Bounce
    stb = (df["stoch_k"]>20)&(df["stoch_k"].shift(1)<=20)
    rsb = (df["rsi"]>30)&(df["rsi"].shift(1)<=30)
    strats["StochRSI_Double"] = (stb&rsb&(c>df["ema50"]), pd.Series(False,index=df.index))

    # 13. MACD Zero Cross
    strats["MACD_Zero"] = ((df["macd"]>0)&(df["macd"].shift(1)<=0)&(df["adx"]>20), (df["macd"]<0)&(df["macd"].shift(1)>=0)&(df["adx"]>20))

    # 14. Inside Bar Breakout
    ib = (h<h.shift(1))&(l>l.shift(1))
    strats["InsideBar"] = (ib.shift(1)&(c>h.shift(1))&(df["adx"]>20), ib.shift(1)&(c<l.shift(1))&(df["adx"]>20))

    # 15. Keltner Mean Reversion
    strats["Keltner_MeanRev"] = ((c>df["keltner_lower"])&(c.shift(1)<=df["keltner_lower"].shift(1))&(c>df["ema50"]), (c<df["keltner_upper"])&(c.shift(1)>=df["keltner_upper"].shift(1))&(c<df["ema50"]))

    for sname, (bull, bear) in strats.items():
        bull = bull.astype(int)
        bear = bear.astype(int) if isinstance(bear, pd.Series) else pd.Series(0, index=df.index)
        best = None
        for tp, sl in [(0.02,0.01),(0.03,0.015),(0.04,0.02),(0.06,0.03),(0.08,0.04),(0.10,0.05),(0.15,0.07)]:
            cap, trades = bt(df, bull, bear, tp, sl, 12)
            if len(trades) < 3: continue
            roi = ((cap/INITIAL_CAPITAL)**(1/yrs)-1)*100 if cap > 0 else -100
            daily = roi/365
            w = [t for t in trades if t["pnl"]>0]
            wr = len(w)/len(trades)*100
            tw = sum(t["pnl"] for t in trades if t["pnl"]>0)
            tl2 = abs(sum(t["pnl"] for t in trades if t["pnl"]<=0))
            pf = tw/tl2 if tl2>0 else 0
            eq=INITIAL_CAPITAL;pk=eq;gdd=0
            for t in trades: eq+=t["pnl"];pk=max(pk,eq);gdd=max(gdd,(pk-eq)/pk*100)
            if best is None or daily>best["d"]:
                best = {"d":daily,"r":roi,"pf":pf,"wr":wr,"t":len(trades),"tp":tp*100,"sl":sl*100,"gdd":gdd,"cap":cap}
        if best and best["d"]>-0.5:
            results.append((best["d"],best["r"],asset,sname,best["pf"],best["wr"],best["t"],best["tp"],best["sl"],best["gdd"],best["cap"]))
    print(f"  {asset} done", flush=True)

results.sort(key=lambda x:-x[0])
print(f"\n{'='*110}")
print(f"  15 NEW STRATEGIES — RESULTS")
print(f"{'='*110}")
print(f"{'#':<3} {'ROI/d':>7} {'ROI/yr':>7} {'Asset':<10} {'Strategy':<22} {'PF':>5} {'WR%':>5} {'GDD%':>5} {'Trd':>5} {'TP%':>4} {'SL%':>4} {'Final$':>8}")
print("-"*110)
seen=set(); n=0
for r in results:
    k=(r[2],r[3])
    if k in seen: continue
    seen.add(k); n+=1
    if n>40: break
    tag=" <<<" if r[0]>=0.1 else ""
    print(f"{n:<3} {r[0]:>6.3f}% {r[1]:>6.1f}% {r[2]:<10} {r[3]:<22} {r[4]:>5.2f} {r[5]:>5.1f} {r[9]:>5.1f} {r[6]:>5} {r[7]:>4} {r[8]:>4} ${r[10]:>7,.0f}{tag}")
a1=len(set((r[2],r[3]) for r in results if r[0]>=0.1))
a05=len(set((r[2],r[3]) for r in results if r[0]>=0.05))
print(f"\n>= 0.1%: {a1} | >= 0.05%: {a05} | Total: {len(set((r[2],r[3]) for r in results))}")
print("DONE")
