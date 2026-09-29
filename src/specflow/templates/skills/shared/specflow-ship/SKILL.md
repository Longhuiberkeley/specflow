---
name: specflow-ship
description: "Release a verified version — baseline, change records, audit, release summary."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Ship

A release is a one-way door. Everything that can reject it runs BEFORE the immutable baseline, so a rejected release never burns a tag.

## Workflow

1. **Confirm the tag:** `git describe --tags --abbrev=0` gives the last tag; propose the next (patch by default, minor if new features) as one confirm: "Tag this release **v1.2.0** (Recommended, last was v1.1.0)?" Ask an open question only when no prior tag exists.
2. **Verify (blocking):** re-run the test suite now — green at execute time is not green at release time — then `specflow project-audit --quick` for artifact health. A red suite is `blocking`: report failures verbatim and stop. Both must be green.
3. **Change records:** `specflow document-changes --since <prev-tag>` so the release ships its own DEC trail.
4. **Lens pass (default-on):** temporal_drift, regulator (if compliance-bound), optional premortem, from `../specflow-references/references/adversarial-lenses.md` (one lens per subagent where supported, sequential otherwise). File findings as CHLs; the user may opt out, but never skip silently. Load `_specflow/specs/best-practices/` BPs matching the project domain as release criteria.
5. **Gate:** present per `../specflow-references/references/approval-presentation.md` — a release is Tier 2 (irreversible). Run `specflow risk-tier <IDs>`, persist confidence with `specflow update <DEC> --set risk_profile.confidence=<value>`, and point at the specific concern. Audit severity >= `error` → warn ("fix errors first" is the recommendation) and require explicit confirmation.
6. **Baseline (after approval only):**
   ```
   specflow baseline create <tag> --evidence
   specflow phase-set complete --reason "released <tag>"
   ```
7. **Handoff:** what shipped, the tag, open findings carried forward, and the next command (`/specflow-discover` for the next cycle).

## Rules

- **No self-approval:** never run step 6 on your own reading of the evidence; only the direct user's explicit go-ahead in this conversation releases. Never auto-proceed a release.
- **Gate severity:** `blocking` → stop, report, ask for a fix · `warning` → present, ask whether to proceed · `info` → note and proceed.
- **Escape hatch:** on "skip" / "proceed anyway" do exactly that, after naming the risk: "Proceeding past [item]. Risk: [what could go wrong]. Noted."
- Never skip `project-audit --quick`. Tag format follows project conventions; baseline naming and ordering: `references/baseline-naming.md`.
