---
id: STORY-625
title: Pre-adoption baseline traceability
type: story
status: implemented
priority: low
rationale: Single documented baseline bucket for source files with no defensible SpecFlow
  owner (predating STORY adoption or external-tool artifacts). Closes the orphan-code
  structural signal honestly via real traceability, never by demotion. Part of the
  v1.13 orphan-code adoption arc (REQ-037).
tags:
- traceability
- baseline
- orphan-code
- v1.13
- accounting-not-policing
suspect: false
links:
- target: REQ-037
  role: implements
created: '2026-08-03'
fingerprint: sha256:fccf88e2d5f3
output_files:
- src/specflow/packs/ops/pack.yaml
- src/specflow/packs/ops/schemas/monitor.yaml
- src/specflow/packs/ops/schemas/run.yaml
- tests/test_ops_pack.py
version: 1
---

# Pre-adoption baseline traceability

## Baseline handshake

This STORY is the traceability home for source files that have no defensible
SpecFlow owner — files that predate STORY adoption entirely or that are
external-tool artifacts no SpecFlow STORY genuinely owns. It is the
"as-built baseline" residue bucket described in the v1.13 orphan-code adoption
arc (REQ-037 / STORY-624): rather than mint per-file junk links, every
honestly-ownerless file rolls up to this single documented baseline.

## What lives here

Files attributed to this baseline are those for which none of the three
attribution orders produced a defensible owner:
  (a) wave-commit message story IDs — none in this repo's history;
  (b) git-history commit → STORY mapping — no STORY ref in the shaping commits;
  (c) feature-area → owning STORY — no feature area matches.

Each file listed in `output_files` below is genuinely ownerless from SpecFlow's
standpoint (e.g. an external AI-tool session/state cache committed to the repo),
and is recorded here so the orphan-code meter reaches zero honestly rather than
by demotion. This is accounting, not policing (BP-006): the structural signal
orphan-code stays escalating in general, and is closed here ONLY by real
traceability — every file is named against the bucket that truthfully owns it.

## Residue inventory

See `output_files`. As of the v1.13.0 sweep the baseline holds the v1.10.0 ops
pack — `pack.yaml`, the `monitor`/`run` schemas, and `tests/test_ops_pack.py` —
shipped at commit `381305e` with no STORY: none of the three attribution orders
(wave-commit IDs, git-history → STORY, feature-area → owning STORY) yields a
defensible owner, so it rolls up here. If future ownerless files appear, they
are added here, not orphaned.

The Antigravity-CLI session cache that previously lived here is now excluded
from source scanning on principle (it is an external-tool cache dir, not code),
so it no longer requires a baseline home.
