# Data Sources and Credit Budget

Ground rule: the YouTube Data API is free with a large quota, so fetch everything it can provide through it. vidIQ credits are limited and take a month to refill, so spend them only on what vidIQ alone can do.

## Contents

1. Who covers what
2. vidIQ tool prices
3. Cost per analysis module
4. Credit-saving rules
5. Async jobs
6. API quota
7. Data neither source can reach

---

## 1. Who covers what

| Data | First choice | Fallback (credits) | Notes |
|---|---|---|---|
| Channel subscribers, total views, description, country | API `channels.list` (fetch script) | `vidiq_channel_stats` (5) | vidIQ adds growth over a period |
| Video title, description, tags, duration, thumbnail, views/likes/comments | API `videos.list` | `vidiq_get_videos_by_ids` (5, up to 50 videos) | |
| Paid-promotion flag | API `videos.list` part `paidProductPlacementDetails` | none | The creator's own "includes paid promotion" declaration; language-independent |
| Recent uploads | API `playlistItems.list` | `vidiq_channel_videos` (5) | vidIQ separates long-form, Shorts and live, and adds VPH and breakout scores |
| Comments and replies | API `commentThreads.list` | `vidiq_video_comments` (5 per page) | The API route saves many credits |
| **Transcript / spoken text** | `vidiq_video_transcript` (5) | none | The official caption download is owner-only |
| **Scene-level breakdown** (scenes, features shown, on-screen text, CTA timing) | `vidiq_video_watch` (25, async) | `vidiq_watch_shortform_content` (10) for Shorts | A transcript alone cannot show on-screen links or codes |
| **Age-matched view baselines** (median and percentiles at 1h/24h/72h/7d) | `vidiq_channel_performance_trends` (5) | none | Comparing total views of new and old videos is unfair; use this |
| **One video's view growth curve** | `vidiq_video_stats` (5) | none | Shows whether views stalled after launch |
| Breakouts and flops on a channel | `vidiq_outliers` (5, one call covers up to 50 `channelIds`) | compute from API data | Shows which topics the audience rewards. `language` defaults to `en` and filters by title language, so pass the channel's language (e.g. `pt`) or non-English channels return nothing |
| Similar or competing channels | `vidiq_similar_channels` (5) | none | Alternative creators |
| Title click-potential score | `vidiq_score_title` (5) | none | Optional support for recommendations |
| Audience pain points in a niche | `vidiq_comment_insights` (per tool description) | none | Category-level insight across channels |
| Candidate channels for a brief (discovery) | API `search.list` (`discover_channels.py`, 100 units per call) | `vidiq_channel_search` / `vidiq_similar_channels` (5 each) | `regionCode` and `relevanceLanguage` only bias ranking; verify country and language when screening |
| Screening many channels at once | API `channels.list` + `playlistItems.list` + `videos.list` (`screen_channels.py`, about 2–3 units per channel) | none worth the credits | Channel IDs are looked up 50 per unit, handles 1 each |
| Public contact emails | Channel and video descriptions via the API (`screen_channels.py`) | none | The business email behind YouTube's "View email address" button is never exposed; only the user can reveal it. Creator websites can be read with a web fetch tool |
| Owned channel retention, traffic sources, demographics | `vidiq_channel_analytics` (5) | none | **Only for channels connected to the user's vidIQ account**, usually not a creator's channel |

## 2. vidIQ tool prices

Prices as seen in the tool descriptions in 2026-09. **The runtime tool description (`Cost: N credit(s)`) is authoritative**; this table may be stale. The vidIQ help page says Video Watch costs 10, but the tool description and actual charges are 25.

- Free (0): `vidiq_balance`, `vidiq_job_poll`, `vidiq_jobs_list`, `vidiq_user_channels`, `vidiq_trend_categories`, `vidiq_submit_feedback`
- 5: `vidiq_video_transcript`, `vidiq_channel_stats`, `vidiq_channel_performance_trends`, `vidiq_video_stats`, `vidiq_video_comments` (per page), `vidiq_outliers`, `vidiq_channel_videos`, `vidiq_get_videos_by_ids`, `vidiq_channel_analytics`, `vidiq_score_title`
- 10: `vidiq_watch_shortform_content`
- 25: `vidiq_video_watch`

Clients prefix tool names, for example `mcp__<uuid>__vidiq_balance` or `vidiq:vidiq_balance`. Match on the part from `vidiq_` onwards.

## 3. Cost per analysis module

The plan is the union of the calls needed by the modules chosen in the intent frame (see `analysis-playbooks.md`). Count shared calls once, and mark calls that only add depth as `:optional` in `scripts/credit_plan.py`.

| Module | Dual-source (API + vidIQ) | Added in vidIQ-only mode |
|---|---|---|
| 1. Performance vs. baseline | `channel_performance_trends` 5 (required when the target is younger than the baseline); `video_stats` 5 optional | `channel_stats` 5 + `channel_videos` 5 + `get_videos_by_ids` 5 |
| 2. Content breakdown (per video) | `video_transcript` 5; `video_watch` 25 optional (`watch_shortform_content` 10 for Shorts) | `get_videos_by_ids` 5 for the description |
| 3. Audience and community | 0 (comments come from the API); `comment_insights` optional | `video_comments` 5 per page per video: the targets plus the recent videos you read |
| 4. Conversion funnel and attribution | 0 of its own (builds on modules 1–3, web fetch and user data) | 0 |
| 5. Sponsorship history and creator fit | `outliers` 5 (shared with module 7 when comparing creators); `video_transcript` 5 each for 1–2 representative videos optional; `similar_channels` 5 optional | `channel_videos` 5 |
| 6. Forecast and pre-spend math | 0 of its own (uses module 1 or 5 baselines) | 0 |
| 7. Channel strategy and benchmark | `outliers` 5 once for all channels (one call per title language); `channel_performance_trends` 5 per channel; `channel_stats` 5 optional; `channel_analytics` 5 for owned channels | `channel_stats` 5 + `channel_videos` 5 |
| 8. Diagnosis and recommendations | 0 | 0 |
| 9. Creator sourcing and shortlisting | 0 for discovery and screening (API quota instead, section 6); `similar_channels` 5 per seed optional; module 5 costs for each top candidate taken to deep fit | `channel_search` 5 per query instead of `search.list`, plus `channel_videos` 5 per channel to screen |

For reference, a single-video analysis that combines modules 1–4 and 8 costs 10 credits in dual-source mode without optional calls, and up to 40 with `video_watch` and `video_stats`. The same analysis in vidIQ-only mode costs about 85–115, mostly for comments.

## 4. Credit-saving rules

- **Reuse first**: `vidiq_jobs_list` (free) lists async jobs this account submitted before. If `vidiq_video_watch` has already run on the same video, fetch the result for free with `vidiq_job_poll` instead of paying 25 again.
- **Free before paid**: run the API scripts and `vidiq_balance` first, then decide what is worth credits. If the API data shows the video performed normally, `vidiq_outliers` may be unnecessary.
- **Ask everything in one `video_watch`**: its `prompt` parameter should cover every question the intent frame needs from the visuals, so no second run is needed to fill a gap.
- **Use the transcript when speech is enough**: 5 credits, a fifth of the price of video_watch.
- **Never fetch the same data twice**: reuse results from this session. When a call fails, read the error before retrying.
- **Cap comment paging**: each page of `vidiq_video_comments` is charged; stop once you have enough.
- **Batch lookups**: `vidiq_get_videos_by_ids` takes up to 50 videos and `vidiq_outliers` up to 50 `channelIds` for one charge.

## 5. Async jobs

Tools like `vidiq_video_watch` return an `mcpJobId` immediately. Credits are charged at submission and refunded automatically if the job fails.

- After submitting, do other work (run API scripts, read the transcript), then check back with `vidiq_job_poll` (free). Longer videos take longer; a video of ten-plus minutes usually needs a few minutes.
- When `status` is `completed`, read `analysisText`. When it is `failed` or `expired`, check `refunded` to confirm the credits came back.
- If the session is interrupted, recover earlier jobs with `vidiq_jobs_list` (free).

## 6. API quota

The default quota is 10,000 units per project per day, reset at midnight Pacific time. Most calls cost 1 unit, so quota rarely matters, except for `search.list` at 100 units, which makes creator discovery the one workflow that needs a quota plan.

| Step | Units |
|---|---|
| `preflight.py` | 1 |
| `fetch_youtube.py`, one channel without comments | about 3 |
| `fetch_youtube.py` comments | 1 per page of 100 threads, plus 1 per thread with more than 5 replies |
| `discover_channels.py` | 100 × queries × durations × pages |
| `screen_channels.py` | about 2–3 per channel |
| A typical sourcing run: 20 queries × 2 durations, then 100 channels screened, then 5 deep fits with comments | about 4,000 + 300 + 100 |

- Both sourcing scripts print an estimate first and refuse to exceed `--max-quota`; `discover_channels.py --dry-run` prints it without calling the API.
- Before a large discovery run, ask whether other work has already used today's quota on the same key; the API does not report the remaining balance.
- When the quota runs out mid-run, `discover_channels.py` saves what it collected. Continue the next day rather than switching to scraping.

## 7. Data neither source can reach

An API key and vidIQ see only public data. Only the channel owner can see the following, so mark them "pending" in the report and name who can supply them:

| Data | Why it matters | How to get it |
|---|---|---|
| Audience retention curve | Whether viewers left before the product segment or CTA | Screenshots from the creator's YouTube Studio, or `vidiq_channel_analytics` (report=audience_retention) after the creator connects the channel to your vidIQ account |
| Thumbnail impressions and CTR | Separates "nobody clicked" from "clicked but did not stay" | Same as above |
| Traffic sources (search, suggested, external) | Whether the platform pushed the video | Same as above (report=traffic_sources) |
| Audience age, gender, geography | Public data only allows inference from comments, which is unreliable | Same as above (report=audience_demographics / audience_geography) |
| Your own visitors, leads, conversions | The lower half of the funnel | The user's data team; ask how each metric is defined and attributed |

**Compliance**: use only the official API and vidIQ. YouTube's Terms of Service forbid unauthorized automated access, so do not scrape youtube.com with yt-dlp, browser automation or similar. YouTube API Developer Policies require stored data to be refreshed or deleted periodically, generally within 30 days. A one-off analysis is fine, but do not keep raw comments long-term.
