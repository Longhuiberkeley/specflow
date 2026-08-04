---
id: CHL-RELEASEB-58c6
title: Release baseline outputs must be committed before tag
type: challenge
status: open
suspect: false
links:
- target: DEC-060
  role: refers_to
created: '2026-08-05'
severity: error
technique: temporal_drift
thinking_techniques:
- temporal_drift
fingerprint: sha256:a879dcc280ff
---

# Release baseline outputs must be committed before tag

## Finding

The first v1.13.4 baseline and release DEC outputs existed only in the working tree while the tag candidate still pointed at the release-prep commit. Tagging that commit would omit the mandatory release records.

## Required Resolution

Commit the release records, regenerate baseline/evidence after blocker fixes, rerun gates on the committed state, and only then request Tier-2 tag approval.
