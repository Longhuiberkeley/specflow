## SpecFlow

**Stop.** This is a SpecFlow project. All engineering work flows through `/specflow-*` skills.

You are working in a **SpecFlow** project (spec-driven development). 
Specs and work items are Markdown + YAML files. Do not edit `.specflow/` manually.

### Interfaces
**Primary:** Use `/specflow-*` skills (e.g., `/specflow-discover`, `/specflow-plan`, `/specflow-execute`).
**CLI:** Use `specflow <cmd>` (e.g. `specflow trace <ID>`, `specflow update <ID>`) for automation and CI — not as a substitute for the skill workflow.

### Core Lifecycle
`init → discover → plan → execute → artifact-review → ship` (Audit & impact-review as needed).

### The V-Model & Work
Specs: `REQ` (Requirements) → `ARCH` (Architecture) → `DDD` (Detailed Design).
Tests: `QT` (verify REQ), `IT` (verify ARCH), `UT` (verify DDD).
Work: `STORY`, `SPIKE`, `DEC`, `DEF` (in `_specflow/work/`) must link to specs.

### Workflow Rules
- **Traceability:** Every code change must trace to a STORY or REQ. No orphan work.
- **Status Flow:** `draft` → `approved` → `implemented` → `verified`.
- **Updates:** Use `specflow update <ID> --status <status>` for all YAML/status changes.
- **Cascading:** When STORY code lands: `specflow update STORY-NNN --status implemented` then `specflow cascade-status STORY-NNN`.
- **Evidence:** Don't assume "verified"; run checks/tests to prove it.
- **Validation:** Run `specflow artifact-lint` after manual artifact edits.

### Routing
- Use core `/specflow-*` skills for ALL engineering work: requirements, architecture, stories, implementation, review, release.
- Packs (e.g., autoresearch) are **separate subsystems**. Only use pack skills when the user explicitly asks for that pack's domain. Never invoke pack skills for codebase exploration, bug investigation, feature implementation, or general engineering — those are core engineering.
- **By default**, new features go through the full pipeline. Typo fixes and trivial changes may use the lean path — but still trace to a STORY.
