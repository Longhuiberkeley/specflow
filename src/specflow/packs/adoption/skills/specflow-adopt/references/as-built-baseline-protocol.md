# As-Built Baseline Protocol

The as-built baseline is the single new concept adoption introduces. Everything else reuses the core artifact model.

## The code-linking model (DEC-057)

Adoption links existing code to specs via **ARCH and DDD `output_files`**, not STORY. STORY is reserved for forward action (the *doing*); adoption records the *system side* (what exists), and code realizes an architecture.

- **ARCH** = component. `output_files` is a **package glob** (`src/payments/**/*.py`) covering the whole component — one entry, hundreds of files.
- **DDD** = internals. `output_files` is the specific subset of files it details.
- **STORY** is NOT created during adoption. It appears only when forward work changes adopted code, `specified_by` the ARCH.
- **Globs expand everywhere** — the orphan meter, source-drift check, and reconcile all expand `**` patterns, so one ARCH glob covers a whole package in every view.
- The orphan meter credits `output_files` on STORY/REQ/ARCH/DDD, so lean (ARCH-only) adoption still moves the coverage meter.

## The mental model

A greenfield SpecFlow project measures drift from "nothing" — the first baseline is the first release. A brownfield project can't do that: it has months or years of existing reality. So adoption cuts an **as-built baseline** — `specflow baseline create adoption-v0 --evidence` — that snapshots the backfilled artifacts representing the project's current state. From that point on:

- `/specflow-ship` baselines measure drift **from adoption**, not from zero.
- `/specflow-audit` assesses a graph that includes the recorded past.
- `/specflow-change-impact-review` finds changes *after* adoption and traces their blast radius against the backfilled specs.

Adoption is a **handshake into the normal lifecycle**, not a parallel track.

## Status: be honest, not ceremonial

SpecFlow is accounting, not policing. When you backfill an artifact for code that already exists, set the status that **reflects reality**. `create` reaches past `draft` only with `--sanctioned "as-built: <why>"` (the creation-status gate records it as `sanctioned_justification`); there is no transition prerequisite:

| Reality | Status |
|--------|--------|
| Code exists and ships, no test yet | `implemented` |
| Code exists and a test confirms it | `verified` |
| Spec matches shipped behavior, reviewed | `approved` |
| Genuinely still in flux / aspirational | `draft` (rare in adoption — you're recording what *is*) |

Do not force backfilled artifacts through `draft → approved → implemented`. That's the forward lifecycle; adoption records the endpoint.

## Provenance: tags + rationale, no new fields

- **`tags: [backfilled]`** — the machine-readable marker that this artifact was recorded after the fact, not authored forward. Lets `specflow adopt status` and audits say "N artifacts are backfilled."
- **`rationale`** — the human-readable provenance. Always set it: where this came from and (if relevant) how a conflict was resolved. `specflow adopt status` parses provenance signals (conflict-resolved, inferred/unconfirmed) out of this field.
  - `"Backfilled from src/auth/ at adoption-v0"`
  - `"Backfilled from docs/adr/0003-token-format.md; README↔code conflict resolved: code authoritative (user, 2026-06-14)"`

No new status, no new artifact type, no schema change. The frozen link-role vocabulary is respected — adoption reuses `derives_from`, `implements`, `guided_by`, `specified_by`, `verified_by`, `addresses`.

## Lint expectations for a skeleton

`specflow artifact-lint` is forward-lifecycle aware, so an as-built record legitimately warns until deepened. All are accounting warnings, none block:

| Warning | Why it fires | Clears when |
|---------|--------------|-------------|
| `missing verification pair` | an ARCH has no IT `verified_by` it | an existing test is mapped (Phase 3 worked example) |
| `body has N words` / `missing structural headers` | ARCH body under ~50 words or no `## Component`-style header | the body summarizes the component under a header |
| `never challenged` | no `thinking_techniques` on an implemented/approved spec | `/specflow-artifact-review` runs a lens and you record it via `update --thinking-techniques` |
| `backfilled artifact has no links` | nothing links to or from it | a verifying test, parent REQ, or DEC is linked |
| `no STORY implements this approved requirement` | a backfilled REQ has no STORY, by design | forward work touches it (adoption never creates STORYs) |

Do not fake a technique or a STORY to silence these.

## When to cut a baseline

- **`adoption-v0`** — the headline as-built baseline, cut when the user declares adoption "done enough" to start governing forward change against it. One per project.
- **`adoption-<boundary>-v0`** — optional interim checkpoints after each major boundary pass in a large multi-pass adoption (e.g. `adoption-auth-v0`, `adoption-payments-v0`). Immutable evidence trail; useful for rollback if a later pass goes sideways.

Baselines are immutable; the **orphan-code count** is the live progress signal between them (see `incremental-adoption-protocol.md`).

## What "done enough" means

Adoption never has to reach 100% of the codebase before forward work resumes. A pragmatic stopping point: every actively-changing subsystem is backfilled and baselined; legacy code that's frozen and rarely touched can stay `backfilled`-lite or even remain orphan (the orphan-code count flags it). The team decides the threshold — adoption is accounting, and you account for what matters.

## Docs surface at adoption-v0

Pre-existing `docs/` (and root markdown — README, AGENTS, etc.) is a **recognized knowledge surface**, not code and not artifacts. Adoption acknowledges it so a mid-project start doesn't leave docs as a blind spot of outdated info:

- **Register, don't convert.** Note the docs root + a few notable docs in the baseline `--rationale`. Docs get no `_index.yaml` lifecycle entry, no status, no `output_files`. They are prose; git history is their change log.
- **Fingerprint for drift.** The derived `_specflow/docs-index.yaml` fingerprints each doc (same `compute_fingerprint` primitive artifacts use), so post-adoption doc drift is measurable — purely informational.
- **Citations stay honest.** If a doc cites an artifact via an `@ID` marker (e.g. `@ARCH-007`) and that artifact is later superseded/cancelled, `specflow detect stale-docs` and `/specflow-audit` warn (never block). See the `/specflow-doc` skill.

This mirrors the code-linking model's philosophy: record reality at the baseline, then govern drift from there. Docs are accounted for, not policed.
