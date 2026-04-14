---
name: specflow-export
description: Use when the user wants to export artifacts to an external format (e.g., ReqIF). Run `/cmd` to invoke.
---

# SpecFlow Export

Export artifacts to an external interchange format.

## Usage

- `/cmd reqif --output requirements.reqif` — Export requirements to ReqIF XML.

Supports adapter-based dispatch. Additional formats (Jira, Linear, etc.) can be added via the adapter framework.
