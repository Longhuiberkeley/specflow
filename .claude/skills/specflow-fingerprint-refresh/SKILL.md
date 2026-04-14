---
name: specflow-fingerprint-refresh
description: Use when the user wants to update an artifact's fingerprint without triggering a suspect cascade. Run `/cmd` to invoke.
---

# SpecFlow Fingerprint Refresh

Update an artifact's fingerprint without suspect cascade (minor edit).

## Usage

- `/cmd _specflow/specs/requirements/REQ-001.md` — Recompute and store fingerprint.

Use after cosmetic edits (formatting, typo fixes) where the normative content hasn changed semantically. Logs the update as `update_type: minor` in the impact-log.
