# Thinking Techniques for Execution

Lightweight thinking checks during implementation. These are quick — a single question asked before writing code — not full adversarial reviews.

## Techniques

### Worst-Case User (Quick)

Before implementing a function that handles input or external data:

- **What to ask:** "What's the most unexpected input this could receive?"
- **How to apply:** Add one edge case to the test stub

### Composition Check (Quick)

Before implementing a feature that shares state with another:

- **What to ask:** "Does STORY-X already modify this state? What happens if both run?"
- **How to apply:** Verify the DDD accounts for concurrent or sequential feature interaction

### Graceful Degradation

Before writing the happy-path code:

- **What to ask:** "If a downstream call (DB, network, external service) fails or times out, what does this code do — crash, hang, or degrade?"
- **How to apply:** Add an explicit fallback path or a clearly-bounded failure mode (timeout + raise + caller-handles). Add one test that exercises the failure path. If the DDD didn't specify the degraded mode, flag it back to plan rather than guessing.

### Partial-Rollout Safety

Before merging a STORY whose linked siblings haven't shipped yet:

- **What to ask:** "If only this STORY merges and STORY-Y / STORY-Z stall for two weeks, does the system stay correct? Does it stay usable?"
- **How to apply:** Either gate the new behavior behind a flag, or split the change so the merged piece is a no-op until siblings land. Avoid hidden ordering dependencies between stories in the same wave.

### Observability

Before closing a STORY as `implemented`:

- **What to ask:** "When this is broken in prod, how will we know — log, metric, error rate, user report? If the only signal is 'someone notices', the observability is missing."
- **How to apply:** Add a structured log line at the boundary (entry + outcome), or a counter/error metric tied to the acceptance criteria. Don't add observability you can't justify; do add it for any path the AC says must succeed.

## Default Application

For `/specflow-execute`, these are applied as quick mental checks during implementation — not as a separate step. The skill should weave them into the implementation loop naturally:

- Before writing code for a STORY: "Any edge cases the DDD didn't cover?" + "What happens when a dependency fails?"
- Before closing a STORY as `implemented`: "Does this interact with another STORY in this wave?" + "If only this STORY merges, is the system still correct?" + "How will we know when this breaks in prod?"

For deeper analysis, the user should run `/specflow-artifact-review` on the completed artifacts.
