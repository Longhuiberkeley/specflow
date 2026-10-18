---
id: STORY-753
title: 'output_files truth sweep: move or drop auto-captured files that other stories
  implement'
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
fingerprint: sha256:6b2b821ee816
modified: '2026-10-18'
---

# output_files truth sweep: move or drop auto-captured files that other stories implement

## Scope
The STORYs named in SPIKE-008 output_files rows (STORY-043 group and any verified STORY whose output_files include files first introduced by a different STORY per git log); correct with `specflow update <STORY> --output-files` and re-seed with `specflow fingerprint-refresh --source`; keep orphan-code at 0.

## Acceptance criteria
- AC1: Given each corrected STORY, when its output_files are read, then every file's introducing commit (git log --diff-filter=A) traces to that STORY or a file it genuinely modified for its scope (REQ AC4).
- AC2: Given `specflow detect orphan-code`, when run after the sweep, then orphan files remain 0.
- AC3: Given `specflow artifact-lint`, when run, then it reports no new findings.
