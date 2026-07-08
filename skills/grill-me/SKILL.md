---
name: grill-me
description: Deeply pressure-test a plan or design by asking one question at a time until assumptions, tradeoffs, risks, failure modes, and scope edges are explicit. Use when the user asks to be grilled, wants a plan or design stress-tested, or needs the live conversation kept in sync with a local Markdown Q&A log.
---

# Grill Me

Pressure-test a plan or design until it is decision-ready. The log is support infrastructure, not the goal. The goal is to expose hidden assumptions, weak tradeoffs, missing branch decisions, and operational gaps before they harden into a plan.

## Depth Standard

Do not stop at surface clarification. Keep questioning until the plan is concrete enough that another engineer could:

- explain the goal, success criteria, and non-goals
- name the critical constraints, assumptions, and unknowns
- compare the main alternatives and why one wins
- describe the major failure modes, edge cases, and irreversible decisions
- state how the decision will be validated, rolled out, monitored, and, if needed, rolled back

Use the highest-leverage unresolved question each turn. Prefer the dependency that blocks many later decisions.

## Coverage Map

Before finalizing, make sure the grilling pass has covered the relevant branches. Not every session needs every branch, but skipping a relevant one is a failure.

- objective, problem statement, and success criteria
- scope, non-goals, phase boundaries, and what is intentionally deferred
- stakeholders, owners, and who pays the cost of failure
- assumptions, evidence, and what would falsify them
- constraints: time, staffing, budget, compatibility, compliance, latency, scale, or policy
- alternatives considered and why they were rejected
- tradeoffs and why the chosen downside is acceptable
- failure modes, abuse cases, edge cases, and one-way-door decisions
- testing, observability, rollout, migration, and rollback
- open unknowns that should block implementation instead of being hand-waved away

## Question Selection

1. Inspect the codebase or existing docs first when a question can be answered locally. Only ask the user when the uncertainty is genuinely external.
2. Ask one question at a time, but stay on the current branch until the answer is operationally useful. Do not breadth-scan ten shallow topics when one foundational decision is still vague.
3. Prefer questions that force consequence, ownership, or measurable boundaries:
   - "What breaks if this assumption is wrong?"
   - "Which alternative did you reject, and why is that cost acceptable?"
   - "How will we know this decision failed in production?"
   - "What is the last safe rollback point?"
4. If the user answers vaguely, sharpen the question. Do not accept words like `simple`, `robust`, `secure`, `scalable`, `later`, or `MVP` without making them concrete.
5. If the user's answer conflicts with your recommendation, follow the consequence of that divergence instead of immediately moving on.
6. If a branch reveals a more fundamental missing decision, pivot upward and resolve that parent decision first.

## Question Quality

Prefer pressure over pleasantries. Weak questions collect narration. Strong questions surface commitments, tradeoffs, and failure boundaries.

- Weak: "How will auth work here?"
  Stronger: "Which actor or threat model makes this auth design necessary, and what unacceptable failure must it prevent?"
- Weak: "How will this scale?"
  Stronger: "At what concrete load or growth assumption does the current design stop being acceptable, and what is the planned escape hatch?"
- Weak: "Do we have a rollback plan?"
  Stronger: "What change here is hard to reverse, and what is the last safe rollback point if rollout goes wrong?"

## Host Adaptation

Before asking the first question in a session:

- Resolve the workspace root. Prefer `git rev-parse --show-toplevel`; otherwise use the current working directory.
- Resolve the installed helper path for `scripts/grill_log.py`. Check the workspace copy first, then direct and collection-style installed-skill locations.
- Treat bundled files as relative to the resolved `grill-me` skill directory, not the target project cwd.
- Determine the session key. Prefer `CODEX_THREAD_ID`. If it is unavailable, choose one stable manual key and reuse it for the whole grilling session.

Normal path:

```bash
workspace_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
helper=""

for candidate in \
  "$workspace_root/skills/grill-me/scripts/grill_log.py" \
  "$workspace_root/grill-me/scripts/grill_log.py" \
  "$HOME/.agents/skills/grill-me/scripts/grill_log.py" \
  "$HOME/.codex/skills/grill-me/scripts/grill_log.py"
do
  if [ -f "$candidate" ]; then
    helper="$candidate"
    break
  fi
done

if [ -z "$helper" ]; then
  for skill_root in "$HOME/.agents/skills" "$HOME/.codex/skills"; do
    [ -d "$skill_root" ] || continue
    candidate="$(find -L "$skill_root" -path "*/grill-me/scripts/grill_log.py" -type f -print 2>/dev/null | head -n 1)"
    if [ -n "$candidate" ]; then
      helper="$candidate"
      break
    fi
  done
fi

[ -n "$helper" ] || { echo "grill_log.py not found" >&2; exit 1; }
```

For exact command patterns, helper discovery, and recovery commands, read [logged-grilling.md](./references/logged-grilling.md).

## Hard Gates

- Before any user-facing clarification question, run the `ask` command in the current turn and wait for success.
- After every user answer, run the `answer` command in the current turn before follow-up analysis. Do only the minimal normalization needed for logging: pass the raw user reply as `--answer` and a planning-ready confirmed conclusion as `--resolved-answer`.
- If `ask` or `answer` fails, stop and tell the user the logging step failed. Do not continue the grilling flow until the log is repaired.
- Use workspace mode during normal operation. Treat `new`, `latest`, and explicit `--file` updates as repair tools, not the default path.
- Keep one pending question at a time. Do not ask the next question until the previous answer is backfilled.

## Answer Normalization

Treat the transcript `Answer` field as the confirmed conclusion, not as a raw echo of the user's message. The raw user reply is audit context only.

- If the user accepts the recommendation (`yes`, `按推荐来`, `sounds good`, or equivalent), set `--resolved-answer` to the actual recommendation.
- If the user modifies the recommendation, set `--resolved-answer` to the merged decision: the accepted parts plus the user's explicit change.
- If the user gives a vague or incomplete reply, set `--resolved-answer` to the concrete part that is confirmed and immediately ask a logged follow-up for the unresolved gap.
- Do not write a planning outcome whose answer is only `按推荐来`, `yes`, `OK`, `later`, `MVP`, or another pointer back to context. It must stand alone for a later planning pass.
- Preserve the exact raw user reply through `--answer`; do not hide reversals, hesitation, or wording that may matter later.

## Workflow

1. Resolve local answers first when the codebase or docs already contain them. Do not waste a user turn on a question the repository can answer.
2. Select the single highest-leverage unresolved question using the depth standard and coverage map above.
3. When you are about to ask a clarification question, log it first:

```bash
python3 "$helper" ask \
  --workspace "$workspace_root" \
  --question "..." \
  --recommendation "..."
```

4. Only after the log write succeeds, send exactly one question to the user. Include your recommended answer in the same message.
5. When the user replies, your first action is to backfill that reply:

```bash
python3 "$helper" answer \
  --workspace "$workspace_root" \
  --answer "..." \
  --resolved-answer "..."
```

6. Only after the answer write succeeds, decide whether the current branch is actually resolved or whether the answer created a sharper follow-up.
7. Conclude only when the depth standard is met or the remaining gaps are explicitly identified as blocking unknowns. Do not stop merely because several questions have already been asked.
8. When the grilling session is complete, finalize it before presenting the result:

```bash
python3 "$helper" finalize --workspace "$workspace_root"
```

9. Finalization writes a planning-ready outcome Markdown file, marks the transcript as finalized, removes the temporary `.active-*` pointer for the session, and prints both the transcript path and the outcome path.
10. Tell the user where both the finalized transcript and the planning-ready outcome file live.

## Response Shape

When asking:

1. Run the log command.
2. Ask one concrete question that targets the highest-leverage unresolved branch.
3. Include the recommended answer.

When the user answers:

1. Run the backfill command first, with raw answer and resolved answer separated.
2. Then either ask the next logged question or conclude with the transcript and outcome paths.

When concluding:

1. Run the finalize command.
2. Tell the user where the transcript and planning-ready outcome file were written.

## Guardrails

- Never let logging mechanics crowd out interrogation depth.
- Never conclude because "enough questions" were asked; conclude only when the core design is decision-ready or the unresolved blockers are explicit.
- Never breadth-scan every topic with shallow questions when one branch is still underspecified.
- Never ask soft preference questions when the real issue is risk, tradeoff, ownership, evidence, or irreversibility.
- Never accept vague language such as `simple`, `robust`, `secure`, `scalable`, `later`, or `MVP` without forcing specificity.
- Never let "we will figure it out later" pass unless later has an owner, a trigger, and an acceptable risk.
- Never recommend an answer without pressure-testing what it costs and what could falsify it.
- Never ask a clarification question from memory and promise yourself you will log it later.
- Never turn the user's raw acknowledgement into the final planning answer. Convert it into the confirmed decision first, while preserving the raw reply separately.
- Never keep the current log path only in shell variables or model memory when the helper can recover it from workspace state.
- Never rewrite earlier answers in place to reflect a changed decision. Capture reversals as new follow-up questions.
- Never end the grilling session without writing the planning-ready outcome Markdown file.
- Never leave the session's `.active-*` pointer behind after successful finalization.
- Never stage, commit, amend, push, or otherwise change Git state unless the user explicitly asks for that Git action.
