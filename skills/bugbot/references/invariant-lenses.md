# Invariant Candidate Lenses

Use these lenses as **candidate generators** during `Map Affected Behavior` and `Recursive Defect Sweep` in [../SKILL.md](../SKILL.md). Apply only the lenses that match constructs touched by the reviewed change set. Never promote a lens hit directly to a finding; every candidate must still satisfy causal proof and the `Finding Bar`.

## Candidate Lenses

### 1. Self-Re-Entrancy Through Shared Wrappers, Delegates, Or Event Buses

- **When relevant:** an operation arms an in-flight flag, generation or sequence token, or re-entrancy depth counter before calling a shared helper, callback delegate, or event bus.
- **What to trace:** follow the operation's own commit, dispatch, or completion path through that shared layer to verify whether it re-enters the guard it just armed and cancels, aborts, or invalidates itself.

### 2. Eager Acquire/Release Ownership Parity And Non-Transition Cleanup

- **When relevant:** a lock, focus claim, reservation, or subscription is acquired synchronously before asynchronous work completes.
- **What to trace:** enumerate every exit path—cancellation, preemption by a competing caller, validation failure, no-op or unopened return, error, and teardown/unmount—and verify both:
  - release does not depend solely on a UI or lifecycle state transition (such as open-to-closed) that never fires when the state remained unchanged;
  - release on cancel or failure is scoped to the acquiring owner or generation so releasing cannot clobber a newer lock held by an external caller.

### 3. Tri-State Async Lifecycles And Multi-Layer Suppression

- **When relevant:** async work is queued before executing, or cancellation/invalidation spans wrapper and listener layers (for example, guarded by an internal-call depth counter).
- **What to trace:** distinguish **queued**, **executing**, and **settled** states rather than treating pending work as binary. Trace competing calls—including unchanged external callers invoking an inner wrapper directly—that arrive while prior work is queued but not yet executing, and check whether an outer suppression guard blocks the fallback cancellation layer.

### 4. Shared Serialization Queues And Mutex Concurrency Topology

- **When relevant:** network, RPC, storage, or other potentially slow or unbounded `await` calls run inside a shared serial queue, mutex, or single-lane dispatcher.
- **What to trace:** list every other task class sharing that queue (such as live event delivery, lifecycle resets, or interactive state updates) and check whether multi-second or unbounded I/O causes head-of-line blocking that stalls unrelated work.

### 5. Multi-Hop Async Budgets And Abort-Cause Separation

- **When relevant:** a diff introduces, documents, or modifies a timeout, deadline, or cancellation signal in a multi-step async workflow.
- **What to trace:** trace every `await` hop from the entry call through follow-up probes or requests to confirm the budget covers the entire chain rather than only one sub-step. Inspect error and abort handling to verify that internal timeouts remain distinct from external caller cancellation so timeouts are not misclassified as user aborts or allowed to bypass intended fallback behavior.

### 6. Sibling-Caller Precondition Parity And Missing-Vs-Empty Sentinel Collapse

- **When relevant:** a shared helper adds a fallback path, optional hint parameter, or default coercion (such as coercing missing data to an empty string or empty collection).
- **What to trace:** compare preconditions and guards across all callers of the helper. Check whether truthy fallback metadata or hints make an emptiness guard unreachable, and verify that missing or `null` input cannot silently collapse into a valid empty payload.

### 7. Security Capability Polarity Flips

- **When relevant:** a diff changes a security, sandbox, permission, origin, or trust-mode check from an explicit allowlist (`===` or explicit membership) to a negated denylist (`!==` or single-case exclusion).
- **What to trace:** audit every existing caller—including default, omitted/`undefined`, background, and non-interactive callers—plus likely future modes to verify whether the negation silently grants elevated capabilities outside the intended surface.

## Precision Guardrails

Apply these checks before reporting or dismissing any lens-generated candidate:

- **Verify concrete wiring, not names:** inspect actual call sites, bindings, and data flow rather than inferring behavior from parameter, prop, or callback names.
- **Verify cross-boundary contracts:** when HTTP status codes, event phases, or wire protocols cross service, runtime, or sibling-repository boundaries, confirm the peer or upstream contract before claiming a defect.
- **Verify frequency and bounds for performance claims:** trace upstream throttling, debouncing, batching, and realistic input sizes before reporting asymptotic complexity or overhead.
- **Apply universal exclusion to shared mutable state:** never dismiss a leak on shared or unkeyed mutable state from a single normal-path clearing call; verify both non-normal exit paths (abort, error, empty payload) and all codebase writers that bypass the cited clearing path.
