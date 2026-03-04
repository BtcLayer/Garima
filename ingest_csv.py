import pandas as pd
import os
import sqlite3
import re

DB_PATH = 'db.sqlite3'
INPUT_DIR = 'backtest_imports'

def clean_val(val):
    if pd.isna(val) or val == "0": return 0.0
    # Removes everything except numbers, dots, and minus signs
    cleaned = re.sub(r'[^\d.-]', '', str(val))
    try:
        return float(cleaned)
    except:
        return 0.0

def parse_tv_csv(file_path):
    # Try multiple encodings because TradingView is inconsistent
    for enc in ['utf-8', 'utf-16', 'cp1252']:
        try:
            df = pd.read_csv(file_path, header=None, encoding=enc)
            break
        except:
            continue
    
    # Helper to find value even if there are extra spaces or weird characters
    def find_val(keyword):
        # Search the first column for the keyword
        mask = df[0].astype(str).str.contains(keyword, case=False, na=False)
        if not mask.any():
            return "0"
        return df[mask].iloc[0, 1]

    raw_name = os.path.basename(file_path)
    clean_name = raw_name.split('_BITSTAMP')[0].replace('_', ' ')

    return {
        "strategy_name": clean_name,
        "net_profit": clean_val(find_val("Net Profit")),
        "profit_factor": clean_val(find_val("Profit Factor")),
        "win_rate": clean_val(find_val("Percent Profitable")),
        "max_dd": clean_val(find_val("Max Drawdown")),
        "sharpe": clean_val(find_val("Sharpe Ratio"))
    }

def save_to_db(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO metrics (strategy_name, net_profit, profit_factor, win_rate, max_dd, sharpe)
        VALUES (:strategy_name, :net_profit, :profit_factor, :win_rate, :max_dd, :sharpe)
        ON CONFLICT(strategy_name) DO UPDATE SET
            net_profit=excluded.net_profit,
            profit_factor=excluded.profit_factor,
            win_rate=excluded.win_rate,
            max_dd=excluded.max_dd,
            sharpe=excluded.sharpe
    ''', data)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    for file in os.listdir(INPUT_DIR):
        if file.endswith(".csv"):
            try:
                stats = parse_tv_csv(os.path.join(INPUT_DIR, file))
                save_to_db(stats)
                # This print will tell us if it's actually finding numbers now
                print(f"✅ {stats['strategy_name']}: Profit=${stats['net_profit']}")
            except Exception as e:
                print(f"❌ Error in {file}: {e}")