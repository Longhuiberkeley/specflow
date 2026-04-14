---
id: STORY-030
title: Ship /specflow-project-audit with conversational scope and chunked fan-out
type: story
status: draft
priority: medium
tags:
- audit
- M3-depth
suspect: false
created: '2026-04-14'
checklists_applied:
- checklist: check-STORY-030
  timestamp: '2026-04-14T17:03:23Z'
---

# Ship /specflow-project-audit with conversational scope and chunked fan-out

## Description

Ship the full `/specflow-project-audit` skill from retrospective §8. This is the periodic full-project health review with conversational scope/depth selection, subagent-based chunked fan-out, and token-budget controls. Absorbs the removed `/specflow-compliance` as a scope choice (auto-detected from `.specflow/standards/`).

### Conversational scope selection

Four scope options: (a) internal coherence only, (b) against installed standard X, (c) both, (d) full (above + adversarial lenses). Three depth levels: Quick (~2 min), Detailed (~10 min), Exhaustive (~30 min).

### Chunking strategy

Three parallel fan-out axes:
- **Horizontal** (per artifact type): 1 subagent per type checking internal consistency
- **Vertical** (per V-model thread): 1 subagent per top-level REQ checking thread coherence
- **Cross-cutting** (per concern): consistency, completeness, baseline-drift, standards-coverage, NFR-coverage, test-coverage

### Token-budget controls

- Sample mode (20% of STORYs + all REQs/ARCHs at Quick depth)
- Baseline anchor (diff against `.specflow/baselines/latest.yaml`)
- Dedup preflight (feed deduplicated artifact set)
- Fingerprint cache (reuse findings if target fingerprint unchanged)
- Upfront spend estimate (announce expected token cost before launching)

### Outputs

- `.specflow/audits/{timestamp}/report.md`
- `.specflow/audits/{timestamp}/subagent-*.md`
- `_specflow/specs/audits/AUD-{timestamp}.md` (AUD artifact)
- CHL artifacts for findings at severity ≥ warn

## Acceptance Criteria

1. `/specflow-project-audit` presents conversational scope/depth selection with token spend estimate and requires user confirmation before launching subagents

2. At Detailed depth, horizontal fan-out launches one subagent per artifact type and produces per-type findings in `.specflow/audits/{timestamp}/subagent-*.md`

3. Vertical fan-out traces REQ→ARCH→DDD→STORY→tests as coherent slices and reports thread-level coherence gaps

4. Cross-cutting analysis covers: consistency, completeness, baseline-drift, standards-coverage, NFR-coverage, test-coverage

5. Fingerprint cache at `.specflow/audits/.cache/{fingerprint}.md` reuses previous findings when target fingerprints haven't changed

6. AUD artifact is created in `_specflow/specs/audits/` with `review_status: open` per the audit schema from STORY-025

7. Exit codes: 0 = clean, 2 = findings ≥ warn, 3 = findings ≥ error, 4 = tool error

8. Compliance scope works by auto-detecting `.specflow/standards/*.yaml` and checking coverage against installed standard clauses

## Out of Scope

- RBAC doctor, compliance dashboard HTML, scheduled audit workflow (enterprise features)
- New CI adapters for audit workflows (STORY-026 territory)

## Dependencies

- STORY-022 (command rename — audit→project-audit)
- STORY-024 (adversarial lenses — used in "full" scope)
- STORY-025 (AUD schema and review_status field)
- STORY-029 (analytical passes — cross-cutting analysis feeds into audit)
