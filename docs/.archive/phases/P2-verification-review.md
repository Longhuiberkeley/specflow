# P2 Verification — Implementation Review & Remediation Plan

**Date:** 2026-04-11
**Reviewer:** opencode (GLM-5.1)
**Scope:** Review of P2 Verification deliverables (24 files created, 4 files edited)

## Executive Summary

The P2 verification implementation delivers functional validation tooling, but suffers from **significant code duplication** between shell scripts and Python modules, **dead code** in the CLI validate command, and a **mismatch** between the architecture doc's stated design and the actual implementation.

The core functionality works: `specflow validate` runs 6 checks, `specflow status` shows a dashboard, and phase-gate checklists are templates. The issues are structural, not functional.

---

## 1. Architecture Context: Skills vs CLI

### Why commands are NOT embedded in skills

The architecture defines two distinct command axes (`docs/architecture.md:286-312`):

| Axis | Technology | Token cost | Examples |
|------|-----------|------------|----------|
| **Conversational** (agent-driven) | SKILL.md files | LLM tokens | `specflow check` → specflow-verify, `specflow new` → specflow-discover |
| **Programmatic** (Python CLI + scripts) | Python + shell | Zero tokens | `specflow validate`, `specflow status`, `specflow init` |

The verify skill (`specflow-verify`) is a **superset** of the validate command:

1. Step 1: Calls `uv run specflow validate` (zero-token deterministic checks)
2. Step 2: Calls `uv run specflow status` (dashboard)
3. Step 3: Assembles checklists, runs LLM-judged review
4. Step 4: Reports findings

**This is correct.** Skills are agent-facing entry points that layer LLM intelligence on top of deterministic CLI tools. The CLI commands are the reusable foundation for both skills and CI/CD pipelines.

---

## 2. Issues Found

### Issue 1: Shell scripts fully duplicate Python logic (Critical)

**7 shell scripts** in `scripts/` each contain ~100-180 lines of inline Python (generated into temp files at runtime) that reimplements the same validation logic as:

- `src/specflow/lib/validation.py` (~320 lines)
- `src/specflow/lib/artifacts.py` (~310 lines)

The CLI validate command (`commands/validate.py`) has:
- A `_run_script()` function that calls shell scripts — **dead code, never invoked**
- A `_run_check_python()` function that runs Python directly — **this is what actually executes**

**Impact:** Any bug fix must be applied in two places. The shell scripts don't import from the installed `specflow` package (except `validate-links.sh` which tries and `validate-status.sh` which has a fragile fallback).

### Issue 2: Duplicate lib modules (Medium)

| Dead module | Living equivalent | Overlap |
|-------------|-------------------|---------|
| `lib/schema_validator.py` | `lib/validation.py` | Both have `load_schemas()` and `validate_artifact()` |
| `lib/fingerprint.py` | `lib/artifacts.py` | Both have `compute_fingerprint()` |

These are never imported by any active code path.

### Issue 3: Architecture doc mismatch (Low)

`docs/architecture.md:300` states:
> "All programmatic commands call shell scripts in `scripts/` internally."

Reality: The Python CLI performs validation directly via `lib/` modules, bypassing shell scripts entirely.

### Issue 4: validate-gate.sh capability missing from CLI (Medium)

The shell script `validate-gate.sh` runs phase-gate checklists interactively. The Python CLI `specflow validate` does not support `--gate <name>` to run a specific phase-gate checklist. This capability would be lost if shell scripts are removed without adding it to the CLI.

---

## 3. Remediation Plan

### Strategy: Python-primary, shell scripts as thin wrappers

Make the Python CLI the single source of truth. Shell scripts become ~3-line wrappers for CI/CD compatibility.

### Phase 1: Remove dead code

| Action | File | Reason |
|--------|------|--------|
| Delete | `src/specflow/lib/schema_validator.py` | Fully duplicated by `lib/validation.py` |
| Delete | `src/specflow/lib/fingerprint.py` | Fully duplicated by `lib/artifacts.py` |
| Clean up | `src/specflow/commands/validate.py` | Remove `_run_script()`, simplify `CHECKS` dict to just check names (no script paths) |

### Phase 2: Add missing --gate flag to validate command

The CLI needs phase-gate checklist execution before shell scripts are simplified.

- Add `--gate <gate-name>` argument to the validate subcommand in `cli.py`
- Implement gate checklist execution in `commands/validate.py` using existing `lib/validation.py` checklist loading functions
- Supported gate names: `idle-to-discovering`, `discovering-to-specifying`, `specifying-to-planning`, `planning-to-executing`, `executing-to-verifying`, `verifying-to-complete`

### Phase 3: Convert shell scripts to thin CLI wrappers

Each script becomes a one-liner delegating to the Python CLI:

| Script | New content |
|--------|-------------|
| `scripts/validate.sh` | `uv run specflow validate "$@"` |
| `scripts/validate-links.sh` | `uv run specflow validate --type links "$@"` |
| `scripts/validate-status.sh` | `uv run specflow validate --type status "$@"` |
| `scripts/validate-ids.sh` | `uv run specflow validate --type ids "$@"` |
| `scripts/validate-fingerprints.sh` | `uv run specflow validate --type fingerprints "$@"` |
| `scripts/validate-gate.sh` | `uv run specflow validate --type gate --gate "$@"` |
| `scripts/check-acceptance-criteria.sh` | `uv run specflow validate --type acceptance "$@"` |

**Lines removed:** ~800 lines of inline Python across 7 scripts.
**Lines added:** ~21 lines total (3 lines × 7 scripts with shebang + error check).

### Phase 4: Update architecture doc

- Revise `docs/architecture.md:300` to reflect Python-primary strategy
- Add note that shell scripts are thin CI/CD wrappers, not independent implementations

---

## 4. Files Changed Summary

| Action | File | Est. lines changed |
|--------|------|--------------------|
| Delete | `src/specflow/lib/schema_validator.py` | -112 |
| Delete | `src/specflow/lib/fingerprint.py` | -76 |
| Edit | `src/specflow/commands/validate.py` | ~30 (cleanup + --gate flag) |
| Edit | `src/specflow/cli.py` | ~5 (add --gate argument) |
| Rewrite | `scripts/validate.sh` | -49 → +3 |
| Rewrite | `scripts/validate-links.sh` | -90 → +3 |
| Rewrite | `scripts/validate-status.sh` | -177 → +3 |
| Rewrite | `scripts/validate-ids.sh` | -115 → +3 |
| Rewrite | `scripts/validate-fingerprints.sh` | -109 → +3 |
| Rewrite | `scripts/validate-gate.sh` | -145 → +3 |
| Rewrite | `scripts/check-acceptance-criteria.sh` | -114 → +3 |
| Edit | `docs/architecture.md` | ~5 |

**Net:** ~800 lines removed, ~50 lines added.

---

## 5. What's NOT in Scope

- The 14 checklist templates — these are correctly placed and well-structured
- The specflow-verify skill — correctly layered on top of CLI
- `commands/status.py` enhancements — working as intended
- `lib/scaffold.py` and `commands/init.py` checklist copying — working as intended
- Any new features (impact, compliance, baseline commands) — those are future P-items

---

## 6. Open Questions for Consultation

1. **Should the thin shell wrappers include any error handling** (e.g., check that `uv` is available), or is failing with a raw error acceptable for CI/CD use?

2. **Should `validate-gate.sh`'s interactive behavior be preserved?** Currently it prints pass/fail per checklist item. The Python `--gate` flag would need to match this output format for CI compatibility.

3. **Are the standalone `lib/schema_validator.py` and `lib/fingerprint.py` used externally** (e.g., imported by user scripts or CI pipelines outside this repo)? If so, we'd keep them as re-exports rather than deleting outright.

4. **Should the architecture doc's "programmatic commands call shell scripts" principle be revised entirely**, or should we add a future milestone to eventually make the CLI call the scripts (the original intent)?
