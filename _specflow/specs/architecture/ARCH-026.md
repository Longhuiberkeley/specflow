---
id: ARCH-026
title: Verification-contract recording + accounting evidence lenses
type: architecture
status: approved
priority: high
rationale: "Refines REQ-037: how SpecFlow turns the verified status from an assertion\
  \ into recorded, machine-checkable evidence without ever becoming a gate. Two coupled\
  \ mechanisms \u2014 a verification-contract recorder (specflow verify) and accounting\
  \ lenses that surface evidence gaps as warnings \u2014 over the existing artifact\
  \ graph. No new artifact types, no new link roles (D-18 respected), zero external\
  \ API calls."
tags:
- v1.13
- verification
- accounting-not-policing
- architecture
suspect: false
links:
- target: REQ-037
  role: derives_from
created: '2026-08-03'
fingerprint: sha256:5b95d52012fe
---

# Verification-contract recording + accounting evidence lenses

Refines REQ-037 (eliminate false-confidence signals). This ARCH describes how
v1.13 turns `verified` from an assertion into machine-checked evidence, and how
the audit surface reports evidence gaps without becoming a gate.

## Context

The v1.12 dogfood audit (DEC-058 lineage; the v1.12.6 RC1 cry-wolf kill) found
two false-confidence signals:

1. **Unverified `verified`.** The `verified` status was granted on the strength
   of a gate-delta narrative recorded in a STORY body — nothing recorded that a
   verification command actually ran, what it returned, or when. The status could
   be truthful or aspirational; a reader could not tell.
2. **Cry-wolf warnings.** Deterministic audit warnings that should have been
   advisory were escalating the gate's exit code, so genuine structural findings
   were drowned out and operators learned to ignore the gate.

Both reduce to the same root: signals that look like proof but are not, eroding
trust in the gate that the whole lifecycle depends on.

## Architecture

Two coupled mechanisms over the **existing** artifact graph (no new types, no
new link roles — D-18 frozen vocabulary respected):

### A. Verification contract (declaration + recorded run)

A V-model test (UT/IT/QT) or STORY may DECLARE a contract in frontmatter:

- `verify_command` — the shell command that proves the artifact works.
- `verify_exit_code` — expected pass code (default `0`).
- `verify_evidence` — human note on what the output proves.

`specflow verify <ID> | --all | --type T` EXECUTES `verify_command` and RECORDS
the run onto the same artifact:

- `verify_run_at` — ISO-8601 timestamp (absent ⇒ declared but never run).
- `verify_run_exit_code` — the actual exit code returned.
- `verify_run_evidence` — captured output / path to captured output
  (`--evidence-file` for long output).

The V-model `verified_by` link (UT/IT/QT → spec) remains the STRUCTURAL
verification proof. The contract adds MACHINE-CHECKABLE evidence on top; it does
not replace the link and is opt-in (no contract ⇒ no penalty, not "unverified").

### B. Accounting evidence lenses (read, never block)

`specflow project-audit` gains two lenses that READ the contract fields and
surface gaps as **warnings** (the same advisory tier as the existing
traceability/accounting debt):

- **Missing-evidence lens** — an implemented/verified UT/IT/QT/STORY that
  declares `verify_command` but has no `verify_run_at` (declared, never run).
- **Divergence lens** — `verify_run_exit_code` != declared `verify_exit_code`
  (ran, but the result diverged from the contract).

Both feed `specflow brief --next` as one deterministic advisory line and the
audit report as warnings. Neither drives the audit/gate exit code — only
structural findings do.

## Keystone invariant

**A failing `verify_command` is RECORDED, never blocking.** `specflow verify`
captures the real exit code truthfully and writes it; it never changes the
artifact status, never blocks a commit/transition/release, and never escalates
the audit to an error. This is accounting-not-policing applied to verification:
the engine never lies about what happened, and never overrides the human. The
human decides what a recorded failure means — fix the code, fix the command, or
accept the gap on record.

## Options considered

- **Blocking verify gate (reject `verified` transition on a failed run).**
  Rejected — violates accounting-not-policing and re-introduces the cry-wolf
  failure mode the v1.12.6 patch just killed. A flaky command would block real
  work; the cost of a false block exceeds the cost of a recorded-and-ignored
  failure.
- **Evidence recorder + advisory surface (CHOSEN).** Records truth, surfaces
  gaps as warnings, leaves the decision with the human. Composes with the
  existing gate (structural findings still block; evidence gaps advise).
- **External LLM judge of verification quality.** Rejected — SpecFlow makes zero
  external API calls and ships no LLM client; verification is the user's own
  deterministic shell command, executed and recorded locally.
- **New `VERIFIED-BY` link role / new artifact type.** Rejected — D-18 frozen
  vocabulary; the existing `verified_by` role already carries the structural
  proof. The contract is frontmatter on the existing test/story artifact.

## Responsibility

- `specflow verify` owns execution + recording (write `verify_run_*`).
- `specflow project-audit` (accounting lenses) + `specflow brief --next` own
  read-only surfacing (warning/advisory, never error/block).
- The `/specflow-execute` skill owns the lifecycle placement: run the contract
  before transitioning to `verified`, mirroring its existing `artifact-lint` step.
- `docs/cli-reference.md`, `docs/lifecycle.md` (mermaid + ASCII), and the README
  own the entry-point sync that keeps the surface discoverable.

## Verification

- `specflow verify` records `verify_run_at` + `verify_run_exit_code` (+ evidence)
  for a declared contract; `--dry-run` executes nothing.
- A failing run is recorded with its real exit code; the artifact status, the
  commit hook, and the audit exit code are all unchanged.
- The shipped `specflow-execute` skill (templates + live mirror) names the step
  and documents the contract fields; skill parity holds.
- `specflow brief --next` emits exactly one advisory line when a contract lacks
  matching run evidence, and is silent for projects with no contracts.
