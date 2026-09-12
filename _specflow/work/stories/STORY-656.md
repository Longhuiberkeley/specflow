---
id: STORY-656
title: Replace always-on context and pack snippets with audit drafts
type: story
status: implemented
suspect: false
links:
- target: REQ-042
  role: implements
created: '2026-09-13'
fingerprint: sha256:f828969e5a0e
modified: '2026-09-13'
---

# Replace always-on context and pack snippets with audit drafts

Replace src/specflow/templates/agent-context.md and the context_snippet of all four packs (tldr-communication, adoption, autoresearch, ops) with the specflow-context-audit drafts: seek-and-proceed consent (I1), no docs/ pointers (DEC-082), tool names instead of recipes. Target: agent-context + installed snippets <= ~500 tokens.
