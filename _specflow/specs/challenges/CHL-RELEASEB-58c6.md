---
id: CHL-RELEASEB-58c6
title: Release baseline outputs must be committed before tag
type: challenge
status: addressed
suspect: false
links:
- target: DEC-060
  role: refers_to
- target: DEC-064
  role: refers_to
created: '2026-08-05'
severity: error
technique: temporal_drift
thinking_techniques:
- temporal_drift
fingerprint: sha256:7b856b9a66c4
version: 1
---

# Release baseline outputs must be committed before tag

## Finding

The first v1.13.4 baseline and release DEC outputs existed only in the working tree while the tag candidate still pointed at the release-prep commit. Tagging that commit would omit the mandatory release records.

## Required Resolution

Commit the release records, regenerate baseline/evidence after blocker fixes, rerun gates on the committed state, and only then request Tier-2 tag approval.

## Resolution Evidence

The initial DEC/audit records and blocker fix are committed at `6027a1a`. The regenerated baseline/evidence captures that committed state (590 artifacts, 39 REQ rows), and DEC-064 records the remediation commit. The final release-record commit and gate rerun occur before tag approval.
