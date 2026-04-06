"""
Garima realism pipeline.

This module turns broad result sheets into a smaller, governance-safe package:
1. Normalize and rerank current result files using deployability metrics.
2. Freeze a 3-5 strategy paper shortlist from the most credible source set.
3. Write an approval pack that makes OOS / walk-forward a hard next gate.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "profitable_results_sheet")
REPORTS_DIR = os.path.join(ROOT, "reports")
STORAGE_DIR = os.path.join(ROOT, "storage")

SOURCE_FILES = [
    "combo_strategy_results_good.csv",
    "combo_strategy_results_cagr.csv",
    "combo_strategy_results_cagr2.csv",
]

RERANKED_OUTPUT = os.path.join(REPORTS_DIR, "REALISM_RERANKED_CANDIDATES.csv")
SHORTLIST_OUTPUT = os.path.join(REPORTS_DIR, "FROZEN_PAPER_CANDIDATES.csv")
APPROVAL_PACK_OUTPUT = os.path.join(REPORTS_DIR, "GARIMA_APPROVAL_PACK.md")
SHORTLIST_JSON = os.path.join(STORAGE_DIR, "garima_frozen_shortlist.json")

FIXED_NOTIONAL_USD = 1000.0
MAX_POSITION_PCT = 10.0
DEFAULT_SLIPPAGE_PCT = 0.05
SHORTLIST_SIZE = 5


@dataclass(frozen=True)
class RealismAssumptions:
    fixed_notional_usd: float = FIXED_NOTIONAL_USD
    max_position_pct: float = MAX_POSITION_PCT
    slippage_pct: float = DEFAULT_SLIPPAGE_PCT
    preferred_timeframe: str = "4h"


def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _base_strategy_name(raw_name: str) -> str:
    raw_name = str(raw_name or "").strip()
    if " BINANCE" in raw_name:
        raw_name = raw_name.split(" BINANCE", 1)[0]
    if raw_name[:2].isdigit() and " " in raw_name:
        raw_name = raw_name.split(" ", 1)[1]
    return raw_name.replace("  ", " ").strip()


def _status_group(status: str) -> str:
    status = str(status or "").strip().upper()
    if status in {"TIER_1_DEPLOY", "READY"}:
        return "LIVE_LIKE"
    if status in {"TIER_1", "REVIEW"}:
        return "PAPER_STRONG"
    if status == "TIER_2":
        return "PAPER_BORDERLINE"
    if status == "PAPER_TRADE":
        return "PAPER_ONLY"
    return "REJECT"


def _source_bias(source_file: str) -> int:
    source_file = os.path.basename(source_file).lower()
    if source_file == "combo_strategy_results_good.csv":
        return 12
    if source_file in {"combo_strategy_results_cagr.csv", "combo_strategy_results_cagr2.csv"}:
        return 3
    return 0


def _timeframe_bias(timeframe: str) -> int:
    tf = str(timeframe or "").lower()
    if tf == "4h":
        return 18
    if tf == "1h":
        return 8
    if tf == "15m":
        return -12
    return -5


def _status_bias(status: str) -> int:
    status = str(status or "").upper()
    return {
        "TIER_1_DEPLOY": 26,
        "TIER_1": 22,
        "TIER_2": 12,
        "PAPER_TRADE": 5,
        "READY": 24,
        "REVIEW": 12,
    }.get(status, -25)


def _build_flags(row: pd.Series) -> list[str]:
    flags: list[str] = []
    if row["timeframe"].lower() != "4h":
        flags.append("NON_4H")
    if row["status_group"] == "REJECT":
        flags.append("BAD_STATUS")
    if row["gross_drawdown_percent"] > 20:
        flags.append("HIGH_DRAWDOWN")
    if row["profit_factor"] < 5:
        flags.append("LOW_PF")
    if row["total_trades"] < 250:
        flags.append("LOW_TRADES")
    if row["annualized_return_pct"] > 1000:
        flags.append("EXTREME_ANNUALIZED")
    if row["source_file"] != "combo_strategy_results_good.csv":
        flags.append("SCREENING_ONLY_SOURCE")
    return flags


def _credibility_score(row: pd.Series) -> float:
    score = 0.0
    score += _source_bias(row["source_file"])
    score += _timeframe_bias(row["timeframe"])
    score += _status_bias(row["deployment_status"])
    score += min(row["roi_per_day_pct"] * 10, 25)
    score += min(row["profit_factor"] * 2.5, 25)
    score += min(row["total_trades"] / 80, 18)
    score += max(0.0, 18 - row["gross_drawdown_percent"])
    if row["gross_drawdown_percent"] > 15:
        score -= 10
    if row["timeframe"].lower() == "15m":
        score -= 10
    return round(score, 2)


def load_realism_frame(result_dir: str = RESULTS_DIR) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for name in SOURCE_FILES:
        path = os.path.join(result_dir, name)
        frame = pd.read_csv(path)
        frame["source_file"] = name
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    annualized_col = df.apply(
        lambda row: "CAGR_Percent" if pd.notna(row.get("CAGR_Percent")) else "ROI_Annual_Percent",
        axis=1,
    )

    normalized = pd.DataFrame(
        {
            "source_file": df["source_file"],
            "strategy_display": df["Strategy"],
            "strategy": df["Strategy"].map(_base_strategy_name),
            "asset": df["Asset"].astype(str).str.replace(".P", "", regex=False),
            "timeframe": df["Timeframe"].astype(str),
            "annualization_metric": annualized_col,
            "annualized_return_pct": [
                _safe_float(row.get("CAGR_Percent", row.get("ROI_Annual_Percent")))
                if metric == "CAGR_Percent"
                else _safe_float(row.get("ROI_Annual_Percent", row.get("CAGR_Percent")))
                for (_, row), metric in zip(df.iterrows(), annualized_col)
            ],
            "roi_per_day_pct": df["ROI_Per_Day_Pct"].map(_safe_float),
            "win_rate_percent": df["Win_Rate_Percent"].map(_safe_float),
            "profit_factor": df["Profit_Factor"].map(_safe_float),
            "gross_drawdown_percent": df["Gross_Drawdown_Percent"].abs().map(_safe_float),
            "total_trades": df["Total_Trades"].map(_safe_int),
            "deployment_status": df["Deployment_Status"].astype(str),
            "time_period_checked": df.get("Time_period_checked", ""),
            "time_start": df.get("Time_start", ""),
            "time_end": df.get("time_end", df.get("Time_End", "")),
            "fees_exchange": df.get("fees_exchnage", df.get("Fees_Exchange", "")),
            "data_source": df.get("Data_Source", ""),
        }
    )

    normalized["status_group"] = normalized["deployment_status"].map(_status_group)
    normalized["credibility_score"] = normalized.apply(_credibility_score, axis=1)
    normalized["flags"] = normalized.apply(_build_flags, axis=1).map(lambda items: ",".join(items) if items else "")
    normalized["eligible_for_paper"] = normalized.apply(
        lambda row: (
            row["source_file"] == "combo_strategy_results_good.csv"
            and row["timeframe"].lower() == "4h"
            and row["deployment_status"] in {"TIER_1", "TIER_1_DEPLOY", "TIER_2"}
            and row["gross_drawdown_percent"] <= 15
            and row["profit_factor"] >= 7
            and row["total_trades"] >= 350
            and row["roi_per_day_pct"] >= 0.75
        ),
        axis=1,
    )
    normalized["promotion_gate"] = normalized["eligible_for_paper"].map(
        lambda eligible: "BLOCKED_PENDING_OOS" if eligible else "NOT_SHORTLISTED"
    )
    normalized["oos_status"] = normalized["eligible_for_paper"].map(
        lambda eligible: "PENDING_WALK_FORWARD" if eligible else "NOT_APPLICABLE"
    )
    normalized["paper_trade_recommendation"] = normalized["eligible_for_paper"].map(
        lambda eligible: "YES" if eligible else "NO"
    )
    normalized = normalized.sort_values(
        ["eligible_for_paper", "credibility_score", "roi_per_day_pct"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    return normalized


def freeze_paper_candidates(frame: pd.DataFrame, limit: int = SHORTLIST_SIZE) -> pd.DataFrame:
    shortlist = frame[frame["eligible_for_paper"]].copy()
    shortlist = shortlist.sort_values(
        ["credibility_score", "roi_per_day_pct", "profit_factor"],
        ascending=[False, False, False],
    )
    shortlist = shortlist.drop_duplicates(subset=["strategy", "asset", "timeframe"], keep="first")
    shortlist = shortlist.head(limit).reset_index(drop=True)

    shortlist["selection_reason"] = shortlist.apply(
        lambda row: (
            f"4h candidate with ROI/day {row['roi_per_day_pct']:.4f}, "
            f"PF {row['profit_factor']:.2f}, GDD {row['gross_drawdown_percent']:.2f}%, "
            f"and {row['total_trades']} trades from the validated base sheet."
        ),
        axis=1,
    )
    shortlist["risk_note"] = shortlist.apply(
        lambda row: (
            "Paper-trade only until walk-forward/OOS passes."
            if row["gross_drawdown_percent"] <= 12
            else "Good candidate but drawdown needs extra watch in paper validation."
        ),
        axis=1,
    )
    return shortlist


def _write_csv(frame: pd.DataFrame, path: str) -> str:
    _ensure_parent(path)
    frame.to_csv(path, index=False)
    return path


def _write_shortlist_json(frame: pd.DataFrame, path: str) -> str:
    _ensure_parent(path)
    frame.to_json(path, orient="records", indent=2)
    return path


def _write_approval_pack(shortlist: pd.DataFrame, assumptions: RealismAssumptions) -> str:
    _ensure_parent(APPROVAL_PACK_OUTPUT)
    lines: list[str] = []
    lines.append("# Garima Approval Pack")
    lines.append("")
    lines.append("## Summary")
    lines.append(
        f"- Frozen shortlist size: {len(shortlist)} paper-trade candidates from `combo_strategy_results_good.csv`."
    )
    lines.append("- `combo_strategy_results_cagr.csv` and `combo_strategy_results_cagr2.csv` are treated as screening inputs, not direct promotion inputs.")
    lines.append("- No strategy is promotion-ready for live deployment until walk-forward / OOS validation passes.")
    lines.append("")
    lines.append("## Realism Assumptions")
    lines.append(f"- Fixed notional per trade: `${assumptions.fixed_notional_usd:.0f}`")
    lines.append(f"- Max position cap: `{assumptions.max_position_pct:.0f}%` of current equity")
    lines.append(f"- Slippage assumption: `{assumptions.slippage_pct:.2f}%` per execution")
    lines.append(f"- Preferred timeframe: `{assumptions.preferred_timeframe}`")
    lines.append("")
    lines.append("## Frozen Paper Candidates")
    lines.append("| Strategy | Asset | TF | ROI/day | PF | GDD% | Trades | Gate |")
    lines.append("|----------|-------|----|---------|----|------|--------|------|")
    for _, row in shortlist.iterrows():
        lines.append(
            f"| {row['strategy']} | {row['asset']} | {row['timeframe']} | "
            f"{row['roi_per_day_pct']:.4f} | {row['profit_factor']:.2f} | "
            f"{row['gross_drawdown_percent']:.2f} | {int(row['total_trades'])} | {row['promotion_gate']} |"
        )
    lines.append("")
    lines.append("## Selection Notes")
    for _, row in shortlist.iterrows():
        lines.append(f"- **{row['strategy']} / {row['asset']} / {row['timeframe']}**: {row['selection_reason']} {row['risk_note']}")
    lines.append("")
    lines.append("## Promotion Rule")
    lines.append("- Current state: `paper-trade candidate only`.")
    lines.append("- Required next gate: `walk-forward / OOS PASS` before any approval for live use.")
    lines.append("- Until that gate is recorded, these candidates should not be moved into the live approved manifest.")

    with open(APPROVAL_PACK_OUTPUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return APPROVAL_PACK_OUTPUT


def build_realism_package(result_dir: str = RESULTS_DIR) -> dict[str, str]:
    assumptions = RealismAssumptions()
    frame = load_realism_frame(result_dir=result_dir)
    shortlist = freeze_paper_candidates(frame)
    outputs = {
        "reranked_csv": _write_csv(frame, RERANKED_OUTPUT),
        "shortlist_csv": _write_csv(shortlist, SHORTLIST_OUTPUT),
        "shortlist_json": _write_shortlist_json(shortlist, SHORTLIST_JSON),
        "approval_pack": _write_approval_pack(shortlist, assumptions),
    }
    return outputs
