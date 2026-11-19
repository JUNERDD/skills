#!/usr/bin/env python3
"""Turn the raw data from fetch_youtube.py into analysis metrics and a compact comment digest.

Writes to the same directory:
  summary.json        all metrics (machine-readable), including the full target descriptions
  summary.md          metric tables that can go straight into a report
  comments_digest.md  anonymized comments for audience and sentiment reading; far fewer tokens than raw JSON

The regex fields (promo_code_hints, disclosure_hints) are only cheap hints. The API's paid-promotion
flag is the reliable disclosure signal, and the agent should read the description text itself for
anything language- or context-dependent.

Usage:
    python3 scripts/analyze_metrics.py yt-data
    python3 scripts/analyze_metrics.py yt-data --recent-per-video 40 --text-limit 300
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytapi import iso_duration_seconds  # noqa: E402

URL_RE = re.compile(r"https?://[^\s)>\]]+")
TRACKING_RE = re.compile(r"[?&](utm_[a-z]+|via|ref|aff|affiliate|coupon|code|promo|fpr|sub_id|irclickid)=", re.I)
PROMO_RE = re.compile(r"\b(code|coupon|promo|discount)\b", re.I)
DISCLOSURE_RE = re.compile(r"(#ad\b|#sponsored|#\w+partner\b|#\w+sponsor\w*|\bsponsored\b|\bsponsoring\b|"
                           r"paid promotion|in partnership with|partnered with)", re.I)
CHAPTER_RE = re.compile(r"^\s*\(?(\d{1,2}:)?\d{1,2}:\d{2}\)?\s", re.M)
MENTION_RE = re.compile(r"@[\w.\-]+")
# the creator's own social or tool links, not sponsors
SOCIAL_DOMAINS = ("youtube.com", "youtu.be", "instagram.com", "tiktok.com", "twitter.com", "x.com", "facebook.com",
                  "linkedin.com", "linktr.ee", "threads.net", "discord.gg", "t.me", "whatsapp.com", "wa.me",
                  "patreon.com", "spotify.com", "apple.com", "google.com", "bit.ly", "beacons.ai", "substack.com")
# YouTube began counting public views from the first frame on 2026-08-24 and completed the global rollout by
# 2026-08-28 (long-form public views typically run 1.7-1.9x higher, varying by channel). Each channel switched
# on some day inside this window, so a long video published in it may be counted under either rule.
VIEW_RULE_ROLLOUT = ("2026-08-24", "2026-08-28")
# Title languages vidiq_outliers accepts. Its `language` defaults to "en" and filters by title
# language, so a non-English channel returns nothing unless the right code is passed.
OUTLIERS_LANGUAGES = {"en", "es", "ko", "de", "hi", "ar", "th", "pl", "it", "ja", "fr", "tr", "ru", "pt", "uk"}


def num(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def fmt_guess(seconds: int) -> str:
    # The API does not mark Shorts. <=60 s is almost always a Short; 61-180 s may be one (the limit became 3 min in 2024)
    return "short" if seconds <= 60 else "short?" if seconds <= 180 else "long"


def pct(a, b):
    return round(100 * a / b, 2) if b else None


def video_row(v, now):
    s, st = v["snippet"], v.get("statistics", {})
    dur = iso_duration_seconds(v.get("contentDetails", {}).get("duration", ""))
    pub = datetime.fromisoformat(s["publishedAt"].replace("Z", "+00:00"))
    age = max((now - pub).total_seconds() / 86400, 0.01)
    views, likes, comments = num(st.get("viewCount")), num(st.get("likeCount")), num(st.get("commentCount"))
    return {
        "id": v["id"], "title": s["title"], "published": s["publishedAt"][:10], "age_days": round(age, 1),
        "duration_s": dur, "format": fmt_guess(dur), "views": views, "likes": likes, "comments": comments,
        "likes_hidden": "likeCount" not in st,
        "paid_promotion": v.get("paidProductPlacementDetails", {}).get("hasPaidProductPlacement"),
        "engagement_pct": pct(likes + comments, views), "views_per_day": round(views / age, 1),
        "url": f"https://youtu.be/{v['id']}",
    }


def description_audit(desc: str) -> dict:
    urls = URL_RE.findall(desc or "")
    first_line = (desc or "").strip().splitlines()[0] if (desc or "").strip() else ""
    return {
        "chars": len(desc or ""),
        "text": (desc or "")[:5000],
        "first_line": first_line[:200],
        "urls": urls,
        "urls_with_tracking": [u for u in urls if TRACKING_RE.search(u)],
        "link_in_first_line": bool(URL_RE.search(first_line)),
        "promo_code_hints": [l.strip()[:160] for l in (desc or "").splitlines() if PROMO_RE.search(l)][:5],
        "disclosure_hints": sorted({m.group(0).lower() for m in DISCLOSURE_RE.finditer(desc or "")}),
        "has_chapters": len(CHAPTER_RE.findall(desc or "")) >= 3,
    }


def baseline(rows, fmt):
    group = [r for r in rows if (r["format"] == "long") == (fmt == "long")]
    views = [r["views"] for r in group]
    if not views:
        return None
    q = statistics.quantiles(views, n=4) if len(views) >= 4 else [min(views), statistics.median(views), max(views)]
    eng = [r["engagement_pct"] for r in group if r["engagement_pct"] is not None]
    return {"format": "long" if fmt == "long" else "short", "n": len(views),
            "median_views": statistics.median(views), "mean_views": round(statistics.mean(views)),
            "p25_views": q[0], "p75_views": q[-1],
            "median_engagement_pct": round(statistics.median(eng), 2) if eng else None,
            "median_age_days": statistics.median(r["age_days"] for r in group)}


def channel_language(videos) -> dict:
    """Most common video language (audio, else metadata) as an ISO 639-1 code, plus the value to pass
    as vidiq_outliers `language` (None when vidIQ does not support it)."""
    codes = [(v["snippet"].get("defaultAudioLanguage") or v["snippet"].get("defaultLanguage") or "")
             .split("-")[0].lower() for v in videos]
    codes = [c for c in codes if c and c != "zxx"]
    if not codes:
        return {"code": None, "videos_tagged": 0, "outliers_language": None}
    code = statistics.mode(codes)
    return {"code": code, "videos_tagged": len(codes), "share": round(codes.count(code) / len(codes), 2),
            "outliers_language": code if code in OUTLIERS_LANGUAGES else None}


def domain_of(url: str) -> str:
    host = re.sub(r"^https?://", "", url).split("/")[0].split("?")[0].lower()
    return host[4:] if host.startswith("www.") else host


def sponsorship_scan(videos, targets):
    """Scan recent videos for paid-promotion flags, disclosure hints and external link domains,
    to gauge sponsorship density, recurring sponsors and competitor deals."""
    domains, sponsored, n, flagged, hinted = {}, [], 0, 0, 0
    for v in videos:
        if v["id"] in targets:
            continue
        n += 1
        desc = v["snippet"].get("description", "")
        paid = v.get("paidProductPlacementDetails", {}).get("hasPaidProductPlacement")
        hint = bool(DISCLOSURE_RE.search(desc))
        flagged += bool(paid)
        hinted += hint
        if paid or hint:
            sponsored.append(v["snippet"]["title"][:60])
        for d in {domain_of(u) for u in URL_RE.findall(desc)}:
            if not any(d == s or d.endswith("." + s) for s in SOCIAL_DOMAINS):
                domains.setdefault(d, []).append(v["snippet"]["title"][:50])
    top = sorted(domains.items(), key=lambda kv: -len(kv[1]))[:20]
    return {"videos_scanned": n, "videos_with_paid_flag": flagged, "videos_with_disclosure_hint": hinted,
            "videos_sponsored_any_signal": len(sponsored), "sponsored_titles": sponsored[:15],
            "external_domains": [{"domain": d, "videos": len(t), "example": t[0]} for d, t in top]}


def view_metric_check(rows, targets):
    """When the baseline spans the view-rule rollout, compare long-form like/view before and after it to estimate
    the view inflation. Videos published inside the rollout window are left out of both groups because the
    channel may have switched on any day in it; their rates are returned so the channel's own break is visible."""
    start, end = VIEW_RULE_ROLLOUT
    long_rows = [r for r in rows if r["format"] == "long" and r["id"] not in targets and r["views"] and not r["likes_hidden"]]
    pre = [r["likes"] / r["views"] for r in long_rows if r["published"] < start]
    post = [r["likes"] / r["views"] for r in long_rows if r["published"] > end]
    window = sorted((r["published"], round(100 * r["likes"] / r["views"], 2))
                    for r in long_rows if start <= r["published"] <= end)
    res = {"rollout_window": [start, end], "pre_n": len(pre), "post_n": len(post),
           "window_excluded": [{"published": p, "like_rate_pct": x} for p, x in window]}
    if len(pre) >= 3 and len(post) >= 2:
        ratio = statistics.median(pre) / statistics.median(post) if statistics.median(post) else None
        res["like_rate_pre_pct"] = round(100 * statistics.median(pre), 2)
        res["like_rate_post_pct"] = round(100 * statistics.median(post), 2)
        res["estimated_inflation"] = round(ratio, 2) if ratio else None
        res["warning"] = bool(ratio and ratio > 1.3)
    return res


def comment_stats(data, channel_id, views, alias):
    threads = data.get("threads", [])
    top_by_others = [t for t in threads
                     if t["snippet"]["topLevelComment"]["snippet"].get("authorChannelId", {}).get("value") != channel_id]
    replied = 0
    creator_replies = 0
    reply_total = 0
    for t in threads:
        reps = t.get("replies", {}).get("comments", [])
        reply_total += len(reps)
        mine = [r for r in reps if r["snippet"].get("authorChannelId", {}).get("value") == channel_id]
        creator_replies += len(mine)
        if mine and t in top_by_others:
            replied += 1
    authors = set()
    for t in threads:
        a = t["snippet"]["topLevelComment"]["snippet"].get("authorChannelId", {}).get("value")
        if a and a != channel_id:
            authors.add(a)
            alias(a)
    return {"top_level": len(threads), "top_level_by_viewers": len(top_by_others), "replies": reply_total,
            "creator_replies": creator_replies,
            "creator_reply_rate_pct": pct(replied, len(top_by_others)),
            "unique_commenters": len(authors),
            "comments_per_1k_views": round(1000 * (len(threads) + reply_total) / views, 2) if views else None,
            "error": data.get("error"), "truncated": data.get("truncated", False)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data_dir")
    ap.add_argument("--recent-per-video", type=int, default=40,
                    help="max comments listed per recent video in the digest (by likes); target videos list all")
    ap.add_argument("--text-limit", type=int, default=300, help="max characters kept per comment")
    args = ap.parse_args()
    d = args.data_dir

    def load(name):
        with open(os.path.join(d, name), encoding="utf-8") as f:
            return json.load(f)

    ch, videos, sel, comments = load("channel.json"), load("videos.json"), load("selection.json"), load("comments.json")
    now = datetime.now(timezone.utc)
    channel_id = ch["id"]
    rows = [video_row(v, now) for v in videos]
    by_id = {r["id"]: r for r in rows}
    targets = [t for t in sel["targets"] if t in by_id]
    others = [r for r in rows if r["id"] not in targets]

    aliases = {}

    def alias(author_id):
        if author_id not in aliases:
            aliases[author_id] = f"U{len(aliases) + 1}"
        return aliases[author_id]

    cstats = {vid: comment_stats(c, channel_id, by_id.get(vid, {}).get("views", 0), alias)
              for vid, c in comments.items()}

    view_check = view_metric_check(rows, targets)
    sponsors = sponsorship_scan(videos, targets)

    target_reports = []
    for t in targets:
        r = by_id[t]
        base = baseline(others, r["format"])
        peers = sorted([o for o in others if (o["format"] == "long") == (r["format"] == "long")][:10] + [r],
                       key=lambda x: -x["views"])
        raw = next(v for v in videos if v["id"] == t)
        target_reports.append({
            **r,
            "vs_median_pct": pct(r["views"], base["median_views"]) if base else None,
            "rank_among_recent_10_plus_target": f"{peers.index(r) + 1}/{len(peers)}",
            "baseline": base,
            "age_warning": (base is not None and r["age_days"] < 0.5 * base["median_age_days"]),
            "description": description_audit(raw["snippet"].get("description", "")),
            "tags": raw["snippet"].get("tags", []),
            "language": raw["snippet"].get("defaultAudioLanguage") or raw["snippet"].get("defaultLanguage"),
            "thumbnail": max(raw["snippet"].get("thumbnails", {}).values(),
                             key=lambda x: x.get("width", 0), default={}).get("url"),
            "comment_stats": cstats.get(t),
        })

    s, st = ch["snippet"], ch.get("statistics", {})
    repeat = {}
    for vid, c in comments.items():
        for th in c.get("threads", []):
            a = th["snippet"]["topLevelComment"]["snippet"].get("authorChannelId", {}).get("value")
            if a and a != channel_id:
                repeat.setdefault(a, set()).add(vid)
    summary = {
        "generated_at": now.isoformat(),
        "channel": {"id": channel_id, "title": s["title"], "handle": s.get("customUrl"),
                    "country": s.get("country"), "created": s.get("publishedAt", "")[:10],
                    "subscribers": num(st.get("subscriberCount")), "subscribers_hidden": st.get("hiddenSubscriberCount"),
                    "total_views": num(st.get("viewCount")), "video_count": num(st.get("videoCount")),
                    "description": s.get("description", "")[:1500],
                    "topics": ch.get("topicDetails", {}).get("topicCategories", []),
                    "language": channel_language(videos)},
        "baseline_long": baseline(others, "long"),
        "baseline_short": baseline(others, "short"),
        "targets": target_reports,
        "view_metric_change": view_check,
        "sponsorship_scan": sponsors,
        "recent_ids": sel["recent"],
        "videos": rows,
        "comment_stats": cstats,
        "audience_sample": {"unique_commenters": len(repeat),
                            "commenters_on_2plus_videos": sum(1 for v in repeat.values() if len(v) >= 2)},
    }
    with open(os.path.join(d, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    # ---- summary.md ----
    L = [f"# {s['title']} ({s.get('customUrl', '')})", "",
         f"- Subscribers {summary['channel']['subscribers']:,}, total views {summary['channel']['total_views']:,}, "
         f"videos {summary['channel']['video_count']}, country {s.get('country', 'not public')}, "
         f"created {summary['channel']['created']}"]
    for key, label in (("baseline_long", "Long-form"), ("baseline_short", "Shorts")):
        b = summary[key]
        if b:
            L.append(f"- {label} baseline (latest {b['n']}, excluding targets): median views {b['median_views']:,.0f}, "
                     f"P25-P75 {b['p25_views']:,.0f}-{b['p75_views']:,.0f}, "
                     f"median engagement {b['median_engagement_pct']}%")
    lang = summary["channel"]["language"]
    if lang["code"] is None:
        L.append("- Video language: not tagged by the creator. Infer it from the titles before calling "
                 "vidiq_outliers, and pass it as `language` (the default is en)")
    elif lang["outliers_language"]:
        L.append(f"- Video language: {lang['code']} ({lang['videos_tagged']} tagged videos). "
                 f"Call vidiq_outliers with language=\"{lang['outliers_language']}\"")
    else:
        L.append(f"- Video language: {lang['code']}, which vidiq_outliers does not support; "
                 f"find breakouts from the API data instead of spending credits")
    yes_no = {True: "yes", False: "no", None: "unknown"}
    for t in target_reports:
        c = t["comment_stats"] or {}
        da = t["description"]
        L += ["", f"## Target video: {t['title']}", "",
              "| Metric | Value |", "|---|---|",
              f"| Published / age | {t['published']} / {t['age_days']} days |",
              f"| Duration / format | {t['duration_s']} s / {t['format']} |",
              f"| Views / likes / comments | {t['views']:,} / {t['likes']:,} / {t['comments']:,} |",
              f"| Engagement (likes+comments)/views | {t['engagement_pct']}% |",
              f"| Views vs channel median | {t['vs_median_pct']}% |",
              f"| Rank among latest 10 same-format videos | {t['rank_among_recent_10_plus_target']} |",
              f"| Creator reply rate (viewer top-level comments the creator answered) | {c.get('creator_reply_rate_pct')}% |",
              f"| Comments per 1k views | {c.get('comments_per_1k_views')} |",
              f"| Description links / with tracking params | {len(da['urls'])} / {len(da['urls_with_tracking'])} |",
              f"| Link in description first line | {yes_no[da['link_in_first_line']]} |",
              f"| Paid-promotion flag (API) | {yes_no[t['paid_promotion']]} |",
              f"| Disclosure hints in description (regex, English only) | {', '.join(da['disclosure_hints']) or 'none'} |"]
        if t["age_warning"]:
            L.append("\n> Note: this video is much younger than the comparison videos and its views are still "
                     "accumulating, so comparing total views understates it. Compare against the age-matched "
                     "baseline (24h/72h/7d) from vidiq_channel_performance_trends instead.")
    if view_check.get("warning"):
        start, end = view_check["rollout_window"]
        win = view_check["window_excluded"]
        win_text = (f" The {len(win)} long videos published inside the window were left out of both groups; their "
                    f"like/view shows where this channel switched: "
                    + ", ".join(f"{w['published'][5:]} {w['like_rate_pct']}%" for w in win) + "."
                    if win else "")
        L += ["", f"> View-count change: YouTube began counting public views from the first frame on {start} and "
              f"completed the rollout by {end}; each channel switched on some day in between. This channel's median "
              f"long-form like/view fell from {view_check['like_rate_pre_pct']}% ({view_check['pre_n']} videos "
              f"published before {start}) to {view_check['like_rate_post_pct']}% ({view_check['post_n']} videos "
              f"published after {end}), suggesting views under the new rule are inflated about "
              f"{view_check['estimated_inflation']}x.{win_text} Adjust view comparisons across the change, or "
              f"compare only videos counted under the same rule."]
    L += ["", f"## Sponsorship scan (latest {sponsors['videos_scanned']}, excluding targets)", "",
          f"- Paid-promotion flag set (API): {sponsors['videos_with_paid_flag']}",
          f"- Disclosure hints in description (regex): {sponsors['videos_with_disclosure_hint']}",
          f"- Sponsored by either signal: {sponsors['videos_sponsored_any_signal']}",
          "- Most frequent external link domains (social platforms removed; recurring ones are usually long-term "
          "sponsors, affiliate links or the creator's own products; check for competitors):"]
    for dom in sponsors["external_domains"][:10]:
        L.append(f"  - {dom['domain']}: {dom['videos']} videos (e.g. {dom['example']})")
    L += ["", "## Latest videos", "", "| Published | Format | Views | Engagement | Paid flag | Title |",
          "|---|---|---|---|---|---|"]
    for r in rows[:15]:
        mark = " **(target)**" if r["id"] in targets else ""
        L.append(f"| {r['published']} | {r['format']} | {r['views']:,} | {r['engagement_pct']}% | "
                 f"{yes_no[r['paid_promotion']]} | {r['title'][:60]}{mark} |")
    with open(os.path.join(d, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # ---- comments_digest.md ----
    creator_handle = (s.get("customUrl") or "").lower()
    handle_alias = {}
    for c in comments.values():
        for th in c.get("threads", []):
            items = [th["snippet"]["topLevelComment"]] + th.get("replies", {}).get("comments", [])
            for it in items:
                sn = it["snippet"]
                a, name = sn.get("authorChannelId", {}).get("value"), (sn.get("authorDisplayName") or "").lower()
                if a and name.startswith("@") and a != channel_id:
                    handle_alias[name] = alias(a)

    def scrub(m):
        h = m.group(0).lower()
        if creator_handle and h == creator_handle:
            return "@[creator]"
        return "@" + handle_alias.get(h, "[user]")

    def clip(text):
        text = MENTION_RE.sub(scrub, " ".join((text or "").split()))
        return text if len(text) <= args.text_limit else text[:args.text_limit] + "…"

    D = ["# Comment digest (authors anonymized as U#, consistent across videos; [creator] = the channel owner)", ""]
    for vid in list(targets) + [v for v in sel["recent"] if v in comments]:
        c = comments.get(vid)
        if c is None:
            continue
        r = by_id.get(vid, {})
        tag = "target" if vid in targets else "recent"
        D.append(f"## [{tag}] {r.get('title', vid)} ({r.get('published', '')}, {r.get('views', 0):,} views)")
        if c.get("error"):
            D.append(f"_Comments unavailable: {c['error']}_")
        threads = c.get("threads", [])
        if vid not in targets:
            threads = sorted(threads, key=lambda t: -t["snippet"]["topLevelComment"]["snippet"].get("likeCount", 0))
            threads = threads[:args.recent_per_video]
        for th in threads:
            top = th["snippet"]["topLevelComment"]["snippet"]
            a = top.get("authorChannelId", {}).get("value")
            who = "[creator]" if a == channel_id else alias(a) if a else "anonymous"
            D.append(f"- {who} ({top.get('publishedAt', '')[:10]}, {top.get('likeCount', 0)} likes): "
                     f"{clip(top.get('textDisplay'))}")
            for rep in th.get("replies", {}).get("comments", []):
                rs = rep["snippet"]
                ra = rs.get("authorChannelId", {}).get("value")
                rwho = "[creator]" if ra == channel_id else alias(ra) if ra else "anonymous"
                D.append(f"  - ↳ {rwho}: {clip(rs.get('textDisplay'))}")
        D.append("")
    with open(os.path.join(d, "comments_digest.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(D))

    print(f"Wrote {d}/summary.json, summary.md, comments_digest.md ({len(aliases)} commenters anonymized)")

if __name__ == "__main__":
    main()
