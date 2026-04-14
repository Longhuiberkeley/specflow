---
name: specflow-done
description: Use when the user wants to close the current phase and extract prevention patterns. Run `/cmd` to invoke.
---

# SpecFlow Done

Close the current phase and extract prevention patterns.

## Usage

- `/cmd` — Interactive: reviews completed work, extracts patterns, closes phase.
- `/cmd --auto` — Skip interactive prompts, auto-close phase.
- `/cmd --no-patterns` — Skip pattern extraction entirely.

Learned patterns are saved to `.specflow/checklists/learned/` and auto-load during future reviews for artifacts with matching tags.
