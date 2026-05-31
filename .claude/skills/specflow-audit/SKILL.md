---
name: specflow-audit
description: Use for a FULL-PROJECT health review — runs a zero-question deterministic core with optional adversarial wings. Creates AUD and CHL artifacts. Triggers when the user says "audit the project," "health check," "how healthy is the project," or asks for a comprehensive project-wide assessment. NOT for: single-artifact review (use specflow-artifact-review), reviewing blast radius of recent changes (use specflow-change-impact-review), or quick spot-checks of one file.
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full LLM analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

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
1. Read `../specflow-references/references/adversarial-lenses.md` for the full 16-lens catalog. Select lenses relevant to the findings from Step 1 (e.g., if coverage gaps found → use `audit-vertical`; if dependency issues → use `dependency_shock`).
2. For any artifact flagged during Step 1, run `uv run specflow trace <ARTIFACT_ID>` to understand its full upstream/downstream dependency context before evaluating lenses.
3. Create 2 parallel subagents (if your environment supports it) to evaluate these lenses against the V-model specifications.
4. Consolidate the findings from the adversarial wings.
5. When creating CHL artifacts, use specific technique names (e.g., `premortem`, `stress_scale`, `dependency_shock`) rather than the generic `project-audit` label. The deterministic core findings use `audit-horizontal`, `audit-vertical`, and `audit-cross-cutting`.
6. After running lenses on sampled artifacts, record which techniques were applied:
   ```
   uv run specflow update <ARTIFACT_ID> --thinking-techniques premortem,stress_scale
   ```

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
- **Gate severity:**
  - `blocking` → Stop. Report the failure. Ask the user to fix before proceeding.
  - `warning` → Present. Ask whether to proceed. Do not proceed silently.
  - `info` → Note for awareness. Proceed.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a `blocking` item, articulate: "Proceeding past [specific blocking item]. Risk: [what could go wrong]. Noted."
- Do not ask context-gathering questions before the deterministic core runs. The core must be zero-question.
- Ensure any generated CHL artifacts include actionable recommendations.
