---
name: specflow-project-audit
description: Full-project health review with seamless core and optional adversarial wings.
version: 1.0.0
---

# /specflow-project-audit

Full-project health review. Runs a **seamless core** (deterministic, zero questions) across all three analysis axes, then optionally offers **wings** (deep adversarial analysis using the 16-lens catalog).

## Design principle

**Seamless is the name of the game.** The core runs automatically with zero user questions. Scope and depth are auto-detected from project state. Only after the core finishes and the user reads the results does the skill ask whether deeper analysis is wanted.

## Workflow

### Step 1: Run the deterministic core

Execute the CLI backend:

```bash
specflow project-audit [--sample-pct N]
```

This runs all three analysis axes in one pass:
- **Horizontal** — per artifact type, internal consistency checks
- **Vertical** — per top-level REQ, V-model thread coherence (REQ→ARCH→DDD→STORY→tests)
- **Cross-cutting** — consistency, completeness, baseline-drift, standards-coverage, NFR-coverage, test-coverage

Outputs:
- `.specflow/audits/{timestamp}/report.md` — top-level summary
- `.specflow/audits/{timestamp}/subagent-horizontal.md`
- `.specflow/audits/{timestamp}/subagent-vertical.md`
- `.specflow/audits/{timestamp}/subagent-cross-cutting.md`
- `_specflow/specs/audits/AUD-{N}.md` — AUD artifact
- CHL artifacts for findings at severity >= warn

Exit codes: 0 = clean, 2 = warnings, 3 = errors, 4 = tool error

### Step 2: Present core findings

Read `.specflow/audits/{timestamp}/report.md` and present the summary to the user:
- Total findings by severity
- Key issues that need attention
- Where to find the full report

### Step 3: Offer wings (only if user wants more)

If the core found any findings, or the user asks for deeper analysis:

> Core audit complete: X errors, Y warnings found. Full report at `.specflow/audits/{ts}/report.md`.
>
> Would you like deeper adversarial analysis? The 16-lens catalog probes blind spots that deterministic checks miss.

If the user declines, stop here. If they accept, proceed to Step 4.

### Step 4: Launch wing subagents

Read the two lens catalog reference docs:
- `references/lens-catalog-structural.md` — 8 structural lenses
- `references/lens-catalog-stakeholder.md` — 8 stakeholder lenses

Launch **2 subagents in parallel**, one per wing:

**Wing A (Structural)** — Subagent prompt:
```
You are a project auditor applying 8 structural adversarial lenses to a SpecFlow project.
Read the lens catalog at references/lens-catalog-structural.md for definitions.
Here is the project context:
[insert report.md contents]
[insert contents of key REQ/ARCH/STORY artifacts]

Apply ALL 8 lenses. For each finding, output:
- title: short finding title
- rationale: explanation
- severity: warn | error | info
- lens: which lens found this
```

**Wing B (Stakeholder)** — Subagent prompt:
```
You are a project auditor applying 8 stakeholder adversarial lenses to a SpecFlow project.
Read the lens catalog at references/lens-catalog-stakeholder.md for definitions.
Here is the project context:
[insert report.md contents]
[insert contents of key REQ/ARCH/STORY artifacts]

Apply ALL 8 lenses. For each finding, output:
- title: short finding title
- rationale: explanation
- severity: warn | error | info
- lens: which lens found this
```

### Step 5: Collect wing findings

For each finding from the wings:
1. Present it in the severity report alongside core findings
2. Create a CHL artifact if severity >= warn:
   ```bash
   specflow create --type challenge --title "<title>" --rationale "<rationale>" --links "AUD-{N}:refers_to"
   specflow update CHL-{M} --severity <severity>
   ```

### Step 6: Final summary

Present the combined core + wings findings organized by severity. Suggest next actions.

## Context efficiency

- The core is deterministic: **zero LLM tokens**
- Wings use ~2 subagent calls, each processing the project summary + one lens catalog
- Project context is the report.md (not raw artifacts) to minimize token spend
- Fingerprint cache skips unchanged artifacts on repeated runs

## Reads

- All artifacts in `_specflow/` (via CLI, not direct reads)
- `.specflow/audits/{ts}/report.md` (core output)
- `.specflow/standards/*.yaml` (auto-detected for compliance scope)
- `.specflow/baselines/*.yaml` (auto-detected for drift comparison)

## Writes

- `.specflow/audits/{ts}/*` (audit reports, created by CLI)
- `_specflow/specs/audits/AUD-{N}.md` (created by CLI)
- `_specflow/specs/challenges/CHL-{N}.md` (created by skill for wing findings)

## Side effects

- CHL artifacts created for findings >= warn
- AUD artifact created with review_status: open
- Fingerprint cache entries at `.specflow/audits/.cache/`
