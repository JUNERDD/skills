#!/usr/bin/env python3
"""Discover candidate channels for a brief by running a keyword matrix through YouTube Data API v3
search.list, then aggregating the hits by channel.

search.list costs 100 quota units per call (10,000 per project per day by default), so this is the
one step where API quota is a real budget. The script estimates the cost before calling anything and
refuses to run past --max-quota. Use --dry-run to see the estimate only.

Each query runs once per --duration and per page. Hits are aggregated by channel: a channel that
surfaces for many different queries is more likely to be centred on the topic than one that matched a
single keyword. Queries passed with --competitor are tagged separately, so channels that have covered
a competing or same-category product stand out for the screening step.

search.list does not filter by country or language: regionCode and relevanceLanguage only bias the
ranking. Verify country and language in screen_channels.py.

Usage:
    python3 scripts/discover_channels.py --dry-run --region BR --language pt \
        --query "claude code" --query "programação com IA" --competitor "Wispr Flow"
    python3 scripts/discover_channels.py --region BR --language pt --queries-file queries.txt \
        --competitor "Wispr Flow" --published-within-days 90 --out yt-analysis/sourcing/discovery

Writes to <out>/: discovery.json, discovery.md, channels.txt (channel IDs ranked, ready for
screen_channels.py --channels-file), fetch_log.json
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytapi import QUOTA_COST, ApiError, Client, find_api_key  # noqa: E402

DURATIONS = ("any", "short", "medium", "long")


def read_queries(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", action="append", default=[], help="topic query; repeatable")
    ap.add_argument("--queries-file", help="one query per line; lines starting with # are ignored")
    ap.add_argument("--competitor", action="append", default=[],
                    help="name of a competing or same-category product; searched like a query and tagged separately")
    ap.add_argument("--region", help="regionCode, e.g. BR (biases ranking, does not filter)")
    ap.add_argument("--language", help="relevanceLanguage, e.g. pt (biases ranking, does not filter)")
    ap.add_argument("--duration", action="append", choices=DURATIONS,
                    help="videoDuration: short <4 min, medium 4-20 min, long >20 min; repeatable, "
                         "each value is a separate call. Default: medium and long")
    ap.add_argument("--published-within-days", type=int, default=90,
                    help="only videos published in the last N days, so inactive channels drop out; 0 = no limit")
    ap.add_argument("--pages", type=int, default=1, help="result pages per query and duration, 50 results each")
    ap.add_argument("--order", default="relevance", choices=("relevance", "date", "viewCount"))
    ap.add_argument("--exclude", action="append", default=[], help="channel ID to leave out; repeatable")
    ap.add_argument("--max-quota", type=int, default=3000,
                    help="refuse to run when the estimate exceeds this many units (default 3000)")
    ap.add_argument("--dry-run", action="store_true", help="print the quota estimate and exit")
    ap.add_argument("--out", default="yt-discovery")
    ap.add_argument("--env-file")
    args = ap.parse_args()

    queries = list(args.query) + (read_queries(args.queries_file) if args.queries_file else [])
    jobs = [(q, "topic") for q in dict.fromkeys(queries)] + [(c, "competitor") for c in dict.fromkeys(args.competitor)]
    if not jobs:
        ap.error("provide --query, --queries-file or --competitor")
    durations = args.duration or ["medium", "long"]
    calls = len(jobs) * len(durations) * args.pages
    estimate = calls * QUOTA_COST["search"]
    print(f"Plan: {len(jobs)} queries x {len(durations)} durations x {args.pages} page(s) = {calls} search calls, "
          f"about {estimate} quota units (default daily quota 10,000)")
    if args.dry_run:
        return
    if estimate > args.max_quota:
        sys.exit(f"Estimate {estimate} exceeds --max-quota {args.max_quota}. Cut queries, durations or pages, "
                 f"or raise --max-quota after checking today's remaining quota.")

    key, _ = find_api_key(args.env_file)
    if not key:
        sys.exit("YOUTUBE_API_KEY not found; run scripts/preflight.py to see how to set it up")
    client = Client(key)
    after = None
    if args.published_within_days:
        after = (datetime.now(timezone.utc) - timedelta(days=args.published_within_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    channels, excluded = {}, set(args.exclude)
    try:
        for q, kind in jobs:
            for dur in durations:
                token = None
                for _ in range(args.pages):
                    params = dict(part="snippet", q=q, type="video", maxResults=50, order=args.order)
                    if dur != "any":
                        params["videoDuration"] = dur
                    for k, v in (("regionCode", args.region), ("relevanceLanguage", args.language),
                                 ("publishedAfter", after), ("pageToken", token)):
                        if v:
                            params[k] = v
                    r = client.get("search", **params)
                    for it in r.get("items", []):
                        s, vid = it["snippet"], it["id"].get("videoId")
                        cid = s.get("channelId")
                        if not cid or not vid or cid in excluded:
                            continue
                        c = channels.setdefault(cid, {"channel_id": cid, "title": html.unescape(s.get("channelTitle", "")),
                                                      "topic_queries": set(), "competitor_queries": set(), "videos": {}})
                        (c["topic_queries"] if kind == "topic" else c["competitor_queries"]).add(q)
                        c["videos"].setdefault(vid, {"id": vid, "title": html.unescape(s.get("title", "")),
                                                     "published": s.get("publishedAt", "")[:10], "matched": dur})
                    token = r.get("nextPageToken")
                    if not token:
                        break
                print(f"  {kind}: {q!r} [{dur}] -> {len(channels)} channels so far", file=sys.stderr)
    except ApiError as e:
        print(f"YouTube API error: {e}. Saving what was collected so far.", file=sys.stderr)

    ranked = sorted(channels.values(),
                    key=lambda c: (-len(c["competitor_queries"]), -len(c["topic_queries"]), -len(c["videos"])))
    out = [{"channel_id": c["channel_id"], "title": c["title"],
            "topic_queries": sorted(c["topic_queries"]), "competitor_queries": sorted(c["competitor_queries"]),
            "distinct_topic_queries": len(c["topic_queries"]), "matched_videos": len(c["videos"]),
            "example_videos": sorted(c["videos"].values(), key=lambda v: v["published"], reverse=True)[:5]}
           for c in ranked]

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "discovery.json"), "w", encoding="utf-8") as f:
        json.dump({"params": {k: v for k, v in vars(args).items() if k != "env_file"}, "queries": queries,
                   "competitors": args.competitor, "channels": out}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "channels.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(c["channel_id"] for c in out) + "\n")

    L = [f"# Channel discovery ({len(out)} channels)", "",
         f"- Region bias {args.region or 'none'}, language bias {args.language or 'none'}, durations {', '.join(durations)}, "
         f"published within {args.published_within_days or 'any'} days",
         "- Ranked by competitor-query hits, then distinct topic queries, then matched videos. "
         "Country and language are not verified yet; run screen_channels.py next.", "",
         "| # | Channel | Channel ID | Topic queries hit | Competitor queries hit | Matched videos | Latest matched video |",
         "|---|---|---|---|---|---|---|"]
    for i, c in enumerate(out, 1):
        ex = c["example_videos"][0] if c["example_videos"] else {}
        L.append(f"| {i} | {c['title']} | {c['channel_id']} | {c['distinct_topic_queries']} | "
                 f"{', '.join(c['competitor_queries']) or '-'} | {c['matched_videos']} | "
                 f"{ex.get('published', '')} {ex.get('title', '')[:60]} |")
    with open(os.path.join(args.out, "discovery.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(args.out, "fetch_log.json"), "w", encoding="utf-8") as f:
        json.dump({"fetched_at": datetime.now(timezone.utc).isoformat(), "quota_units_used": client.quota_used,
                   "search_calls": client.quota_used // QUOTA_COST["search"]}, f, indent=1)
    print(f"Done: {len(out)} channels, about {client.quota_used} quota units used -> {args.out}/")


if __name__ == "__main__":
    main()
