---
id: STORY-626
title: Decision & objective quality — computed risk tiers + AC observability (v1.13.1)
type: story
status: implemented
rationale: v1.13.1 honest-quality lenses (risk tiers + AC observability); accounting,
  not policing. Sibling design DDD-026.
suspect: false
links:
- target: REQ-037
  role: implements
- target: ARCH-026
  role: derives_from
created: '2026-08-03'
fingerprint: sha256:354f29fa9053
modified: '2026-08-03'
output_files:
- tests/test_risk.py
- src/specflow/lib/risk.py
- tests/test_ac_quality.py
- src/specflow/commands/risk_tier.py
- src/specflow/lib/ac_quality.py
---

# Decision & objective quality — computed risk tiers + AC observability (v1.13.1)

## Scope

v1.13.1 ships two honest-quality lenses — one for decisions, one for objectives —
both **accounting, not policing**: they surface gaps for review and never gate a
release. Sibling design is DDD-026 ("Verification-contract recording + accounting
evidence lenses"); this story does **not** carry its own DDD — it reuses DDD-026's
evidence/observability model directly.

### Computed risk tiers (decisions)

- `lib/risk.py` — deterministic risk-tier compute for a change set: a risk **floor**
  from reversibility + blast-radius-count, producing a tier (T0/T1/T2). Pure read of
  the artifact graph; no external calls.
- `commands/risk_tier.py` + `cli.py` — `specflow risk-tier <IDs>` renders the tier.
  **Read-only; the tier gates nothing.** It makes the Risk Profile visible.
- `document_changes.py` persists the computed `risk_profile` (tier + deterministic
  subset) into DEC frontmatter; `decision.yaml` schema gains the `risk_profile` field.
- `artifact_lint.py` `dec-risk-profile` check (advisory): warns when an approved DEC
  carries no persisted `risk_profile`. Advisory only — never blocking, never in
  `--type gate`.

### AC observability (objectives)

- `lib/ac_quality.py` — classifies each AC item as **observable** / **aspirational** /
  **unclassified**. Anti-cry-wolf guardrail is the classification *conjunction*: an
  item is aspirational only with NO outcome marker AND an ambiguity/bare-vague-verb
  match; a miss demotes to unclassified (info), never aspirational. Zero external LLM.
- `project_audit.py` `ac-observability` cross-cutting lens — INFO-severity aggregate
  only (per-REQ ratio + project summary), registered in `_ACCOUNTING_CONCERNS` so any
  signal it emits can never drive exit-2.
- `artifact_lint.py` `ac-observable` check (advisory): REQ-level aspirational-AC
  warnings, never blocking, never in `--type gate`.
- `brief.py` surfaces one aggregate "REQ quality" line (aspirational-free REQ count).

### Verification-evidence line

`brief.py` `_next_skill_recommendation` surfaces artifacts that declare a
`verify_command` with no matching `verify_run` evidence (accounting advisory).

## Acceptance Criteria

- `specflow risk-tier <IDs>` renders a deterministic tier and exits without mutating artifacts.
- An approved DEC's persisted `risk_profile` is visible in `brief` (tier marker) and surfaced by the advisory `dec-risk-profile` lint check.
- `ac-observable` / `ac-observability` classify ACs without smearing domain observables as aspirational (conjunction guardrail), and never produce a blocking finding.
