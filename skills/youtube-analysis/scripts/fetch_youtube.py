#!/usr/bin/env python3
"""Fetch the public data an analysis needs through YouTube Data API v3 (free, official API, no scraping).

Fetches:
  - channel info (subscribers, total views, description, country, creation date)
  - statistics for the latest --baseline uploads (used for the channel baseline)
  - details of the target videos (title, description, tags, duration, thumbnail, stats,
    paid-promotion flag)
  - comments and replies on the targets plus the latest --recent videos (audience and engagement analysis)

Usage:
    python3 scripts/fetch_youtube.py --video https://youtu.be/P9AG4ad4Xjs --out yt-data
    python3 scripts/fetch_youtube.py --channel @SomeCreator --recent 10 --out yt-data
    python3 scripts/fetch_youtube.py --channel @SomeCreator --comments none   # stats only

Writes to <out>/: channel.json, videos.json, selection.json, comments.json, fetch_log.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytapi import ApiError, Client, find_api_key, parse_channel, parse_video_id  # noqa: E402

CHANNEL_PARTS = "snippet,statistics,contentDetails,brandingSettings,topicDetails"
# paidProductPlacementDetails is the creator's "includes paid promotion" flag; extra parts cost no extra quota
VIDEO_PARTS = "snippet,statistics,contentDetails,topicDetails,status,paidProductPlacementDetails"


def resolve_channel(client: Client, spec: str) -> dict:
    kind, value = parse_channel(spec)
    params = {"id": value} if kind == "id" else {"forHandle": value} if kind == "handle" \
        else {"forUsername": value} if kind == "username" else None
    if params is None:
        # /c/ custom URLs have no direct lookup, so this needs search (100 quota units)
        r = client.get("search", part="snippet", type="channel", q=value, maxResults=1)
        items = r.get("items", [])
        if not items:
            sys.exit(f"Channel not found: {spec}")
        params = {"id": items[0]["snippet"]["channelId"]}
    r = client.get("channels", part=CHANNEL_PARTS, **params)
    if not r.get("items"):
        sys.exit(f"Channel not found: {spec} (check the handle spelling, or use the channel ID starting with UC)")
    return r["items"][0]


def list_uploads(client: Client, playlist_id: str, limit: int) -> list[str]:
    ids, token = [], None
    while len(ids) < limit:
        params = dict(part="contentDetails", playlistId=playlist_id, maxResults=min(50, limit - len(ids)))
        if token:
            params["pageToken"] = token
        r = client.get("playlistItems", **params)
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    return ids


def get_videos(client: Client, ids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(ids), 50):
        out += client.get("videos", part=VIDEO_PARTS, id=",".join(ids[i:i + 50])).get("items", [])
    return out


def get_comments(client: Client, video_id: str, limit: int) -> dict:
    threads, token = [], None
    try:
        while len(threads) < limit:
            params = dict(part="snippet,replies", videoId=video_id, maxResults=100,
                          order="time", textFormat="plainText")
            if token:
                params["pageToken"] = token
            r = client.get("commentThreads", **params)
            threads += r.get("items", [])
            token = r.get("nextPageToken")
            if not token:
                break
    except ApiError as e:
        # commentsDisabled is common and not a failure
        return {"error": e.reason, "threads": threads, "truncated": False}
    # commentThreads embeds at most 5 replies per thread; fetch the rest when there are more
    for t in threads:
        total = t["snippet"].get("totalReplyCount", 0)
        have = len(t.get("replies", {}).get("comments", []))
        if total > have:
            try:
                r = client.get("comments", part="snippet", parentId=t["id"], maxResults=100,
                               textFormat="plainText")
                t["replies"] = {"comments": r.get("items", [])}
            except ApiError:
                pass
    return {"error": None, "threads": threads[:limit], "truncated": bool(token)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--channel", help="@handle, channel URL or UC... ID; defaults to the channel of the first --video")
    ap.add_argument("--video", action="append", default=[], help="target video URL or ID; repeatable")
    ap.add_argument("--recent", type=int, default=10, help="number of recent videos (excluding targets) to fetch comments for, default 10")
    ap.add_argument("--baseline", type=int, default=30, help="number of latest uploads used for the baseline, default 30")
    ap.add_argument("--comments", choices=["all", "targets", "none"], default="all",
                    help="all = targets + recent videos; targets = targets only; none = no comments")
    ap.add_argument("--max-comments", type=int, default=500, help="maximum top-level comments per video")
    ap.add_argument("--out", default="yt-data")
    ap.add_argument("--env-file")
    args = ap.parse_args()
    if not args.channel and not args.video:
        ap.error("provide --channel or --video")

    key, _ = find_api_key(args.env_file)
    if not key:
        sys.exit("YOUTUBE_API_KEY not found; run scripts/preflight.py to see how to set it up")
    client = Client(key)
    os.makedirs(args.out, exist_ok=True)

    try:
        targets = [parse_video_id(v) for v in args.video]
        target_videos = get_videos(client, targets) if targets else []
        missing = set(targets) - {v["id"] for v in target_videos}
        if missing:
            print(f"Warning: these videos are unavailable (private, deleted or wrong ID): {', '.join(missing)}", file=sys.stderr)

        channel_spec = args.channel or (target_videos[0]["snippet"]["channelId"] if target_videos else None)
        if not channel_spec:
            sys.exit("No usable target video and no --channel given")
        ch = resolve_channel(client, channel_spec)
        uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]

        ids = list_uploads(client, uploads, max(args.baseline, args.recent + len(targets)))
        vids = {v["id"]: v for v in get_videos(client, [i for i in ids if i not in targets])}
        for v in target_videos:
            vids[v["id"]] = v
        all_videos = sorted(vids.values(), key=lambda v: v["snippet"]["publishedAt"], reverse=True)

        recent = [v["id"] for v in all_videos if v["id"] not in targets][:args.recent]
        comment_ids = [] if args.comments == "none" else targets + ([] if args.comments == "targets" else recent)

        comments = {}
        for vid in comment_ids:
            c = get_comments(client, vid, args.max_comments)
            comments[vid] = c
            note = f" ({c['error']})" if c["error"] else " (truncated)" if c["truncated"] else ""
            print(f"  comments {vid}: {len(c['threads'])} top-level{note}", file=sys.stderr)
    except ApiError as e:
        sys.exit(f"YouTube API error: {e}. Run scripts/preflight.py to diagnose")

    def dump(name, obj):
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)

    dump("channel.json", ch)
    dump("videos.json", all_videos)
    dump("selection.json", {"channel_id": ch["id"], "targets": targets, "recent": recent})
    dump("comments.json", comments)
    dump("fetch_log.json", {"fetched_at": datetime.now(timezone.utc).isoformat(),
                            "quota_units_used": client.quota_used, "args": vars(args)})
    print(f"Done: channel {ch['snippet']['title']}, {len(all_videos)} videos, "
          f"comments for {len(comments)} videos, about {client.quota_used} quota units used "
          f"(10,000 per day) -> {args.out}/")


if __name__ == "__main__":
    main()
