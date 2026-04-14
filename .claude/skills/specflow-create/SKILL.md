---
name: specflow-create
description: Use when the user wants to create a new artifact directly via CLI. Run `/cmd` to invoke.
---

# SpecFlow Create

Create a new artifact with specified frontmatter and body.

## Usage

- `/cmd create REQ "User authentication" --status draft --tags auth` — Create a requirement.
- `/cmd create STORY "Implement login" --links REQ-001:refined_by` — Create a story linked to a requirement.

Supports all artifact types. Auto-generates IDs (draft IDs on feature branches, sequential on main). Runs a duplicate-detection search before creation.
