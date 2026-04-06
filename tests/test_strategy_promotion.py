import os
import shutil
import sys
import uuid

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def make_test_dir(name: str) -> str:
    root = os.path.join(os.path.dirname(__file__), ".tmp_runtime")
    path = os.path.join(root, f"{name}_{uuid.uuid4().hex}")
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_test_dir(path: str) -> None:
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)


def test_generate_candidates_from_folder(monkeypatch):
    import src.strategy_promotion as sp

    tmp_dir = make_test_dir("promotion_folder")
    try:
        reports_dir = os.path.join(tmp_dir, "reports")
        storage_dir = os.path.join(tmp_dir, "storage")
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(storage_dir, exist_ok=True)

        monkeypatch.setattr(sp, "REPORTS", reports_dir)
        monkeypatch.setattr(sp, "STORAGE", storage_dir)
        monkeypatch.setattr(sp, "CANDIDATES_FILE", os.path.join(storage_dir, "promotion_candidates.json"))
        monkeypatch.setattr(sp, "APPROVED_FILE", os.path.join(storage_dir, "approved_strategies.json"))
        monkeypatch.setattr(sp, "PROMOTION_LOG", os.path.join(storage_dir, "promotion_log.json"))
        monkeypatch.setattr(sp, "REVIEW_REPORT_FILE", os.path.join(reports_dir, "STRATEGY_PROMOTION_REVIEW.md"))
        monkeypatch.setattr(sp, "APPROVED_MANIFEST_FILE", os.path.join(reports_dir, "APPROVED_STRATEGY_MANIFEST.md"))

        file1 = os.path.join(tmp_dir, "part1.csv")
        file2 = os.path.join(tmp_dir, "part2.csv")
        pd.DataFrame(
            [
                {
                    "Strategy": "Alpha",
                    "Asset": "BTC",
                    "Timeframe": "4h",
                    "CAGR_Percent": 120,
                    "ROI_Per_Day_Pct": 0.3,
                    "Win_Rate_Percent": 61,
                    "Profit_Factor": 2.2,
                    "Sharpe_Ratio": 1.8,
                    "Gross_Drawdown_Percent": -8,
                    "Max_Drawdown_Percent": -5,
                    "Total_Trades": 150,
                    "Deployment_Status": "TIER_1",
                    "Rank": 1,
                    "Data_Source": "test",
                }
            ]
        ).to_csv(file1, index=False)
        pd.DataFrame(
            [
                {
                    "Strategy": "Beta",
                    "Asset": "ETH",
                    "Timeframe": "15m",
                    "CAGR_Percent": 1500,
                    "ROI_Per_Day_Pct": 1.1,
                    "Win_Rate_Percent": 66,
                    "Profit_Factor": 2.0,
                    "Sharpe_Ratio": 2.0,
                    "Gross_Drawdown_Percent": -10,
                    "Max_Drawdown_Percent": -6,
                    "Total_Trades": 300,
                    "Deployment_Status": "IGNORE",
                    "Rank": 2,
                    "Data_Source": "test",
                }
            ]
        ).to_csv(file2, index=False)

        candidates = sp.generate_candidates(tmp_dir)
        ids = {candidate["id"] for candidate in candidates}

        assert "Alpha_BTC_4h" in ids
        assert "Beta_ETH_15m" in ids
        beta = next(candidate for candidate in candidates if candidate["id"] == "Beta_ETH_15m")
        assert "EXTREME_CAGR" in beta["flags"]
        assert "LOWER_TIMEFRAME" in beta["flags"]
        assert os.path.exists(sp.REVIEW_REPORT_FILE)
    finally:
        cleanup_test_dir(tmp_dir)


def test_approval_and_match(monkeypatch):
    import src.strategy_promotion as sp

    tmp_dir = make_test_dir("promotion_approve")
    try:
        reports_dir = os.path.join(tmp_dir, "reports")
        storage_dir = os.path.join(tmp_dir, "storage")
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(storage_dir, exist_ok=True)

        monkeypatch.setattr(sp, "CANDIDATES_FILE", os.path.join(storage_dir, "promotion_candidates.json"))
        monkeypatch.setattr(sp, "APPROVED_FILE", os.path.join(storage_dir, "approved_strategies.json"))
        monkeypatch.setattr(sp, "PROMOTION_LOG", os.path.join(storage_dir, "promotion_log.json"))
        monkeypatch.setattr(sp, "APPROVED_MANIFEST_FILE", os.path.join(reports_dir, "APPROVED_STRATEGY_MANIFEST.md"))

        sp.save_json(
            sp.CANDIDATES_FILE,
            [
                {
                    "id": "Alpha_BTC_4h",
                    "strategy": "Alpha",
                    "asset": "BTC",
                    "asset_normalized": "BTC",
                    "timeframe": "4h",
                    "metrics": {"cagr_pct": 120, "gdd_pct": 8},
                    "score": 50,
                    "tier": "TIER_1",
                    "flags": [],
                    "status": "PENDING",
                    "reviewed_by": None,
                    "review_date": None,
                    "review_notes": "",
                }
            ],
        )

        assert sp.approve_strategy("Alpha_BTC_4h", reviewer="Garima", notes="approved for live gate")
        assert sp.is_strategy_approved("Alpha", asset="BTCUSDT", timeframe="4h")
        assert os.path.exists(sp.APPROVED_MANIFEST_FILE)
    finally:
        cleanup_test_dir(tmp_dir)
