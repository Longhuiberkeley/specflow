---
name: specflow-start
description: Use when unsure which SpecFlow step to run next, or for a quick "where am I / what's next" orientation. Runs `specflow brief --next` for a deterministic next-step recommendation, asks ONE disambiguating question only if intent is ambiguous, and points at the right /specflow-* skill. Triggers on "what should I do," "what's next," "what now," "where do I start," "where are we," "what's the status," "continue," "resume," "remind me where we are," "help me get started," "I'm stuck," "point me in the right direction," or any request that doesn't clearly match a specific lifecycle or review skill. This is the safe default when no other skill clearly fits — prefer routing over guessing. NOT a replacement for the lifecycle skills (discover/plan/execute/ship) or the review skills — it only routes you to the correct one. Prefer this over guessing when the user's intent is vague.
---

# SpecFlow Start

A thin, host-neutral router: orient on project state, then point at the right next skill.

## Workflow

1. **Recall state (deterministic, zero tokens):** run `specflow brief --next`. It reads `state.yaml` + the artifact graph and prints a deterministic next-step recommendation with any actionable advisory notes (e.g. *"REQs approved, no ARCH yet → /specflow-plan"*).

2. **Honor health/setup advisories before routing:** if `brief` reports drifted schemas, preview with `specflow refresh --schemas --dry-run`; plain `--schemas` preserves local changes, while explicit `--force` restores shipped defaults. Never overwrite schema customizations silently.

3. **If the recommendation is unambiguous:** tell the user exactly which slash-command to run next, and stop. Examples:
   - *"You have approved REQs but no architecture yet → run `/specflow-plan`."*
   - *"All stories are implemented → run `/specflow-artifact-review` (review + V-model tests UT/IT/QT), then `/specflow-ship`."*
   - *"3 suspects are open → run `specflow change-impact` (or `specflow defect-from-suspect <ID> --req <REQ>`), then continue."*

4. **If intent is ambiguous, ask ONE disambiguating question, then route.** The common ambiguity is the three review skills:
   > "Reviewing **(a)** one specific artifact, **(b)** the impact of recent changes, or **(c)** the whole project's health?"
   - (a) → `/specflow-artifact-review`
   - (b) → `/specflow-change-impact-review`
   - (c) → `/specflow-audit`

   Another: "build X" with no REQs yet → `/specflow-discover`; with REQs already approved → `/specflow-execute`.
   Docs intent — "write/update the docs or README", "cite the spec from a doc", "are the docs stale / out of date" → `/specflow-doc`.

5. **Do not call the Skill tool yourself.** Tell the user which slash-command to run. This keeps routing host-neutral — it works identically on Claude Code, OpenCode, Codex, and the ALM/CLI lane.

## Rules
- Always run `brief --next` first — the recommendation is deterministic and free.
- At most ONE disambiguating question. If still unclear, surface the `brief --next` recommendation and let the user choose.
- This skill never creates or modifies artifacts; it only orients and routes.
