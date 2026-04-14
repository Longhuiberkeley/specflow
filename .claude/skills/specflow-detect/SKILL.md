---
name: specflow-detect
description: Use when the user wants to run project-hygiene scans (dead code, function similarity). Run `/cmd` to invoke.
---

# SpecFlow Detect

Project-hygiene scans for dead code and function similarity.

## Usage

- `/cmd dead-code` — Report top-level functions/classes never referenced.
- `/cmd similarity --threshold 0.9` — Report function pairs with near-identical bodies.

Informational only — does not block workflows. Intended for CI pipelines and periodic code quality reviews.
