---
name: specflow-checklist-run
description: Use when the user wants to run context-specific checklist review on artifacts. Run `/cmd` to invoke.
---

# SpecFlow Checklist Run

Run context-specific checklist review on one or more artifacts.

## Usage

- `/cmd REQ-001` — Review a single artifact.
- `/cmd --all` — Review all artifacts.
- `/cmd --proactive REQ-001` — Include proactive challenge items.
- `/cmd --dedup` — Run the duplicate-detection pipeline.

Assembles checklists from artifact type, domain tags, shared patterns, phase-gates, and learned prevention patterns. Runs automated checks first, then lists LLM-judged items.
