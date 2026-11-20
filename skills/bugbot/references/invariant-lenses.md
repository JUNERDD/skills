# Invariant Candidate Lenses

Use these lenses as **candidate generators** during `Map Affected Behavior` and `Recursive Defect Sweep` in [../SKILL.md](../SKILL.md). Apply only the lenses that match constructs touched by the reviewed change set. Never promote a lens hit directly to a finding; every candidate must still satisfy causal proof and the `Finding Bar`.

## Candidate Lenses

### 1. Self-Re-Entrancy Through Shared Wrappers, Delegates, Or Event Buses

- **When relevant:** an operation arms an in-flight flag, generation or sequence token, or re-entrancy depth counter before calling a shared helper, callback delegate, or event bus.
- **What to trace:** follow the operation's own commit, dispatch, or completion path through that shared layer to verify whether it re-enters the guard it just armed and cancels, aborts, or invalidates itself.

### 2. Eager Acquire/Release Ownership, Non-Transition Cleanup, And State-Backfill Parity

- **When relevant:** a provisional lock, focus claim, gate, override, or subscription is acquired synchronously before asynchronous work completes.
- **What to trace:** enumerate every exit path—cancellation, preemption by a competing caller, validation failure, no-op or unopened return, error, and teardown/unmount—and verify all five:
  - release does not depend solely on a UI or lifecycle state transition (such as open-to-closed) that never fires when the state remained unchanged;
  - release on cancel or failure is scoped to the acquiring owner or generation so releasing cannot clobber a newer lock held by an external caller;
  - **state-backfill / restoration parity:** when a provisional lock, gate, or override is released on failure, no-op, or cancellation, background streams, queued updates, or suppressed first-time work accumulated while locked actively catch up and restore consistent visible state rather than remaining frozen, stale, or blank;
  - **external passive-observer pause-vs-abandon parity:** sweep external readers and observers of the provisional lock or pending flag (such as restore flows, deep-link hydrators, or background retry effects) and verify they pause and **reactively retry**—via a real subscription or revision signal rather than a non-reactive imperative getter—when a provisional attempt exits without taking ownership, rather than permanently marking consume-once state resolved or dropping explicit target identifiers;
  - **two-phase skeleton / in-place completion parity:** distinguish suppressing a new initial auto-open from blocking an in-place completion update for an already-mounted pending skeleton while a provisional lock is active, ensuring the skeleton is not stranded in a loading state if the provisional attempt exits unopened while still preventing updates after committed takeover, replacement, or close.

### 3. Tri-State Async Lifecycles And Multi-Layer Suppression

- **When relevant:** async work is queued before executing, or cancellation/invalidation spans wrapper and listener layers (for example, guarded by an internal-call depth counter).
- **What to trace:** distinguish **queued**, **executing**, and **settled** states rather than treating pending work as binary. Trace competing calls—including unchanged external callers invoking an inner wrapper directly—that arrive while prior work is queued but not yet executing, and check whether an outer suppression guard blocks the fallback cancellation layer.

### 4. Serialization Queues, Mutex Topology, And Concurrency Relaxation

- **When relevant:** network, RPC, storage, or other potentially slow or unbounded `await` calls enter a shared serial queue, mutex, or single-lane dispatcher, **or** work is moved off a serial queue, mutex, or exclusive lock (or split across a new `await` boundary).
- **What to trace (serialization risk):** when I/O enters a shared serial lane, list every other task class sharing that lane (such as live event delivery, lifecycle resets, or interactive state updates) and check whether multi-second or unbounded I/O causes head-of-line blocking that stalls unrelated work.
- **What to trace (de-serialization / concurrency-relaxation risk):** when work leaves a serial queue, mutex, or lock—or splits across a new `await`—re-audit **unchanged** `await` resumption points and synchronous guard helpers sharing that state. Check for missing post-`await` staleness, lock, or revision re-checks before state mutation, and inspect unchanged guard helpers for stale closure precedence or non-atomic reads that only held under prior serialization.

### 5. Multi-Hop Async Budgets, Handshake Deadlines, And Abort-Cause Separation

- **When relevant:** a diff introduces, documents, or modifies a timeout, deadline, or cancellation signal in a multi-step async workflow, **or** introduces or caches a single-flight, event, `postMessage`, or responder-handshake Promise (especially in shared or module-singleton state).
- **What to trace:**
  - **end-to-end budget and abort separation:** trace every `await` hop from the entry call through follow-up probes or requests to confirm the budget covers the entire chain rather than only one sub-step. Inspect error and abort handling to verify that internal timeouts remain distinct from external caller cancellation so timeouts are not misclassified as user aborts or allowed to bypass intended fallback behavior;
  - **bounded handshakes and uniform cleanup:** for single-flight, event, `postMessage`, or responder-handshake Promises, verify a bounded settlement deadline exists so missing responders, unmounted listeners, or synchronous dispatch throws cannot leave a cached Promise permanently unsettled or leak listeners, and confirm settlement cleanup clears timers, listeners, and cached state uniformly across success, failure, timeout, and synchronous throw paths.

### 6. Sibling-Caller Parity, Conflated Guards, And Missing-Vs-Empty Sentinel Collapse

- **When relevant:** a shared helper, controller, or fallback path adds a fallback branch, optional hint parameter, upgrade/monotonicity guard, or default coercion (such as coercing missing data to an empty string or empty collection); combines distinct throttle, cooldown, or backoff guards; or enriches an async helper's return union or side effects shared across multiple callers.
- **What to trace:**
  - **input sentinels and ownership parity:** compare preconditions, guards, and ownership outcomes across all callers or entry paths. Check whether truthy fallback metadata or hints make an emptiness guard unreachable, verify that missing or `null` input cannot silently collapse into a valid empty payload, and check upgrade or fallback length/version guards (such as `current && candidate.length > current.length`) for truthy short-circuits that reject empty (`""`) or `undefined` inputs from receiving a more complete snapshot. Never excuse a failed user-initiated action (exiting unopened and dropping user focus or lock ownership) by citing a passive background replay that leaves ownership or locking unmet;
  - **conflated guard predicates:** when one predicate or exemption gates distinct cooldown and error-backoff states, verify an exemption valid for one state (such as idempotent retry during post-success cooldown) does not silently bypass another (such as server-triggered error backoff);
  - **return-union and post-`await` side-effect parity:** when an async helper mutates shared state and returns terminal metadata or notices, inspect every sibling caller (interactive, reload/recovery, background sync) to ensure post-`await` state guards do not short-circuit on the helper's own state transition and drop terminal outcomes.

### 7. Security Capability Polarity Flips

- **When relevant:** a diff changes a security, sandbox, permission, origin, or trust-mode check from an explicit allowlist (`===` or explicit membership) to a negated denylist (`!==` or single-case exclusion).
- **What to trace:** audit every existing caller—including default, omitted/`undefined`, background, and non-interactive callers—plus likely future modes to verify whether the negation silently grants elevated capabilities outside the intended surface.

### 8. Async Continuation Context Capture And Post-Predicate Gating

- **When relevant:** an async callback, continuation, or completion handler runs after an earlier trigger and evaluates staleness, cancellation, or ownership before triggering downstream side effects.
- **What to trace:**
  - **initiation-time capture:** verify that the continuation compares against a sequence number, identity, or ownership token captured when the operation started rather than reading mutable shared state at callback execution time, where concurrent operations can advance or overwrite it;
  - **post-predicate ownership gating:** verify that when a cancellation or rejection predicate evaluates false and execution proceeds, downstream side effects still respect active locks, focus claims, or ownership boundaries rather than executing unconditionally.

### 9. Speculative Or Multi-Phase Persistence Vs. Rollback Invalidation Symmetry

- **When relevant:** a workflow persists state or snapshots during intermediate or pre-terminal phases (such as streaming chunks, argument-completion hooks, or optimistic writes) while error classification, cancellation, or retry arrives in a later phase (such as a terminal result, run reset, or abort), **or** an async persistent cache or store tracks keys in memory for invalidation, overwrite, and bulk teardown.
- **What to trace:**
  - **real cross-phase wire order:** verify the actual producer or upstream event sequence across phases rather than assuming a later rollback or error skips earlier persistence;
  - **rollback-before-flush ordering:** confirm rollback or error classification runs **before** flushing queued deltas or triggering speculative renders or writes;
  - **symmetric cache invalidation with revision fencing:** verify rollback invalidates every memory and async or persistent cache written by earlier phases—including unchanged cache classes—using monotonic revision or state guards so in-flight async writes, error-path fallbacks, secondary caches, or concurrent reads cannot resurrect invalidated data;
  - **async delete failure vs. bulk-teardown key retention:** verify in-memory tracking keys required by bulk teardown (such as `clearAll`-style cleanup) are not discarded before async persistent deletion succeeds, and clear pending-delete tracking only after a subsequent overwrite write succeeds rather than before it settles so a failed write falling back to memory cannot lose cleanup tracking for the stale persistent record.

## Precision Guardrails

Apply these checks during candidate discovery and before reporting or dismissing any lens-generated candidate:

- **Verify concrete wiring, not names:** inspect actual call sites, bindings, and data flow rather than inferring behavior from parameter, prop, or callback names.
- **Inspect cross-boundary contracts for both discovery and verification:** when status codes, event phases, payload optionality, concurrency models, or timing and wire protocols cross service, runtime, or sibling-repository boundaries, actively inspect the upstream or peer contract whenever it governs the diff's assumptions—both to discover violated assumptions (such as concurrent emissions or optional fields) and to suppress false positives before reporting.
- **Verify frequency and bounds for performance claims:** trace upstream throttling, debouncing, batching, and realistic input sizes before reporting asymptotic complexity or overhead.
- **Verify the exact branch before dismissing:** never dismiss a candidate by superficial analogy to a different lifecycle transition (such as user-initiated teardown vs a failed operation leaving state active) or by conflating distinct operational modes (such as in-progress streaming vs completed fallback); verify the branch's exact preconditions, guard predicates, and resulting visible state.
- **Reject diff-comment excuses and speculative baseline dismissals:** never cite a diff-added or diff-modified comment as sole authority for intentional UX degradation, and inspect actual baseline code before dismissing an exposed or widened defect as pre-existing.
- **Audit test mirages before citing passing tests:** check added or modified tests for synthetic sequences omitting real upstream phases (trace the omitted phase statically in production) and pre-action state or omitted call-count assertions after resetting mocks or spies that make checks vacuous.
- **Apply universal exclusion to shared mutable state:** never dismiss a leak on shared or unkeyed mutable state from a single normal-path clearing call; verify both non-normal exit paths (abort, error, empty payload) and all codebase writers that bypass the cited clearing path.
