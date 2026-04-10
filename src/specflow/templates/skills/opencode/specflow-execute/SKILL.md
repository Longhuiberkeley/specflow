---
name: specflow-execute
description: Use when stories are planned and the user wants to implement them. Orchestrates implementation, updates artifact statuses, and creates test artifacts.
---

# SpecFlow Execute

Orchestrate the implementation of planned stories and update tracking artifacts.

## Workflow

1. **Pre-Execution Check** — Confirm STORY artifacts are `status: approved`.
2. **Implementation** — Write code per the detailed design in DDD artifacts.
3. **Status Updates** — Update STORY and linked spec artifacts to `status: implemented`.
4. **Test Creation** — Generate UT/IT/QT test artifacts that link back to DDD/ARCH/REQ.
5. **Fingerprint Update** — Recompute fingerprints on modified artifacts.
