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

### Step 3: Assemble Review Checklists

Based on what's being reviewed, assemble relevant checklists:

1. **Artifact type checklists** — Load from `.specflow/checklists/in-process/` based on the artifact types being reviewed (e.g., `requirement-writing.yaml` for REQs).
2. **Domain tag checklists** — Load from `.specflow/checklists/shared/` if any match the artifact's tags.
3. **Phase-gate checklists** — Load from `.specflow/checklists/phase-gates/` if a phase transition is pending.
4. **Learned checklists** — Load from `.specflow/checklists/learned/` for prevention patterns from past work.

Read `references/checklist-assembly.md` for the full assembly algorithm.

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

## Rules

- Automated checks (zero tokens) always run first.
- LLM-judged checks only run if automated checks pass.
- Severity levels: `blocking` (must fix), `warning` (should fix), `info` (nice to know).
- Never skip automated checks, even if the user asks for "just a quick review."

## References

- `references/checklist-assembly.md` — How checklists are assembled for review.
- `references/severity-levels.md` — Severity level definitions and escalation rules.
