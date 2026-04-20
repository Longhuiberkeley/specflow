---
name: specflow-artifact-review
description: Use when the user wants to review, validate, or verify any SpecFlow artifacts. Triggers context-specific checks using automated scripts and checklist review.
---

# SpecFlow Artifact Review

Review artifacts by composing deterministic lint → context-specific checklists → LLM judgment → optional adversarial lenses. Lens-based thinking techniques always come **after** checklists, never before.

## Workflow

### Step 1: Run Automated Lint (Zero Tokens)

Always start with deterministic checks:

```
uv run specflow artifact-lint
```

This runs schema, link, status, ID, fingerprint, and acceptance-criteria checks.

If any **blocking** issues are found, report them and stop. The user must fix blocking issues before LLM-judged review — otherwise LLM findings will be noise on top of structural problems.

### Step 2: Review Dashboard

```
uv run specflow status
```

Present the status summary to the user. Note any:
- Artifacts in unexpected phases
- Broken links or orphans
- Missing verification pairs
- Suspect flags

If reviewing a specific artifact, also show its traceability chain:

```
uv run specflow trace <ARTIFACT_ID>
```

This displays upstream (standards, parents) and downstream (implementation, tests) links as a tree, giving full context for the review.

### Step 3: Run Context-Specific Checklists (DO THIS BEFORE LENSES)

This step is **mandatory before Step 4**. Checklists are the curated coverage the project has already invested in; running lenses first would duplicate that work and waste tokens.

Run:

```
uv run specflow checklist-run <ARTIFACT_ID>
```

or, for the full set:

```
uv run specflow checklist-run --all
```

The `checklist-run` command automatically assembles:

1. **Artifact type checklists** from `.specflow/checklists/in-process/`
2. **Review checklists** from `.specflow/checklists/review/`
3. **Domain tag checklists** from `.specflow/checklists/shared/` matching artifact tags
4. **Phase-gate checklists** from `.specflow/checklists/phase-gates/` (with `--gate`)
5. **Learned patterns** from `.specflow/checklists/learned/` matching artifact tags

Read `references/checklist-assembly.md` for the full assembly algorithm.

**Read the full checklist output before continuing.** You will need to know what has already been covered so the LLM and lens passes complement rather than re-ask.

### Step 4: Run LLM-Judged Checklist Items

For each assembled checklist item that is **not** automated (`automated: false`):

1. Evaluate the artifact against the checklist item's `llm_prompt`.
2. Classify the finding: `blocking`, `warning`, or `info`.
3. Read `references/severity-levels.md` for severity definitions.

### Step 5: Apply Adversarial Lenses (Optional, Scoped)

Lenses are adversarial "thinking techniques" that attack the artifact from angles the checklists do not cover. Only apply lenses **after** Steps 3 and 4 — the value of a lens is what it adds beyond existing checklist coverage.

**Starter lenses** (use these by default for most artifacts):

- **Devil's advocate** — Assume the artifact is wrong. What evidence says this requirement, design, or story is mistaken or unnecessary?
- **Premortem** — Six months out, this failed. What caused it?
- **Assumption surfacing** — Enumerate every implicit assumption. Attack each: what if it's false?
- **Red team / blue team** — Especially for security-adjacent REQs and ARCHs with trust boundaries. Red finds exploits; blue finds defenses.

Run with:

```
uv run specflow checklist-run --proactive <ARTIFACT_ID>
```

This surfaces proactive challenge items ("what could go wrong? what's missing?") alongside the assembled checklist.

For the full 16-lens catalog (stress-scale, dependency shock, reversal, five-whys, outside view, worst-case user, regulator, temporal drift, composition, inversion, competitor, cost-scaling) and the lens-selection checklist UX, read `references/adversarial-lenses.md`.

**Rule:** never propose a lens whose finding would be a direct duplicate of a checklist item already run in Step 3. If a lens would only repeat the checklist, skip it.

### Step 6: Report Findings

Present results organized by severity:

```
## Blocking Issues (must fix)
1. [REQ-001] Missing acceptance criteria
2. [ARCH-002] No public interface defined

## Warnings (should fix)
1. [REQ-003] Non-functional requirement "fast" is not quantified
2. [STORY-001] Only 1 acceptance criterion (minimum is 3)

## Info (nice to know)
1. [REQ-004] Uses "should" where "shall" may be more appropriate

## Passed
- Schema validation: 12/12 artifacts pass
- Link integrity: all links resolve
- Status transitions: all valid
```

Each finding should note which layer produced it (`lint`, `checklist`, `llm`, or `lens:<name>`), so the user can tell curated coverage from adversarial probing.

### Step 7: Human-Review Summary

Before offering remediation, present a structured summary so the user can validate the review itself — not just its findings:

```
## Summary for Human Review

### Key Decisions Made
- Scope of this review (which artifact IDs, which depth)
- Which lenses were applied vs. skipped, and why
- Severity classification calls that were borderline

### Assumptions That Need Validation
- Each artifact's stated purpose was taken at face value — risk if wrong: review is graded against the wrong rubric
- Severity thresholds follow `references/severity-levels.md` defaults — risk if wrong: urgency signal is miscalibrated for this project
- Lenses not run may have found issues we missed — risk if wrong: false clean bill of health

### Please Review
- Every `blocking` and `warning` finding individually — decide fix-now vs. defer
- Any artifact that passed cleanly but feels risky — consider rerunning with a deeper lens selection
- Any finding flagged as `info` that you think should be a `warning`
```

### Step 8: "Improve Now?" Prompt

After the summary, offer concrete remediation commands the user can run:

- For a status change: `uv run specflow update <ID> --status <newstatus>`
- For a fingerprint refresh after manual edits: `uv run specflow fingerprint-refresh <ID>`
- For renumbering draft IDs before merge: `uv run specflow renumber-drafts`
- For re-running a deeper review on one artifact: `uv run specflow checklist-run --proactive <ID>`

Ask: **"Improve now — or defer?"** Do not mutate target artifact statuses without an explicit user "yes" per finding.

### Step 9: Phase Closure (Optional)

If this review concludes the phase's work, the user may run `uv run specflow done` to:
1. Review completed work in the current phase
2. Extract prevention patterns into `.specflow/checklists/learned/`
3. Close the phase and archive in `state.yaml`
4. Suggest the next phase

Use `--no-patterns` to skip pattern extraction, or `--auto` to skip prompts. This is a separate decision from the review itself — do not run it automatically.

## Rules

- **Automated lint (zero tokens) always runs first.** LLM-judged checks only run if lint passes.
- **Checklists before lenses, always.** Lenses complement checklists; they do not replace them.
- Severity levels: `blocking` (must fix), `warning` (should fix), `info` (nice to know).
- Never skip automated checks, even if the user asks for "just a quick review."
- Never silently mutate a target artifact's status. The user confirms each change.
- Review is never generic — it is assembled from artifact type + domain + shared + learned sources, then optionally probed with lenses.

## References

- `references/checklist-assembly.md` — How checklists are assembled for review.
- `references/severity-levels.md` — Severity level definitions and escalation rules.
- `references/challenge-engine.md` — Proactive and reactive challenge modes.
- `references/adversarial-lenses.md` — Full 16-lens catalog and lens-selection UX for adversarial review.
