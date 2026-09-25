---
id: ARCH-038
title: 'Research integrity guards: evaluator fingerprint, jump and guard flags, external
  scores'
type: architecture
status: implemented
suspect: false
links:
- target: REQ-047
  role: derives_from
- target: DEC-088
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:47c45af0ea47
modified: '2026-09-25'
thinking_techniques:
- '[premortem'
- dependency-shock]
---

# Research integrity guards: evaluator fingerprint, jump and guard flags, external scores

## Responsibility
Detect and route metric gaming deterministically: the frozen evaluator fingerprint on COMP, one-shot drift lint routing to the successor-COMP path, noise-denominated single-iteration jump advisories, guard-metric regression warnings, and external score (CV-external relation) rendering with an offline fallback.

## Public interface
- COMP.evaluator_fingerprint recorded at setup (verify command plus evaluation-script hashes)
- artifact_lint: fingerprint-drift check (flag once per COMP, successor routing, never retroactive)
- autoresearch status: jump advisory (k x noise sigma), guard regression warning, CV-external relation; EXPT.external_score, EXPT.guard_metrics optional fields
- competition-setup-protocol: metric bundle with fixed horizon for quant domains

## Dependencies
Uses lib/noise_probe.py sigma; pure frontmatter + filesystem hashing, zero LLM inference; advisory output only (DEC-088).

## Data flow
COMP setup hashes the harness -> each EXPT logs metrics -> status/lint compare against fingerprint, noise floor, and guards -> advisories render; drift routes once to the successor-COMP recipe.
