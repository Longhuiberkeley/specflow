---
id: ARCH-LOUDFAIL-d87a
title: Loud-failure and advisory ergonomics command surfaces (v1.13.2)
type: architecture
status: implemented
priority: high
rationale: 'Centralize authoring semantics in Python helpers and commands: precise
  body mutation, validated nested merges, actionable repair hints, and one-pass graph
  accounting; CLI and skills remain thin.'
tags:
- v1.13.2
- ergonomics
- architecture
- accounting-not-policing
suspect: false
links:
- target: REQ-TRANSCRI-24b7
  role: derives_from
created: '2026-08-04'
fingerprint: sha256:f9a476477150
modified: '2026-08-04'
---

## Architecture

### Write surfaces

`commands/update.py` and `commands/create.py` own intent and conflict handling. `lib/artifacts.py` owns schema-aware nested-map merge, status repair, and fingerprint-safe persistence. `lib/lint.py` owns pure, heading-anchored/fence-aware AC-section replacement.

### Advisory surfaces

`commands/artifact_lint.py` decorates existing findings with executable remedies only. `commands/brief.py` uses `lib/impact.py` one-pass downstream-union accounting so `/specflow-start` stays fast and shared downstream artifacts count once. Bare fingerprint refresh is report-only.

### Invariants

- Every body writer is explicit; ambiguous writers fail loudly.
- Established custom fields remain writable.
- Invalid current statuses remain repairable through the CLI.
- Advisories never add warnings or change exit codes.
- Live and shipped skill mirrors remain byte-identical.
