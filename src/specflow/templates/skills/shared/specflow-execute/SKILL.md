---
name: specflow-execute
description: Implementation path for planned stories. Orchestrates implementation of approved stories, updates artifact statuses, creates V-model test artifacts (UT/IT/QT), and enforces traceability. Triggers when the user is ready to CODE approved, planned work — "implement the stories," "execute the plan," "start coding," "build out the approved stories," or "run the next wave." Also triggers for reverse lifecycle: "rethink the implementation," or "this approach isn't working." (To go BACK to architecture use specflow-plan; to go back to requirements use specflow-discover.) This is step 3 of the core lifecycle. For trivial changes (typos, formatting, dependency updates), the lean path is available — but every code change still traces to a STORY. NOT for: requirements gathering (use specflow-discover), architecture design (use specflow-plan), single-artifact review (use specflow-artifact-review), or research experiments.
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full agent-driven analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Execute

Orchestrate the implementation of planned stories and update tracking artifacts.

## Workflow

### Step 0: Reverse Lifecycle Check

If the user said "rethink the implementation," "this approach isn't working," or "go back to architecture" (or if you detect the user wants to revisit architecture/requirements after executing), ask: "Do you want to (a) revise the current STORY's implementation, (b) go back to architecture (run /specflow-plan), or (c) go back to requirements (run /specflow-discover)?" If revising a STORY, read the existing STORY and DDD and offer targeted edits rather than starting from scratch. If going back to architecture or requirements, route the user to the appropriate skill.

### Step 1: Implementation-Readiness Gate

The planning-to-executing phase gate IS the readiness check. Run it before any implementation work. The gate adapts to change scope:

| Change type | Minimum bar |
|-------------|-------------|
| New feature / new component | Full gate pass (no blocking items). All warnings reviewed. |
| Bug fix (unknown root cause) | REQ must exist. STORY must have acceptance criteria. |
| Bug fix (clear scope, existing REQ) | STORY linked to REQ. DDD optional. |
| Refactoring (no behavior change) | STORY linked to affected ARCH. Warnings advisory. |
| Typo / formatting / dependency updates | Gate is advisory. State skip reason and proceed. |

**Escalation check.** If you arrived here mid-chat on work that started as a SPIKE or ad-hoc experiment, apply the **Permanence Test** before treating it as throwaway — work that will be reused, is on its second pass, defines an interface, or must outlive the session should be **promoted** to a durable REQ/ARCH/DDD (or a research COMP) first. See `references/escalation-and-promotion.md` for the recipe.

1. **Run the deterministic gate:**
   ```
   uv run specflow artifact-lint --type gate --gate planning-to-executing
   ```
   - Exit 1 → at least one automated blocking item failed (missing ARCH, broken links, etc.). **Stop. Do not proceed.** Report the failures verbatim and ask the user to address them. Re-run the gate after fixes.
   - Exit 0 → automated checks pass; agent-judged items show as `○` (skipped by the deterministic runner).

2. **Evaluate the agent-judged items yourself.** Read `.specflow/checklists/phase-gates/planning-to-executing.yaml`. For every item with `automated: false`, scope artifact reads narrowly:
   - Use `_index.yaml` files in `_specflow/work/stories/` and `_specflow/specs/architecture/` to enumerate IDs, statuses, and link metadata without opening every artifact body.
   - Open full artifact bodies only for the subset that needs agent judgement (e.g., the STORYs in the current wave, ARCHs referenced by those STORYs). At 100+ stories, sample by wave or by suspect/recently-modified flags rather than reading every file.
   - Then answer the `llm_prompt` against the scoped subset and report findings as:
     - `blocking` severity items → these MUST be addressed before proceeding.
     - `warning` severity items → present them and ask the user whether to proceed anyway. Do not proceed silently.

3. **Identify the in-scope STORY set.** Use `uv run specflow go --dry-run` to compute the next wave; that's the read-set for this run. Avoid reading STORYs outside the upcoming wave unless an agent-judged item explicitly requires cross-story analysis.

4. **Check `suspect: true` flags** on ALL linked artifacts in the in-scope set. Run `uv run specflow status` and scan for suspect markers. If upstream specs are suspect, do NOT just warn — **actively propose resolution**:
   - "ARCH-001 is suspect (REQ-001 changed on 2026-06-01). Options: (a) Create DEF — the ARCH genuinely no longer satisfies the REQ. (b) Mark resolved — the change was cosmetic. (c) Update ARCH to match the new REQ."
   - The human picks. You execute. Do not let suspect flags sit unresolved.
   - If the human chooses (a): run `uv run specflow defect-from-suspect <SUSPECT_ID> --req <REQ_ID> [--severity ...]`. This creates a DEF with auto-linked `fails_to_meet` → REQ and `exposed_by` → the suspect artifact, registered in the index. Then `uv run specflow change-impact --resolve <SUSPECT_ID>` once addressed.
   - If the human chooses (b): `uv run specflow change-impact --resolve <SUSPECT_ID>`.

5. Run `uv run specflow status` silently for the state overview.

6. **RBAC pre-check (if `.specflow/adapters.yaml` has team config):** Verify the current user is authorized to implement the in-scope stories. Run `uv run specflow hook pre-commit` as a dry-run — it checks RBAC on staged artifact changes. If the project has no team configuration, skip this step. If RBAC check fails, surface the failure as a `warning` — the user can proceed but the commit hook will catch it.

 **Why the gate is mandatory:** the gate verifies the task is sufficiently specified to start coding (ARCH exists, links resolve, AC are clear, interfaces defined, test strategy specified, dependencies approved, RBAC allows implementation). Skipping it lets implementation start against draft specs and produces rework.

7. **Load best practices** as context for implementation. Read BP artifacts from `_specflow/specs/best-practices/`. If execution-phase BPs don't exist yet, generate them covering implementation patterns relevant to the project domain.

**Proactive Enforcement Loop:** Actively audit your implementation strategy against these BPs before writing code. If a BP suggests a specific pattern (e.g., defensive copies for data pipelines, dependency injection for web apps), ensure your code uses it, and briefly tell the user that you applied it.

### Step 2: Wave Planning

1. Run `uv run specflow go --dry-run` to compute the execution wave plan.
2. Review the wave groupings -- stories in the same wave can run in parallel.
3. If the wave plan looks wrong, check story dependencies (`derives_from`, shared `specified_by`).
4. Read `references/wave-computation.md` for algorithm details.

### Step 3: Implementation

**Capture the gate baseline first (once per run).** Before writing any code, run the project's test suite and record the baseline — pass/fail counts and the names of currently-failing tests. This is the diff point for later "no regressions" claims. If the project has no test runner yet, capture the `artifact-lint` baseline instead and say so explicitly. You will re-run this same gate in Step 6 (Validation) and report the delta.

For each story (or wave of stories):

1. Run `uv run specflow go` to compute wave context, or implement manually:
   a. **Load context:** Run `uv run specflow brief` for a one-call digest (phase, inventory, suspects, next wave, recent changes), then read the story and its linked REQ, ARCH, and DDD artifacts. Use the brief's inventory and `_index.yaml` to scope what to open — read full bodies only for the in-scope set.
   b. **Verify spec approval:** All linked spec artifacts (REQ/ARCH/DDD) must be `approved` or later. If any linked spec is still `draft`, STOP and ask the human: "STORY-NNN links to ARCH-NNN which is still `draft`. I need approval before implementing against it. Approve ARCH-NNN? (y/n)" Do not implement against unapproved specs.
   c. **Decompose and Validate:** For complex stories (especially ML/quant data pipelines, trading logic, or multi-step algorithms), **do not write monolithic code immediately**.
      - Present a logical decomposition first (e.g., "1. Data ingestion, 2. Signal generation, 3. Portfolio allocation").
      - Propose internal sanity checks (e.g., "I will assert that the resulting weights sum to 1.0").
      - Ask the user: *"Does this flow and these checks look correct before I implement the code?"*
   c. **Implement the code** per the detailed design and your validated decomposition.
   d. **Follow the acceptance criteria** -- implement each criterion from the story.
   e. **Thinking during implementation** (from `references/thinking-techniques.md`):
      - **Mental prompts (reflection only, not recorded):** before writing each function, ask "what's the most unexpected input?" and "does this share state with another STORY in this wave?" — these guide your coding but do not produce `thinking_techniques` records.
      - **Catalog lenses (recorded):** apply `worst-case-user` and `composition` to the STORY. After applying, record them: `uv run specflow update <STORY-ID> --thinking-techniques worst_case_user,composition`.

      **Optional fan-out for complex stories** (see `../specflow-references/references/adversarial-lenses.md` § Multi-Agent Strategy): for stories with 3+ linked DDDs or cross-cutting risk tags, spawn two subagents — one for worst-case-user analysis, one for composition analysis — each with its own context window. Fallback: sequential (the reference implementation).

### Step 4: Status Updates

After implementing a story, update its status and cascade to linked specs:

```
uv run specflow update STORY-001 --status implemented
uv run specflow cascade-status STORY-001
```

`cascade-status` automatically updates linked ARCH/DDD artifacts from `approved` to `implemented`. Add `--include-req` to also cascade to the linked REQ.

**Execution state is machine-managed.** `specflow go` writes per-artifact locks to `.specflow/locks/*.json` while waves run and tracks progress in `.specflow/execution-state.yaml`. Do not edit these by hand -- the CLI releases locks on completion and uses `execution-state.yaml` to resume interrupted runs.

### Step 5: Test Creation

For each implemented spec artifact, create its V-model verification test -- **all three levels**, not just unit tests:

| Spec type | Test type | Link role |
|-----------|-----------|-----------|
| REQ | QT (qualification test) | `verified_by` |
| ARCH | IT (integration test) | `verified_by` |
| DDD | UT (unit test) | `verified_by` |

Use `specflow generate-tests` to create stubs deterministically:

```
# Generate test stubs for all implemented specs missing verification
uv run specflow generate-tests

# Generate for a specific artifact
uv run specflow generate-tests --from DDD-001

# Preview what would be created
uv run specflow generate-tests --dry-run
```

Alternatively, create manually:

```
uv run specflow create \
  --type unit-test \
  --title "Test <DDD function>" \
  --links "[{\"target\": \"DDD-001\", \"role\": \"verified_by\"}]" \
  --body "<test cases>"
```

Read `references/test-pairing.md` when you are unsure which test level a given change needs.

### Step 5.5: Human-Review Summary (Approval Gate)

Before running full validation, present the implementation summary following the **Approval Presentation Format** (see `../specflow-references/references/approval-presentation.md`):

1. **TLDR** — What was implemented and what changed (1-3 sentences).
2. **What this does (functional)** — The implemented behavior in plain terms (purpose · what's in · what's out), so the human grasps what changed before reading STORY IDs.
3. **Changes inline** — For each STORY implemented: what code was written, what tests were created, any deviations from ARCH/DDD. The human should not need to open files.
4. **Assessment lenses** — Apply coverage, traceability, and staleness lenses, then a **Risk Profile per change** (reversibility, blast radius via `specflow change-impact`, confidence + why it isn't higher).
5. **Key decisions (2–3)** — The decisions that determine whether this implementation is right (what was chosen · alternative · tradeoff · what validates it). **Fold the coverage checks in here**, not after the gate:
   - For each STORY: does every acceptance criterion map to at least one test (UT/IT/QT)?
   - Any STORY marked `implemented` whose linked ARCH/DDD is still `approved`?
   - Any code file NOT referenced by a test artifact?
   - Implementation choices not pre-specified by DDD (library picks, file layout)

   Make the gate the approve-or-improve loop: proceed · discuss #N · revise and re-present.
6. **Risk-proportional gate** — Assign a tier (0 light / 1 normal / 2 stop) from the risk profile; for Tier 2, point at the specific concern. Tier comes from the change, not past approvals.
7. **Action options** — Approve / Request changes / Discuss.

Wait for user acknowledgement before proceeding.

### Step 6: Validation

Run full validation after all changes:
```
uv run specflow artifact-lint
```

Report results and fix any issues.

**Verification-gate delta.** Re-run the *same* gate you baselined at the top of Step 3 (the test suite, or `artifact-lint` if that was the baseline). Report the delta vs baseline: "baseline N failing {a,b} → now M failing {…}: +c I caused it / -d I fixed it / unchanged." Read a real exit code — don't grep narrowed to your own files. If the count rose, you caused a regression: revert the offending step, re-diagnose, re-sequence — don't stack a fix on a broken base.

Record the gate result (baseline + final + delta) in the STORY or its linked UT/IT/QT artifact so `verified` is traced, not asserted. Do not move a STORY or test artifact to `verified` without this delta on record.

**Exit message:** Report the count of stories marked `implemented`, tests created (UT/IT/QT), and the verification-gate delta. Recommend the next skill -- `/specflow-artifact-review`.

### Step 7: Phase Closure (Optional)

1. After all stories are implemented and validated, check readiness with `uv run specflow phase-status` — a read-only advisory that reports whether the phase is ready to close (suspects resolved, gate green). Then offer closure: "All planned stories are implemented and the phase is ready to close. Close it now and extract prevention patterns?" If `phase-status` reports blockers, address those first rather than offering closure.
2. If the user declines ("not yet", "skip"), do not force closure.
3. If accepted, run `uv run specflow done`. Options:
   - `--no-patterns` -- skip prevention-pattern extraction.
   - `--auto` -- accept defaults without interactive prompts.
4. Engage in a conversational review:
   - Summarize the accomplishments (count of stories, tests).
   - Review any extracted prevention patterns with the user to ensure they are actionable.
   - Recommend archiving or cleaning up any temporary context files from the implementation phase.

**Final Exit message:** If the phase was closed, recommend the next logical skill: `/specflow-ship`.

## Rules

- **Gate severity:**
  - `blocking` → Stop. Report the failure. Ask the user to fix before proceeding.
  - `warning` → Present. Ask whether to proceed. Do not proceed silently.
  - `info` → Note for awareness. Proceed.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a `blocking` item, articulate: "Proceeding past [specific blocking item]. Risk: [what could go wrong]. Noted."
- Always update `status` and `modified` timestamp via `specflow update` -- never edit artifact files directly.
- Link tests to what they verify using `verified_by` role.
- Run `uv run specflow artifact-lint` after status changes.
- When unsure about valid status transitions, read `references/status-lifecycle.md`.
- When unsure about V-model test pairing, read `references/test-pairing.md`.

## References

- `references/status-lifecycle.md` -- Valid status transitions for all artifact types.
- `references/test-pairing.md` -- V-model verification test pairing rules.
- `references/wave-computation.md` -- Wave computation algorithm and context isolation.
- `references/thinking-techniques.md` -- Quick execution-stage thinking checks (points to shared catalog at `../specflow-references/references/adversarial-lenses.md`).
