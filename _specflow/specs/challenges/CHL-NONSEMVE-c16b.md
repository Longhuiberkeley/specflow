---
id: CHL-NONSEMVE-c16b
title: Non-semver baseline names can outrank release baselines
type: challenge
status: open
suspect: false
links:
- target: STORY-627
  role: refers_to
created: '2026-08-05'
severity: info
technique: premortem
thinking_techniques:
- premortem
fingerprint: sha256:b157eaef4aa4
---

# Non-semver baseline names can outrank release baselines

## Finding

Semver-parseable baselines sort before freeform names, while newest/predecessor callers select the final entries. External projects mixing release tags with names such as `snapshot` can therefore compare the freeform baseline instead of the newest release. This repository uses version-shaped baseline names and is unaffected.

## Follow-up

Choose and document a policy: enforce semver baseline names, or have newest/predecessor callers prefer semver names and fall back only when none parse.
