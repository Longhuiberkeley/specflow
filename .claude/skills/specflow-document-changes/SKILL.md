---
name: specflow-document-changes
description: Use when the user wants to generate change records (DEC artifacts) from recent git history. Run `/cmd` to invoke.
---

# SpecFlow Document Changes

Generate Decision (DEC) artifacts representing change records from git commit history. This is stage 1 of the two-stage change-audit pipeline (stage 2 is `/specflow-change-impact-review`).

## Workflow

### Step 1: Determine the Since Reference

Ask the user for a git reference to start from, or infer a sensible default:
- The last tag or baseline
- The most recent DEC's commit date
- A user-supplied branch or tag name

### Step 2: Run the CLI Command

Execute the `document-changes` command with the `--since` flag:

```bash
uv run specflow document-changes --since <git-ref>
```

This command is idempotent — commits already recorded in existing DECs are skipped.

### Step 3: Report Results

Summarize the output for the user:
- How many DEC artifacts were created
- How many commits were skipped (no spec artifact changes or already documented)
- List the new DEC IDs with their titles

### Step 4: Suggest Next Step

If any DECs were created, suggest running `/specflow-change-impact-review` to review them.

## Rules

- **Idempotency:** The underlying CLI deduplicates by commit SHA. Running twice with the same `--since` is safe.
- **No manual DEC creation:** Always use the CLI command to ensure consistent formatting, linking, and indexing.
- **`review_status`:** All generated DECs start with `review_status: unreviewed`. Do not change this field manually.
