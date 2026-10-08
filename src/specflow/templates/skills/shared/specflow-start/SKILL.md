---
name: specflow-start
description: "Next SpecFlow step is unknown — run `specflow brief --next` and name the skill."
---

# SpecFlow Start

A thin, host-neutral router: orient on project state, then point at the right next skill.

## Workflow

0. **No `.specflow/` directory in the project?** SpecFlow is not initialized — route to `/specflow-init` and stop (`brief` cannot run without it).

1. **Recall state (deterministic, zero tokens):** run `specflow brief --next`. It reads `state.yaml` + the artifact graph and prints a deterministic next-step recommendation with any actionable advisory notes (e.g. *"REQs approved, no ARCH yet → /specflow-plan"*).

2. **Honor health/setup advisories before routing:** if `brief` reports drifted schemas, preview with `specflow refresh --schemas --dry-run`; plain `--schemas` preserves local changes, while explicit `--force` restores shipped defaults. Never overwrite schema customizations silently.

3. **If the recommendation is unambiguous:** tell the user exactly which slash-command to run next, and stop. Examples:
   - *"You have approved REQs but no architecture yet → run `/specflow-plan`."*
   - *"All stories are implemented → run `/specflow-artifact-review` on what changed, then `/specflow-ship`."*
   - *"3 suspects are open → run `/specflow-change-impact-review`, then continue."*

4. **If intent is ambiguous, ask ONE disambiguating question, then route.** The common ambiguity is the three review skills:
   > "Reviewing **(a)** one specific artifact, **(b)** the impact of recent changes, or **(c)** the whole project's health?"
   - (a) → `/specflow-artifact-review`
   - (b) → `/specflow-change-impact-review`
   - (c) → `/specflow-audit`

   Another: "build X" — no REQs yet → `/specflow-discover`; approved REQs but no STORYs → `/specflow-plan`; approved STORYs (or a trivial change that still needs a STORY) → `/specflow-execute`. `brief --next` routes approved REQs with no STORY to `/specflow-plan`; the discover lean path (one REQ + one STORY, no ARCH by design) goes to `/specflow-execute` while a covering STORY is approved, and to `/specflow-artifact-review` → `/specflow-ship` once every covering STORY is implemented/verified.
   Docs intent — "write/update the docs or README", "cite the spec from a doc", "are the docs stale / out of date" → `/specflow-doc`.

5. **Do not call the Skill tool yourself.** Tell the user which slash-command to run. This keeps routing host-neutral — it works identically on Claude Code, OpenCode, Codex, and the ALM/CLI lane.

## Delegating to subagents

When you fan work out to subagents, each brief carries: the skill to follow (name it — `/specflow-execute`, `/specflow-plan` — so the subagent reads that SKILL.md first), the current `specflow brief --next` output, and the exact STORY/REQ IDs in scope — never "the next story". Allocate IDs serially in the parent before fan-out (`specflow create ...` once per artifact, then pass the IDs); parallel creates race the index. Tell subagents to read skill references with a bounded read (`sed -n 1,80p <file>`, or the host's file-read tool with a line range), never `cat <file> | head` — a closed pipe aborts the command. Subagents report back the IDs they changed and the exact `specflow update ...` commands they ran; the parent runs `specflow artifact-lint` once after the wave.

## Rules
- Always run `brief --next` first — the recommendation is deterministic and free.
- At most ONE disambiguating question. If still unclear, surface the `brief --next` recommendation and let the user choose.
- This skill never creates or modifies artifacts; it only orients and routes.
