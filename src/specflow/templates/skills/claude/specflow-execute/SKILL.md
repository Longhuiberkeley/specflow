---
name: specflow-execute
description: Use when stories are planned and the user wants to implement them. Orchestrates implementation, updates artifact statuses, and creates test artifacts.
---

# SpecFlow Execute

Orchestrate the implementation of planned stories and update tracking artifacts.

## Workflow

1. **Pre-Execution Check** — Confirm STORY artifacts are `status: approved`. Check for blocking suspect flags.
2. **Implementation** — Write code per the detailed design in DDD artifacts.
3. **Status Updates** — Update STORY and linked spec artifacts to `status: implemented`.
4. **Test Creation** — Generate UT/IT/QT test artifacts that link back to DDD/ARCH/REQ via `verified_by`.
5. **Fingerprint Update** — Recompute fingerprints on modified artifacts.

## Rules

- Always update `modified` timestamp in frontmatter when editing artifacts
- Link tests to what they verify using `verified_by` role
- Run `uv run specflow validate` after status changes

## References

- Read `references/status-lifecycle.md` for valid status transitions.
- Read `references/test-pairing.md` for V-model test pairings.
