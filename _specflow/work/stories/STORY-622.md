---
id: STORY-622
title: 'v1.12.6 gate patch: kill the foundational-doctrine cry-wolf + add project-audit
  --dry-run (retro)'
type: story
status: verified
priority: high
rationale: "Backfilled record of work that already shipped in v1.12.6. The release-gate\
  \ horizontal analysis falsely flagged every BP/DEC as orphan-provenance (no links),\
  \ escalating 17 cry-wolf structural warns that drowned real findings. BP/DEC are\
  \ foundational doctrine \u2014 upstream-less by design \u2014 so absent links[]\
  \ is correct, not an orphan. Fixed by exempting best-practice and decision in has_provenance\
  \ (mirroring the existing competition exemption). Also added project-audit --dry-run\
  \ so the gate exit code can be checked without dirtying the tree. This is the accounting-side\
  \ half of REQ-037."
tags:
- backfilled
- v1.12.6
- accounting-not-policing
- gate
suspect: false
links:
- target: REQ-037
  role: implements
- target: ARCH-026
  role: derives_from
created: '2026-08-03'
fingerprint: sha256:bebfe53d9f39
---

# v1.12.6 gate patch: kill the foundational-doctrine cry-wolf + add project-audit --dry-run (retro)

Backfilled STORY for work that shipped in v1.12.6 (recorded after the fact so the
v1.13 cycle has a complete REQ→ARCH→STORY chain for the false-confidence theme).

## What shipped (v1.12.6)

- **RC1 cry-wolf kill.** `has_provenance` in the horizontal analysis no longer
  emits "N/N best-practice (or decision) artifacts have no links/provenance":
  `best-practice` and `decision` are foundational doctrine (other artifacts
  derive FROM them), so an empty `links[]` is correct, not orphan-provenance.
  Mirrors the existing exemption for the autoresearch competition root. Dropped
  the release-gate audit from 17 to 16 escalating structural warns.
- **`specflow project-audit --dry-run`.** Prints the full findings/report with
  the identical exit code (errors→3, escalating warns→2, else 0) but skips all
  four write side-effects (audit snapshot dir, AUD artifact, CHL artifacts, the
  cache + index mutations). Enables local pre-push exit-code checks without
  dirtying the tree.

## Acceptance criteria (met)

- A BP or DEC with no `links[]` is NOT flagged as orphan-provenance.
- Genuine orphan-provenance detection for every other type stays intact.
- `specflow project-audit --dry-run` exits with the same code as a real run and
  writes nothing to disk.
- The release-gate audit escalates only on real structural findings (16 warns
  at v1.12.6, down from 17).

## Verification (already on record)

- 825 tests passing (baseline 820; +5, no regressions) per the v1.12.6 changelog.
- `specflow project-audit --dry-run` exits 2 with 16 escalating warns, tree clean.
