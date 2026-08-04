---
id: CHL-RELEASEE-b5ca
title: Release evidence RTM collapses after first verified REQ
type: challenge
status: addressed
suspect: false
links:
- target: REQ-015
  role: refers_to
- target: STORY-KEEPRELE-37de
  role: refers_to
- target: UT-EVIDENCE-9a3d
  role: refers_to
- target: DEC-064
  role: refers_to
created: '2026-08-05'
severity: error
technique: regulator
thinking_techniques:
- regulator
fingerprint: sha256:fa58a4e002b6
version: 1
---

# Release evidence RTM collapses after first verified REQ

## Finding

The evidence generator selected verified REQs exclusively whenever any existed, hiding approved and implemented peers. v1.13.4 first triggered the latent defect and reduced the evidence RTM from 39 rows to 1.

## Required Resolution

Render approved, implemented, and verified requirements together; prove mixed statuses with an executable UT contract; regenerate release evidence before tagging.

## Resolution Evidence

Implemented by STORY-KEEPRELE-37de and verified by UT-EVIDENCE-9a3d (exit 0). The regenerated v1.13.4 evidence report contains all 39 eligible requirements and the baseline captures 590 artifacts at committed git ref `6027a1a`.
