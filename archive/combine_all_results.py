"""
Combine all strategy results into a common CSV file
Run this AFTER running all 5 individual scripts
"""

import pandas as pd
import os
import re

CSV_FILES = [
    "btc_all_results.csv",
    "eth_all_results.csv",
    "bnb_all_results.csv",
    "sol_all_results.csv",
    "xrp_all_results.csv",
]

OUTPUT_FILE = "all_assets_strategies_combined.csv"

def extract_days(period_str):
    """Extract number of days from period string like '365 days'"""
    if pd.isna(period_str):
        return 365
    match = re.search(r'(\d+)', str(period_str))
    return int(match.group(1)) if match else 365

def calculate_annualized_roi(row):
    """Calculate annualized ROI using the formulas:
    - ROI = (Final Capital - Initial Capital) / Initial Capital × 100
    - ROI_Annual = ((Final Capital / Initial Capital)^(365 / Days)) - 1
    - ROI_Annual_Percent = ROI_Annual × 100
    """
    initial_cap = row.get('Initial_Capital_USD', 10000)
    final_cap = row.get('Final_Capital_USD', 10000)
    period_str = row.get('Time_period_checked', '365 days')
    
    period_days = extract_days(period_str)
    
    if initial_cap <= 0 or final_cap <= 0 or period_days <= 0:
        return pd.Series({
            'roi_up': 0,
            'roi/annum_up': 0,
            'roi/annum%_up': 0
        })
    
    # Basic ROI = (Final Capital - Initial Capital) / Initial Capital × 100
    roi = (final_cap - initial_cap) / initial_cap * 100
    
    # ROI_Annual = ((Final Capital / Initial Capital)^(365 / Days)) - 1
    if period_days > 0:
        roi_annum = ((final_cap / initial_cap) ** (365 / period_days)) - 1
    else:
        roi_annum = 0
    
    # ROI_Annual_Percent = ROI_Annual × 100
    roi_annum_percent = roi_annum * 100
    
    return pd.Series({
        'roi_up': round(roi, 2),
        'roi/annum_up': round(roi_annum * 100, 2),
        'roi/annum%_up': round(roi_annum_percent, 2)
    })

def combine_results():
    all_results = []
    
    print("="*60)
    print("COMBINING ALL STRATEGY RESULTS")
    print("="*60)
    
    for csv_file in CSV_FILES:
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                if len(df) > 0:
                    all_results.append(df)
                    print(f"✅ Loaded {csv_file}: {len(df)} results")
                else:
                    print(f"⚠️  Empty file: {csv_file}")
            except Exception as e:
                print(f"❌ Error loading {csv_file}: {e}")
        else:
            print(f"⚠️  File not found: {csv_file}")
    
    if not all_results:
        print("No results found! Run the individual scripts first.")
        return
    
    # Combine all dataframes
    combined = pd.concat(all_results, ignore_index=True)
    
    # Calculate annualized ROI columns
    print("\n📊 Calculating annualized ROI...")
    roi_columns = combined.apply(calculate_annualized_roi, axis=1)
    combined['roi_up'] = roi_columns['roi_up']
    combined['roi/annum_up'] = roi_columns['roi/annum_up']
    combined['roi/annum%_up'] = roi_columns['roi/annum%_up']
    
    # Sort by roi_up descending
    combined = combined.sort_values("roi_up", ascending=False)
    
    # Re-rank after combining
    combined["Rank"] = range(1, len(combined) + 1)
    
    # Save to common CSV
    combined.to_csv(OUTPUT_FILE, index=False)
    
    print(f"\n{'='*60}")
    print(f"COMBINED RESULTS: {len(combined)} total strategy tests")
    print(f"Saved to: {OUTPUT_FILE}")
    print("="*60)
    
    # Show top 30 most profitable
    print("\n📈 TOP 30 MOST PROFITABLE STRATEGIES:")
    print("-"*60)
    print(combined[["Rank", "Strategy", "Asset", "Timeframe", "roi_up", "roi/annum_up", "Win_Rate_Percent", "Performance_Grade"]].head(30).to_string())
    
    # Summary by asset
    print("\n📊 SUMMARY BY ASSET:")
    print("-"*60)
    summary = combined.groupby("Asset").agg({
        "roi_up": ["mean", "max", "count"],
        "Win_Rate_Percent": "mean"
    }).round(2)
    summary.columns = ["Avg_ROI", "Max_ROI", "Total_Tests", "Avg_WinRate"]
    summary = summary.sort_values("Max_ROI", ascending=False)
    print(summary)
    
    # Profitable only
    profitable = combined[combined["roi_up"] > 0]
    print(f"\n💰 PROFITABLE STRATEGIES: {len(profitable)} ({len(profitable)/len(combined)*100:.1f}%)")
    
    # Grade distribution
    print("\n📈 GRADE DISTRIBUTION:")
    print(combined["Performance_Grade"].value_counts().sort_index())
    
    return combined

if __name__ == "__main__":
    combine_results()
