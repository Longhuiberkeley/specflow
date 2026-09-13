---
id: ARCH-029
title: 'Privacy gate: denylist release check + sanctioned-exception model'
type: architecture
status: approved
suspect: false
links:
- target: REQ-038
  role: derives_from
created: '2026-08-30'
summary: 'Architecture of the REQ-038 privacy gate: (1) a deterministic denylist grep
  over src/ tests/ docs/ scripts/ _specflow/ CHANGELOG README ROADMAP runs as a release-checklist
  gate (REQ-038 AC-1); (2) sanctioned exceptions are enumerated, not pattern-based:
  attribution email + upstream fork URLs (pack.yaml, README, autoresearch SKILL.md)
  and layer-2 domain vocabulary (domain-research-checklists model families); (3) baselines
  are write-once: titles may be neutralized in place, fingerprints stay historical;
  (4) live skill mirror must be re-synced (byte-equality guards) whenever a template
  that ships in the mirror changes. History rewrite (git filter-repo) is out of scope
  for the gate and tracked as a separate owner decision.'
fingerprint: sha256:6bd010cdbfc6
modified: '2026-09-13'
thinking_techniques:
- assumption-surfacing
---

# Privacy gate: denylist release check + sanctioned-exception model

## Structure

The privacy gate (REQ-038) has three components: a deterministic denylist pattern owned by `src/specflow/lib/privacy.py` (single source of truth, shipped in the wheel), a release-checklist gate that greps the pattern across `src/ tests/ docs/ scripts/ _specflow/ CHANGELOG.md README.md ROADMAP.md` (implemented as `scripts/denylist_gate.py`, consumed by the CI PR/push job and the release-authoritative tag job), and generation-time redaction so every project-audit report/cache write passes through `privacy.redact_text`.

## Interface

CI and the release checklist call `scripts/denylist_gate.py`, which imports the shared pattern via src-bootstrap — no embedded copy, no drift. The pattern is case-sensitive, word-bounded, with numeric tokens anchored (REQ-038).

## Responsibilities

- Sanctioned exceptions are enumerated, not pattern-based: attribution email + upstream fork URLs (pack.yaml, README, autoresearch SKILL.md) and layer-2 domain vocabulary (domain-research-checklists model families).
- Baselines are write-once: titles may be neutralized in place, fingerprints stay historical.
- `.specflow/` generated state is excluded from the grep — it is redacted at write time instead.
- The live skill mirror must be re-synced (byte-equality guards) whenever a template that ships in the mirror changes.

## Dependencies

History rewrite (git filter-repo) is out of scope for the gate and tracked as a separate owner decision. Implementation detail lives in DDD-029.
