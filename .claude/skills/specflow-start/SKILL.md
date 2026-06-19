---
name: specflow-start
description: Use when unsure which SpecFlow step to run next, or for a quick "where am I / what's next" orientation. Runs `specflow brief --next` for a deterministic next-step recommendation, asks ONE disambiguating question only if intent is ambiguous, and points at the right /specflow-* skill. Triggers on "what now", "what next", "where do I start", "continue", "resume", or general uncertainty about the next lifecycle step. NOT a replacement for the lifecycle skills (discover/plan/execute/ship) or the review skills — it only routes you to the correct one. Prefer this over guessing when the user's intent is vague.
---

# SpecFlow Start

A thin, host-neutral router: orient on project state, then point at the right next skill.

## Workflow

1. **Recall state (deterministic, zero tokens):** run `uv run specflow brief --next`. It reads `state.yaml` + the artifact graph and prints a single next-step recommendation (e.g. *"REQs approved, no ARCH yet → /specflow-plan"*).

2. **If the recommendation is unambiguous:** tell the user exactly which slash-command to run next, and stop. Examples:
   - *"You have approved REQs but no architecture yet → run `/specflow-plan`."*
   - *"All stories are implemented → run `/specflow-ship`."*
   - *"3 suspects are open → run `specflow change-impact` (or `specflow defect-from-suspect <ID> --req <REQ>`), then continue."*

3. **If intent is ambiguous, ask ONE disambiguating question, then route.** The common ambiguity is the three review skills:
   > "Reviewing **(a)** one specific artifact, **(b)** the impact of recent changes, or **(c)** the whole project's health?"
   - (a) → `/specflow-artifact-review`
   - (b) → `/specflow-change-impact-review`
   - (c) → `/specflow-audit`

   Another: "build X" with no REQs yet → `/specflow-discover`; with REQs already approved → `/specflow-execute`.

4. **Do not call the Skill tool yourself.** Tell the user which slash-command to run. This keeps routing host-neutral — it works identically on Claude Code, OpenCode, Codex, and the ALM/CLI lane.

## Rules
- Always run `brief --next` first — the recommendation is deterministic and free.
- At most ONE disambiguating question. If still unclear, surface the `brief --next` recommendation and let the user choose.
- This skill never creates or modifies artifacts; it only orients and routes.
