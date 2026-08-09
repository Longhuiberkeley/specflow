---
name: specflow-audit
description: SCOPE = the whole project. Use for a FULL-PROJECT health review — runs a zero-question deterministic core with optional adversarial wings. Creates AUD and CHL artifacts. Triggers when the user says "audit the project," "health check," "how healthy is the project," "review the whole project," "review overall spec quality," or asks for a comprehensive project-wide assessment. NOT for: single-artifact review (use specflow-artifact-review), reviewing blast radius of recent changes (use specflow-change-impact-review), or quick spot-checks of one file.
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full agent-driven analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

## Disambiguation

If the user's intent could match another review skill, confirm scope with **one** question before proceeding:
- **Whole-project health** → stay here (`specflow-audit`).
- **One specific artifact** → `/specflow-artifact-review`.
- **Impact cone of recent changes** → `/specflow-change-impact-review`.

If still unclear, run `specflow brief --next` (or `/specflow-start`) and let the user choose.

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Audit

Full-project health review.

## Workflow

### Step 1: Load Best Practices (Zero Tokens)

Before running the audit, check for active best-practice artifacts in `_specflow/specs/best-practices/`. If present, read the ones matching the project's domain tags. These BPs define domain-specific health criteria that the audit should cross-reference against artifact state. If no BPs exist, note this in the audit summary as a gap.

### Step 2: Deterministic Core (Zero-Question)

Run the automated audit pipeline silently. This covers horizontal, vertical, and cross-cutting checks — including an **orphan-code lens** that flags source files not traced to any STORY/REQ via `output_files`, and a **docs-staleness** check that flags docs citing superseded/cancelled/deprecated artifacts via inline `@ID` markers (warning only — never escalates the exit code). (Skipped under `--quick`.)

```
specflow project-audit
```

Useful flags:
- `--quick` skips cross-cutting analysis.
- `--dry-run` prints findings without writing snapshots, AUD/CHL artifacts, or cache.
- `--sample-pct N` samples STORY artifacts (default 100).
- `--baseline <name>` anchors drift from that baseline to the newest release.

Findings are cached in `.specflow/audits/.cache/` with a generation key. Body edits and audit-relevant frontmatter edits (status, links, tags, NFR, verification fields) invalidate the cache; `--dry-run` writes nothing.

If the audit reports orphaned source code, list the specific files with `specflow detect orphan-code` and offer to adopt them (`--retro-link STORY-NNN`) so every file traces back to a spec.

After the project audit, run the chain depth survey to show traceability coverage distribution:

```
specflow artifact-lint --type chain-report
```

For the full bidirectional traceability matrix (REQ → ARCH → STORY → verifying tests, gap markers per row), run `specflow rtm --gaps`.

Then, run the standards gap analysis to check compliance health against installed packs:

```
specflow standards gaps
```

Include the chain depth distribution and the standards compliance score in the audit summary (Step 5). The chain depth is informational data about how deep traceability chains run across the project — not a pass/fail indicator. The standards compliance score should be highlighted if it is below 100%.

### Step 3: Adversarial Wings (Optional)

After the core audit completes, offer to run deeper, AI-driven adversarial reviews:

- "The deterministic audit is complete. Would you like me to run the adversarial wings to review qualitative alignment? (Recommended: Yes, if preparing for a release/milestone)"

If accepted:
1. Read `../specflow-references/references/adversarial-lenses.md` for the full 16-lens catalog. Select lenses relevant to the findings from Step 2 (e.g., if coverage gaps found → use `audit-vertical`; if dependency issues → use `dependency_shock`).
2. For any artifact flagged during Step 2, run `specflow trace <ARTIFACT_ID>` to understand its full upstream/downstream dependency context before evaluating lenses.

3. **Parallel lens fan-out (error-driven scaling).** DEFAULT on Claude Code/OpenCode; sequential single-agent fallback on hosts without native subagents (see `../specflow-references/references/adversarial-lenses.md` § Multi-Agent Strategy). Context budget ~2000 tokens/lens; output is identical either way (CHL findings tagged per lens + `thinking_techniques` records). The per-scale subagent counts below are for capable hosts:
   - **Standard (0-2 errors in Step 2):** Create 2 parallel subagents (if your platform supports spawning subagents) each covering a subset of the selected lenses. Sequential fallback: run lens groups sequentially.
   - **Elevated (3-7 errors in Step 2):** Create 3-4 parallel subagents (if supported), one lens per subagent. This gives each lens its own context window for deeper analysis. Sequential fallback: run lenses one at a time.
   - **Critical (8+ errors in Step 2):** Create 4-5 parallel subagents, plus a dedicated cross-cutting subagent that reads ALL lens outputs and synthesizes systemic patterns (e.g., "4 of 5 lenses flagged the same coupling issue — this is architectural, not local"). Sequential fallback: run all lenses sequentially, then a dedicated synthesis pass.

4. Consolidate the findings from the adversarial wings.
5. When creating CHL artifacts, use specific technique names (e.g., `premortem`, `stress_scale`, `dependency_shock`) rather than the generic `project-audit` label. The deterministic core findings use `audit-horizontal`, `audit-vertical`, and `audit-cross-cutting`.
6. After running lenses on sampled artifacts, record which techniques were applied:
   ```
   specflow update <ARTIFACT_ID> --thinking-techniques premortem,stress_scale
   ```

### Step 4: Artifacts (Auto-Created)

The `specflow project-audit` command in Step 2 already creates an AUD artifact for the run and title-deduplicated CHL artifacts for actionable findings. Do not create duplicates manually.

If Step 2 used `--dry-run`, no artifacts were written. Only when the user explicitly wants to persist that dry-run should you create one AUD plus CHLs for its actionable findings, linking each CHL to the AUD via `identified_by`.

### Step 5: Summary

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
