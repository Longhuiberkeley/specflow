---
name: specflow-ship
description: REQUIRED to release a version. Produces a baseline, generates change records (DEC), runs a quick audit, and presents a release summary. Triggers when the user says "release," "ship," "publish v," or asks to tag a version. This is the final step of the core lifecycle — use it when implementation is complete and verified. NOT for: mid-development checkpoints (use specflow-audit or specflow-artifact-review).
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full LLM analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Ship

Release workflow: baseline, change records, and audit.

## Workflow

### Step 1: Baseline Creation

1. Ask the user for the release tag/version: "What tag should we use for this release baseline? (e.g., v1.2.0)"
2. Create an immutable baseline snapshot with compliance evidence:
```
uv run specflow baseline create <tag> --evidence
```

### Step 2: Document Changes (DEC Trail)

Generate the change records for this release:
1. Ask the user for the previous tag/commit to compare against: "What was the previous release tag or commit? (e.g., v1.1.0)"
2. Run document-changes:
```
uv run specflow document-changes --since <prev>
```
*Note: `document-changes` runs here so each release ships its own DEC trail.*

### Step 3: Quick Audit

Run a fast health check across the final state of the release:
```
uv run specflow project-audit --quick
```

### Step 4: Review and Advisory

1. Present the release summary, including:
   - Links to the created baseline snapshot.
   - Links to the generated DEC artifacts.
   - A summary of the audit report.
2. **Advisory Gate:** If the audit severity is >= `error`, present a clear warning. "The audit returned errors. Are you sure you want to proceed with this release? (Recommended: No, fix errors first)"
3. Require explicit user confirmation to proceed if there are errors.

## Rules
- **Gate severity:**
  - `blocking` → Stop. Report the failure. Ask the user to fix before proceeding.
  - `warning` → Present. Ask whether to proceed. Do not proceed silently.
  - `info` → Note for awareness. Proceed.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a `blocking` item, articulate: "Proceeding past [specific blocking item]. Risk: [what could go wrong]. Noted."
- Ensure the tag format follows project conventions.
- Never skip the Quick Audit step.
- Only proceed past the Advisory Gate if the user gives explicit confirmation when errors are present.
