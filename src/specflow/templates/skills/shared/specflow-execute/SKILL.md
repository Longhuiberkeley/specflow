---
name: specflow-execute
description: DEFAULT implementation path for ANY code change in this project. Orchestrates implementation of planned stories, updates artifact statuses, creates V-model test artifacts (UT/IT/QT), and enforces traceability. Triggers when the user says "implement," "write code for," "build," "fix bug in," or any code-writing request. This is step 3 of the core lifecycle — use it for ALL implementation work. For trivial changes (typos, formatting, dependency updates), the lean path is available — but every code change still traces to a STORY. NOT for: requirements gathering (use specflow-discover), architecture design (use specflow-plan), or research experiments (use specflow-autoresearch if installed).
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full LLM analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Execute

Orchestrate the implementation of planned stories and update tracking artifacts.

## Workflow

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
   - Exit 0 → automated checks pass; LLM-judged items show as `○` (skipped by the deterministic runner).

2. **Evaluate the LLM-judged items yourself.** Read `.specflow/checklists/phase-gates/planning-to-executing.yaml`. For every item with `automated: false`, scope artifact reads narrowly:
   - Use `_index.yaml` files in `_specflow/work/stories/` and `_specflow/specs/architecture/` to enumerate IDs, statuses, and link metadata without opening every artifact body.
   - Open full artifact bodies only for the subset that needs LLM judgement (e.g., the STORYs in the current wave, ARCHs referenced by those STORYs). At 100+ stories, sample by wave or by suspect/recently-modified flags rather than reading every file.
   - Then answer the `llm_prompt` against the scoped subset and report findings as:
     - `blocking` severity items → these MUST be addressed before proceeding.
     - `warning` severity items → present them and ask the user whether to proceed anyway. Do not proceed silently.

3. **Identify the in-scope STORY set.** Use `uv run specflow go --dry-run` to compute the next wave; that's the read-set for this run. Avoid reading STORYs outside the upcoming wave unless an LLM-judged item explicitly requires cross-story analysis.

4. **Check `suspect: true` flags** on ALL linked artifacts in the in-scope set. Run `uv run specflow status` and scan for suspect markers. If upstream specs are suspect, surface this as a `blocking` item — do not proceed against stale specs without explicit user confirmation. Report: "Artifact [ID] is flagged suspect (modified [date]). [Reason]. Proceeding may waste effort. Continue anyway?"

5. Run `uv run specflow status` silently for the state overview.

6. **RBAC pre-check (if `.specflow/adapters.yaml` has team config):** Verify the current user is authorized to implement the in-scope stories. Run `uv run specflow hook pre-commit` as a dry-run — it checks RBAC on staged artifact changes. If the project has no team configuration, skip this step. If RBAC check fails, surface the failure as a `warning` — the user can proceed but the commit hook will catch it.

 **Why the gate is mandatory:** the gate verifies the task is sufficiently specified to start coding (ARCH exists, links resolve, AC are clear, interfaces defined, test strategy specified, dependencies approved, RBAC allows implementation). Skipping it lets implementation start against draft specs and produces rework.

7. **Load execution-phase best practices** as context for implementation:
   ```
   uv run specflow handbook generate execute-impl
   ```
   Read the output with `uv run specflow handbook show execute-impl`. The generated BPs provide domain-specific guidance on what good implementation and testing look like for this project's domain. 

**Proactive Enforcement Loop:** Actively audit your implementation strategy against these BPs before writing code. If a BP suggests a specific pattern (e.g., defensive copies for data pipelines, dependency injection for web apps), ensure your code uses it, and briefly tell the user that you applied it. If no API key is configured, this step is skipped gracefully.

### Step 2: Wave Planning

1. Run `uv run specflow go --dry-run` to compute the execution wave plan.
2. Review the wave groupings -- stories in the same wave can run in parallel.
3. If the wave plan looks wrong, check story dependencies (`derives_from`, shared `specified_by`).
4. Read `references/wave-computation.md` for algorithm details.

### Step 3: Implementation

For each story (or wave of stories):

1. Run `uv run specflow go` to compute wave context, or implement manually:
   a. **Load context:** Read the story, its linked REQ, ARCH, and DDD artifacts.
   b. **Decompose and Validate:** For complex stories (especially ML/quant data pipelines, trading logic, or multi-step algorithms), **do not write monolithic code immediately**.
      - Present a logical decomposition first (e.g., "1. Data ingestion, 2. Signal generation, 3. Portfolio allocation").
      - Propose internal sanity checks (e.g., "I will assert that the resulting weights sum to 1.0").
      - Ask the user: *"Does this flow and these checks look correct before I implement the code?"*
   c. **Implement the code** per the detailed design and your validated decomposition.
   d. **Follow the acceptance criteria** -- implement each criterion from the story.
   e. **Quick thinking check** (from `references/thinking-techniques.md`): before writing each function, ask "what's the most unexpected input?" and "does this share state with another STORY in this wave?" After applying techniques to a STORY, record them: `uv run specflow update <STORY-ID> --thinking-techniques worst_case_user,composition`.

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

### Step 5.5: Human-Review Summary

Before running full validation, present a structured summary so the user can catch silent implementation decisions:

```
## Summary for Human Review

### Key Decisions Made
- Implementation choices not pre-specified by DDD (library/framework picks, file layout)
- Test strategy: how QT / IT / UT are split per story, and where you stopped
- Any deviation from the linked ARCH/DDD and why

### Assumptions That Need Validation
- External dependencies assumed available in test (stubs, fixtures, network) -- risk if wrong: tests pass locally but fail in CI
- Performance/latency assumptions baked into code -- risk if wrong: NFRs silently violated
- Any STORY that was implemented without a linked DDD -- risk if wrong: future changes lack a specification anchor

### Please Review
- For each STORY: does every acceptance criterion map to at least one of UT / IT / QT?
- Any STORY marked `implemented` whose linked ARCH/DDD is still `approved` (not `implemented`)?
- Any code file written that is NOT referenced by a test artifact?
```

Wait for user acknowledgement before proceeding.

### Step 6: Validation

Run full validation after all changes:
```
uv run specflow artifact-lint
```

Report results and fix any issues.

**Exit message:** Report the count of stories marked `implemented` and tests created (UT/IT/QT). Recommend the next skill -- `/specflow-artifact-review`.

### Step 7: Phase Closure (Optional)

1. After all stories are implemented and validated, offer phase closure: "All planned stories are implemented. Would you like to close this phase and extract prevention patterns?" (Recommended: Not yet, if more work remains, or Yes if the sprint/wave is complete).
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
