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

A greenfield SpecFlow project measures drift from "nothing" — the first baseline is the first release. A brownfield project can't do that: it has months or years of existing reality. So adoption cuts an **as-built baseline** — `specflow baseline create v0.0.0-adoption.1 --evidence` — that snapshots the backfilled artifacts (status, title, type, body fingerprint) representing the project's current state. Immediately after, `specflow fingerprint-refresh --source` seeds the source-file hashes. From that point on:

- `specflow baseline diff` and `/specflow-ship` compare later baselines against the adoption snapshot, not against zero.
- `specflow adopt status` reports source drift as files changed since the `fingerprint-refresh --source` seed; it reads no baseline.
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

Decisions (DEC) take only `approved` or `draft` — the decision schema has no `implemented`/`verified`, so a backfilled DEC records "this is what we decided" with `--status approved`.

Do not force backfilled artifacts through `draft → approved → implemented`. That's the forward lifecycle; adoption records the endpoint.

## Provenance: tags + rationale, no new fields

- **`tags: [backfilled]`** — the machine-readable marker that this artifact was recorded after the fact, not authored forward. Lets `specflow adopt status` and audits say "N artifacts are backfilled."
- **`rationale`** — the human-readable provenance. Always set it: where this came from and (if relevant) how a conflict was resolved. `specflow adopt status` parses provenance signals (conflict-resolved, inferred/unconfirmed) out of this field.
  - `"Backfilled from src/auth/ at v0.0.0-adoption.1"`
  - `"Backfilled from docs/adr/0003-token-format.md; README↔code conflict resolved: code authoritative (user, 2026-06-14)"`

No new status, no new artifact type, no schema change. The frozen link-role vocabulary is respected — adoption reuses `derives_from`, `implements`, `guided_by`, `specified_by`, `verified_by`, `addresses`.

## Lint expectations for a skeleton

`specflow artifact-lint` is forward-lifecycle aware, so an as-built record legitimately warns until deepened. None of these is blocking, but most are **escalating**: while the project has no findings baseline (`.specflow/findings-baseline.yaml`) they only print (until the ratchet's v1.18.0 sunset); once one exists, a full `specflow artifact-lint` exits 1 on any escalating warning not yet recorded in it, which fails Phase 6 and the pre-commit/CI gate.

| Warning (rule) | Class | Why it fires | Clears when |
|----------------|-------|--------------|-------------|
| `missing verification pair` (`links/missing-v-pair`) | escalating at `implemented`/`verified` — the status backfill sets; accounting before that | an ARCH has no IT `verified_by` it | an existing test is mapped (Phase 3 worked example) |
| `body has N words` / `missing structural headers` (`spec-body/word-count`, `spec-body/headers`) | escalating | ARCH body under ~50 words or no `## Component`-style header | the body summarizes the component under a header |
| `never challenged` (`thinking-techniques/unchallenged`) | escalating | no `thinking_techniques` on an implemented/approved spec | `/specflow-artifact-review` runs a lens and you record it via `update --thinking-techniques` |
| `backfilled artifact has no links` (`backfilled-links/unlinked`), `orphan(s) with no links` (`links/orphan`) | escalating (`links/orphan` on a REQ is accounting before the planning phase) | nothing links to or from it | a verifying test, parent REQ, or DEC is linked |
| `no STORY implements this approved requirement` (`coverage/no-story`) | escalating from the planning phase on; accounting while idle/discovering | a backfilled REQ has no STORY, by design | forward work touches it (adoption never creates STORYs) |

Do not fake a technique or a STORY to silence these. After the user reviews an adoption pass, record the remaining skeleton debt as known with `specflow findings-baseline update --accept-new`. It is approval-gated: present it and name the impact (lint stops failing on these keys; each later fix drops its key, and the ratchet only tightens). With no findings baseline yet, `specflow findings-baseline update` seeds one from every current escalating warning.

## When to cut a baseline

Baseline names MUST be semver-shaped (`baseline create` rejects anything else), so every adoption cut is `v0.0.0-adoption.<n>`, with `<n>` = 1, 2, … in cut order:

- **Interim checkpoints** — optional cuts after each major boundary pass in a large multi-pass adoption (e.g. `v0.0.0-adoption.1` after auth, `v0.0.0-adoption.2` after payments). Immutable evidence trail; useful for rollback if a later pass goes sideways.
- **The headline** — the highest `<n>`, cut when the user declares adoption "done enough" to start governing forward change against it.
- **Legacy name** — a repo that already has `adoption-v0` keeps it (baselines are write-once and nothing looks one up by name) and anchors audits with `specflow project-audit --baseline adoption-v0`.

After each cut, run `specflow fingerprint-refresh --source` so artifacts backfilled since the last seed are tracked for drift. Baselines are immutable; the **orphan-code count** is the live progress signal between them (see `incremental-adoption-protocol.md`).

## What "done enough" means

Adoption never has to reach 100% of the codebase before forward work resumes. A pragmatic stopping point: every actively-changing subsystem is backfilled and baselined; legacy code that's frozen and rarely touched can stay `backfilled`-lite or even remain orphan (the orphan-code count flags it). The team decides the threshold — adoption is accounting, and you account for what matters.

## Docs surface at adoption

Pre-existing `docs/` (and root markdown — README, AGENTS, etc.) is a **recognized knowledge surface**, not code and not artifacts. Adoption acknowledges it so a mid-project start doesn't leave docs as a blind spot of outdated info:

- **Recognized, not registered or converted.** SpecFlow discovers the docs surface from the config `docs:` block (default `docs/` plus root markdown); configure that block through `/specflow-doc` if the docs live elsewhere. A baseline records artifacts only, so there is nothing to note in it. Docs get no `_index.yaml` lifecycle entry, no status, no `output_files`. They are prose; git history is their change log.
- **Fingerprints for drift.** `specflow rebuild-index` writes the derived `_specflow/docs-index.yaml`, which fingerprints each doc (same `compute_fingerprint` primitive artifacts use). No command compares those fingerprints over time: commit the cache at adoption, and a later `git diff` of it after `rebuild-index` shows doc drift — purely informational.
- **Citations stay honest.** If a doc cites an artifact via an `@ID` marker (e.g. `@ARCH-007`) and that artifact is later superseded/cancelled, `specflow detect stale-docs` and `/specflow-audit` warn (never block). See the `/specflow-doc` skill.

This mirrors the code-linking model's philosophy: record reality at the baseline, then govern drift from there. Docs are accounted for, not policed.
