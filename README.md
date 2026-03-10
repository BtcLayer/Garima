# 🚀 Crypto Quant Trading Hub

This repository contains a modular quantitative trading system designed for **Bitcoin (BTC)**, **Ethereum (ETH)**, and **Solana (SOL)**. The project is organized into three distinct workflows to separate historical backtesting, live signal ingestion, and data refinement.

## 📂 Project Structure

```text
Garima/
├── db.sqlite3                 # Central Database (Shared across all workflows)
├── core/                      # SYSTEM KERNEL
│   ├── models.py              # SQLAlchemy Schema (Master Table Rules)
│   ├── init_db.py             # Database Initialization Script
│   └── check_table.py         # Table Diagnostics
│
├── Workflow_A_Leaderboard/    # WORKFLOW A: Historical Analysis
│   ├── ingest_csv.py          # TradingView CSV -> DB Ingestor
│   ├── report.py              # Performance Ranking Report
│   └── backtest_imports/      # Folder for raw backtest CSVs
│
├── Workflow_B_Webhook/        # WORKFLOW B: Live Signal Listener
│   ├── main.py                # FastAPI Webhook Server
│   ├── test_webhook.py        # Connection Simulator
│   └── test_schema.py         # JSON Validator
│
└── Workflow_C_Processor/      # WORKFLOW C: Data Refinement
    └── process_events.py      # Raw JSON -> Clean Trade Logic

```

---

## 🛠 Workflow Usage

### **Workflow A: The "CSV Leaderboard"**

*Process and rank historical backtest data from TradingView.*

1. Place CSVs in `Workflow_A_Leaderboard/backtest_imports/`.
2. Run Ingestion: `python Workflow_A_Leaderboard/ingest_csv.py`
3. Generate Report: `python Workflow_A_Leaderboard/report.py`

### **Workflow B: The "Live Webhook"**

*Start the server to catch real-time alerts.*

1. Start Server: `uvicorn Workflow_B_Webhook.main:app --reload`
2. Test Endpoint: `python Workflow_B_Webhook/test_webhook.py`

### **Workflow C: The "Event Processor"**

*Clean and move raw alerts into actionable trade tables.*

1. Run Processor: `python Workflow_C_Processor/process_events.py`

---

## 🚀 Setup for New Users

1. **Install Dependencies:**
```bash
pip install fastapi uvicorn sqlalchemy pandas

```


2. **Initialize Database:**
```bash
# Run this from the root directory
python core/init_db.py

```


3. **Verify Setup:**
```bash
python core/check_table.py

```

## 📊 Technical Capabilities

* **Deduplication:** Uses SHA-256 idempotency keys to prevent double-trading.
* **Architecture:** Decoupled design allows the API (Workflow B) to run independently of the Processor (Workflow C).
* **Security:** Token-based header validation for all incoming TradingView webhooks.
