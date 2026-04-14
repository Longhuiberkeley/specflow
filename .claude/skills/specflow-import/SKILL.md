---
name: specflow-import
description: Use when the user wants to import artifacts from an external format (e.g., ReqIF). Run `/cmd` to invoke.
---

# SpecFlow Import

Import artifacts from an external interchange format.

## Usage

- `/cmd reqif requirements.reqif` — Import requirements from a ReqIF XML file.

Supports adapter-based dispatch. Additional formats (Jira, Linear, etc.) can be added via the adapter framework.
