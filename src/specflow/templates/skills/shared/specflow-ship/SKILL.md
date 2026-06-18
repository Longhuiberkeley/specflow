---
name: specflow-ship
description: REQUIRED to release a version. Produces a baseline, generates change records (DEC), runs a quick audit, and presents a release summary. Triggers when the user says "release," "ship," "publish v," or asks to tag a version. This is the final step of the core lifecycle — use it when implementation is complete and verified. NOT for: mid-development checkpoints (use specflow-audit or specflow-artifact-review).
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full agent-driven analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Ship

Release workflow: baseline, change records, and audit.

## Workflow

### Step 1: Load Best Practices and Thinking Techniques

Before starting the release workflow, load domain-specific context:

1. **Best practices:** Check `_specflow/specs/best-practices/` for active BP artifacts. If present, read the ones matching the project's domain tags. These define compliance requirements that the release gate should verify against.
2. **Thinking techniques:** Apply ship-phase defaults from the adversarial lens catalog:
   - **Temporal drift** — Are any assumptions, dependencies, or specs stale relative to when they were written?
   - **Regulator** — If this project is compliance-bound, does the release satisfy the relevant standard's exit criteria?
   - **Premortem** (optional) — Six months out, this release caused a production incident. What went wrong?

Read `../specflow-references/references/adversarial-lenses.md` for the full catalog. Apply the relevant lenses to the release scope in Step 4.

### Step 2: Baseline Creation

1. Ask the user for the release tag/version: "What tag should we use for this release baseline? (e.g., v1.2.0)"
2. Create an immutable baseline snapshot with compliance evidence:
```
uv run specflow baseline create <tag> --evidence
```

### Step 3: Document Changes (DEC Trail)

Generate the change records for this release:
1. Ask the user for the previous tag/commit to compare against: "What was the previous release tag or commit? (e.g., v1.1.0)"
2. Run document-changes:
```
uv run specflow document-changes --since <prev>
```
*Note: `document-changes` runs here so each release ships its own DEC trail.*

### Step 4: Quick Audit

**Verification-gate re-run (blocking).** A release is a one-way door, so confirm the gate is green *now* — not just that it was green at execute time. Re-run the test suite (the same gate execute baselined in Step 3 of `/specflow-execute`). A non-green gate is **`blocking`**: stop, report the failures verbatim, and do not proceed until green. If execute recorded a baseline + delta, surface it here. `project-audit --quick` below checks artifact health; it does *not* prove the suite passes — both must be green to ship.

Run a fast health check across the final state of the release:
```
uv run specflow project-audit --quick
```

### Step 5: Review and Advisory (Approval Gate)

Present the release summary following the **Approval Presentation Format** (see `../specflow-references/references/approval-presentation.md`):

1. **TLDR** — What's being released, version tag, scope summary (1-3 sentences).
2. **Changes inline** — Baseline snapshot details, DEC artifacts with key changes summarized (not just links), audit findings. The human should not need to open files.
3. **Assessment lenses** — Apply staleness, coverage, and compliance lenses, then a **Risk Profile** for the release (a release is **irreversible** by default — a published tag is a one-way door; report blast radius and your confidence). Show ✅/⚠️/❌ results.
4. **Risk-proportional gate** — A release is Tier 2 (irreversible): point at any specific concern and require targeted sign-off. Never auto-proceed a release.
5. **Advisory Gate:** If the audit severity is >= `error`, present a clear warning. "The audit returned errors. Are you sure you want to proceed with this release? (Recommended: No, fix errors first)"
6. Require explicit user confirmation to proceed if there are errors.

## Rules
- **Gate severity:**
  - `blocking` → Stop. Report the failure. Ask the user to fix before proceeding.
  - `warning` → Present. Ask whether to proceed. Do not proceed silently.
  - `info` → Note for awareness. Proceed.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a `blocking` item, articulate: "Proceeding past [specific blocking item]. Risk: [what could go wrong]. Noted."
- Ensure the tag format follows project conventions.
- Never skip the Quick Audit step.
- Only proceed past the Advisory Gate if the user gives explicit confirmation when errors are present.
