## SpecFlow

**Stop.** This is a SpecFlow project. Describe what you want in plain language — the matching `/specflow-*` skill engages automatically (slash optional). The raw `specflow` CLI is for CI and power users.

You are working in a **SpecFlow** project. Specs and work items are Markdown + YAML. **Never edit `.specflow/` manually** (config, state, schemas, indexes). Artifact YAML in `_specflow/` is CLI-managed: use `specflow update <ID>` for frontmatter/status/link changes. After a true hand-edit, run `specflow artifact-lint`.

### How to talk
Lead with the answer or next action. Then: what's happening · change · why · risks.
One idea per line. No preamble, no closer. First and last line must tell the reader what happened and what to do next.

### Interfaces
**Primary:** `/specflow-*` skills. Vague intent → `/specflow-start` or `specflow brief --next`.
**CLI:** `specflow trace <ID>`, `specflow update <ID>`, `specflow list`, `specflow transitions <ID>` (status maps are type-specific — never assume `draft → approved → implemented`).

### Lifecycle & V-model
`init → discover → plan → execute → artifact-review → ship` (audit / impact-review as needed).
Specs: REQ → ARCH → DDD. Tests: QT verifies REQ, IT verifies ARCH, UT verifies DDD.
Work (STORY / SPIKE / DEC / DEF in `_specflow/work/`) must link to a spec. Unlinked work is a SPIKE.

### Workflow rules
- Every code change traces to a STORY or REQ. No orphan work.
- **No self-approval:** never move `draft` → `approved` without a human. Present; they approve.
- Status changes: `specflow update <ID> --status …` after `specflow transitions <ID>`. Links: `--add-link TARGET:ROLE` / `--remove-link TARGET`.
- After STORY code lands: `specflow update STORY-NNN --status implemented` then `specflow cascade-status STORY-NNN`.
- Prove gates: capture a baseline *before* the change, re-run the same gate after, report the delta.
- Suspect flags: propose a DEF, a resolve, or an update — do not leave them sitting.
- Vague or fresh prompt: `specflow brief --next` first. Do not guess the phase.
- Packs (autoresearch, ops, adopt) are separate subsystems — invoke only when the user names that domain.
- User says skip / proceed anyway: do it, and name the risk.
- Reverse lifecycle ("go back to requirements"): `specflow phase-set <phase> --reason "…"` then the matching skill.
- Docs are a knowledge surface, not an artifact: "update the README" → `/specflow-doc` — never a new REQ/DEC for a doc edit.

### Memory (one line)
`specflow brief` is the digest. Artifacts are memory: spec/ = truth, work/ = what happened, impact-log/ = causality, links = `specflow trace`. Promote reusable / second-pass / interface work from SPIKE to REQ/ARCH/DDD (`derives_from`).
