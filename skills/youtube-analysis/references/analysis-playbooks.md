# Analysis Modules

Each module answers one kind of question and names the evidence and the vidIQ calls it needs. Pick the modules whose evidence the intent frame calls for, and combine as many as the objective requires. None of them is tied to a task type. If the user gave an outline, map modules onto its sections; otherwise order them so they build toward the answer to the objective. The shared lenses and reporting rules at the end apply to every analysis.

## Contents

1. Performance vs. baseline
2. Content breakdown
3. Audience and community
4. Conversion funnel and attribution
5. Sponsorship history and creator fit
6. Forecast and pre-spend math
7. Channel strategy and competitive benchmark
8. Diagnosis and recommendations
9. Creator sourcing and shortlisting
10. Shared lenses
11. Reporting

Credit costs per module are in `data-sources.md`.

---

## 1. Performance vs. baseline

**Answers**: did this video do well or badly for this channel, and is its trajectory healthy?

- Channel context: subscribers, total views, video count, creation date, country or language, upload cadence.
- Baseline: long-form median views, P25–P75, and median engagement, from `summary.md`. Shorts are baselined separately.
- Target vs. baseline: `vs_median_pct`, rank among recent videos of the same format, engagement.
- **Age matching**: if the target is younger than the baseline's median age (`age_warning`), compare against the 24h/72h/7d baselines from `vidiq_channel_performance_trends`, not total views.
- Optional: `vidiq_video_stats` shows whether views stalled after launch or are still growing.
- Apply the view-count change lens (section 10) whenever the compared videos were published on both sides of the 2026-08-24 to 2026-08-28 rollout, or any of them inside it.

## 2. Content breakdown

**Answers**: what does the video actually say and show, and where?

Build a **timeline**. For each beat, record the timestamp, what is shown or said, any product feature or scenario, and its function (hook, setup, demo, CTA).
- **Title**: compare it with the creator's usual title style. Note where a brand name sits, and whether any quantified promise is kept by the video.
- **Thumbnail**: what it promises, and whether the title and content deliver on it.
- **First product appearance**: timestamp, and its position as a percentage of the runtime.
- **CTAs**: how many spoken CTAs there are and when, as a percentage of the runtime. Also check for on-screen links or codes and for a pinned comment.
- **Description**: which line carries the link, tracking parameters, how clearly any code is stated, and disclosure. Read `description.text` in `summary.json` yourself; the API's `paid_promotion` flag settles disclosure.
- Sources: `vidiq_video_transcript` for speech, `vidiq_video_watch` for visuals and timestamps (`vidiq_watch_shortform_content` for Shorts). With a transcript only, mark on-screen elements and exact timings as "cannot confirm".

## 3. Audience and community

**Answers**: who watches, what they care about, and how they reacted.

- **Persona**: read the recent-video comments in `comments_digest.md` and infer age range, occupation or life situation, pain points, interests, language ability and price sensitivity. **Mark everything as "inferred"** and give the basis, for example "several commenters mention unemployment or childcare". For real demographics, add "pending: ask the creator for Studio audience screenshots".
- **Engagement quality**: engagement rate, comments per 1k views, creator reply rate (`creator_reply_rate_pct`), and repeat commenters (`audience_sample.commenters_on_2plus_videos`). More repeat commenters means a stronger core audience.
- **Reaction to the subject** (a product, topic or format): count comments that relate to it, are positive, negative or doubtful, ask questions, or report bugs. Quote representative ones with authors anonymized.
- **Conversion signals**: comments saying the viewer already uses it, clicked the link, or hit a sign-up error. These are key evidence for explaining attribution gaps (module 4).
- Optional: `vidiq_comment_insights` for category-level pain points across channels.

## 4. Conversion funnel and attribution

**Answers**: where along the path from impression to payment people drop off, and whether the measured numbers reflect reality.

Walk each layer, with evidence for each:

1. **Impression → view**: views against the baseline (module 1). Do the thumbnail, title and topic match what the channel's audience subscribed for?
2. **View → sees the CTA**: when do the product and CTA appear (module 2)? Without a retention curve, write "under typical retention, only a minority reaches a CTA at XX% (inferred)" and list the curve as pending.
3. **Sees CTA → clicks**: is there an on-screen link, which description line carries it, is there a pinned comment, how attractive is the offer, and does this audience read descriptions?
4. **Click → sign-up or lead**: check the landing page's language, errors, permission prompts, and local pricing and payment options. Web-fetch the tracked landing page and the pricing page; check for a version in the audience's language and for price or free-tier changes around the publish date.
5. **Sign-up → payment**.

**Checklist when comments show conversions but the backend shows none**:
- Tracking covers only web parameters, while people signed up through an app store or desktop client
- People searched the brand or typed the site directly instead of clicking
- Cross-device: watched on a phone, signed up on a computer
- The attribution window is too short, or only last click counts
- Promo-code redemptions are not counted as leads
- The creator shared an untracked link in replies
- "I use it" in a comment was only an intention

## 5. Sponsorship history and creator fit

**Answers**: does this creator's audience match what we offer, and what does their sponsorship record tell us?

1. **Who the audience is**: module 3 applied to the last ~10 videos. Use `vidiq_outliers` to see which topics the audience rewards.
2. **Intersection scenario**: which product feature solves which audience pain point. **If no concrete intersection can be written, that is the strongest signal against the deal.**
3. **Scale and stability**: median views and P25–P75 (a wide spread means unpredictable results), plus the age-matched curve from `vidiq_channel_performance_trends`.
4. **Sponsorship record** from the sponsorship scan in `summary.md`. The API `paid_promotion` flag is the reliable signal; recurring external domains usually mean long-term sponsors, affiliate links or the creator's own products.
   - **Competitors sponsoring**: a recent deal with a same-category product may carry exclusivity, and the audience may already be sold on or tired of the category. Put this in the conclusion, and advise asking about exclusivity and its end date before signing.
   - **The creator's own products** that compete with ours or create a conflict of interest: flag them.
   - **Sponsorship density**: how many of the recent videos are sponsored. If density is high, check whether comments complain about ads.
   - Past sponsored videos' views ÷ the channel median: do sponsored videos lose views?
5. **Risk signals**: likes or comments unusually high or low for the views, many near-identical comments, or high subscribers with low views (an inactive audience).
6. **Partnership format**: for a brand the audience does not know, working with a small or mid-size creator, default to integrating the product into the creator's high-performing topics. Reserve a fully dedicated video for products that are already a hot topic for this audience.
7. Optional: `vidiq_similar_channels` to find 3–5 comparable creators.

## 6. Forecast and pre-spend math

**Answers**: what outcome to expect, and whether it clears the target.

`expected leads = median views × click-through rate × sign-up rate`

State every assumption. Mark click-through and sign-up rates as assumed values, and give optimistic, neutral and pessimistic cases. Derive a cost-per-acquisition range and compare it with the target. If even the optimistic case misses, recommend performance-based pricing or not proceeding. Use views counted under a consistent rule (section 10).

## 7. Channel strategy and competitive benchmark

**Answers**: what works for a channel, and how it compares with peers.

- Fundamentals: subscribers, total views, cadence, and the long-form vs. Shorts mix with a baseline for each.
- What works: use `vidiq_outliers` to find breakouts, with `language` set to the channel's title language (see `summary.md`), then summarize their topics, title patterns and lengths. For non-English channels vidIQ covers long-form videos from the last six months only.
- Growth: `vidiq_channel_stats` for growth over a period.
- Peers: compute the same metrics for every channel in one table. Conclude with who is strong where and what can be learned from them.
- Owned channels (connected to the user's vidIQ account): add retention, traffic sources and audience from `vidiq_channel_analytics`.

## 8. Diagnosis and recommendations

**Answers**: why it turned out this way, and what to do about it.

- **Causes**, attributed to three parties **without blaming individuals**:
  - **Us**: creator selection, brief, tracking plan, launch QA, no one watching after publish
  - **The creator**: execution and creative
  - **The product**: experience, localization, bugs

  Then go one level deeper into mechanisms. For example, a topic that departs from what the audience subscribed for gets no platform push; a flat fee with full creative freedom weakens the CTA.
- **Recommendations**: tie each one to a finding and say who does what and what "done" looks like. Split them into what can still be salvaged now (a pinned comment, paid boost, a reply kit for the creator) and what to change next time (brief and contract).
- **Reusable lessons**: write them as process rules, not a critique of one video. These five gates are a useful frame:
  1. **Selection**: fit before size. Write the intersection of "audience pain points ∩ product features" before signing.
  2. **Brief and contract**: make conversion elements hard terms: product within the first 60 seconds, at least 2 CTAs with an on-screen link and code, a pinned comment, the link in the first description line, compliant disclosure. Leave the creative to the creator. Pay a base fee plus performance, and secure data sharing and reuse rights.
  3. **Launch**: set up tracking along the user's real conversion path; app products need a unique code, a smart link and self-reported source. Walk through the flow end to end on a phone in the target country before launch.
  4. **Operations**: someone watches the comments for 72 hours after publishing.
  5. **Review**: do the math before spending and reconcile afterwards. Judge a channel on a batch, never on a single video.

  Hard rules govern only process and infrastructure; creative gets principles.

## 9. Creator sourcing and shortlisting

**Answers**: which creators, not yet known, fit a brief, and who should be contacted first?

Use this when the subjects are a pool still to be found rather than named channels. It narrows a wide search to a short list cheaply, then hands the top candidates to module 5 for the expensive, per-creator judgement.

1. **Scorecard from the brief**, written before any search, so selection is not driven by subscriber counts:
   - **Hard thresholds**: country, content language, minimum size, recent long-form activity (the brief's format decides whether long-form or Shorts cadence matters), and exclusions such as creators who already covered the user's product.
   - **Ranking signals**: median views of recent videos in the brief's format, views-to-subscribers, the share of recent titles on the brief's topic, and sponsorship density.
   - **Conflicts**: competing or same-category products, the creator's own competing products, and brand-safety topics the brief rules out.

   Show the scorecard in the intent-frame summary, so the user can correct it before quota is spent.
2. **Discovery** with `scripts/discover_channels.py`, which runs `search.list` at 100 quota units per call:
   - Build the keyword matrix **in the audience's language**, with no translation from the brief's language. Cover the dimensions the audience actually searches: the tools or products they use, the workflows or problems they work on, their role or stack, and the career or opinion topics that surface commentary channels. Keep each query to the phrasing a viewer would type.
   - **Competitor reverse lookup**: pass competing and same-category product names as `--competitor`. Creators who covered them have shown that the category fits their audience and that they accept such deals; they are often the best-fit leads, and exclusivity has to be checked before contact.
   - **Seed expansion**: once a few strong fits are known, `vidiq_similar_channels` (5 credits each) can find neighbours that keyword search misses. It is optional and goes through the credit budget.
   - Run `--dry-run` first and keep the plan inside the day's remaining quota.
3. **Screening** with `scripts/screen_channels.py` at about 2–3 units per channel. Pass the scorecard's thresholds as flags, its topic terms in the audience's language as `--topic`, the user's product as `--brand` and competitors as `--competitor`. `search.list` only biases by region and language, so the screen is what verifies country and language. Read the excluded list, not only the passed one: a wrong threshold shows up there.
4. **Contacts**, in this order of reliability, each recorded with its source:
   1. Emails written in the channel or video descriptions (reported by the screening script).
   2. The creator's own website, link page or media kit, read with a web fetch tool. These are not youtube.com pages, so fetching them raises no Terms-of-Service issue.
   3. The business email behind YouTube's "View email address" button. It needs sign-in and a CAPTCHA, so only the user can reveal it; list these channels for them.
   4. Social direct messages.
   5. Company support or general inboxes, which have the lowest reply rate; label them as such.

   Never construct an address from a pattern. A wrong guess hurts the sender's domain reputation.
5. **Deep fit on the top 5–10 only**: run module 5 on each with `fetch_youtube.py` and comments, to see whether the audience matches the brief, plus a transcript of one sponsored video when the integration style matters. This is where credits are worth spending, not on the whole pool.
6. **Shortlist deliverable**: tiers (primary, secondary, backup) with the reason for each placement, plus per creator: name, handle, URL, subscribers, median views, public email and its source, the search keywords that surfaced them, and conflict flags. Also list the keyword matrix itself, so the user can repeat the search. Date the table: the figures are a snapshot.

---

## 10. Shared lenses

Run every analysis through these; in past analyses they explained the most:

- **Promise consistency**: do the thumbnail, title, opening, content, CTA and landing page all deliver the same promise? Each mismatch leaks another slice of the funnel.
- **The audience's promise**: viewers subscribe for a certain kind of content, and videos that depart from it get neither platform push nor clicks.
- **Position beats absolute time**: a CTA at minute 12 only means something as a percentage of the runtime.
- **Sample size**: 0 leads versus 3 leads on one video may be noise; state your confidence.
- **Unmeasured is not absent**: backend numbers depend on which paths tracking covers.
- **Age matching**: views accumulate, so compare only equal time since publish.
- **View-count change**: YouTube began counting public views from the first frame on 2026-08-24 and completed the global rollout by 2026-08-28, with each channel switching on some day inside that window. Views on opposite sides of the change are not directly comparable. A video published inside the window may be counted under either rule, so place it by its like/view rate; `view_metric_change.window_excluded` in `summary.json` lists the window videos' rates, which show where the channel switched. When expected views or CPM are quoted on public views, adjust them using the channel's like/view shift (`view_metric_change`), or ask for engaged views (YouTube Analytics, Advanced Mode): they keep the old count and remain the basis of creator earnings.

---

## 11. Reporting

- **Format**: Markdown by default; it opens in any client and pastes into documents. If the host supports web pages or Artifacts and the user needs to share, add an HTML page that charts the timeline, baseline comparison and funnel.
- **Open with 3–5 lines** that answer the objective directly, then expand.
- **Label** data sources (API / vidIQ / user-provided), inferences, and pending items (with who can supply them).
- **Privacy**: refer to commenters as U#; never list personal details.
- **Close with** the vidIQ credits spent, the credits remaining, the reset date, and the API quota units used.
- Write in the user's language. Quotes can stay in the original language with a translation.
