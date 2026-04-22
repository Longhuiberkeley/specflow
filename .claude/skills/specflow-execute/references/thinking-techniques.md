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

## Default Application

For `/specflow-execute`, these are applied as quick mental checks during implementation — not as a separate step. The skill should weave them into the implementation loop naturally:

- Before writing code for a STORY: "Any edge cases the DDD didn't cover?"
- Before closing a STORY as `implemented`: "Does this interact with another STORY in this wave?"

For deeper analysis, the user should run `/specflow-artifact-review` on the completed artifacts.
