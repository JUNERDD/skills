#!/usr/bin/env python3
"""Screen a pool of candidate channels against a brief's scorecard with YouTube Data API v3, and write
one comparable row per channel.

For each channel it fetches the latest uploads and computes: country and dominant video language,
subscribers, recent long-form cadence, median views of the latest long-form videos (with P25-P75 and
views-to-subscribers), topic share of recent long-form titles, paid-promotion density, mentions of
the user's own brand or competitors in titles and descriptions, and public contact emails written in
the channel or video descriptions. Hard thresholds mark channels as excluded with the reason, so
nothing disappears silently.

Cost: about 2-3 quota units per channel (handle lookup 1, uploads playlist 1, video details 1 per
50 videos). Channel IDs are looked up 50 per unit, so prefer the channels.txt from discover_channels.py.

Emails behind YouTube's "View email address" button are never returned by the API. Do not guess
addresses; mark them for the user to reveal manually.

Usage:
    python3 scripts/screen_channels.py --channels-file yt-analysis/sourcing/discovery/channels.txt \
        --country BR --language pt --active-days 30 --min-subs 5000 \
        --topic "claude,codex,cursor,vibe coding,agente,IA" --brand Typeless \
        --competitor "Wispr Flow,SuperWhisper" --out yt-analysis/sourcing/screening
    python3 scripts/screen_channels.py --channel @SomeCreator --channel UCxxxx... --out screening

Writes to <out>/: screening.csv, screening.md, screening.json, fetch_log.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_metrics import baseline, channel_language, sponsorship_scan, video_row, view_metric_check  # noqa: E402
from fetch_youtube import CHANNEL_PARTS, get_videos, list_uploads  # noqa: E402
from ytapi import ApiError, Client, find_api_key, parse_channel  # noqa: E402

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EMAIL_JUNK = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", "example.", "domain.com", "email.com", "sentry")


def fold(text: str) -> str:
    """Lowercase and strip accents so 'programação' matches 'programacao'."""
    return "".join(c for c in unicodedata.normalize("NFKD", (text or "").lower()) if not unicodedata.combining(c))


def terms(values: list[str]) -> list[str]:
    return [fold(t.strip()) for v in values for t in v.split(",") if t.strip()]


def term_hit(text: str, ts: list[str]) -> list[str]:
    f = fold(text)
    return [t for t in ts if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", f)]


def emails_in(text: str) -> list[str]:
    return [e.strip(".") for e in EMAIL_RE.findall(text or "") if not any(j in e.lower() for j in EMAIL_JUNK)]


def read_specs(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [l.split()[0] for l in f if l.strip() and not l.lstrip().startswith("#")]


def resolve(client: Client, specs: list[str]) -> tuple[list[dict], list[str]]:
    ids, others, unresolved = [], [], []
    for s in dict.fromkeys(specs):
        kind, value = parse_channel(s)
        (ids if kind == "id" else others).append((kind, value, s))
    found = []
    for i in range(0, len(ids), 50):
        chunk = [v for _, v, _ in ids[i:i + 50]]
        items = client.get("channels", part=CHANNEL_PARTS, id=",".join(chunk)).get("items", [])
        found += items
        got = {c["id"] for c in items}
        unresolved += [s for _, v, s in ids[i:i + 50] if v not in got]
    for kind, value, s in others:
        if kind == "custom":
            # /c/ URLs need search.list (100 units); ask for the UC... ID or @handle instead
            unresolved.append(s + " (custom /c/ URL: pass the @handle or UC... ID)")
            continue
        r = client.get("channels", part=CHANNEL_PARTS, **({"forHandle": value} if kind == "handle" else {"forUsername": value}))
        if r.get("items"):
            found.append(r["items"][0])
        else:
            unresolved.append(s)
    return found, unresolved


def screen(ch: dict, videos: list[dict], a, now) -> dict:
    s, st = ch["snippet"], ch.get("statistics", {})
    subs = int(st.get("subscriberCount", 0) or 0)
    rows = sorted((video_row(v, now) for v in videos), key=lambda r: r["published"], reverse=True)
    long_rows = [r for r in rows if r["format"] == "long"]
    recent_long = long_rows[:a.baseline_long]
    base = baseline(recent_long, "long")
    lang = channel_language(videos)
    topic_ts, brand_ts, comp_ts = terms(a.topic), terms(a.brand), terms(a.competitor)
    topic_share = (round(100 * sum(bool(term_hit(r["title"], topic_ts)) for r in recent_long) / len(recent_long))
                   if topic_ts and recent_long else None)

    brand_hits, comp_hits, emails = [], [], {}
    for e in emails_in(s.get("description", "")):
        emails.setdefault(e, "channel description")
    for v in videos:
        text = v["snippet"]["title"] + "\n" + v["snippet"].get("description", "")
        ref = f"{v['snippet']['publishedAt'][:10]} {v['snippet']['title'][:50]} (youtu.be/{v['id']})"
        if term_hit(text, brand_ts):
            brand_hits.append(ref)
        hit = term_hit(text, comp_ts)
        if hit:
            comp_hits.append(f"{'/'.join(hit)}: {ref}")
        for e in emails_in(v["snippet"].get("description", "")):
            emails.setdefault(e, f"video description youtu.be/{v['id']}")

    days_since_long = round(long_rows[0]["age_days"]) if long_rows else None
    sponsors = sponsorship_scan(videos, [])
    vcheck = view_metric_check(rows, [])

    reasons = []
    country = s.get("country")
    if a.country and country and country not in a.country:
        reasons.append(f"country {country}")
    if a.country and not country and a.require_country:
        reasons.append("country not set")
    if a.language and lang["code"] and lang["code"] not in a.language:
        reasons.append(f"language {lang['code']}")
    if a.min_subs and subs < a.min_subs:
        reasons.append(f"subscribers < {a.min_subs:,}")
    if a.max_subs and subs > a.max_subs:
        reasons.append(f"subscribers > {a.max_subs:,}")
    if a.active_days and (days_since_long is None or days_since_long > a.active_days):
        reasons.append(f"no long-form video in {a.active_days} days")
    if a.min_median_views and (not base or base["median_views"] < a.min_median_views):
        reasons.append(f"median long-form views < {a.min_median_views:,}")
    if a.min_topic_share and (topic_share or 0) < a.min_topic_share:
        reasons.append(f"topic share < {a.min_topic_share}%")

    flags = []
    if a.country and not country:
        flags.append("country not set: verify")
    if a.language and not lang["code"]:
        flags.append("language not tagged: verify from titles")
    if brand_hits:
        flags.append("already covered our brand")
    if comp_hits:
        flags.append("covered a competitor: ask about exclusivity")
    if vcheck.get("warning"):
        flags.append(f"views inflated ~{vcheck['estimated_inflation']}x after the "
                     f"{vcheck['rollout_window'][0]}..{vcheck['rollout_window'][1]} view-rule rollout")

    return {
        "status": "excluded" if reasons else "pass", "exclude_reasons": "; ".join(reasons), "flags": "; ".join(flags),
        "title": s["title"], "handle": s.get("customUrl", ""), "channel_id": ch["id"],
        "url": f"https://www.youtube.com/{s['customUrl']}" if s.get("customUrl") else f"https://www.youtube.com/channel/{ch['id']}",
        "country": country or "", "language": lang["code"] or "", "subscribers": subs,
        "videos_fetched": len(rows), "long_videos_fetched": len(long_rows),
        "long_uploads_30d": sum(1 for r in long_rows if r["age_days"] <= 30),
        "days_since_last_long": days_since_long,
        "median_long_views": base["median_views"] if base else None,
        "p25_long_views": base["p25_views"] if base else None, "p75_long_views": base["p75_views"] if base else None,
        "views_to_subs_pct": round(100 * base["median_views"] / subs, 1) if base and subs else None,
        "median_engagement_pct": base["median_engagement_pct"] if base else None,
        "topic_share_pct": topic_share,
        "paid_flag_videos": sponsors["videos_with_paid_flag"],
        "top_external_domains": ", ".join(d["domain"] for d in sponsors["external_domains"][:5]),
        "brand_hits": " | ".join(brand_hits[:5]), "competitor_hits": " | ".join(comp_hits[:5]),
        "public_emails": ", ".join(emails), "email_sources": " | ".join(f"{e}: {src}" for e, src in emails.items()),
        "latest_long_titles": " | ".join(f"{r['published']} {r['title'][:60]}" for r in long_rows[:5]),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--channel", action="append", default=[], help="@handle, channel URL or UC... ID; repeatable")
    ap.add_argument("--channels-file", help="one channel spec per line, e.g. channels.txt from discover_channels.py")
    ap.add_argument("--limit", type=int, default=0, help="screen only the first N channels from the inputs")
    ap.add_argument("--uploads", type=int, default=30, help="latest uploads fetched per channel, default 30")
    ap.add_argument("--baseline-long", type=int, default=10, help="latest long-form videos used for the median, default 10")
    ap.add_argument("--country", action="append", help="allowed channel country code, e.g. BR; repeatable")
    ap.add_argument("--require-country", action="store_true", help="exclude channels that do not set a country")
    ap.add_argument("--language", action="append", help="allowed dominant video language, e.g. pt; repeatable")
    ap.add_argument("--min-subs", type=int, default=0)
    ap.add_argument("--max-subs", type=int, default=0)
    ap.add_argument("--active-days", type=int, default=0, help="exclude when the latest long-form video is older")
    ap.add_argument("--min-median-views", type=int, default=0)
    ap.add_argument("--topic", action="append", default=[],
                    help="comma-separated terms that mark an on-topic title (accent-insensitive); repeatable")
    ap.add_argument("--min-topic-share", type=int, default=0, help="exclude when fewer recent long-form titles are on topic (percent)")
    ap.add_argument("--brand", action="append", default=[], help="our own product names to look for; comma-separated")
    ap.add_argument("--competitor", action="append", default=[], help="competing product names to look for; comma-separated")
    ap.add_argument("--max-quota", type=int, default=1000, help="refuse to run when the estimate exceeds this, default 1000")
    ap.add_argument("--out", default="yt-screening")
    ap.add_argument("--env-file")
    a = ap.parse_args()

    specs = list(a.channel) + (read_specs(a.channels_file) if a.channels_file else [])
    specs = list(dict.fromkeys(specs))
    if a.limit:
        specs = specs[:a.limit]
    if not specs:
        ap.error("provide --channel or --channels-file")
    n_ids = sum(1 for s in specs if parse_channel(s)[0] == "id")
    per_channel_pages = -(-a.uploads // 50)
    estimate = -(-n_ids // 50) + (len(specs) - n_ids) + len(specs) * per_channel_pages + -(-len(specs) * a.uploads // 50)
    print(f"Plan: screen {len(specs)} channels, about {estimate} quota units", file=sys.stderr)
    if estimate > a.max_quota:
        sys.exit(f"Estimate {estimate} exceeds --max-quota {a.max_quota}; use --limit or raise --max-quota")

    key, _ = find_api_key(a.env_file)
    if not key:
        sys.exit("YOUTUBE_API_KEY not found; run scripts/preflight.py to see how to set it up")
    client = Client(key)
    now = datetime.now(timezone.utc)
    try:
        channels, unresolved = resolve(client, specs)
        uploads = {c["id"]: list_uploads(client, c["contentDetails"]["relatedPlaylists"]["uploads"], a.uploads)
                   for c in channels}
        all_ids = [v for ids in uploads.values() for v in ids]
        by_id = {v["id"]: v for v in get_videos(client, all_ids)}
    except ApiError as e:
        sys.exit(f"YouTube API error: {e}. Run scripts/preflight.py to diagnose")

    results = [screen(c, [by_id[v] for v in uploads[c["id"]] if v in by_id], a, now) for c in channels]
    results.sort(key=lambda r: (r["status"] != "pass", -(r["median_long_views"] or 0)))

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "screening.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": now.isoformat(), "criteria": {k: v for k, v in vars(a).items() if k != "env_file"},
                   "unresolved": unresolved, "channels": results}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "screening.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else ["status"])
        w.writeheader()
        w.writerows(results)

    passed = [r for r in results if r["status"] == "pass"]
    excluded = [r for r in results if r["status"] != "pass"]
    fmt = lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else "-"  # noqa: E731
    L = [f"# Channel screening: {len(passed)} pass, {len(excluded)} excluded, {len(unresolved)} unresolved", "",
         f"- Generated {now:%Y-%m-%d}. Median views use the latest {a.baseline_long} long-form videos (>3 min).",
         "- Emails are only those written in descriptions; hidden business emails need the user to reveal them on YouTube.",
         "- YouTube API policy: refresh or delete stored data within 30 days.", "",
         "## Passed", "",
         "| # | Channel | Subs | Median long views (P25-P75) | Views/subs | Long in 30d | Topic share | Paid flags | Public email | Flags |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(passed, 1):
        L.append(f"| {i} | [{r['title']}]({r['url']}) | {fmt(r['subscribers'])} | {fmt(r['median_long_views'])} "
                 f"({fmt(r['p25_long_views'])}-{fmt(r['p75_long_views'])}) | {r['views_to_subs_pct'] or '-'}% | "
                 f"{r['long_uploads_30d']} | {'-' if r['topic_share_pct'] is None else str(r['topic_share_pct']) + '%'} | "
                 f"{r['paid_flag_videos']} | {r['public_emails'] or '-'} | {r['flags'] or '-'} |")
    if excluded:
        L += ["", "## Excluded", "", "| Channel | Subs | Reasons |", "|---|---|---|"]
        L += [f"| [{r['title']}]({r['url']}) | {fmt(r['subscribers'])} | {r['exclude_reasons']} |" for r in excluded]
    hits = [r for r in results if r["brand_hits"] or r["competitor_hits"]]
    if hits:
        L += ["", "## Brand and competitor mentions", ""]
        for r in hits:
            L.append(f"- **{r['title']}**: " + "; ".join(x for x in (
                r["brand_hits"] and f"our brand: {r['brand_hits']}", r["competitor_hits"] and f"competitors: {r['competitor_hits']}") if x))
    if unresolved:
        L += ["", "## Unresolved inputs", ""] + [f"- {u}" for u in unresolved]
    with open(os.path.join(a.out, "screening.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(a.out, "fetch_log.json"), "w", encoding="utf-8") as f:
        json.dump({"fetched_at": now.isoformat(), "quota_units_used": client.quota_used}, f, indent=1)
    print(f"Done: {len(passed)} pass, {len(excluded)} excluded, {len(unresolved)} unresolved, "
          f"about {client.quota_used} quota units used -> {a.out}/")


if __name__ == "__main__":
    main()
