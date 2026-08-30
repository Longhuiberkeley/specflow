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
fingerprint: sha256:52b000665f0a
modified: '2026-08-30'
---

# Privacy gate: denylist release check + sanctioned-exception model
