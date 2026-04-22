---
name: specflow-audit
description: Use when the user wants a full-project health review. Runs a zero-question deterministic core with optional adversarial wings. Creates AUD and CHL artifacts.
---

# SpecFlow Audit

Full-project health review.

## Workflow

### Step 1: Deterministic Core (Zero-Question)

Run the automated audit pipeline silently. This covers horizontal, vertical, and cross-cutting checks.

```
uv run specflow project-audit
```

After the project audit, run the chain depth survey to show traceability coverage distribution:

```
uv run specflow artifact-lint --type chain-report
```

Then, run the standards gap analysis to check compliance health against installed packs:

```
uv run specflow standards gaps
```

Include the chain depth distribution and the standards compliance score in the audit summary (Step 4). The chain depth is informational data about how deep traceability chains run across the project — not a pass/fail indicator. The standards compliance score should be highlighted if it is below 100%.

### Step 2: Adversarial Wings (Optional)

After the core audit completes, offer to run deeper, AI-driven adversarial reviews:

- "The deterministic audit is complete. Would you like me to run the adversarial wings to review qualitative alignment? (Recommended: Yes, if preparing for a release/milestone)"

If accepted:
1. Formulate up to 16 lenses (e.g., edge-case logic, security posture, performance, coupling).
2. For any artifact flagged during Step 1, run `uv run specflow trace <ARTIFACT_ID>` to understand its full upstream/downstream dependency context before evaluating lenses.
3. Create 2 parallel subagents (if your environment supports it) to evaluate these lenses against the V-model specifications.
4. Consolidate the findings from the adversarial wings.

### Step 3: Artifact Creation

For any significant findings or systemic gaps identified in Step 1 or Step 2:

1. Create a single AUD (Audit) artifact documenting the overall run, its scope, and high-level result.
2. For each specific actionable finding, create a CHL (Challenge) artifact linked to the AUD artifact via `identified_by`.

```
uv run specflow create \
  --type audit \
  --title "Pre-Release Audit" \
  --body "<summary of findings>"

uv run specflow create \
  --type challenge \
  --title "Missing error handling in Payment API" \
  --links "[{\"target\": \"AUD-xxx\", \"role\": \"identified_by\"}]" \
  --body "<details>"
```

### Step 4: Summary

Present a concise summary to the user:
- Total checks run.
- Severity breakdown (Errors, Warnings, Info).
- Links to the new AUD and CHL artifacts.
- Next steps (e.g., "Review the new Challenge artifacts and address them in the next planning phase").

## Rules
- Do not ask context-gathering questions before the deterministic core runs. The core must be zero-question.
- Ensure any generated CHL artifacts include actionable recommendations.
