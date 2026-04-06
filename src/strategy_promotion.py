"""
Strategy promotion pipeline.

Garima's workstream is the control plane around strategy approval:
1. Generate an offline review artifact from validated TV results.
2. Let a human approve/reject candidates with notes.
3. Keep a clean approved manifest for live deployment.
4. Ensure live execution can rely on that manifest instead of dynamic rankings.
"""

import json
import os
from datetime import datetime
from typing import Any

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE = os.path.join(ROOT, "storage")
REPORTS = os.path.join(ROOT, "reports")

DEFAULT_RESULTS_FILE = os.path.join(STORAGE, "tv_cagr_results.csv")
CANDIDATES_FILE = os.path.join(STORAGE, "promotion_candidates.json")
APPROVED_FILE = os.path.join(STORAGE, "approved_strategies.json")
PROMOTION_LOG = os.path.join(STORAGE, "promotion_log.json")
REVIEW_REPORT_FILE = os.path.join(REPORTS, "STRATEGY_PROMOTION_REVIEW.md")
APPROVED_MANIFEST_FILE = os.path.join(REPORTS, "APPROVED_STRATEGY_MANIFEST.md")
ARTIFACT_VERSION = "1.0"


def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_json(path: str, default: Any = None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return [] if default is None else default


def save_json(path: str, data: Any) -> None:
    _ensure_parent(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _normalize_asset(asset: str) -> str:
    asset = (asset or "").upper().strip()
    for suffix in ("USDT", "USD", ".P", ".PERP"):
        if asset.endswith(suffix):
            asset = asset[: -len(suffix)]
    return asset


def _build_flags(row: dict) -> list[str]:
    cagr = _safe_float(row.get("CAGR_Percent"))
    wr = _safe_float(row.get("Win_Rate_Percent"))
    gdd = abs(_safe_float(row.get("Gross_Drawdown_Percent")))
    pf = _safe_float(row.get("Profit_Factor"))
    trades = _safe_int(row.get("Total_Trades"))
    sharpe = _safe_float(row.get("Sharpe_Ratio"))
    timeframe = str(row.get("Timeframe", "4h")).lower()

    flags: list[str] = []
    if wr > 80:
        flags.append("HIGH_WR")
    if gdd > 15:
        flags.append("HIGH_GDD")
    if trades < 100:
        flags.append("LOW_TRADES")
    if pf > 15:
        flags.append("UNUSUAL_PF")
    if cagr > 1000:
        flags.append("EXTREME_CAGR")
    if timeframe in {"15m", "5m", "3m", "1m"}:
        flags.append("LOWER_TIMEFRAME")
    if sharpe == 0:
        flags.append("MISSING_SHARPE")
    return flags


def _score_candidate(row: dict) -> float:
    cagr = _safe_float(row.get("CAGR_Percent"))
    wr = _safe_float(row.get("Win_Rate_Percent"))
    gdd = abs(_safe_float(row.get("Gross_Drawdown_Percent")))
    pf = _safe_float(row.get("Profit_Factor"))
    trades = _safe_int(row.get("Total_Trades"))
    sharpe = _safe_float(row.get("Sharpe_Ratio"))

    score = 0.0
    score += min(cagr / 100, 30)
    score += min(pf * 2, 20)
    score += min(wr * 0.2, 15)
    score += max(0, 15 - gdd * 0.6)
    score += min(trades / 50, 10)
    score += min(sharpe * 3, 10)
    return round(score, 1)


def _assign_tier(row: dict) -> str:
    existing = str(row.get("Deployment_Status", "")).strip()
    if existing:
        return existing

    cagr = _safe_float(row.get("CAGR_Percent"))
    wr = _safe_float(row.get("Win_Rate_Percent"))
    gdd = abs(_safe_float(row.get("Gross_Drawdown_Percent")))
    if cagr >= 500 and gdd < 10 and wr >= 60:
        return "TIER_1_DEPLOY"
    if cagr >= 200 and gdd < 15 and wr >= 55:
        return "TIER_1"
    if cagr >= 50 and gdd < 25 and wr >= 50:
        return "TIER_2"
    return "PAPER_TRADE"


def _candidate_from_row(row: dict, source_csv_path: str) -> dict:
    strategy = str(row.get("Strategy", "")).strip()
    asset = str(row.get("Asset", "")).strip()
    timeframe = str(row.get("Timeframe", "4h")).strip()
    flags = _build_flags(row)
    return {
        "artifact_type": "PROMOTION_CANDIDATE",
        "artifact_version": ARTIFACT_VERSION,
        "id": f"{strategy}_{asset}_{timeframe}",
        "strategy": strategy,
        "asset": asset,
        "asset_normalized": _normalize_asset(asset),
        "timeframe": timeframe,
        "source": {
            "results_file": os.path.abspath(source_csv_path),
            "data_source": str(row.get("Data_Source", "")),
            "rank": _safe_int(row.get("Rank")),
        },
        "metrics": {
            "cagr_pct": round(
                _safe_float(row.get("CAGR_Percent", row.get("ROI_Annual_Percent"))), 2
            ),
            "roi_annual_pct": round(
                _safe_float(row.get("ROI_Annual_Percent", row.get("CAGR_Percent"))), 2
            ),
            "roi_per_day_pct": round(_safe_float(row.get("ROI_Per_Day_Pct")), 4),
            "win_rate": round(_safe_float(row.get("Win_Rate_Percent")), 2),
            "profit_factor": round(_safe_float(row.get("Profit_Factor")), 2),
            "sharpe": round(_safe_float(row.get("Sharpe_Ratio")), 2),
            "gdd_pct": round(abs(_safe_float(row.get("Gross_Drawdown_Percent"))), 2),
            "max_dd_pct": round(abs(_safe_float(row.get("Max_Drawdown_Percent"))), 2),
            "trades": _safe_int(row.get("Total_Trades")),
        },
        "score": _score_candidate(row),
        "tier": _assign_tier(row),
        "flags": flags,
        "requires_manual_review": any(
            flag in {"EXTREME_CAGR", "LOWER_TIMEFRAME", "MISSING_SHARPE"} for flag in flags
        ),
        "oos_status": "PENDING_WALK_FORWARD",
        "promotion_gate": "BLOCKED_PENDING_OOS",
        "paper_trade_recommendation": "YES" if timeframe.lower() == "4h" else "NO",
        "status": "PENDING",
        "reviewed_by": None,
        "review_date": None,
        "review_notes": "",
        "params": {
            "position_size_pct": 10.0,
            "cooldown_bars": 6,
            "max_trades_day": 3,
            "circuit_breaker_pct": -3.0,
        },
        "generated_at": datetime.now().isoformat(),
    }


def _load_results_frame(source_path: str) -> tuple[pd.DataFrame, str]:
    source_path = os.path.abspath(source_path)
    if os.path.isdir(source_path):
        csv_files = sorted(
            [
                os.path.join(source_path, name)
                for name in os.listdir(source_path)
                if name.lower().endswith(".csv")
            ]
        )
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in directory: {source_path}")

        frames = []
        for csv_path in csv_files:
            frame = pd.read_csv(csv_path)
            frame["Source_File"] = os.path.abspath(csv_path)
            frames.append(frame)
        return pd.concat(frames, ignore_index=True), source_path

    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Results source not found: {source_path}")

    frame = pd.read_csv(source_path)
    frame["Source_File"] = os.path.abspath(source_path)
    return frame, source_path


def _write_review_report(candidates: list[dict], source_csv_path: str) -> str:
    _ensure_parent(REVIEW_REPORT_FILE)
    lines: list[str] = []
    lines.append("# Strategy Promotion Review")
    lines.append("")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- Source: `{os.path.abspath(source_csv_path)}`")
    lines.append(f"- Candidates: {len(candidates)}")
    lines.append(f"- Pending: {len([c for c in candidates if c['status'] == 'PENDING'])}")
    lines.append("")
    lines.append("## What This Artifact Is")
    lines.append("- This is the offline review set for Garima's approval workflow.")
    lines.append("- Only reviewed and approved strategies should be considered for live execution.")
    lines.append("- High-output or lower-timeframe rows should be reviewed carefully before approval.")
    lines.append("")

    top_candidates = sorted(candidates, key=lambda x: (-x["score"], x["metrics"]["gdd_pct"]))[:20]
    lines.append("## Top Candidates")
    lines.append("| ID | Tier | Score | CAGR% | GDD% | Trades | Flags |")
    lines.append("|----|------|-------|-------|------|--------|-------|")
    for candidate in top_candidates:
        metrics = candidate["metrics"]
        flags = ", ".join(candidate["flags"]) if candidate["flags"] else "-"
        lines.append(
            f"| `{candidate['id']}` | {candidate['tier']} | {candidate['score']} | "
            f"{metrics['cagr_pct']} | {metrics['gdd_pct']} | {metrics['trades']} | {flags} |"
        )

    with open(REVIEW_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return REVIEW_REPORT_FILE


def _write_approved_manifest(approved: list[dict]) -> str:
    _ensure_parent(APPROVED_MANIFEST_FILE)
    lines: list[str] = []
    lines.append("# Approved Strategy Manifest")
    lines.append("")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- Approved strategies: {len(approved)}")
    lines.append("")
    lines.append("## Live Set")
    if not approved:
        lines.append("- No approved strategies yet.")
    else:
        lines.append("| Strategy | Asset | TF | Tier | Score | CAGR% | GDD% | Reviewer |")
        lines.append("|----------|-------|----|------|-------|-------|------|----------|")
        for item in sorted(approved, key=lambda x: (-x["score"], x["metrics"]["gdd_pct"])):
            metrics = item["metrics"]
            lines.append(
                f"| {item['strategy']} | {item['asset']} | {item['timeframe']} | {item['tier']} | "
                f"{item['score']} | {metrics['cagr_pct']} | {metrics['gdd_pct']} | {item.get('reviewed_by') or '-'} |"
            )

    with open(APPROVED_MANIFEST_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return APPROVED_MANIFEST_FILE


def generate_candidates(
    source_csv_path: str | None = None,
    min_cagr: float = 50,
    min_trades: int = 50,
    max_gdd: float = 25,
) -> list[dict]:
    """
    Generate promotion candidates from validated TV results.

    This is Garima's offline review artifact. It should be reviewed before
    any strategy is allowed into the live deployment set.
    """
    source_csv_path = source_csv_path or DEFAULT_RESULTS_FILE
    df, resolved_source = _load_results_frame(source_csv_path)
    metric_col = "CAGR_Percent" if "CAGR_Percent" in df.columns else "ROI_Annual_Percent"
    df = df[df[metric_col] >= min_cagr]
    if "Total_Trades" in df.columns:
        df = df[df["Total_Trades"] >= min_trades]
    if "Gross_Drawdown_Percent" in df.columns:
        df = df[abs(df["Gross_Drawdown_Percent"]) <= max_gdd]
    df = df.sort_values(["CAGR_Percent", "Profit_Factor"], ascending=[False, False])

    candidates = [_candidate_from_row(row, str(row.get("Source_File", resolved_source))) for row in df.to_dict(orient="records")]
    best_by_id: dict[str, dict] = {}
    for candidate in candidates:
        current = best_by_id.get(candidate["id"])
        if current is None or candidate["score"] > current["score"]:
            best_by_id[candidate["id"]] = candidate
    candidates = sorted(best_by_id.values(), key=lambda x: (-x["score"], x["metrics"]["gdd_pct"]))
    save_json(CANDIDATES_FILE, candidates)
    _write_review_report(candidates, resolved_source)
    return candidates


def _append_promotion_log(action: str, strategy_id: str, reviewer: str, notes: str = "") -> None:
    log = load_json(PROMOTION_LOG, default=[])
    log.append(
        {
            "action": action,
            "strategy_id": strategy_id,
            "reviewer": reviewer,
            "timestamp": datetime.now().isoformat(),
            "notes": notes,
        }
    )
    save_json(PROMOTION_LOG, log)


def approve_strategy(strategy_id: str, reviewer: str = "Garima", notes: str = "") -> bool:
    candidates = load_json(CANDIDATES_FILE, default=[])
    approved = load_json(APPROVED_FILE, default=[])

    found = None
    for candidate in candidates:
        if candidate["id"] == strategy_id:
            candidate["status"] = "APPROVED"
            candidate["reviewed_by"] = reviewer
            candidate["review_date"] = datetime.now().isoformat()
            candidate["review_notes"] = notes
            found = candidate
            break

    if not found:
        return False

    approved_by_id = {item["id"]: item for item in approved}
    approved_by_id[strategy_id] = found
    save_json(CANDIDATES_FILE, candidates)
    save_json(APPROVED_FILE, list(approved_by_id.values()))
    _append_promotion_log("APPROVE", strategy_id, reviewer, notes)
    _write_approved_manifest(list(approved_by_id.values()))
    return True


def reject_strategy(strategy_id: str, reviewer: str = "Garima", notes: str = "") -> bool:
    candidates = load_json(CANDIDATES_FILE, default=[])
    found = False
    for candidate in candidates:
        if candidate["id"] == strategy_id:
            candidate["status"] = "REJECTED"
            candidate["reviewed_by"] = reviewer
            candidate["review_date"] = datetime.now().isoformat()
            candidate["review_notes"] = notes
            found = True
            break

    if not found:
        return False

    save_json(CANDIDATES_FILE, candidates)
    _append_promotion_log("REJECT", strategy_id, reviewer, notes)
    return True


def revoke_strategy(strategy_id: str, reviewer: str = "Garima", notes: str = "") -> bool:
    approved = load_json(APPROVED_FILE, default=[])
    original_len = len(approved)
    approved = [item for item in approved if item["id"] != strategy_id]
    if len(approved) == original_len:
        return False

    save_json(APPROVED_FILE, approved)
    _append_promotion_log("REVOKE", strategy_id, reviewer, notes)
    _write_approved_manifest(approved)
    return True


def get_approved_strategies() -> list[dict]:
    return load_json(APPROVED_FILE, default=[])


def get_pending_candidates() -> list[dict]:
    return [item for item in load_json(CANDIDATES_FILE, default=[]) if item.get("status") == "PENDING"]


def can_promote_live(strategy_id: str) -> bool:
    for item in load_json(CANDIDATES_FILE, default=[]):
        if item.get("id") != strategy_id:
            continue
        return item.get("oos_status") in {"PASS", "STRONG"} and item.get("promotion_gate") == "LIVE_ELIGIBLE"
    return False


def get_promotion_report() -> str:
    candidates = load_json(CANDIDATES_FILE, default=[])
    approved = load_json(APPROVED_FILE, default=[])
    pending = [item for item in candidates if item.get("status") == "PENDING"]
    rejected = [item for item in candidates if item.get("status") == "REJECTED"]

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("STRATEGY PROMOTION REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)
    lines.append(f"Total candidates: {len(candidates)}")
    lines.append(f"Approved: {len(approved)}")
    lines.append(f"Pending: {len(pending)}")
    lines.append(f"Rejected: {len(rejected)}")

    if approved:
        lines.append("\n--- APPROVED ---")
        for item in sorted(approved, key=lambda x: -x["score"]):
            metrics = item["metrics"]
            flags = f" [{', '.join(item['flags'])}]" if item["flags"] else ""
            lines.append(
                f"{item['strategy']} {item['asset']} {item['timeframe']} "
                f"| {item['tier']} | Score {item['score']} | CAGR {metrics['cagr_pct']}% | GDD {metrics['gdd_pct']}%{flags}"
            )

    if pending:
        lines.append("\n--- PENDING REVIEW ---")
        for item in sorted(pending, key=lambda x: -x["score"])[:20]:
            metrics = item["metrics"]
            flags = f" [{', '.join(item['flags'])}]" if item["flags"] else ""
            lines.append(
                f"{item['id']} | {item['tier']} | Score {item['score']} | "
                f"CAGR {metrics['cagr_pct']}% | GDD {metrics['gdd_pct']}%{flags}"
            )

    return "\n".join(lines)


def is_strategy_approved(strategy: str, asset: str | None = None, timeframe: str | None = None) -> bool:
    """
    Check whether a strategy is present in the approved manifest.

    Matching is exact on strategy and tolerant on asset naming so webhook symbols
    like BTCUSDT can match approved assets recorded as BTC.
    """
    strategy = (strategy or "").strip()
    asset_norm = _normalize_asset(asset or "")
    timeframe = (timeframe or "").strip()

    for approved in get_approved_strategies():
        if approved.get("strategy") != strategy:
            continue

        approved_asset = _normalize_asset(approved.get("asset", ""))
        approved_timeframe = str(approved.get("timeframe", "")).strip()

        asset_ok = not asset_norm or not approved_asset or approved_asset == asset_norm
        timeframe_ok = not timeframe or not approved_timeframe or approved_timeframe == timeframe
        if asset_ok and timeframe_ok:
            return True
    return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python strategy_promotion.py generate [csv_path]")
        print("  python strategy_promotion.py report")
        print("  python strategy_promotion.py approve <id> [notes]")
        print("  python strategy_promotion.py reject <id> [notes]")
        print("  python strategy_promotion.py revoke <id> [notes]")
        print("  python strategy_promotion.py list-approved")
        print("  python strategy_promotion.py list-pending")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "generate":
        csv_path = sys.argv[2] if len(sys.argv) > 2 else None
        candidates = generate_candidates(source_csv_path=csv_path)
        print(f"Generated {len(candidates)} candidates")
        print(f"Review report written to: {REVIEW_REPORT_FILE}")

    elif cmd == "report":
        print(get_promotion_report())

    elif cmd == "approve" and len(sys.argv) >= 3:
        print(approve_strategy(sys.argv[2], notes=" ".join(sys.argv[3:])))

    elif cmd == "reject" and len(sys.argv) >= 3:
        print(reject_strategy(sys.argv[2], notes=" ".join(sys.argv[3:])))

    elif cmd == "revoke" and len(sys.argv) >= 3:
        print(revoke_strategy(sys.argv[2], notes=" ".join(sys.argv[3:])))

    elif cmd == "list-approved":
        for item in get_approved_strategies():
            print(item["id"])

    elif cmd == "list-pending":
        for item in get_pending_candidates():
            print(item["id"])
