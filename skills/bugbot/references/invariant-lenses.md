# Invariant Candidate Lenses

Use these lenses as **candidate generators** during `Map Affected Behavior` and `Recursive Defect Sweep` in [../SKILL.md](../SKILL.md). Apply only the lenses that match constructs touched by the reviewed change set. Never promote a lens hit directly to a finding; every candidate must still satisfy causal proof and the `Finding Bar`.

## Candidate Lenses

### 1. Self-Re-Entrancy Through Shared Wrappers, Delegates, Or Event Buses

- **When relevant:** an operation arms an in-flight flag, generation or sequence token, or re-entrancy depth counter before calling a shared helper, callback delegate, or event bus.
- **What to trace:** follow the operation's own commit, dispatch, or completion path through that shared layer to verify whether it re-enters the guard it just armed and cancels, aborts, or invalidates itself.

### 2. Eager Acquire/Release Ownership, Non-Transition Cleanup, And State-Backfill Parity

- **When relevant:** a provisional lock, focus claim, gate, override, or subscription is acquired synchronously before asynchronous work completes.
- **What to trace:** enumerate every exit path—cancellation, preemption by a competing caller, validation failure, no-op or unopened return, error, and teardown/unmount—and verify all three:
  - release does not depend solely on a UI or lifecycle state transition (such as open-to-closed) that never fires when the state remained unchanged;
  - release on cancel or failure is scoped to the acquiring owner or generation so releasing cannot clobber a newer lock held by an external caller;
  - **state-backfill / restoration parity:** when a provisional lock, gate, or override is released on failure, no-op, or cancellation, background streams, queued updates, or suppressed first-time work accumulated while locked actively catch up and restore consistent visible state rather than remaining frozen, stale, or blank.

### 3. Tri-State Async Lifecycles And Multi-Layer Suppression

- **When relevant:** async work is queued before executing, or cancellation/invalidation spans wrapper and listener layers (for example, guarded by an internal-call depth counter).
- **What to trace:** distinguish **queued**, **executing**, and **settled** states rather than treating pending work as binary. Trace competing calls—including unchanged external callers invoking an inner wrapper directly—that arrive while prior work is queued but not yet executing, and check whether an outer suppression guard blocks the fallback cancellation layer.

### 4. Serialization Queues, Mutex Topology, And Concurrency Relaxation

- **When relevant:** network, RPC, storage, or other potentially slow or unbounded `await` calls enter a shared serial queue, mutex, or single-lane dispatcher, **or** work is moved off a serial queue, mutex, or exclusive lock (or split across a new `await` boundary).
- **What to trace (serialization risk):** when I/O enters a shared serial lane, list every other task class sharing that lane (such as live event delivery, lifecycle resets, or interactive state updates) and check whether multi-second or unbounded I/O causes head-of-line blocking that stalls unrelated work.
- **What to trace (de-serialization / concurrency-relaxation risk):** when work leaves a serial queue, mutex, or lock—or splits across a new `await`—re-audit **unchanged** `await` resumption points and synchronous guard helpers sharing that state. Check for missing post-`await` staleness, lock, or revision re-checks before state mutation, and inspect unchanged guard helpers for stale closure precedence or non-atomic reads that only held under prior serialization.

### 5. Multi-Hop Async Budgets And Abort-Cause Separation

- **When relevant:** a diff introduces, documents, or modifies a timeout, deadline, or cancellation signal in a multi-step async workflow.
- **What to trace:** trace every `await` hop from the entry call through follow-up probes or requests to confirm the budget covers the entire chain rather than only one sub-step. Inspect error and abort handling to verify that internal timeouts remain distinct from external caller cancellation so timeouts are not misclassified as user aborts or allowed to bypass intended fallback behavior.

### 6. Sibling-Caller Precondition Parity And Missing-Vs-Empty Sentinel Collapse

- **When relevant:** a shared helper adds a fallback path, optional hint parameter, or default coercion (such as coercing missing data to an empty string or empty collection).
- **What to trace:** compare preconditions and guards across all callers of the helper. Check whether truthy fallback metadata or hints make an emptiness guard unreachable, and verify that missing or `null` input cannot silently collapse into a valid empty payload.

### 7. Security Capability Polarity Flips

- **When relevant:** a diff changes a security, sandbox, permission, origin, or trust-mode check from an explicit allowlist (`===` or explicit membership) to a negated denylist (`!==` or single-case exclusion).
- **What to trace:** audit every existing caller—including default, omitted/`undefined`, background, and non-interactive callers—plus likely future modes to verify whether the negation silently grants elevated capabilities outside the intended surface.

### 8. Async Continuation Context Capture And Post-Predicate Gating

- **When relevant:** an async callback, continuation, or completion handler runs after an earlier trigger and evaluates staleness, cancellation, or ownership before triggering downstream side effects.
- **What to trace:**
  - **initiation-time capture:** verify that the continuation compares against a sequence number, identity, or ownership token captured when the operation started rather than reading mutable shared state at callback execution time, where concurrent operations can advance or overwrite it;
  - **post-predicate ownership gating:** verify that when a cancellation or rejection predicate evaluates false and execution proceeds, downstream side effects still respect active locks, focus claims, or ownership boundaries rather than executing unconditionally.

## Precision Guardrails

Apply these checks during candidate discovery and before reporting or dismissing any lens-generated candidate:

- **Verify concrete wiring, not names:** inspect actual call sites, bindings, and data flow rather than inferring behavior from parameter, prop, or callback names.
- **Inspect cross-boundary contracts for both discovery and verification:** when status codes, event phases, payload optionality, concurrency models, or timing and wire protocols cross service, runtime, or sibling-repository boundaries, actively inspect the upstream or peer contract whenever it governs the diff's assumptions—both to discover violated assumptions (such as concurrent emissions or optional fields) and to suppress false positives before reporting.
- **Verify frequency and bounds for performance claims:** trace upstream throttling, debouncing, batching, and realistic input sizes before reporting asymptotic complexity or overhead.
- **Verify the exact branch before dismissing:** never dismiss a candidate by superficial analogy to a different lifecycle transition (such as user-initiated teardown vs a failed operation leaving state active) or by conflating distinct operational modes (such as in-progress streaming vs completed fallback); verify the branch's exact preconditions, guard predicates, and resulting visible state.
- **Apply universal exclusion to shared mutable state:** never dismiss a leak on shared or unkeyed mutable state from a single normal-path clearing call; verify both non-normal exit paths (abort, error, empty payload) and all codebase writers that bypass the cited clearing path.
