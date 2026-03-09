# 📈 TradingView Strategy Hub

A high-performance automated system for ingesting TradingView backtest data, generating comparative performance reports, and listening for live trade signals via Webhooks.

## 🚀 Features

* **Multi-Tab Ingestion [QBA-005]:** Process "Performance Summary" and "List of Trades" CSV exports directly from TradingView.
* **Database Persistence [QBA-006]:** Local SQLite storage for both historical backtests and live forward-test signals.
* **Automated Reporting [QBA-007]:** Generates HTML leaderboards and CSV summaries, including a "Stability View" to analyze profit consistency.
* **Live Webhook API [QBA-008]:** FastAPI-powered listener to catch and log real-time trade alerts from TradingView via ngrok.
* **Production Ready [QBA-011]:** Modular structure with clean dependency management.

---

## 🛠 Tech Stack

* **Language:** Python 3.9+
* **API Framework:** FastAPI & Uvicorn
* **Data Science:** Pandas & NumPy
* **Database:** SQLite3
* **Tunneling:** ngrok

---

## 📂 Project Structure

```text
├── app/
│   └── main.py          # FastAPI Webhook Server [QBA-008]
├── backtest_imports/    # Raw TradingView CSV exports
├── reports/             # Generated HTML & CSV reports [QBA-007]
├── ingest_csv.py        # CLI for data processing [QBA-005]
├── report.py            # Report generation logic
├── init_db.py           # Database schema initialization
├── RUNBOOK.md           # Operational instructions
└── requirements.txt     # Python dependencies

```

---

## 🚦 Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
python init_db.py

```

### 2. Import Data

```bash
python ingest_csv.py --run-id "BTC_4H_SMC" backtest_imports/Performance.csv

```

### 3. Launch Webhook

```bash
uvicorn app.main:app --reload --port 8000

```

---

## 📊 Sample Metrics (SuperTrend BTC 4H)

Based on current data ingestion, the system is tracking:

* **Net Profit:** $1,676.63 (167.66%)
* **Profit Factor:** 1.412
* **Win Rate:** 41.46%
* **Total Trades:** 82

---

## 📜 Documentation

For detailed operational steps, refer to the [RUNBOOK.md](https://www.google.com/search?q=./RUNBOOK.md).

---

### **Final GitHub Push Steps**

Now that you have your `README.md`, `RUNBOOK.md`, and `requirements.txt`:

1. `git add README.md RUNBOOK.md requirements.txt`
2. `git commit -m "docs: add professional README and Runbook"`
3. `git push origin main`

