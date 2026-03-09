import pandas as pd

# Load trades
df = pd.read_csv("results/trades.csv", header=None)

df.columns = [
    "timestamp",
    "symbol",
    "action",
    "price"
]

print("\nTrade Data:\n")
print(df)

# Count trades
total_trades = len(df)

buy_trades = len(df[df["action"] == "buy"])
sell_trades = len(df[df["action"] == "sell"])

print("\n----- Trading Stats -----\n")

print("Total Trades:", total_trades)
print("Buy Trades:", buy_trades)
print("Sell Trades:", sell_trades)

# Basic PnL calculation
profit = 0
position = None
entry_price = 0

for index, row in df.iterrows():

    if row["action"] == "buy":
        position = "long"
        entry_price = row["price"]

    elif row["action"] == "sell" and position == "long":
        exit_price = row["price"]
        profit += exit_price - entry_price
        position = None

print("Total Profit:", profit)