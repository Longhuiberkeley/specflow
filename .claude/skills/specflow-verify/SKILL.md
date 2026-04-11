---
name: specflow-verify
description: Use when the user wants to review, validate, or verify any SpecFlow artifacts. Triggers context-specific checks using automated scripts and checklist review.
---

# SpecFlow Verify

Review and verify artifacts using automated validation and checklist review.

## Workflow

### Step 1: Run Automated Validation (Zero Tokens)

Always start with deterministic checks:

```
uv run specflow validate
```

This runs all 6 checks: schema, links, status, IDs, fingerprints, acceptance criteria.

If any blocking issues are found, report them and stop. The user must fix blocking issues before proceeding to LLM-judged review.

### Step 2: Review Dashboard

```
uv run specflow status
```

Present the status summary to the user. Note any:
- Artifacts in unexpected phases
- Broken links or orphans
- Missing verification pairs
- Suspect flags

### Step 3: Context-Specific Review

Run `uv run specflow check <ARTIFACT_ID>` to assemble and execute context-specific checklists, or `uv run specflow check --all` for all artifacts. The check command automatically:

1. Loads **artifact type checklists** from `.specflow/checklists/in-process/`
2. Loads **review checklists** from `.specflow/checklists/review/`
3. Loads **domain tag checklists** from `.specflow/checklists/shared/` matching artifact tags
4. Loads **phase-gate checklists** from `.specflow/checklists/phase-gates/` (with `--gate`)
5. Loads **learned patterns** from `.specflow/checklists/learned/` matching artifact tags

Read `references/checklist-assembly.md` for the full assembly algorithm.

### Step 3.5: Proactive Challenges (Optional)

Run `uv run specflow check --proactive <ARTIFACT_ID>` to include proactive challenge items that ask "What could go wrong? What's missing?" Read `references/challenge-engine.md` for details.

### Step 4: Run LLM-Judged Checks

For each assembled checklist item that is NOT automated (`automated: false`):

1. Evaluate the artifact against the checklist item's `llm_prompt`.
2. Classify the finding: `blocking`, `warning`, or `info`.
3. Read `references/severity-levels.md` for severity definitions.

### Step 5: Report Findings

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

### Step 6: Phase Closure

After all work is done, run `uv run specflow done` to:
1. Review completed work in the current phase
2. Extract prevention patterns into `.specflow/checklists/learned/`
3. Close the phase and archive in `state.yaml`
4. Suggest the next phase

Use `--no-patterns` to skip pattern extraction, or `--auto` to skip prompts.

## Rules

- Automated checks (zero tokens) always run first.
- LLM-judged checks only run if automated checks pass.
- Severity levels: `blocking` (must fix), `warning` (should fix), `info` (nice to know).
- Never skip automated checks, even if the user asks for "just a quick review."
- Review is never generic — it's assembled from artifact type + domain + shared + learned sources.

## References

- `references/checklist-assembly.md` — How checklists are assembled for review.
- `references/severity-levels.md` — Severity level definitions and escalation rules.
- `references/challenge-engine.md` — Proactive and reactive challenge modes.
