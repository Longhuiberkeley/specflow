---
id: STORY-062
title: Pass domain classification from discover to plan skill
type: story
status: draft
priority: low
tags:
- plan
- discover
- domain
suspect: false
links:
- target: REQ-027
  role: implements
- target: ARCH-021
  role: guided_by
- target: DDD-021
  role: specified_by
created: '2026-05-04'
---

# Pass domain classification from discover to plan skill

Update the plan skill to read domain classification from config.yaml and use it to scope the decomposition approach during architecture discussion.

## Acceptance Criteria

1. Given a project with domain set to `cli-tool` and tags `[developer-tools]`, when the plan skill Step 2 runs, then it reads the domain and tags from config and incorporates them into the architecture discussion framing.
2. Given a project with no domain set, when the plan skill Step 2 runs, then it proceeds without domain-specific framing (no error, no warning).
3. Given the plan skill, when Step 2 reads domain context, then the summary presented to the user acknowledges the project type and adjusts decomposition guidance accordingly.
