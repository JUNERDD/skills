#!/usr/bin/env python3
"""Estimate the vidIQ credits an analysis will spend and compare them with the current balance.

Usage:
    python3 scripts/credit_plan.py --balance 148 \
        --call vidiq_video_transcript \
        --call vidiq_video_watch:optional \
        --call vidiq_channel_performance_trends \
        --call vidiq_video_comments=3:optional

Each --call is `tool[=count][:optional]`. optional means the call can be dropped or downgraded
when the balance is short.
The unit price in the tool description ("Cost: N credit(s)") is authoritative; when it differs
from the default table below, override it with --cost tool=N.

When the user has set a spending limit, pass it with --cap. If that limit applies to a whole
billing period rather than to this task, also pass --spent with the credits already used in the
period (estimate: maxRenewableCredits - renewableCredits). A plan within the cap counts as approved.

Verdicts:
    OK            planned spend + reserve <= balance and within --confirm-ratio of the balance,
                  or within the user's cap
    CONFIRM       affordable, but a large share of the balance or includes an expensive tool; ask first
    INSUFFICIENT  exceeds the balance or the user's cap; lists optional calls to cut, highest unit cost first
"""
from __future__ import annotations

import argparse
import json
import sys

# Unit prices observed in 2026-09. vidIQ may change them; the runtime tool description wins.
DEFAULT_COSTS = {
    "vidiq_balance": 0, "vidiq_job_poll": 0, "vidiq_jobs_list": 0, "vidiq_user_channels": 0,
    "vidiq_submit_feedback": 0, "vidiq_trend_categories": 0,
    "vidiq_video_watch": 25,
    "vidiq_watch_shortform_content": 10,
    # verified against the tool descriptions in 2026-09: all 5
    "vidiq_video_transcript": 5, "vidiq_channel_stats": 5, "vidiq_channel_performance_trends": 5,
    "vidiq_video_stats": 5, "vidiq_video_comments": 5, "vidiq_outliers": 5, "vidiq_channel_videos": 5,
    "vidiq_channel_analytics": 5, "vidiq_get_videos_by_ids": 5, "vidiq_score_title": 5,
}
STANDARD_COST = 5  # most other data tools cost 5
EXPENSIVE = 20     # a single call at or above this is expensive and needs confirmation


def parse_call(spec: str) -> dict:
    optional = spec.endswith(":optional")
    spec = spec[: -len(":optional")] if optional else spec
    name, _, count = spec.partition("=")
    return {"tool": name.strip(), "count": int(count) if count else 1, "optional": optional}


def plan(calls, balance, reserve, confirm_ratio, costs, cap=None, spent=0):
    rows, total = [], 0
    for c in calls:
        unit = costs.get(c["tool"], DEFAULT_COSTS.get(c["tool"], STANDARD_COST))
        known = c["tool"] in costs or c["tool"] in DEFAULT_COSTS
        sub = unit * c["count"]
        total += sub
        rows.append({**c, "unit": unit, "subtotal": sub, "unit_assumed": not known})

    result = {"rows": rows, "total": total, "balance": balance, "reserve": reserve}
    if balance is None:
        result["verdict"] = "UNKNOWN_BALANCE"
        return result
    result["remaining_after"] = balance - total
    has_expensive = any(r["unit"] >= EXPENSIVE for r in rows)
    # take the tighter of two limits: the account balance (minus reserve) and the user's own cap
    need = total + reserve - balance
    if cap is not None:
        result["cap"], result["spent_this_cycle"] = cap, spent
        result["cap_left_after"] = cap - spent - total
        need = max(need, total - (cap - spent))
    if need > 0:
        result["verdict"] = "INSUFFICIENT"
        cuts, freed = [], 0
        for r in sorted((r for r in rows if r["optional"]), key=lambda r: -r["unit"]):
            for _ in range(r["count"]):
                if freed >= need:
                    break
                cuts.append(r["tool"])
                freed += r["unit"]
        result["shortfall"] = need
        result["suggested_cuts"] = cuts
        result["cuts_enough"] = freed >= need
    elif cap is not None:
        result["verdict"] = "OK"  # within a cap the user set, so already approved
    elif total > balance * confirm_ratio or has_expensive:
        result["verdict"] = "CONFIRM"
    else:
        result["verdict"] = "OK"
    return result


def render(res) -> str:
    out = ["| Tool | Count | Unit | Subtotal | Optional |", "|---|---|---|---|---|"]
    for r in res["rows"]:
        unit = f"{r['unit']}" + (" (default; check the tool description)" if r["unit_assumed"] else "")
        out.append(f"| {r['tool']} | {r['count']} | {unit} | {r['subtotal']} | {'yes' if r['optional'] else ''} |")
    out.append(f"\nPlanned spend: {res['total']} credits")
    if res["balance"] is None:
        out.append("No balance given: call vidiq_balance (free) first and pass totalCredits.")
        return "\n".join(out)
    out.append(f"Balance: {res['balance']}, reserve {res['reserve']}, left after the plan: {res['remaining_after']}")
    if "cap" in res:
        out.append(f"User cap: {res['cap']}, already spent in this period: {res['spent_this_cycle']}, cap left after the plan: {res['cap_left_after']}")
    v = res["verdict"]
    if v == "OK":
        out.append("Verdict: OK, within the user's cap; go ahead." if "cap" in res else "Verdict: OK, the balance is sufficient.")
    elif v == "CONFIRM":
        out.append("Verdict: CONFIRM, affordable but a large share of the balance or includes an expensive tool; ask the user first.")
    else:
        out.append(f"Verdict: INSUFFICIENT, short by {res['shortfall']}.")
        if res["suggested_cuts"]:
            out.append("Suggested cuts: " + ", ".join(res["suggested_cuts"])
                       + ("" if res["cuts_enough"] else " (still not enough after these cuts; use the YouTube Data API instead or wait for the credit reset)"))
        else:
            out.append("No optional calls to cut: use the YouTube Data API instead, or wait for the credit reset.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--call", action="append", default=[], help="tool[=count][:optional]")
    ap.add_argument("--balance", type=int, help="totalCredits returned by vidiq_balance")
    ap.add_argument("--reserve", type=int, default=10, help="credits kept back for retries and follow-up questions, default 10")
    ap.add_argument("--confirm-ratio", type=float, default=0.3,
                    help="ask for confirmation when the spend exceeds this share of the balance, default 0.3")
    ap.add_argument("--cost", action="append", default=[], help="override a unit price: tool=N")
    ap.add_argument("--cap", type=int, help="spending limit the user set")
    ap.add_argument("--spent", type=int, default=0, help="credits already spent in the billing period (only when the cap covers the whole period)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.call:
        ap.error("provide at least one --call")
    costs = {}
    for c in args.cost:
        k, _, v = c.partition("=")
        costs[k.strip()] = int(v)
    res = plan([parse_call(c) for c in args.call], args.balance, args.reserve, args.confirm_ratio, costs,
               args.cap, args.spent)
    print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else render(res))
    sys.exit(1 if res.get("verdict") == "INSUFFICIENT" else 0)


if __name__ == "__main__":
    main()
