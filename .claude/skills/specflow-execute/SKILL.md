---
name: specflow-execute
description: Use when stories are planned and the user wants to implement them. Orchestrates implementation, updates artifact statuses, and creates test artifacts.
---

# SpecFlow Execute

Orchestrate the implementation of planned stories and update tracking artifacts.

## Workflow

### Step 1: Pre-Execution Check

1. Read all STORY artifacts from `_specflow/work/stories/`.
2. Verify stories have `status: approved`. If not, tell the user which need approval.
3. Check for blocking `suspect: true` flags on linked artifacts. If upstream specs are suspect, warn the user before proceeding.
4. Run `uv run specflow status` silently to get the current state overview.

### Step 2: Wave Planning

1. Run `uv run specflow go --dry-run` to compute the execution wave plan.
2. Review the wave groupings — stories in the same wave can run in parallel.
3. If the wave plan looks wrong, check story dependencies (`derives_from`, shared `specified_by`).
4. Read `references/wave-computation.md` for algorithm details.

### Step 3: Implementation

For each story (or wave of stories):

1. Run `uv run specflow go` to execute all waves, or implement manually:
   a. **Load context:** Read the story, its linked REQ, ARCH, and DDD artifacts.
   b. **Implement the code** per the detailed design in DDD artifacts.
   c. **Follow the acceptance criteria** — implement each criterion from the story.

### Step 4: Status Updates

After implementation, update artifact statuses:

```
uv run specflow update STORY-001 --status implemented
```

If the linked DDD/ARCH artifacts should reflect implementation:
```
uv run specflow update DDD-001 --status implemented
```

**Execution state is machine-managed.** `specflow go` writes per-artifact locks to `.specflow/locks/*.json` while waves run and tracks progress in `.specflow/execution-state.yaml`. Do not edit these by hand — the CLI releases locks on completion and uses `execution-state.yaml` to resume interrupted runs.

### Step 5: Test Creation

For each implemented spec artifact, create its V-model verification test — **all three levels**, not just unit tests:

| Spec type | Test type | Link role |
|-----------|-----------|-----------|
| REQ | QT (qualification test) | `verified_by` |
| ARCH | IT (integration test) | `verified_by` |
| DDD | UT (unit test) | `verified_by` |

```
uv run specflow create \
  --type unit-test \
  --title "Test <DDD function>" \
  --links "[{\"target\": \"DDD-001\", \"role\": \"verified_by\"}]" \
  --body "<test cases>"
```

Read `references/test-pairing.md` when you are unsure which test level a given change needs.

### Step 5.5: Human-Review Summary

Before running full validation, present a structured summary so the user can catch silent implementation decisions:

```
## Summary for Human Review

### Key Decisions Made
- Implementation choices not pre-specified by DDD (library/framework picks, file layout)
- Test strategy: how QT / IT / UT are split per story, and where you stopped
- Any deviation from the linked ARCH/DDD and why

### Assumptions That Need Validation
- External dependencies assumed available in test (stubs, fixtures, network) — risk if wrong: tests pass locally but fail in CI
- Performance/latency assumptions baked into code — risk if wrong: NFRs silently violated
- Any STORY that was implemented without a linked DDD — risk if wrong: future changes lack a specification anchor

### Please Review
- For each STORY: does every acceptance criterion map to at least one of UT / IT / QT?
- Any STORY marked `implemented` whose linked ARCH/DDD is still `approved` (not `implemented`)?
- Any code file written that is NOT referenced by a test artifact?
```

Wait for user acknowledgement before proceeding.

### Step 6: Validation

Run full validation after all changes:
```
uv run specflow artifact-lint
```

Report results and fix any issues.

**Exit message:** Report the count of stories marked `implemented` and tests created (UT/IT/QT). Recommend the next skill — `/specflow-artifact-review`.

## Rules

- Always update `status` and `modified` timestamp via `specflow update` — never edit artifact files directly.
- Link tests to what they verify using `verified_by` role.
- Run `uv run specflow artifact-lint` after status changes.
- When unsure about valid status transitions, read `references/status-lifecycle.md`.
- When unsure about V-model test pairing, read `references/test-pairing.md`.

## References

- `references/status-lifecycle.md` — Valid status transitions for all artifact types.
- `references/test-pairing.md` — V-model verification test pairing rules.
- `references/wave-computation.md` — Wave computation algorithm and context isolation.
