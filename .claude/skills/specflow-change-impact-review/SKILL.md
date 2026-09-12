---
name: specflow-change-impact-review
description: "Review the blast radius of recent DECs."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Change Impact Review

The change-audit pipeline: find unreviewed change records (DECs), compute their blast radius, review the impacted artifacts, file findings as CHLs, and update the DEC.

## Workflow

1. **Discover:** DEC artifacts in `_specflow/work/decisions/` with `review_status: unreviewed`. None found → announce the pipeline is clean and exit (idempotent).
2. **Scope the blast radius:** `specflow change-impact <DEC_ID>`. To map recent non-`_specflow/` code changes back to artifacts via `output_files`: `specflow change-impact --flag`. Review only the cone — never the whole project.
3. **Review the cone:** read the DEC and each impacted artifact; look for contradictions with existing REQs, unhandled edge cases, missing test updates, and docs whose `@ID` citations now point at superseded/cancelled/deprecated artifacts (`specflow detect stale-docs`; resolve by updating the citation — warning only).
4. **Pick 2-3 lenses** from `../specflow-references/references/adversarial-lenses.md` by cone signal: safety/hazard/compliance/complies_with → regulator + premortem · public API/interface → worst-case-user + composition · performance/latency/load → stress-scale + cost-scaling · pinned vendor/protocol/schema assumption → temporal-drift + dependency-shock · otherwise → premortem + composition. Apply to cone artifacts only; each lens is one focused question.
5. **File findings:** one CHL per distinct issue — `specflow create --type challenge --title "<summary>"`, set `severity`, link it to the DEC with the `challenges` role.
6. **Resolve:** `specflow change-impact --resolve <ARTIFACT_ID>` for reviewed suspect flags, then stamp the DEC — issues found → `specflow update <DEC-ID> --set review_status=flagged`; clean → `--set review_status=reviewed`. Record the lenses applied: `specflow update <ARTIFACT-ID> --thinking-techniques <lens1,lens2>`.

Repeat for every unreviewed DEC.

## Rules

- **No self-approval:** resolving a suspect (`--resolve`) and stamping `review_status=reviewed` assert that you presented the evidence to the direct user and they accepted it. Filing CHLs is yours; clearing them is not — walk the user through it.
- Every CHL links explicitly to the DEC that triggered it.
- Gate severity: `blocking` → stop and report · `warning` → present, don't proceed silently · `info` → note and proceed. If the user says "skip" or "proceed anyway", do it and name the risk.
