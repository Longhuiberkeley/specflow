---
name: specflow-ship
description: Use when the user wants to release a version. Produces a baseline, generates change records, runs a quick audit, and presents a release summary.
---

# SpecFlow Ship

Release workflow: baseline, change records, and audit.

## Workflow

### Step 1: Baseline Creation

1. Ask the user for the release tag/version: "What tag should we use for this release baseline? (e.g., v1.2.0)"
2. Create an immutable baseline snapshot:
```
uv run specflow baseline create <tag>
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
- Ensure the tag format follows project conventions.
- Never skip the Quick Audit step.
- Only proceed past the Advisory Gate if the user gives explicit confirmation when errors are present.
