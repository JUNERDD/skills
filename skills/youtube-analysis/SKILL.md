---
name: youtube-analysis
description: YouTube channel and video analysis using the vidIQ MCP server plus the official YouTube Data API v3, with a dependency preflight, a vidIQ credit budget and an API quota check before anything is spent. Use when the user's question or decision depends on real data from YouTube channels or videos: how a video or channel performed, what a video contains and how its audience reacted, why a sponsored video did or did not convert, whether a creator fits a product, how channels compare, or which creators match a brief and should be shortlisted. Works out what the user needs to learn or decide, then assembles only the evidence that answers it from composable analysis modules. Do not use for producing YouTube content (scripts, titles, thumbnails, edits), for operating or uploading to the user's own channel, or for general questions about YouTube that need no channel or video data.
argument-hint: "[YouTube channel or video URL, or a brief] [what you want to find out]"
compatibility: Works in any agent that can call MCP tools (Claude.ai, Claude Desktop/Cowork, Claude Code, Codex, Cursor, VS Code, Gemini CLI, OpenCode). Needs the vidIQ MCP server (https://mcp.vidiq.com/mcp) and/or a YouTube Data API v3 key; bundled scripts need Python 3.8+ with network access to www.googleapis.com.
---

# YouTube Analysis (vidIQ + YouTube Data API)

Use this skill when the user's goal can only be answered with evidence from real YouTube channels or videos, whether they invoke it by name (`/youtube-analysis`, `$youtube-analysis`) or the need emerges from the task, such as finding creators for a campaign brief or judging a sponsored video. It does not apply to creating YouTube content, operating the user's own channel, or questions about YouTube that need no channel or video data. Starting without an explicit invocation relaxes nothing: the preflight and budget gates below still run before any credits or search quota are spent, and the intent-frame summary tells the user that this skill is being used.

Two data sources, each with its own strengths:

- **YouTube Data API v3**: official and free, 10,000 quota units per day. Covers channel and video statistics, descriptions, recent uploads, comments, the creator's paid-promotion flag, and keyword search for finding channels.
- **vidIQ MCP**: billed in credits (the Free plan gets about 150 a month and waits a full cycle to refill). Covers what the API cannot: transcripts, scene-level video breakdowns, age-matched view baselines, outlier detection, similar channels.

Both spend the user's resources, and vidIQ credits are scarce. So the work runs in this order: understand what the user needs, confirm the dependencies are ready, and confirm the credits cover the plan. Only then fetch and analyze. In earlier real runs, the costly failures were a key the agent could not read, repeated polling of async jobs, and Video Watch costing more than the vidIQ help page said. The two gates exist to catch these before they cost anything.

Relative paths here (`scripts/`, `references/`) are relative to the directory containing this SKILL.md. Resolve that absolute path before running scripts.

## Step 0: Recognize intent

Do not sort the request into a predefined task type, and do not match it against example phrases. Requests about YouTube are open-ended, mix goals, and often leave the real question unstated. Reconstruct what the user is trying to accomplish from everything available: the invocation arguments, the earlier conversation, attached files, outlines or backend numbers, and what their role appears to be. Then derive the plan from that understanding.

Build an **intent frame** with these fields:

- **Objective**: the question the user needs answered, and the decision or action the answer feeds. Examples of decisions: whether to renew a partnership, what to change in the next brief, which creators to shortlist, what to publish next. If the user did not name the decision, infer the most plausible one from context and mark it as an assumption.
- **Subjects and roles**: every video and channel involved, and the role each plays. A subject can be the thing being judged, the comparison baseline, a competitor, or the user's own channel; an own channel unlocks owner-only analytics, which you can check with `vidiq_user_channels`. Resolve indirect references such as "this video" or "the creator from last month" from the conversation. The subjects can also be a pool not yet known, when the user needs creators found for a brief; the pool is then defined by the brief's audience, language, market and format, and module 9 in `references/analysis-playbooks.md` turns it into named channels.
- **Evidence needed**: the facts that could change the answer. Derive these from the objective, then map them to modules in `references/analysis-playbooks.md` and to data sources. Evidence that could not change the answer is not worth collecting, especially when it costs credits.
- **Constraints**:
  - **Spending limit**: any limit the user has expressed on credits. It may be stated as a number or only implied, such as a wish to avoid credits entirely or to go as deep as needed. Work out its scope from meaning: this task, a whole billing period, or each item in a batch.
  - **Depth and time**: a quick read or a full report.
  - **User-supplied data**: numbers or materials the user has given or will give, such as backend visitors, leads and conversions, tracking links, the product, or the brief. Record how each number is defined.
- **Deliverable**: form, audience (a team meeting, a client, the user alone), language, and structure. If the user supplied an outline, it takes precedence over any module order.

Handling uncertainty:

- Ask only when an ambiguity would materially change what gets spent or concluded, such as which subject is meant, whether credits may be used at all, or the scope of a budget. Ask one concise question and bundle it with the preflight report. Otherwise proceed on the most plausible reading and state it.
- A request can combine several objectives or be unlike anything described here. Compose modules to fit it rather than forcing it into a familiar shape. If public data plus vidIQ cannot answer it, say so and name the data that would.
- Revisit the frame when new information arrives. For example, the user may supply backend numbers, or the free data may already answer part of the question.

Show the user a 1–3 line summary of the frame together with the preflight results, so a misreading can be corrected before any credits are spent. When creators are to be sourced, include the scorecard and the keyword plan in that summary. Missing backend data is not a reason to wait: fetch the public data first and mark the gaps as "pending" in the report.

## Step 1: Dependency preflight (no credits)

Run both checks:

**A. vidIQ connector**
Look for a tool whose name ends in `vidiq_balance`. Clients add prefixes, for example `mcp__<id>__vidiq_balance` or `vidiq:vidiq_balance`. If the client defers tool loading, search its tools for `vidiq` first. Call it once (free) and note `totalCredits` and `renewableResetsAt`.

**B. YouTube Data API**
If you can run commands:

```bash
python3 <skill-dir>/scripts/preflight.py
```

It checks the Python version, whether the key can be found, whether googleapis.com is reachable, and whether the key works. Each failure comes with its fix, and the whole check costs 1 quota unit. Where commands cannot run, such as a chat surface without code execution, skip this and record "API unavailable".

**Report the results in a small table**, then pick a mode:

| vidIQ | API | Mode | What to do |
|---|---|---|---|
| ✅ | ✅ | Dual-source | Proceed normally |
| ✅ | ❌ | vidIQ-only | Comments and stats also cost credits, roughly 2–3× the dual-source cost. Explain this and ask whether to set up the API first or spend credits |
| ❌ | ✅ | API-only | Stats, comments and description analysis work; transcripts, scene breakdowns and age-matched baselines do not. Say which evidence in the intent frame is lost and ask whether to install vidIQ first or deliver a reduced analysis |
| ❌ | ❌ | Blocked | Guide the setup using `references/setup.md` |

**When guiding setup**: cover only the section for the current client (`references/setup.md` is organized by client), one step at a time. The user must do the sign-ins, authorizations and key creation themselves. **Have the user save the key to a config file or environment variable, never paste it into the chat**, because anything in the chat history can leak. When the user says it is done, rerun the preflight rather than taking their word for it.

Do not fill gaps by scraping: yt-dlp or browser automation on youtube.com violates YouTube's Terms of Service, and this kind of analysis often feeds brand partnerships.

## Step 2: Credit budget (before any credits are spent)

1. **Reuse first**: call `vidiq_jobs_list` (free) and look for completed jobs on the same video, especially the 25-credit `vidiq_video_watch`. If one exists, fetch it with `vidiq_job_poll` (free) and drop that call from the plan. Users often come back to the same video, so this can save 25 credits outright.
2. List the vidIQ calls the evidence in the intent frame requires, using the per-module cost table in `references/data-sources.md`. When modules share a call, count it once. Leave out anything the API can supply.
3. **The unit price in the runtime tool description (`Cost: N credit(s)`) is authoritative.** Use it whenever it differs from the reference table.
4. If you can run commands, compute the plan with the script and mark the calls that could be cut as `:optional`:

   ```bash
   python3 <skill-dir>/scripts/credit_plan.py --balance <totalCredits> \
     --call vidiq_video_transcript --call vidiq_channel_performance_trends \
     --call vidiq_video_watch:optional --call vidiq_outliers:optional
   ```

   If the intent frame contains a spending limit, pass it as `--cap N`: a plan within the cap counts as already approved. Add `--spent <credits used this period>` only when the limit's scope is a billing period rather than this task. Estimate it as `maxRenewableCredits - renewableCredits`. Add-on credit spending is not visible in those fields, so this is only an estimate; cross-check it against job timestamps in `vidiq_jobs_list`, taking the period start as roughly one month before `renewableResetsAt`. If counting prior spend changes the verdict, show the user how you computed it and confirm which scope they meant.

   Without command execution, do the same arithmetic by hand: the total plus a reserve of 10, compared with the balance and any cap.
5. Act on the verdict:
   - **OK** (planned spend, excluding the reserve, is under 30% of the balance and no tool costs 20 or more credits; or the plan is within the user's cap): tell the user the expected spend in one sentence and start.
   - **CONFIRM** (a large share of the balance, or an expensive tool such as `vidiq_video_watch`): show the plan (tool, purpose, credits), the current balance, what remains afterwards and the reset date, then wait. If the user wants only part of it, adjust the plan to their choice.
   - **INSUFFICIENT**: do not run it. Offer choices: drop the optional calls the script suggests, substitute the API, wait for the reset date, or let the user decide on upgrading their plan.
6. Once the user has approved a budget in this conversation, do not ask again for work that stays within it.

Record the actual credits each call spends. Before adding a call that was not in the plan, such as another page of comments, check it against the remaining budget.

**API quota** matters only when the plan includes keyword search for discovery (`search.list`, 100 units per call; see "API quota" in `references/data-sources.md`). Get the estimate from `discover_channels.py --dry-run` and include it in the same report as the credit plan. A discovery plan above about half of the daily quota needs the user's confirmation, because other work may share the key.

## Step 3: Fetch data

Run the free sources first. The free data sometimes makes a paid call unnecessary.

```bash
# one or more target videos (the channel is inferred from the first one)
python3 <skill-dir>/scripts/fetch_youtube.py --video <video-URL> --out yt-analysis/<slug>/data
# a channel with no specific target video
python3 <skill-dir>/scripts/fetch_youtube.py --channel @handle --recent 10 --out yt-analysis/<slug>/data
# compute metrics and the comment digest
python3 <skill-dir>/scripts/analyze_metrics.py yt-analysis/<slug>/data
```

When creators have to be found for a brief, the pool is discovered and screened before any channel gets the per-channel fetch above (module 9 in `references/analysis-playbooks.md`):

```bash
# keyword matrix in the audience's language, plus competitor reverse lookup; --dry-run first for the quota estimate
python3 <skill-dir>/scripts/discover_channels.py --region <CC> --language <lang> \
  --queries-file yt-analysis/<slug>/queries.txt --competitor "<competing product>" --out yt-analysis/<slug>/discovery
# verify country and language, apply the scorecard, flag brand and competitor mentions, extract public emails
python3 <skill-dir>/scripts/screen_channels.py --channels-file yt-analysis/<slug>/discovery/channels.txt \
  --country <CC> --language <lang> --active-days 30 --topic "<terms>" --brand "<our product>" \
  --competitor "<competing products>" --out yt-analysis/<slug>/screening
```

Read `screening.md`, then take only the top candidates into `fetch_youtube.py` with comments for module 5.

Set the flags from the evidence you need. Fetch comments only when audience or reaction evidence matters (`--comments none|targets|all`). Widen `--recent` or `--baseline` when the objective depends on stability or trends. Run `--help` for all options.

- `summary.md`: channel baselines, target-vs-baseline comparison, description audit, paid-promotion flags and the sponsorship scan. It can be pasted into a report.
- `summary.json`: all metrics, including the full description text of each target video.
- `comments_digest.md`: anonymized comments grouped by video. **Read this, not the raw `comments.json`**, which is more than ten times larger.

Judge sponsorship disclosure, promo codes and calls to action by reading the description text yourself. The API's `paid_promotion` flag is the reliable disclosure signal. The regex fields (`disclosure_hints`, `promo_code_hints`) only catch English keywords and miss other languages.

Then call vidIQ within the budget:

- `vidiq_video_watch` is **asynchronous**. Submitting it returns an `mcpJobId`; do other work while it runs (read the transcript, read the summary), then fetch the result with `vidiq_job_poll` (free). Write every question into the `prompt` at submission time, derived from the evidence in the intent frame, so a single run is enough. Typical questions: scene timestamps, product features shown, on-screen links or codes, spoken CTA timestamps, and a paid-promotion label.
- `vidiq_outliers` filters by title language and defaults to `en`, so a non-English channel returns nothing unless you pass `language`. Use the language that `summary.md` reports for the channel; for channels in different languages, make one call per language. If `summary.md` says the language is unsupported, find breakouts from the API data and do not spend the credits.
- **vidIQ's AI analysis can be wrong.** A scene report may say "no sponsorship disclosure" while the API shows the paid-promotion flag set. When it conflicts with API facts (description, flags, statistics), trust the API and note the conflict in the report.
- See `references/data-sources.md` for other tools and credit-saving rules.

If the host supports subagents and there are hundreds of comments or more, hand the comment reading and audience synthesis to a subagent and take back only its conclusions.

## Step 4: Analyze

Open `references/analysis-playbooks.md` and use the modules that supply the evidence in the intent frame. Order them by the user's outline if there is one; otherwise order them by the argument that answers the objective.

Requirements for every analysis:
- Back every conclusion with data or quoted text.
- Mark audience traits inferred from comments (age, occupation and the like) as "inferred".
- Mark data public sources cannot provide (retention curves, CTR, traffic sources, audience demographics, backend conversions) as "pending", and name who can supply it.
- Account for video age when comparing views; compare young videos against age-matched baselines.
- YouTube began counting public views from the first frame on 2026-08-24 and completed the global rollout by 2026-08-28. Channels switched on different days inside that window, so a long video published in it may be counted under either rule. Long-form public views typically run about 1.7–1.9× higher under the new rule, and the factor varies by channel. The older, stricter count survives as "Engaged views" in YouTube Analytics (Advanced Mode), and creator earnings are still based on engaged views and engaged watch hours. When `summary.md` shows a "View-count change" note, adjust or caveat any view comparison that spans the change, and place a video published inside the window by its like/view rate. Engaged views, when the creator can supply them, compare like for like across the change.
- When the objective involves conversion, use a web fetch tool to check the landing and pricing pages. Look at localization, price and offers, the sign-up flow, and any recent redesign or price change. These are not YouTube pages, so fetching them raises no Terms-of-Service issue.

## Step 5: Deliver

- By default, write a Markdown report in `yt-analysis/<slug>/`, in the user's language. Markdown opens in any client and pastes easily into documents. If the host supports Artifacts or web pages and the user needs something shareable, a page with charts can be added.
- Open with 3–5 lines that answer the objective from the intent frame directly.
- Refer to commenters as U#.
- Call `vidiq_balance` once more at the end. State in both the report and the reply: credits spent this run, credits remaining, the reset date, and the API quota units used.
- For a creator shortlist, deliver the tiered table from module 9 as Markdown plus a CSV that opens in a spreadsheet, and list the channels whose business email only the user can reveal.
- Leave the data files in `data/` for follow-up questions. Remind the user not to keep raw comments long-term: YouTube API policy requires stored data to be refreshed or deleted periodically.
