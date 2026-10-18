---
id: STORY-663
title: 'CLI backstops: 3-run escalation, pack-validate, autoresearch status codes'
type: story
status: verified
suspect: false
links:
- target: REQ-042
  role: implements
created: '2026-09-13'
fingerprint: sha256:2cb49e04a641
modified: '2026-10-09'
output_files:
- src/specflow/commands/pack_validate.py
version: 1
---

# CLI backstops: 3-run escalation, pack-validate, autoresearch status codes

Per SPIKE-002 STORY-8 section. Gates STORY 9 and the HIGH-risk cuts; implement before them.

## Acceptance Criteria

1. Full `specflow artifact-lint` runs escalate warnings persisting across 3 runs to blocking; counts persist in `.specflow/lint-warning-history.yaml`; filtered `--type` runs do not advance counts and a fixed warning resets (tests/test_artifact_lint.py).

> Amended 2026-10-18 (SPIKE-008 R1-144): AC1 was superseded by the findings-baseline ratchet (DEC-099, REQ-053 AC7). Escalation is decided against the committed `.specflow/findings-baseline.yaml`; lint keeps no run counts and writes nothing under `.specflow/`, and `refresh` deletes the legacy `lint-warning-history.yaml` (commands/artifact_lint.py:58-65).

2. `specflow pack-validate <path>` exists and the shipped validate-pack.sh defers to it — no `uv run` in shipped skill scripts (tests/test_cli_commands.py).
3. `specflow autoresearch status` fails/warns on Phase 0 git problems, discard streaks, category-run length, missing research_agenda, and diversity/stuck signals (tests/test_autoresearch_cli.py).
