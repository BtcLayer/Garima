from flask import Flask, request, jsonify
from binance.client import Client
import config
from strategy_engine import execute

app = Flask(__name__)

# Binance client
client = Client(config.API_KEY, config.API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"

# ---- Risk Settings ----
RISK_PERCENT = 1
STOP_LOSS_PERCENT = 1
TAKE_PROFIT_PERCENT = 2

# ---- Duplicate Signal Protection ----
last_signal = None


def calculate_quantity(symbol):

    balance = client.get_asset_balance(asset='USDT')
    usdt_balance = float(balance['free'])

    risk_amount = usdt_balance * (RISK_PERCENT / 100)

    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker["price"])

    quantity = risk_amount / price

    quantity = round(quantity, 3)

    if quantity <= 0:
        quantity = 0.001

    return quantity


@app.route('/webhook', methods=['POST'])
def webhook():

    global last_signal

    try:

        data = request.get_json(force=True)

        print("Signal received:", data)

        action = data["action"].lower()
        symbol = data["symbol"]
        price = float(data.get("price", 0))

        # ---- Convert TradingView symbol to Binance symbol ----
        if symbol == "BTCUSD":
            symbol = "BTCUSDT"

        # ---- Duplicate Signal Protection ----
        current_signal = f"{symbol}_{action}"

        if current_signal == last_signal:
            print("Duplicate signal ignored")
            return jsonify({"status": "duplicate ignored"})

        last_signal = current_signal

        quantity = calculate_quantity(symbol)

        # ---------------- BUY ----------------
        if action == "buy":

            order = client.order_market_buy(
                symbol=symbol,
                quantity=quantity
            )

            print("BUY order executed:", order)

            # Stop Loss
            stop_price = price * (1 - STOP_LOSS_PERCENT/100)

            client.create_order(
                symbol=symbol,
                side="SELL",
                type="STOP_LOSS_LIMIT",
                quantity=quantity,
                price=round(stop_price, 2),
                stopPrice=round(stop_price, 2),
                timeInForce="GTC"
            )

            # Take Profit
            tp_price = price * (1 + TAKE_PROFIT_PERCENT/100)

            client.create_order(
                symbol=symbol,
                side="SELL",
                type="LIMIT",
                quantity=quantity,
                price=round(tp_price, 2),
                timeInForce="GTC"
            )

            execute(symbol, "buy", price)

        # ---------------- SELL ----------------
        elif action == "sell":

            order = client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )

            print("SELL order executed:", order)

            execute(symbol, "sell", price)

        return jsonify({"status": "success"})

    except Exception as e:

        print("Order error:", e)

        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)