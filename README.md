# Quant-Trade-Lab: Multi-Asset Algorithmic Backtesting 🚀

An automated quantitative trading research environment for backtesting and optimizing high-frequency cryptocurrency strategies. This lab focuses on **Annualized Alpha**—normalizing performance across different timeframes to identify the most efficient capital deployment strategies.

## 📊 Performance Overview

This engine evaluates strategies across 3 years of historical data, specifically targeting assets like **BTC**, **ETH**, **SOL**, **LINK**, and **AVAX**.

### Key Metrics

* **Primary Metric:** ROI per Annum % (Annualized Efficiency).
* **Benchmarks:** Strategies must exceed **6% ROI/Annum** to be considered for live deployment.
* **Timeframes:** Optimized for **15m** (Scalping), **1h** (Day Trading), and **4h** (Swing Trading).

---

## 🛠 Features

* **Multi-Factor Ensembles:** Integration of EMA, RSI, Bollinger Bands, and Smart Money Concepts (SMC).
* **Dynamic Universe:** Support for the Top 300 CoinMarketCap assets.
* **Automated Pipeline:** * **Signal Orchestrator:** Manages multi-timeframe signal logic.
* **Flask Webhook Gateway:** Ready for bridge execution between TradingView and Binance.


* **Performance Grading:** Automatic classification of results into `EXCEPTIONAL` (ROI/Annum ≥ 10%) and `GOOD`.

---

## 📈 Top Strategy Leaderboard (3-Year Sample)

| Rank | Strategy | Asset | Timeframe | ROI per Annum % | Win Rate % |
| --- | --- | --- | --- | --- | --- |
| 1 | Stochastic Oversold | LINK/USDT | 15m | **260.77%** | 74.39% |
| 2 | Bollinger MeanReversion | AVAX/USDT | 15m | **131.90%** | 79.17% |
| 3 | RSI Trend | SOL/USDT | 1h | **117.43%** | 25.64% |

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* Pandas / NumPy
* VectorBT or Backtrader
* Binance API / TradingView Webhooks

### Installation

```bash
git clone https://github.com/your-username/Quant-Trade-Lab.git
cd Quant-Trade-Lab
pip install -r requirements.txt

```

### Usage

Run the main backtesting engine to generate the `optimized_200_results_3y_multi_tf.csv` file:

```python
python run_backtest.py --period 3y --assets BTC,ETH,SOL --timeframes 15m,1h,4h

```

---

## 📂 Project Structure

* `/strategies`: Pine Script and Python logic for signal generation.
* `/gateway`: Flask-based server for execution management.
* `/reports`: Performance leaderboards and CSV exports.
* `/notebooks`: Data Science research for Alpha generation.

---

## 🛡 Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves significant risk. Always test thoroughly in a paper-trading environment before deploying live capital.

---

**Would you like me to add a "How it Works" section with specific Pine Script and Python integration steps?**
