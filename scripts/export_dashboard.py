import pandas as pd
import json
import os
from datetime import datetime

INPUT_FILE = "storage/trades.jsonl"
OUTPUT_FILE = "storage/dashboard_upload.csv"

def fetch_and_format_logs():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found.")
        return

    trades = []
    with open(INPUT_FILE, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                trades.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    if not trades:
        print("❌ Error: No valid trade data found in the file.")
        return

    # Convert list of dicts to DataFrame
    df = pd.DataFrame(trades)

    # 1. Standardize column names to lowercase
    df.columns = [c.lower() for c in df.columns]
    
    # 2. SAFETY PATCHES: Ensure required columns exist for math/export
    if 'quantity' not in df.columns:
        df['quantity'] = 0.01  # Default trade size
    
    if 'entry_side' not in df.columns:
        df['entry_side'] = 'BUY' # Assumption for history
        
    if 'logged_at' not in df.columns:
        df['logged_at'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # 3. Convert numeric columns to proper float types
    numeric_cols = ['entry_price', 'exit_price', 'quantity', 'pnl']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 4. Perform Calculations
    if 'entry_price' in df.columns and 'exit_price' in df.columns:
        # Commission: 0.1% for entry + 0.1% for exit
        df['commission'] = (df['entry_price'] * df['quantity'] * 0.001) + \
                           (df['exit_price'] * df['quantity'] * 0.001)
        
        # PnL % calculation (Safety check for division by zero)
        df['pnl_pct'] = df.apply(
            lambda x: (x['pnl'] / (x['entry_price'] * x['quantity']) * 100) 
            if (x['entry_price'] * x['quantity']) != 0 else 0, axis=1
        )

    # 5. Filter and Order Columns for Google Sheets
    cols_to_export = [
        'logged_at', 'symbol', 'entry_side', 'entry_price', 
        'exit_price', 'quantity', 'commission', 'pnl', 'pnl_pct'
    ]
    
    # Only grab columns that exist or were just created
    available_cols = [c for c in cols_to_export if c in df.columns]
    final_df = df[available_cols]
    
    # 6. Save to CSV
    final_df.to_csv(OUTPUT_FILE, index=False)
    
    print("-" * 30)
    print(f"✅ Success! Dashboard data generated.")
    print(f"📍 File Location: {OUTPUT_FILE}")
    print(f"📈 Total Trades Processed: {len(final_df)}")
    print("-" * 30)

if __name__ == "__main__":
    fetch_and_format_logs()