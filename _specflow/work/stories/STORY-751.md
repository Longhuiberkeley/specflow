---
id: STORY-751
title: Rewrite 19 ARCH/DDD bodies to the engine as built (SPIKE-008 ARCH rows)
type: story
status: verified
tags:
- consistency
- v1.17.8
suspect: false
links:
- target: REQ-071
  role: implements
- target: SPIKE-008
  role: derives_from
created: '2026-10-18'
fingerprint: sha256:a3778d1a96c3
modified: '2026-10-18'
output_files:
- tests/test_arch_bodies_current.py
---

# Rewrite 19 ARCH/DDD bodies to the engine as built (SPIKE-008 ARCH rows)

## Scope
ARCH-001/003/004/005/007/009/010/011/014/015/016/017/018/019/020/025/027/031/035 and DDD-020: rewrite stale components, interfaces, data flows and ACs in place from the current source; fold the v1.17.7 amendment note into one rewrite line; `specflow fingerprint-refresh <ID>` after each body edit.

## Acceptance criteria
- AC1: Given each listed artifact after the rewrite, when SPIKE-008's stale names are grepped, then none remains outside the rewrite line (REQ AC1).
- AC2: Given each rewritten body, when a verifier reads it against the cited engine files, then every named module, function, flag and flow exists.
- AC3: Given `specflow artifact-lint`, when run, then no fingerprints/stale or new finding is reported for the rewritten artifacts.
