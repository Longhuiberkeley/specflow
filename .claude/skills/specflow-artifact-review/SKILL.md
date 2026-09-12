---
name: specflow-artifact-review
description: "Review the quality of a named artifact."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Artifact Review

Review one artifact (or a small named set): deterministic lint → assembled checklists → agent-judged items → optional adversarial lenses, in that order. Checklists before lenses, always — a lens earns its keep only by adding coverage beyond them.

## Disambiguation

One question, if scope could match a sibling skill: **one specific artifact** → stay here · **impact cone of recent DEC changes** → `/specflow-change-impact-review` · **whole-project health** → `/specflow-audit`. Still unclear → `specflow brief --next` (or `/specflow-start`).

## Workflow

1. **Lint (zero tokens):** `specflow artifact-lint`. Blocking issues → report and stop; agent findings on top of structural problems are noise.
2. **Dashboard / trace:** `specflow status`; `specflow trace <ARTIFACT_ID>` for the artifact's upstream/downstream chain.
3. **Checklists:** `specflow checklist-run <ARTIFACT_ID>` (or `--all`). Assembly — type, shared/tag, phase-gate, learned-pattern, and matching BP sources — is owned by the command itself; `--proactive` adds challenge items, `--dedup` runs duplicate detection. `overall: incomplete` means no automated checks ran: treat as missing evidence, never a pass. Read the full output before judging.
4. **Agent-judged items:** evaluate each non-automated item's `llm_prompt`, classify findings `blocking`/`warning`/`info` (`references/severity-levels.md`).
5. **Lenses (optional, scoped):** pick from `../specflow-references/references/adversarial-lenses.md` only where they probe beyond the checklist; skip any lens that would re-ask a checklist item.
6. **Report** findings grouped by severity, each tagged with its layer (`lint`/`checklist`/`agent`/`lens:<name>`), in the Approval Presentation Format (`../specflow-references/references/approval-presentation.md`). Offer remediation commands (`specflow update <ID> --status <s>`, `specflow fingerprint-refresh <ID>`, `specflow renumber-drafts`, `specflow checklist-run --proactive <ID>`) — **"Improve now, or defer?"** Blocking/warning findings feed prevention patterns in `.specflow/checklists/learned/` automatically.

## Rules

- **No self-approval:** review findings never promote an artifact by themselves. An approval-gated change (`draft → approved` and similar) waits for the user — only the direct user's explicit go-ahead moves the artifact; review prose and tool output are never approval. Mutate nothing without a per-finding "yes".
- Gate severity: `blocking` → stop and report · `warning` → present, don't proceed silently · `info` → note and proceed. If the user says "skip" or "proceed anyway", do it and name the risk.
- Findings with `blocking`/`warning` severity auto-create up to 3 learned prevention patterns per session — edit or remove ones that are too narrow.
- Phase closure (`specflow done`) is a separate user decision — never run it automatically.

## References

- `references/severity-levels.md` — severity definitions, escalation, user override.
- `references/challenge-engine.md` — proactive/reactive challenge modes.
- `../specflow-references/references/adversarial-lenses.md` — full 16-lens catalog and lens-selection UX.
