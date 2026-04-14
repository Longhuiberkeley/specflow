---
name: specflow-artifact-lint
description: Use when the user wants to run deterministic validation checks on artifacts (schema, links, status, IDs, fingerprints). Run `/cmd` to invoke.
---

# SpecFlow Artifact Lint

Run deterministic validation checks on artifacts (zero tokens).

## Usage

- `/cmd` — Run all checks: schema, links, status, IDs, fingerprints, acceptance criteria.
- `/cmd --type schema` — Run only schema validation.
- `/cmd --fix` — Auto-fix: rebuild indexes, recompute fingerprints.

Exit code 0 = all pass, 1 = blocking issues found. Used internally by `/specflow-artifact-review` and in CI pipelines.
