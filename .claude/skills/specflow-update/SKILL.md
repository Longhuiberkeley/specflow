---
name: specflow-update
description: Use when the user wants to update an artifact's frontmatter fields. Run `/cmd` to invoke.
---

# SpecFlow Update

Update an artifact's frontmatter fields.

## Usage

- `/cmd update REQ-001 --status approved` — Change status.
- `/cmd update STORY-003 --priority high --tags security` — Update multiple fields.

Validates status transitions against schema rules. Recomputes fingerprint on save (may trigger suspect cascade on linked artifacts).
