import csv
import time

def execute(ticker, signal, price):

    print(ticker, signal, price)

    with open("results/trades.csv","a",newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            ticker,
            signal,
            price
        ])