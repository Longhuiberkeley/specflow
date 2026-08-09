---
id: STORY-631
title: Close v1.13.8 readiness and distribution gaps
type: story
status: verified
priority: high
tags:
- v1.13.8
- readiness
- dogfood
suspect: false
links:
- target: DEC-076
  role: guided_by
- target: ARCH-026
  role: implements
- target: QT-023
  role: verified_by
- target: QT-024
  role: verified_by
- target: QT-025
  role: verified_by
- target: QT-026
  role: verified_by
- target: QT-027
  role: verified_by
- target: QT-028
  role: verified_by
created: '2026-08-10'
fingerprint: sha256:7642a070b2c7
rationale: All acceptance criteria are implemented and covered by focused/full tests,
  qualification contracts, schema/skill parity, and built-wheel smoke validation.
modified: '2026-08-10'
output_files:
- src/specflow/commands/brief.py
- src/specflow/commands/status.py
- src/specflow/lib/checklists.py
- src/specflow/commands/project_audit.py
- src/specflow/lib/skill_export.py
- src/specflow/commands/refresh.py
- src/specflow/commands/init.py
- src/specflow/lib/scaffold.py
- src/specflow/commands/handbook.py
- src/specflow/lib/handbook.py
- src/specflow/commands/change_impact.py
- scripts/wheel-smoke.sh
- scripts/wheel_smoke.py
- tests/test_brief.py
- tests/test_status_coverage.py
- tests/test_checklists.py
- tests/test_project_audit.py
- tests/test_skill_export.py
- tests/test_schema_drift.py
- tests/test_ops_pack.py
- tests/test_wheel_smoke.py
- tests/test_handbook.py
- tests/test_change_impact_cli.py
- tests/test_discovery_plan_continuity.py
- tests/test_tags_normalization.py
---

# Close v1.13.8 readiness and distribution gaps

## Scope

Correct brief routing, checklist empty outcomes, audit cache freshness, complete skill exports, safe schema drift/sync, Python compatibility CI, built-wheel smoke validation, and dogfood evidence reconciliation.

## Acceptance Criteria

- [ ] brief --next never routes to execute without approved stories.
- [ ] empty checklist runs cannot report passed.
- [ ] audit cache invalidates on audit-relevant frontmatter-only edits.
- [ ] exported skills include all reference guidance and live/shipped skill trees are byte-identical.
- [ ] schema drift is previewed, preserved by default, and replaced only with explicit --force.
- [ ] Python 3.11-3.13 and built-wheel init paths are exercised.
- [ ] outstanding qualification/provenance/ledger evidence is reconciled honestly.
- [ ] full tests, project audit, and release gates pass.
