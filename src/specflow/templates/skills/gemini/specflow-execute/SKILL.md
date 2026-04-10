---
name: specflow-execute
description: Use when stories are planned and the user wants to implement them. Orchestrates implementation and updates artifact statuses.
---

# SpecFlow Execute

Orchestrate implementation of planned stories and update tracking artifacts.

## Workflow

1. **Pre-Execution Check** — Confirm STORY artifacts are `status: approved`.
2. **Implementation** — Write code per DDD artifacts.
3. **Status Updates** — Update to `status: implemented`.
4. **Test Creation** — Generate UT/IT/QT test artifacts.
