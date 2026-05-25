# Project Audit Report

- **Timestamp**: 20260525T070329Z
- **Artifacts analyzed**: 413 (cached: 8)
- **Baseline drift: compared v1.4.0 → v1.6.3**

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
