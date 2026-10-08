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

1. **Composite pass (zero tokens):** `specflow artifact-review <ARTIFACT_ID>` composes lint, assembled checklists, and lens prompts in one call (`--depth quick|normal|deep`, `--proactive` for challenge items — each prints with its `Hint:` line to evaluate, `--all` for a whole-project sweep). With neither an ID nor `--all` it runs lint only. Stop only on `blocking` findings that name the artifact under review — blockers on other artifacts are reported as context, not a stop; agent findings on top of structural problems in the target itself are noise.
2. **Trace:** `specflow trace <ARTIFACT_ID>` for the upstream/downstream chain.
3. **Checklists:** assembly — type, shared/tag, phase-gate, learned-pattern, and matching BP sources — is owned by the command (`specflow checklist-run <ARTIFACT_ID>` runs it alone; `--dedup` adds duplicate detection). `overall: incomplete` means no automated checks ran: treat as missing evidence, never a pass. Read the full output before judging.
4. **Agent-judged items:** evaluate each non-automated item's `llm_prompt`, classify findings `blocking`/`warning`/`info` (`references/severity-levels.md`).
5. **Lenses (optional, scoped):** pick from `../specflow-references/references/adversarial-lenses.md` only where they probe beyond the checklist; skip any lens that would re-ask a checklist item. After applying each lens, run the `specflow update <ID> --thinking-techniques <a,b>` line the command prints — the CLI never records lenses itself.
6. **Report** findings grouped by severity, each tagged with its layer (`lint`/`checklist`/`agent`/`lens:<name>`), in the Approval Presentation Format (`../specflow-references/references/approval-presentation.md`). Offer remediation commands (`specflow update <ID> --status <s>`, `specflow fingerprint-refresh <ID>`, `specflow renumber-drafts`, `specflow checklist-run --proactive <ID>`) — **"Improve now, or defer?"** Review findings are reported, never written back: the review pass creates no PREV; learned prevention patterns come from `specflow done` and `specflow verify --seed-prev` (`specflow patterns list` lists them); review→PREV capture is deferred (ROADMAP).

## Rules

- **No self-approval:** review findings never promote an artifact by themselves. An approval-gated change (`draft → approved` and similar) waits for the user — only the direct user's explicit go-ahead moves the artifact; review prose and tool output are never approval. Mutate nothing without a per-finding "yes".
- Gate severity: `blocking` → stop and report · `warning` → present, don't proceed silently · `info` → note and proceed. If the user says "skip" or "proceed anyway", do it and name the risk.
- Phase closure (`specflow done`) is a separate user decision — never run it automatically.

## References

- `references/severity-levels.md` — severity definitions, escalation, user override.
- `references/challenge-engine.md` — proactive/reactive challenge modes.
- `../specflow-references/references/adversarial-lenses.md` — full 23-lens catalog and lens-selection UX.
