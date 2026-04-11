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

### Step 2: Story Selection

1. Present available stories to the user with their priorities and dependencies.
2. Ask: "Which story (or stories) should we implement?"
3. If multiple stories are independent (no shared dependencies), they can be implemented in parallel waves.
4. If stories depend on each other, implement in dependency order.

### Step 3: Implementation

For each story being implemented:

1. **Load context:** Read the story, its linked REQ, ARCH, and DDD artifacts. This gives the full specification context.
2. **Implement the code** per the detailed design in DDD artifacts.
3. **Follow the acceptance criteria** — implement each criterion from the story.

### Step 4: Status Updates

After implementation, update artifact statuses:

```
uv run specflow update STORY-001 --status implemented
```

If the linked DDD/ARCH artifacts should reflect implementation:
```
uv run specflow update DDD-001 --status implemented
```

### Step 5: Test Creation

For each implemented spec artifact, create its V-model verification test:

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

### Step 6: Validation

Run full validation after all changes:
```
uv run specflow validate
```

Report results and fix any issues.

## Rules

- Always update `status` and `modified` timestamp via `specflow update` — never edit artifact files directly.
- Link tests to what they verify using `verified_by` role.
- Run `uv run specflow validate` after status changes.
- When unsure about valid status transitions, read `references/status-lifecycle.md`.
- When unsure about V-model test pairing, read `references/test-pairing.md`.

## References

- `references/status-lifecycle.md` — Valid status transitions for all artifact types.
- `references/test-pairing.md` — V-model verification test pairing rules.
