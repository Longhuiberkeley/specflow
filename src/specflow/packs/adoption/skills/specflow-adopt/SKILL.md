---
name: specflow-adopt
description: >
  Use when bringing an EXISTING codebase into SpecFlow (brownfield adoption) —
  inventory current code/docs/tests, backfill REQ/ARCH/DDD/DEC describing what
  already exists (code is linked to ARCH/DDD via output_files globs), cut an
  as-built baseline, and steer deepening with `specflow adopt status`. STORY is
  NOT backfilled — it is reserved for forward action. Incremental and resumable
  for large codebases. NOT for greenfield projects (use /specflow-discover).
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (framing conversation → scoped inventory → backfill → baseline)
- **A named scope** ("/specflow-adopt the payments service") → adopt that one boundary this pass
- **"resume" / "continue"** → pick up a prior adoption pass (see Resume, below)
- **A question** ("how much is left to adopt?", "is REQ-007 complete?") → run `specflow adopt status` (project view) or `specflow adopt status <ID>` (artifact view) and report

Start with the framing conversation unless this is a resume (see Resume below).

---

# SpecFlow Adopt

Bring an existing codebase into SpecFlow by **recording its current state**, then handing off to the normal lifecycle for forward work. This is *adoption*, not migration — nothing leaves; you capture what exists and govern change from there.

**Core idea:** inventory → backfill ARCH/DDD/REQ/DEC describing existing reality, **link code to ARCH/DDD via `output_files` globs** (one ARCH per component covers a whole package) → cut an as-built baseline → steer deepening with `specflow adopt status` → forward work uses `/specflow-discover` → plan → execute as normal.

## Two rules that govern the whole skill

1. **Be conversational, not a mechanical extractor.** Mirror `/specflow-discover`'s readiness style: ask one question at a time about what the project aims to do, the scope of *this pass*, the key decisions to capture, and which sources are authoritative vs stale. Seed the extraction with intent so you aren't blindly reverse-engineering. See `references/backfill-extraction-checklist.md` for the framing questions.

2. **Never silently resolve conflicting information (most important).** When sources disagree — README vs code, doc vs test, comment vs implementation, two docs contradicting — **pause, surface the specific conflict** (quote both sides with `file:line`), and ask the user which is authoritative or how to reconcile. Record the resolution in the artifact's `--rationale`. Adoption records reality, but *which* reality is authoritative is a human call. See `references/conflict-resolution-protocol.md`.

## The code-linking model (D-20) — read this before Phase 3

- **REQ** = behavior (what the system must do). No code refs.
- **ARCH** = component. **Owns `output_files` — typically a package glob** (e.g. `src/main/java/com/acme/payments/**/*.java`). One ARCH per component covers hundreds of files in one entry.
- **DDD** = internals. Owns a finer-grained `output_files` list for the specific files it details.
- **STORY is reserved for forward action.** Adoption creates **zero** STORYs. The action already happened; STORY records the *doing*, and there is nothing to do. A STORY appears only when forward work changes adopted code, `specified_by` the existing ARCH.
- The orphan meter credits `output_files` on STORY/REQ/ARCH/DDD, so lean (ARCH-only) adoption still moves the coverage meter. Globs expand everywhere.

## Prerequisites / redirect

- If SpecFlow is not initialized → run `/specflow-init --preset adoption` first (or `/specflow-init` then `/specflow-init --preset adoption`).
- If the repo is empty or genuinely greenfield (no existing code to record) → tell the user to use `/specflow-discover` instead; there's nothing to adopt.

## Phases (run scoped to one boundary per pass)

- **0 · Precheck.** Confirm SpecFlow is initialized. Run `specflow brief` — if the Adoption section appears (backfilled artifacts exist), this is a **resume**: skip to Resume below.

- **1 · Framing conversation.** Ask, one question at a time:
  - What does this project (or this subsystem) aim to do? Its goals?
  - **What is this pass's scope?** For large codebases: ONE boundary (subsystem / module / package). For small repos: the whole repo. Propose boundary candidates (see Inventory).
  - Which key decisions do you most want captured as DEC/ARCH?
  - Which sources are authoritative, which are known-stale (an outdated README, a deprecated design doc)?
  Present the proposed backfill plan for this boundary and confirm before scanning further.

- **2 · Inventory + conflict detection.** Gather signals, scoped to the chosen boundary, surfacing conflicts to the user as they appear:
  - `git ls-files` grouped by top-level dir (and module markers: npm/pnpm workspaces, `go.mod`, `Cargo.toml` workspaces, monorepo packages) → candidate boundaries / component structure.
  - `specflow detect orphan-code` → source files not yet referenced by any STORY/REQ/ARCH/DDD, with coverage %. *(Pre-backfill, everything is "orphan" — use this as the post-pass gap check and the progress meter; use `git ls-files` for the initial map.)*
  - Existing docs: `README.md`, `docs/**/*.md`, any `adr/` or `decisions/` dir, `REQUIREMENTS*.md`, `CONTRIBUTING.md` → candidate REQ/DEC source.
  - Existing tests (`**/test_*.py`, `*.test.ts`, `*_test.go`, …) → evidence for `verified` + candidate UT/IT/QT. A common conflict source when tests disagree with docs.
  - Commit ticket refs: `git log --oneline | grep -oE '[A-Z][A-Z0-9]+-[0-9]+'` → candidate DEF/DEC + provenance.
  Present a structured inventory summary and the proposed artifacts to backfill for this boundary.

- **3 · Backfill (drive `specflow create`).** Create core artifacts describing *existing* reality. **The component is the unit — one ARCH per component, `output_files` = component glob.**
  - **ARCH per component** (primary code-link): `--set output_files='["src/<component>/**/*.java"]'`. Status `implemented` (or `verified` if a test confirms it). This is the custody record for the component's code.
  - **DDD only where genuinely complex** — algorithms, state machines, data flows. Skip DDD for simple CRUD/config. A DDD's `output_files` is the specific subset of files it details.
  - **REQ** for behavioral requirements (from README / product docs / framing), with Given/When/Then acceptance criteria where inferable. Link the realizing ARCH with `derives_from`.
  - **DEC** from existing ADRs / `git log` "why" commits / framework choices in manifests.
  - **UT/IT/QT only where an existing test maps cleanly** to a backfilled spec — link `verified_by`. Don't fabricate.
  - Tag every backfilled artifact: `--tags backfilled`.
  - Record provenance in `--rationale` (e.g. `"Backfilled from src/auth/ at adoption-v0"`; or `"README vs code conflict — user confirmed code authoritative"`).
  - **Set status honestly** — `create` accepts any valid status directly: `implemented` for code that exists, `verified` where a test confirms it, `approved` for specs that match shipped reality. This is accounting, not policing.
  - **Do NOT create STORYs.** STORY is forward action (D-20). If you catch yourself creating a STORY for existing code, stop — that's an ARCH.

- **4 · As-built baseline.** `specflow baseline create adoption-v0 --evidence` (or `adoption-<boundary>-v0` for an interim checkpoint in a multi-pass adoption). State plainly: this is the handshake — from here, drift is measured against this snapshot.

- **5 · Retro-link & completeness check.**
  - `specflow detect orphan-code --retro-link ARCH-NNN` to wire any remaining unreferenced files (in this boundary) to their backfilled ARCH. (Accepts STORY/ARCH/DDD/REQ; ARCH is the usual target.)
  - `specflow adopt status` — the project/boundary dashboard. Confirm coverage rose this pass and note the biggest remaining cluster.
  - `specflow adopt status <REQ-NNN|ARCH-NNN>` for any artifact whose completeness is in doubt — it surfaces realization, acceptance-criteria count, linked tests, provenance, depth (skeleton/full), gaps, and post-adoption drift.

- **6 · Validate & handoff.**
  - `specflow artifact-lint` on the backfilled graph; optionally `/specflow-audit`.
  - Close resolved AUDs: after an audit, run `specflow update AUD-NNN --status closed` for any AUD whose findings are provably resolved. Don't leave resolved audits as `status: open` — they accumulate and lose signal.
  - Report from `specflow adopt status`: coverage %, what was adopted this pass, the biggest un-adopted cluster (what's left). Recommend the next boundary, or declare adoption "done enough."
  - Tell the user: forward work uses `/specflow-discover` → plan → execute; the as-built baseline is the reference for `/specflow-change-impact-review` and `/specflow-ship`. Any future change to an adopted component creates a real (non-`backfilled`) STORY `specified_by` that component's ARCH.

## Scaling to large codebases — skeleton-first, incremental, resumable

A single pass can't adopt a big repo. Adoption is **scope-bounded, resumable, and interleaves with forward work**, and the default huge-codebase strategy is **skeleton-first**:

1. **Skeleton sweep.** First pass across the whole project: **one ARCH per component**, `output_files` = component glob, status `implemented`. No REQ, no DDD, no STORY. Goal: get every component under an ARCH so coverage rises fast with maybe 15-30 artifacts, not 300.
2. **Steer deepening with `specflow adopt status`.** The completeness view flags which components deserve REQ (behavior) + DDD (internals): the ones with high churn, thin specs, missing tests, or drift. Deepen those; leave frozen legacy at skeleton. **`adopt status` is the prioritization signal for "where do I deepen next."**
3. **One boundary per pass** for the deepening work. The framing conversation proposes boundaries; the user picks this pass's scope.

Other essentials (full protocol in `references/incremental-adoption-protocol.md`):
- **Resumable & idempotent.** Resume via `specflow brief` (now shows the Adoption section) + `specflow adopt status`; skip anything already `tags: [backfilled]` and continue. Nothing is redone.
- **Progress meter = coverage %.** `specflow adopt status` and `specflow detect orphan-code` both report coverage %; it trends toward 100% (or toward a residual of genuinely-unspec'd frozen code, which is fine).
- **Concurrent with forward work.** New features flow through `/specflow-discover` → plan → execute (not `backfilled`); adoption passes keep digesting legacy surface area. The `backfilled` tag separates recorded-past from governed-forward.
- **Cross-boundary synthesis.** Passes may overlap on cross-cutting concerns (e.g. "auth" spans modules). Dedup/merge overlapping REQs/ARCHs; where two passes produced conflicting specs, surface it via the conflict protocol.
- **Optional parallel fan-out.** If the host supports multi-agent orchestration, each boundary's backfill can run as a parallel agent (one per module) + a synthesis pass. This is the accelerator for big repos — but the **sequential core works at any scale**; the fan-out is never required and the pack stays host-agnostic.

### Resume (mid-adoption, new session)

1. `specflow brief` — the Adoption section reconstructs adoption state in one call (coverage %, backfilled counts, biggest cluster).
2. Check for `needs-decision` tags — if any artifacts are tagged `needs-decision`, resolve their unresolved conflicts first (see `references/conflict-resolution-protocol.md`).
3. `specflow adopt status` — the boundary dashboard; pick the next boundary from the biggest un-adopted cluster.
4. Read the latest `adoption-*` baseline — see what's already recorded and snapshotted.
5. Skip anything already `tags: [backfilled]`; continue at Phase 1.

## Deterministic core (zero-token, always available)

Everything this skill does is composed from CLI commands — no new Python per pass:

| Step | Command |
|------|---------|
| Load state | `specflow brief` |
| Coverage / progress | `specflow adopt status` |
| Artifact completeness | `specflow adopt status <ID>` |
| Orphan scan | `specflow detect orphan-code` |
| Backfill ARCH (code-link) | `specflow create --type architecture --title "Payments" --status implemented --tags backfilled --rationale "…" --set 'output_files=["src/payments/**/*.py"]' --links '[{"target":"REQ-007","role":"derives_from"}]'` |
| Backfill REQ/DDD/DEC | `specflow create --type <requirement\|detailed-design\|decision> --title "…" --status <approved\|implemented\|verified> --tags backfilled --rationale "…" --links '[…]'` |
| Snapshot | `specflow baseline create adoption-v0 --evidence` |
| Retro-link files | `specflow detect orphan-code --retro-link ARCH-NNN` |
| Validate | `specflow artifact-lint` |

## References

- `references/as-built-baseline-protocol.md` — the mental model + status/tagging conventions + the code-linking model (D-20).
- `references/backfill-extraction-checklist.md` — per-type extraction prompts (REQ/ARCH/DDD/DEC/UT/IT/QT) **plus the framing questions**.
- `references/conflict-resolution-protocol.md` — common conflict patterns and how to surface each to the user with `file:line` evidence.
- `references/incremental-adoption-protocol.md` — boundary discovery, skeleton-first strategy, the resume flow, and using coverage % as the progress meter.
