---
id: STORY-623
title: 'Verification arc: specflow verify + verify_run_* evidence + entry-point sync'
type: story
status: implemented
priority: high
rationale: 'The evidence-recorder half of REQ-037/ARCH-026. Adds specflow verify (run
  a declared verify_command, record verify_run_* evidence), wires it into the execute
  skill as a deterministic step before transitioning to verified, and syncs every
  entry point (CLI reference, lifecycle mermaid+ASCII, README feature table, brief
  --next advisory). Accounting-not-policing throughout: a failing run is recorded,
  never blocking.'
tags:
- v1.13
- verification
- contracts
- entry-point-sync
suspect: false
links:
- target: REQ-037
  role: implements
- target: ARCH-026
  role: derives_from
created: '2026-08-03'
fingerprint: sha256:29ac4ed67fa9
output_files:
- src/specflow/commands/verify.py
- src/specflow/lib/verification.py
- tests/test_verify.py
---

# Verification arc: specflow verify + verify_run_* evidence + entry-point sync

The evidence-recorder half of REQ-037 / ARCH-026.

## Scope

- `specflow verify [ID|--all|--type T] [--evidence-file PATH] [--dry-run]` —
  executes a declared `verify_command` and records `verify_run_at` +
  `verify_run_exit_code` (+ `verify_run_evidence`) on the artifact's frontmatter.
- Contract fields: `verify_command`, `verify_exit_code`, `verify_evidence`
  (declared) and `verify_run_at`, `verify_run_exit_code`, `verify_run_evidence`
  (recorded by the command).
- `/specflow-execute` skill names `specflow verify <ID>` (or `--all`) as a
  deterministic step before transitioning test/story artifacts to `verified`,
  mirroring its existing `specflow artifact-lint` step; new
  `references/verification-contracts.md` documents the fields + invariant.
- Entry-point sync (one atomic unit): `docs/cli-reference.md`, `docs/lifecycle.md`
  (mermaid AND ASCII), README feature table, and the `brief --next` router
  advisory (declared verify_command with no matching verify_run evidence → one
  advisory line, never blocking).
- Shipped skill template and live `.claude/skills/` mirror kept in parity.

## Acceptance criteria

- `specflow verify` writes the recorded run fields; `--dry-run` executes nothing.
- A failing `verify_command` records its real exit code and does NOT block any
  commit, transition, or release, and does NOT escalate the audit to an error.
- `specflow brief --next` emits one advisory line for a contract lacking matching
  run evidence, and is silent for projects with no contracts.
- Skill template and live mirror are byte-identical (parity test green).
- `specflow artifact-lint --method programmatic` adds 0 blocking issues from the
  new artifacts.

## Keystone invariant

A failing `verify_command` is RECORDED, never blocks. The engine never lies about
what happened; it never overrides the human. (accounting-not-policing.)

## Status note

Code in progress this cycle (verify command implementation is concurrent); the
entry-point sync (skill/docs/brief) is the part this story owns directly. Moves
to `verified` once the verify command runs against declared contracts and
records real evidence end-to-end.
