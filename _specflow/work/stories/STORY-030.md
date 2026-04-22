---
id: STORY-030
title: Ship /specflow-project-audit with conversational scope and chunked fan-out
type: story
status: verified
priority: medium
tags:
- audit
- M3-depth
suspect: false
created: '2026-04-14'
links:
- target: STORY-022
  role: depends_on
- target: STORY-024
  role: depends_on
- target: STORY-025
  role: depends_on
- target: STORY-029
  role: depends_on
- target: UT-009
  role: verified_by
- target: IT-007
  role: verified_by
- target: QT-017
  role: verified_by
checklists_applied:
- checklist: check-STORY-030
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-22'
fingerprint: sha256:8d8779ab40c0
---

# Ship /specflow-project-audit with seamless core + wings

## Description

Ship `/specflow-project-audit` as a **seamless, zero-question core** that runs automatically and presents results, with optional **wings** (deep adversarial analysis) that the user can request after reading the core findings. The design philosophy is SKILL-driven: the `/specflow-project-audit` skill orchestrates everything, and `specflow project-audit` CLI is the deterministic backend.

### Seamless core (always runs, zero questions, deterministic)

The core runs all 9 lint checks, compliance gap analysis, baseline drift detection, and coverage completeness — entirely deterministic, zero LLM tokens. Three analysis axes run in parallel via subagents:

- **Horizontal** (per artifact type): 1 subagent per type checking internal consistency
- **Vertical** (per V-model thread): 1 subagent per top-level REQ checking thread coherence
- **Cross-cutting** (per concern): consistency, completeness, baseline-drift, standards-coverage, NFR-coverage, test-coverage

The core spawns 2–3 subagents to cover all three axes. After completion, results are presented to the user as a unified report.

### Wings (optional, user-initiated after reading core results)

After the core finishes and the user reads the report, the skill asks one question: *"Would you like deeper adversarial analysis?"* Two wing subagents run in parallel, each covering 8 of the 16 adversarial lenses:

- **Wing A (Structural)**: stress-scale, dependency-shock, composition, inversion, five-whys, temporal-drift, assumption-surfacing, reversal
- **Wing B (Stakeholder)**: devils-advocate, premortem, red-blue-team, worst-case-user, regulator, outside-view, competitor, cost-scaling

Wings are prompt-engineered in the SKILL reference docs, not Python code. The CLI is pure deterministic.

### Scope auto-detection

- If `.specflow/standards/*.yaml` exists → compliance scope included automatically
- If `.specflow/baselines/latest.yaml` exists → baseline drift included automatically
- No scope/depth selection prompts — the core always runs the full analysis

### Token-budget controls

- Fingerprint cache (reuse findings if target fingerprint unchanged)
- Sample mode for large projects (20% of STORYs at Quick depth)
- Dedup preflight (feed deduplicated artifact set)

### Outputs

- `.specflow/audits/{timestamp}/report.md`
- `.specflow/audits/{timestamp}/subagent-*.md`
- `_specflow/specs/audits/AUD-{N}.md` (AUD artifact)
- CHL artifacts for findings at severity ≥ warn

## Acceptance Criteria

1. `/specflow-project-audit` runs the full core analysis automatically with zero questions — scope and depth are auto-detected from project state (installed standards, available baselines)

2. Core spawns 2–3 subagents covering horizontal (per-type), vertical (per-REQ thread), and cross-cutting (per-concern) analysis axes, producing per-axis findings in `.specflow/audits/{timestamp}/subagent-*.md`

3. Vertical fan-out traces REQ→ARCH→DDD→STORY→tests as coherent slices and reports thread-level coherence gaps

4. Cross-cutting analysis covers: consistency, completeness, baseline-drift, standards-coverage, NFR-coverage, test-coverage

5. Fingerprint cache at `.specflow/audits/.cache/{fingerprint}.md` reuses previous findings when target fingerprints haven't changed

6. AUD artifact is created in `_specflow/specs/audits/` with `review_status: open` per the audit schema from STORY-025

7. Exit codes: 0 = clean, 2 = findings ≥ warn, 3 = findings ≥ error, 4 = tool error

8. Compliance scope works by auto-detecting `.specflow/standards/*.yaml` and checking coverage against installed standard clauses

9. After core completes, SKILL presents results and offers optional "wings" — 2 subagents covering the 16 adversarial lenses split into structural (8) and stakeholder (8) groups

10. Core is entirely deterministic (zero LLM tokens); wings are prompt-engineered in SKILL reference docs

## Out of Scope

- RBAC doctor, compliance dashboard HTML, scheduled audit workflow (enterprise features)
- New CI adapters for audit workflows (STORY-026 territory)

## Dependencies

- STORY-022 (command rename — audit→project-audit)
- STORY-024 (adversarial lenses — used in "full" scope)
- STORY-025 (AUD schema and review_status field)
- STORY-029 (analytical passes — cross-cutting analysis feeds into audit)
