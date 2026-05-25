# Project Audit Report

- **Timestamp**: 20260522T160842Z
- **Artifacts analyzed**: 410 (cached: 0)
- **Baseline drift: compared v1.3.1 → v1.4.0**

## Horizontal Analysis (per artifact type)

### challenge
- [○] No challenge artifacts use tags

### integration-test
- [○] No integration-test artifacts use tags

### qualification-test
- [○] No qualification-test artifacts use tags

### unit-test
- [○] No unit-test artifacts use tags

## Vertical Analysis (V-model threads)

No V-model thread gaps found.

## Cross-cutting Analysis

### completeness
- [⚠] 1 coverage gap(s):   ⚠ [STORY-058] no UT linked via 'verified_by' (covers REQ REQ-026)

### consistency
- [⚠] 146 schema warning(s)

### nfr-coverage
- [○] 15/36 REQs have no non_functional_category
- [○] NFR categories: functional(21)

## Summary

| Severity | Count |
|----------|-------|
| Error    | 0 |
| Warning  | 2 |
| Info     | 6 |
