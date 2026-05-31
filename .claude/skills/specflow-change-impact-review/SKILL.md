---
name: specflow-change-impact-review
description: Use to review the IMPACT CONE of recent changes — finds unreviewed DEC artifacts, computes blast radius, reviews impact, creates CHL findings. Triggers when the user says "what's the impact of this change," "review recent changes," "change impact," or after a series of commits/PRs. NOT for: full-project audits (use specflow-audit), single-artifact review (use specflow-artifact-review), or reviewing changes that don't have DEC artifacts yet.
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

5. **Auto-select adversarial lenses based on cone signals.** Pure pattern-matching misses risks that need an explicit frame. Inspect the tags and types in the impact cone and pick 2-3 lenses from `../specflow-references/references/adversarial-lenses.md` to apply to the impacted artifacts. Selection rules:

   | Signal in cone | Lenses to add |
   |---|---|
   | Tags include `safety`, `hazard`, `compliance`, or any `complies_with: [...]` link | **Regulator** + **Premortem** |
   | Public API / interface changes (ARCH or DDD with `interface` tag, or contract artifacts) | **Worst-case user** + **Composition** |
   | Scale-sensitive change (tags `performance`, `latency`, `throughput`, or DEC mentions traffic/load) | **Stress-scale ×100** + **Cost-scaling** |
   | Long-lived assumption baked in (DEC pins a vendor, protocol version, schema format) | **Temporal drift** + **Dependency shock** |
   | None of the above | **Premortem** + **Composition** (default minimum) |

   Apply the selected lenses to the cone artifacts only — never the full project. Each lens is one focused question; spend a few sentences per lens, not a deep audit. The output is one or more findings per lens, which feed Step 4.

6. **Parallel fan-out for large impact cones (if your platform supports spawning subagents):**
   - **Standard (1-5 impacted artifacts):** Review sequentially — context load is manageable.
   - **Elevated (6-15 impacted artifacts):** Spawn one subagent per artifact type group (e.g., REQs together, ARCHs together). Each subagent applies the selected lenses to its group and returns findings.
   - **Critical (16+ impacted artifacts):** Spawn one subagent per artifact + one synthesis subagent that reads all outputs and identifies cross-artifact patterns. This prevents missing systemic issues that only emerge when you see the whole cone.
   - **Fallback (no subagent support):** Review in artifact-type groups sequentially. For critical cones, do a two-pass review: first pass per-artifact, second pass cross-artifact synthesis.

   **Subagent prompt template (per-artifact-group):**
   > "You are reviewing the impact of change [DEC-ID]: [summary]. Review artifact group [types] within the blast radius. Apply lenses: [lens list]. For each artifact: does the change introduce contradictions, unhandled edge cases, or missing updates? Return findings at blocking/warning/info severity with artifact references."

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
2. Record which lenses were applied to each impacted artifact:
   ```bash
   uv run specflow update <ARTIFACT-ID> --thinking-techniques <lens1,lens2>
   ```
3. Save the updated DEC artifact.

Repeat Steps 2-5 for all unreviewed DECs discovered in Step 1.

## Rules

- **Gate severity:**
  - `blocking` → Stop. Report the failure. Ask the user to fix before proceeding.
  - `warning` → Present. Ask whether to proceed. Do not proceed silently.
  - `info` → Note for awareness. Proceed.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a `blocking` item, articulate: "Proceeding past [specific blocking item]. Risk: [what could go wrong]. Noted."
- **Idempotency:** Always check for `review_status: unreviewed`. If none exist, do nothing.
- **Scoping:** Strictly limit the review to the blast radius computed by `change-impact`. Do not review the entire project.
- **Traceability:** Ensure all findings (CHLs) are explicitly linked to the source DEC that triggered them.
