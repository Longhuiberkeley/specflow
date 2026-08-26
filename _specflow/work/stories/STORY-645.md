---
id: STORY-645
title: 'v1.15.0: skill slimming / lazy reference loading'
type: story
status: draft
tags:
- v1.15.0-backlog
suspect: false
links:
- target: REQ-001
  role: implements
created: '2026-08-27'
fingerprint: sha256:239a1f65c6cf
---

# v1.15.0: skill slimming / lazy reference loading

Always-on context is capped (2.6KB/3KB) but on-demand bundles are chunky: discover ~64KB (23K skill + 41K refs), execute ~40KB, plan ~38KB. Introduce reference-aware lazy loading / progressive disclosure so frequently-loaded skills get smaller without weakening routing. Also adds a context-cost regression test so bundles can't silently grow.
