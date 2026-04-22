---
name: specflow-change-impact-review
description: Use when the user wants to run the change-audit pipeline to autonomously review impact cones of recent changes and log findings.
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full LLM analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Change Impact Review

This skill implements the change-audit pipeline. It finds all unreviewed Change Records (DEC artifacts), computes their blast radius, reviews impacted artifacts against architectural constraints, files findings as Challenges (CHL artifacts), and updates the DEC status.

## Workflow

### Step 1: Discovery

Find all Decision (DEC) artifacts representing change records that need review.
Look in `_specflow/work/decisions/` for artifacts containing `review_status: unreviewed` in their YAML frontmatter.

If no unreviewed DECs are found, announce that the pipeline is clean (idempotent behavior) and exit gracefully without doing any work.

### Step 2: Scoping (Blast Radius)

For each unreviewed DEC found:
1. Identify the impacted artifacts. You can use the `specflow change-impact` command on the DEC's ID (or the artifacts it addresses) to compute the blast radius.
   ```bash
   uv run specflow change-impact <DEC_ID>
   ```
2. Note the "cone of impact". This limits the scope of the review to only the artifacts affected by the change, preventing unnecessary full-project reviews.

### Step 3: Review

For each DEC and its impact cone:
1. Read the DEC artifact to understand the nature of the change (from its `body` and `rationale`).
2. Read the impacted artifacts within the cone.
3. Analyze the change against existing architectural constraints, requirements, and system design.
4. Look for:
   - Contradictions with existing REQs.
   - Unhandled edge cases introduced by the change.
   - Missing updates to related tests or documentation.

### Step 4: Filing Findings

If issues are discovered during the review of a DEC's impact cone:
1. Create a Challenge (CHL) artifact for each distinct issue.
   ```bash
   uv run specflow create --type challenge --title "<Summary of issue>"
   ```
2. Set the `severity` of the CHL (e.g., `warning`, `error`).
3. Link the CHL to the DEC using the role `challenges`.

### Step 5: Resolution

After the review for a specific DEC is complete:
1. Update the DEC's `review_status` in its YAML frontmatter.
   - If issues were found and CHL artifacts created, set `review_status: flagged`.
   - If the change is clean and no issues were found, set `review_status: reviewed`.
2. Save the updated DEC artifact.

Repeat Steps 2-5 for all unreviewed DECs discovered in Step 1.

## Rules

- **Idempotency:** Always check for `review_status: unreviewed`. If none exist, do nothing.
- **Scoping:** Strictly limit the review to the blast radius computed by `change-impact`. Do not review the entire project.
- **Traceability:** Ensure all findings (CHLs) are explicitly linked to the source DEC that triggered them.
