# As-Built Baseline Protocol

The as-built baseline is the single new concept adoption introduces. Everything else reuses the core artifact model.

## The code-linking model (D-20)

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

SpecFlow is accounting, not policing. When you backfill an artifact for code that already exists, set the status that **reflects reality** — `create` accepts any valid status directly (no transition prerequisite on create):

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

No new status, no new artifact type, no schema change. The frozen vocabulary (D-18) is respected — adoption reuses `derives_from`, `implements`, `guided_by`, `specified_by`, `verified_by`, `addresses`.

## When to cut a baseline

- **`adoption-v0`** — the headline as-built baseline, cut when the user declares adoption "done enough" to start governing forward change against it. One per project.
- **`adoption-<boundary>-v0`** — optional interim checkpoints after each major boundary pass in a large multi-pass adoption (e.g. `adoption-auth-v0`, `adoption-payments-v0`). Immutable evidence trail; useful for rollback if a later pass goes sideways.

Baselines are immutable; the **orphan-code count** is the live progress signal between them (see `incremental-adoption-protocol.md`).

## What "done enough" means

Adoption never has to reach 100% of the codebase before forward work resumes. A pragmatic stopping point: every actively-changing subsystem is backfilled and baselined; legacy code that's frozen and rarely touched can stay `backfilled`-lite or even remain orphan (the orphan-code count flags it). The team decides the threshold — adoption is accounting, and you account for what matters.
