# Project Audit Report

- **Timestamp**: 20260804T115641Z
- **Artifacts analyzed**: 579 (cached: 20)
- **Baseline drift: compared v1.13.2 → v1.13.3**

## Horizontal Analysis (per artifact type)

### challenge
- [○] No challenge artifacts use tags

## Vertical Analysis (V-model threads)

No V-model thread gaps found.

## Cross-cutting Analysis

### ac-coverage
- [○] REQ-001: 3 linked test(s) < 28 AC item(s) (0 green) — review coverage
- [○] REQ-006: 3 linked test(s) < 5 AC item(s) (0 green) — review coverage
- [○] REQ-007: 3 linked test(s) < 5 AC item(s) (0 green) — review coverage
- [○] REQ-008: 3 linked test(s) < 6 AC item(s) (0 green) — review coverage
- [○] REQ-009: 3 linked test(s) < 6 AC item(s) (0 green) — review coverage
- [○] REQ-010: 4 linked test(s) < 8 AC item(s) (0 green) — review coverage
- [○] REQ-011: 3 linked test(s) < 5 AC item(s) (0 green) — review coverage
- [○] REQ-012: 4 linked test(s) < 7 AC item(s) (0 green) — review coverage
- [○] REQ-014: 3 linked test(s) < 5 AC item(s) (0 green) — review coverage
- [○] REQ-015: 3 linked test(s) < 8 AC item(s) (0 green) — review coverage
- [○] REQ-016: 3 linked test(s) < 7 AC item(s) (0 green) — review coverage
- [○] REQ-017: 3 linked test(s) < 7 AC item(s) (0 green) — review coverage
- [○] REQ-022: 3 linked test(s) < 6 AC item(s) (0 green) — review coverage

### docs-staleness
- [○] 15 doc(s) scanned; all citations current.

### nfr-coverage
- [○] 18/39 REQs have no non_functional_category
- [○] NFR categories: functional(21)

### orphan-code
- [○] All 222 source files traced to a STORY/REQ.

### verification
- [⚠] 27 test-verification coverage gap(s):   ⚠ [STORY-082] no IT linked via 'verified_by' (covers REQ REQ-001);   ⚠ [STORY-082] no QT linked via 'verified_by' (covers REQ REQ-001);   ⚠ [STORY-082] no IT linked via 'verified_by' (covers REQ REQ
- [○] 32 artifact(s) declare verify_command; all have current, green verify runs.

## Summary

| Severity | Count |
|----------|-------|
| Error    | 0 |
| Warning  | 1 |
| Info     | 19 |
