---
name: specflow-ship
description: "Release a verified version — baseline, change records, audit, release summary."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Ship

A release is a one-way door. Everything that can reject it runs BEFORE the immutable baseline, so a rejected release never burns a tag.

## Workflow

1. **Confirm the tag:** `git describe --tags --abbrev=0` gives the last tag; propose the next (patch by default, minor if new features) as one confirm: "Tag this release **v1.2.0** (Recommended, last was v1.1.0)?" Ask an open question only when no prior tag exists. Pre-flight: `specflow renumber-drafts --dry-run` — slug IDs (e.g. `ARCH-041`) still unrenumbered get sequential IDs now, before anything cites them in a baseline Run it without `--dry-run`, then present the findings whose subject IDs changed (`renumber-drafts` rewrites `_specflow/` only, so every baselined finding on a renumbered artifact reappears as new) and, on the user's go-ahead, `specflow findings-baseline update --accept-new` (approval-gated — plain `update` writes nothing and exits 1 here).
2. **Verify (blocking):** re-run the test suite now — green at execute time is not green at release time — then `specflow project-audit --quick` for artifact health. A red suite is `blocking`: report failures verbatim and stop. Both must be green. Findings the user accepts as known debt: `specflow findings-baseline update --accept-new` (approval-gated — present the list first) before the baseline; plain `specflow findings-baseline update` after fixes drops resolved entries.
3. **Promote to verified (advisory):** `specflow verify --all --dry-run` lists every `verify_command`; run `specflow verify --all` where the project records evidence, then `specflow artifact-lint --type gate --gate verifying-to-complete` and evaluate its `automated: false` items yourself. Present the `implemented → verified` batch as one Tier 2 approval (`specflow update <ID> --status verified` per artifact on the user's go-ahead), then `specflow phase-set verifying --reason "release <tag>"` — bookkeeping only (phase-set never gates), so the phase history and `brief --next` stay honest. Unverified artifacts never block the release — list them in the handoff.
4. **Change records:** `specflow document-changes --since <prev-tag>` so the release ships its own DEC trail.
5. **Lens pass (default-on):** temporal_drift, regulator (if compliance-bound), optional premortem, from `../specflow-references/references/adversarial-lenses.md` (one lens per subagent where supported, sequential otherwise). File findings as CHLs; the user may opt out, but never skip silently. Load `_specflow/specs/best-practices/` BPs matching the project domain as release criteria.
6. **Gate:** present per `../specflow-references/references/approval-presentation.md` — a release is Tier 2 (irreversible). Run `specflow risk-tier <IDs>`, persist confidence with `specflow update <DEC> --set risk_profile.confidence=<value>`, and point at the specific concern. Audit severity >= `error` → warn ("fix errors first" is the recommendation) and require explicit confirmation.
7. **Baseline (after approval only):**
   ```
   specflow baseline create <tag> --evidence
   specflow phase-set complete --reason "released <tag>"
   ```
8. **Handoff:** what shipped, the tag, the next command (`/specflow-discover` for the next cycle), and every open item tagged by owner: `[engine]` (a SpecFlow bug or cry-wolf signal — suggest `specflow create --type defect --title "<symptom>"`, a suggestion, not an action), `[this repo]` (project debt carried forward), `[you]` (only the user can do it, e.g. restart the host). Never file an engine bug as "existing debt".

## Rules

- **No self-approval:** never run step 7 on your own reading of the evidence; only the direct user's explicit go-ahead in this conversation releases. Never auto-proceed a release.
- **Gate severity:** `blocking` → stop, report, ask for a fix · `warning` → present, ask whether to proceed · `info` → note and proceed.
- **Escape hatch:** on "skip" / "proceed anyway" do exactly that, after naming the risk: "Proceeding past [item]. Risk: [what could go wrong]. Noted."
- Never skip `project-audit --quick`. Tag format follows project conventions; baseline naming and ordering: `references/baseline-naming.md`.
