---
id: CHL-RELEASEE-b5ca
title: Release evidence RTM collapses after first verified REQ
type: challenge
status: open
suspect: false
links:
- target: REQ-015
  role: refers_to
- target: STORY-KEEPRELE-37de
  role: refers_to
created: '2026-08-05'
severity: error
technique: regulator
thinking_techniques:
- regulator
fingerprint: sha256:525fa5b10b1d
---

# Release evidence RTM collapses after first verified REQ

## Finding

The evidence generator selected verified REQs exclusively whenever any existed, hiding approved and implemented peers. v1.13.4 first triggered the latent defect and reduced the evidence RTM from 39 rows to 1.

## Required Resolution

Render approved, implemented, and verified requirements together; prove mixed statuses with an executable UT contract; regenerate release evidence before tagging.
