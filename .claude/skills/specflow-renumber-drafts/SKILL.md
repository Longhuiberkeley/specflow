---
name: specflow-renumber-drafts
description: Use when the user wants to renumber draft IDs to sequential integers after merging feature branches. Run `/cmd` to invoke.
---

# SpecFlow Renumber Drafts

Renumber draft IDs (e.g., `REQ-AUTH-a7b9`) to sequential integers (`REQ-006`).

## Usage

- `/cmd --dry-run` — Show the renumber plan without writing.
- `/cmd` — Renumber all draft artifacts and rewrite references across the repo.

Run after merging feature branches to main. Updates `_index.yaml` files and rewrites all links referencing draft IDs throughout the repository.
