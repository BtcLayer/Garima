import sqlite3
import os

# --- Configuration (Fixed Pathing) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')

def get_stars(sharpe, pf, profit):
    """Logic to assign star ratings based on performance."""
    if profit <= 0: return "❌"
    if sharpe > 20 and pf > 2.5: return "⭐⭐⭐"
    if sharpe > 10 or pf > 1.8: return "⭐⭐"
    return "⭐"

def generate_report():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Fetch all strategies ranked by Net Profit
        cursor.execute("SELECT strategy_name, net_profit, profit_factor, win_rate, max_dd, sharpe FROM metrics ORDER BY net_profit DESC")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        print("❌ Error: The 'metrics' table does not exist. Please run ingest_csv.py first.")
        conn.close()
        return

    if not rows:
        print("⚠️ No data found in the database. Ensure ingest_csv.py processed your files correctly.")
        conn.close()
        return

    print("="*60)
    print("🏆 TRADINGVIEW INDICATOR LEADERBOARD")
    print("="*60 + "\n")

    # 1. Print the Ranked List
    for i, row in enumerate(rows):
        name, profit, pf, win, dd, sharpe = row
        stars = get_stars(sharpe, pf, profit)
        
        print(f"{i+1}. {name} {stars}")
        print(f"   💰 Net Profit: ${profit:,.2f} | 📊 PF: {pf} | 🎯 Win: {win}% | 📉 MaxDD: ${dd:,.2f} | ⚡ Sharpe: {sharpe}\n")

    # 2. Key Insights Section (QBA-007)
    print("-" * 30)
    print("📊 KEY INSIGHTS")
    
    # Best Sharpe
    cursor.execute("SELECT strategy_name, sharpe FROM metrics ORDER BY sharpe DESC LIMIT 1")
    res = cursor.fetchone()
    if res: print(f"✔️ Highest Risk-Adjusted Return (Sharpe): {res[0]} ({res[1]})")

    # Best Win Rate
    cursor.execute("SELECT strategy_name, win_rate FROM metrics ORDER BY win_rate DESC LIMIT 1")
    res = cursor.fetchone()
    if res: print(f"✔️ Most Reliable Entry (Win Rate): {res[0]} ({res[1]}%)")

    # Lowest Drawdown (Safest)
    cursor.execute("SELECT strategy_name, max_dd FROM metrics WHERE net_profit > 0 ORDER BY max_dd ASC LIMIT 1")
    res = cursor.fetchone()
    if res: print(f"✔️ Safest Strategy (Lowest DD): {res[0]} (${res[1]:,.2f})")

    conn.close()

if __name__ == "__main__":
    generate_report()