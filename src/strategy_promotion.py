"""
Strategy Promotion Pipeline — T07
Moves tournament/ML approval output to an offline reviewed artifact.

Flow:
1. Strategies tested on TV → results fed to system
2. System generates PROMOTION_CANDIDATE artifact (JSON + readable report)
3. Human reviews artifact → approves/rejects each strategy
4. Only APPROVED strategies go into the live deployment set
5. Live bot reads ONLY from approved_strategies.json

This prevents:
- Leaderboard changes directly affecting live execution
- Untested strategies accidentally reaching live
- Strategy drift without explicit approval
"""
import json
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE = os.path.join(ROOT, "storage")
CANDIDATES_FILE = os.path.join(STORAGE, "promotion_candidates.json")
APPROVED_FILE = os.path.join(STORAGE, "approved_strategies.json")
PROMOTION_LOG = os.path.join(STORAGE, "promotion_log.json")


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ══════════════════════════════════════════════════════════
# STEP 1: Generate promotion candidates from TV results
# ══════════════════════════════════════════════════════════
def generate_candidates(min_cagr=50, min_trades=50, max_gdd=25):
    """
    Read TV results CSV and generate promotion candidates.
    Only strategies meeting minimum criteria become candidates.
    """
    import pandas as pd

    csv_path = os.path.join(STORAGE, "tv_cagr_results.csv")
    if not os.path.exists(csv_path):
        print("No TV results CSV found.")
        return []

    df = pd.read_csv(csv_path)
    df = df[df["CAGR_Percent"] >= min_cagr]
    df = df[df["Total_Trades"] >= min_trades]
    df = df[abs(df["Gross_Drawdown_Percent"]) <= max_gdd]
    df = df.sort_values("CAGR_Percent", ascending=False)

    candidates = []
    for _, row in df.iterrows():
        cagr = float(row.get("CAGR_Percent", 0))
        wr = float(row.get("Win_Rate_Percent", 0))
        gdd = abs(float(row.get("Gross_Drawdown_Percent", 0)))
        pf = float(row.get("Profit_Factor", 0))
        trades = int(row.get("Total_Trades", 0))

        # Auto-score: weighted combination
        score = 0
        score += min(cagr / 100, 30)       # max 30 pts for CAGR
        score += min(pf * 2, 20)            # max 20 pts for PF
        score += min(wr * 0.2, 15)          # max 15 pts for WR
        score += max(0, 15 - gdd * 0.6)    # max 15 pts for low GDD
        score += min(trades / 50, 10)       # max 10 pts for trade count
        score += min(float(row.get("Sharpe_Ratio", 0)) * 3, 10)  # max 10 pts for Sharpe

        # Risk flags
        flags = []
        if wr > 80:
            flags.append("HIGH_WR")
        if gdd > 15:
            flags.append("HIGH_GDD")
        if trades < 100:
            flags.append("LOW_TRADES")
        if pf > 15:
            flags.append("UNUSUAL_PF")

        # Tier assignment
        if cagr >= 500 and gdd < 10 and wr >= 60:
            tier = "TIER_1_DEPLOY"
        elif cagr >= 200 and gdd < 15 and wr >= 55:
            tier = "TIER_1"
        elif cagr >= 50 and gdd < 25 and wr >= 50:
            tier = "TIER_2"
        else:
            tier = "PAPER_TRADE"

        candidates.append({
            "id": f"{row.get('Strategy', '')}_{row.get('Asset', '')}_{row.get('Timeframe', '4h')}",
            "strategy": str(row.get("Strategy", "")),
            "asset": str(row.get("Asset", "")),
            "timeframe": str(row.get("Timeframe", "4h")),
            "cagr_pct": round(cagr, 2),
            "roi_per_day_pct": round(float(row.get("ROI_Per_Day_Pct", 0)), 4),
            "win_rate": round(wr, 2),
            "profit_factor": round(pf, 2),
            "sharpe": round(float(row.get("Sharpe_Ratio", 0)), 2),
            "gdd_pct": round(gdd, 2),
            "max_dd_pct": round(abs(float(row.get("Max_Drawdown_Percent", 0))), 2),
            "trades": trades,
            "score": round(score, 1),
            "tier": tier,
            "flags": flags,
            "status": "PENDING",  # PENDING → APPROVED / REJECTED
            "reviewed_by": None,
            "review_date": None,
            "review_notes": "",
            "params": {
                "sl_pct": 1.5,
                "tp_pct": 12.0,
                "trail_pct": 4.0,
                "position_size_pct": 10.0,  # realistic sizing
                "adx_filter": 20,
                "volume_filter": True,
                "max_trades_day": 3,
                "cooldown_bars": 6,
                "circuit_breaker_pct": -3.0,
            },
            "generated_at": datetime.now().isoformat(),
        })

    # Save candidates
    save_json(CANDIDATES_FILE, candidates)
    print(f"Generated {len(candidates)} promotion candidates")
    return candidates


# ══════════════════════════════════════════════════════════
# STEP 2: Review & approve/reject candidates
# ══════════════════════════════════════════════════════════
def approve_strategy(strategy_id, reviewer="Garima", notes=""):
    """Approve a strategy for live deployment."""
    candidates = load_json(CANDIDATES_FILE)
    approved = load_json(APPROVED_FILE)
    log = load_json(PROMOTION_LOG)

    found = False
    for c in candidates:
        if c["id"] == strategy_id:
            c["status"] = "APPROVED"
            c["reviewed_by"] = reviewer
            c["review_date"] = datetime.now().isoformat()
            c["review_notes"] = notes

            # Add to approved list (avoid duplicates)
            existing_ids = {a["id"] for a in approved}
            if c["id"] not in existing_ids:
                approved.append(c)

            # Log the action
            log.append({
                "action": "APPROVE",
                "strategy_id": strategy_id,
                "reviewer": reviewer,
                "timestamp": datetime.now().isoformat(),
                "notes": notes,
            })

            found = True
            break

    if not found:
        print(f"Strategy {strategy_id} not found in candidates")
        return False

    save_json(CANDIDATES_FILE, candidates)
    save_json(APPROVED_FILE, approved)
    save_json(PROMOTION_LOG, log)
    print(f"APPROVED: {strategy_id} by {reviewer}")
    return True


def reject_strategy(strategy_id, reviewer="Garima", notes=""):
    """Reject a strategy — will not be deployed."""
    candidates = load_json(CANDIDATES_FILE)
    log = load_json(PROMOTION_LOG)

    for c in candidates:
        if c["id"] == strategy_id:
            c["status"] = "REJECTED"
            c["reviewed_by"] = reviewer
            c["review_date"] = datetime.now().isoformat()
            c["review_notes"] = notes

            log.append({
                "action": "REJECT",
                "strategy_id": strategy_id,
                "reviewer": reviewer,
                "timestamp": datetime.now().isoformat(),
                "notes": notes,
            })
            break

    save_json(CANDIDATES_FILE, candidates)
    save_json(PROMOTION_LOG, log)
    print(f"REJECTED: {strategy_id}")
    return True


def revoke_strategy(strategy_id, reviewer="Garima", notes=""):
    """Remove a previously approved strategy from live set."""
    approved = load_json(APPROVED_FILE)
    log = load_json(PROMOTION_LOG)

    approved = [a for a in approved if a["id"] != strategy_id]

    log.append({
        "action": "REVOKE",
        "strategy_id": strategy_id,
        "reviewer": reviewer,
        "timestamp": datetime.now().isoformat(),
        "notes": notes,
    })

    save_json(APPROVED_FILE, approved)
    save_json(PROMOTION_LOG, log)
    print(f"REVOKED: {strategy_id}")
    return True


# ══════════════════════════════════════════════════════════
# STEP 3: Get live deployment set (only approved strategies)
# ══════════════════════════════════════════════════════════
def get_approved_strategies():
    """Return only approved strategies — this is what the live bot should read."""
    return load_json(APPROVED_FILE)


def get_pending_candidates():
    """Return strategies awaiting review."""
    candidates = load_json(CANDIDATES_FILE)
    return [c for c in candidates if c["status"] == "PENDING"]


def get_promotion_report():
    """Generate human-readable promotion report."""
    candidates = load_json(CANDIDATES_FILE)
    approved = load_json(APPROVED_FILE)

    pending = [c for c in candidates if c["status"] == "PENDING"]
    rejected = [c for c in candidates if c["status"] == "REJECTED"]

    report = []
    report.append("=" * 60)
    report.append("STRATEGY PROMOTION REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 60)
    report.append(f"\nTotal candidates: {len(candidates)}")
    report.append(f"Approved: {len(approved)}")
    report.append(f"Pending: {len(pending)}")
    report.append(f"Rejected: {len(rejected)}")

    if approved:
        report.append("\n--- APPROVED (LIVE READY) ---")
        for a in sorted(approved, key=lambda x: -x["score"]):
            flags_str = f" [{', '.join(a['flags'])}]" if a["flags"] else ""
            report.append(
                f"  [{a['tier']}] {a['strategy']} on {a['asset']} {a['timeframe']} "
                f"— CAGR {a['cagr_pct']}% GDD {a['gdd_pct']}% Score {a['score']}/100{flags_str}"
            )

    if pending:
        report.append(f"\n--- PENDING REVIEW ({len(pending)}) ---")
        for p in sorted(pending, key=lambda x: -x["score"])[:20]:
            flags_str = f" [{', '.join(p['flags'])}]" if p["flags"] else ""
            report.append(
                f"  [{p['tier']}] {p['strategy']} on {p['asset']} {p['timeframe']} "
                f"— CAGR {p['cagr_pct']}% GDD {p['gdd_pct']}% Score {p['score']}/100{flags_str}"
                f"\n    ID: {p['id']}"
            )

    return "\n".join(report)


# ══════════════════════════════════════════════════════════
# CLI interface
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python strategy_promotion.py generate        — create candidates from TV results")
        print("  python strategy_promotion.py report          — show promotion report")
        print("  python strategy_promotion.py approve <id>    — approve a strategy")
        print("  python strategy_promotion.py reject <id>     — reject a strategy")
        print("  python strategy_promotion.py revoke <id>     — revoke approved strategy")
        print("  python strategy_promotion.py list-approved   — list live deployment set")
        print("  python strategy_promotion.py list-pending    — list awaiting review")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "generate":
        candidates = generate_candidates()
        print(f"\n{len(candidates)} candidates generated. Run 'report' to review.")

    elif cmd == "report":
        print(get_promotion_report())

    elif cmd == "approve":
        if len(sys.argv) < 3:
            print("Usage: approve <strategy_id> [notes]")
        else:
            notes = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
            approve_strategy(sys.argv[2], notes=notes)

    elif cmd == "reject":
        if len(sys.argv) < 3:
            print("Usage: reject <strategy_id> [notes]")
        else:
            notes = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
            reject_strategy(sys.argv[2], notes=notes)

    elif cmd == "revoke":
        if len(sys.argv) < 3:
            print("Usage: revoke <strategy_id>")
        else:
            revoke_strategy(sys.argv[2])

    elif cmd == "list-approved":
        approved = get_approved_strategies()
        for a in approved:
            print(f"  {a['strategy']} {a['asset']} {a['timeframe']} — CAGR {a['cagr_pct']}% | {a['tier']}")

    elif cmd == "list-pending":
        pending = get_pending_candidates()
        for p in pending:
            print(f"  [{p['tier']}] {p['id']} — CAGR {p['cagr_pct']}% Score {p['score']}")
