# Incremental Adoption Protocol

A single pass can't adopt a large codebase: context can't hold it, the user can't review hundreds of artifacts at once, and the team won't freeze development while adoption runs. Adoption is **boundary-scoped, resumable, and interleaves with forward work**.

## Skeleton-first — the default strategy for large repos

Don't go boundary-by-boundary at full V-model depth from the start. For a large repo, **skeleton-first** gets the whole project under coverage fast, then deepens where it matters:

1. **Skeleton sweep (first passes).** One ARCH per component across the *whole* project, `output_files` = component glob, status `implemented`. No REQ, no DDD, no STORY. Goal: every component under an ARCH — coverage rises fast with maybe 15-30 artifacts, not 300. Cut an interim `adoption-<boundary>-v0` baseline per pass if useful.

2. **Steer deepening with `specflow adopt status`.** The completeness view flags which components deserve REQ (behavior) + DDD (internals):
   - high churn (files changed since the as-built baseline = drift),
   - thin specs (REQ with 0 acceptance criteria),
   - missing tests (no linked UT/IT/QT),
   - "inference debt" (rationale says "inferred / not confirmed").
   Deepen those; leave frozen, rarely-touched legacy at skeleton. **`adopt status` is the prioritization signal for "where do I deepen next."**

3. **One boundary per deepening pass.** The framing conversation proposes the next boundary (from `adopt status`'s biggest-cluster hint or the user's priorities); phases run scoped to it.

The skeleton-first ordering matters: a full-V-model pass on the wrong boundary wastes effort on frozen code. Skeleton cheaply, then deepen where the heat is.

## Boundary discovery (Phase 1)

Propose boundaries, then let the user pick this pass's scope. Sources of boundary candidates:

- **Top-level directories** — `git ls-files | awk -F/ '{print $1}' | sort -u` gives the coarse shape. Each major top-level package is a candidate.
- **Workspace / module markers** — these are usually the *right* boundary, because they're how the code is already organized:
  - JS/TS: `package.json` `workspaces`, pnpm `packages/`
  - Go: `go.mod` modules
  - Rust: `Cargo.toml` `[workspace]` members
  - Python: `src/<package>/` top-level packages, or monorepo `pants`/`nx` project specs
  - Java/Kotlin: Gradle subprojects / Maven modules
- **Import-graph communities** — for a tangled repo, cluster files by import relationships; a community with strong internal coupling and weak external coupling is a natural boundary.
- **Deployment units** — services in a monorepo (`services/auth/`, `services/payments/`) are clean boundaries.

Recommend a boundary that's **cohesive and not too large** — adoptable in one sitting, producing a reviewable set of artifacts (rough target: a handful to low-double-digits of artifacts per pass). If a boundary is huge, split it.

For a **small repo** (one or two top-level packages), the boundary is the whole repo — adopt it in a single pass.

## One pass = one boundary

Each `/specflow-adopt` invocation runs Phases 1–6 scoped to the chosen boundary. Don't try to adopt two boundaries in one pass — context and reviewability suffer. Finish one, baseline it (optional interim), then start the next.

## Resume (new session, mid-adoption)

Adoption routinely spans sessions. To resume:

1. **`specflow brief`** — the Adoption section reconstructs adoption state in one call (coverage %, backfilled counts by type, biggest un-adopted cluster).
2. **`specflow adopt status`** — the boundary dashboard. Each ARCH is a row with its file count, depth (skeleton/full), drift flag, and parent REQ. Pick the next boundary from the biggest-cluster hint.
3. **Read the latest `adoption-*` baseline** — what's already been recorded and snapshotted.
4. **Skip anything already `tags: [backfilled]`** — idempotent. Don't redo a boundary that's already adopted (unless the user asks to refresh it because the code changed).
5. **Propose the next boundary** from what `adopt status` still flags as skeleton/empty, confirm with the user, and continue at Phase 1.

Nothing is redone. The `backfilled` tag + the baseline + `adopt status` together make adoption safely interruptible.

## Progress meter = coverage %

`specflow adopt status` and `specflow detect orphan-code` both report **coverage %** (files under any STORY/REQ/ARCH/DDD ÷ total source files). As adoption proceeds, coverage trends toward 100% — or toward a residual of genuinely-unspec'd frozen code, which is fine (see "done enough" in `as-built-baseline-protocol.md`).

Report it to the user every pass: "Coverage: 62% → 71% after this pass. Next biggest un-adopted cluster: `src/legacy_importer/` (312 files)."

Because the meter credits ARCH `output_files` globs, a skeleton sweep (ARCH-only) moves the meter even without REQ/DDD — that's what makes skeleton-first viable as a coverage strategy.

## Interleaving with forward work

Adoption does not freeze the codebase. While you're adopting boundary B, the team may ship a feature in boundary A. That's fine and expected:

- **Forward work** (new features, bug fixes) flows through `/specflow-discover` → plan → execute as normal. Those artifacts are NOT tagged `backfilled` — they're governed-forward.
- **Adoption passes** keep digesting legacy surface area, tagged `backfilled`.
- The `backfilled` tag cleanly separates recorded-past from governed-forward. An audit can tell them apart; the moment forward work touches an adopted component, a real (non-`backfilled`) STORY is created `specified_by` its ARCH — that's the "graduation" into forward-governed work.

If a forward feature touches code that hasn't been adopted yet, that's a signal to adopt that boundary next (or adopt just the touched files) so the change has specs to trace against.

## Cross-boundary synthesis

Boundaries aren't perfectly independent — cross-cutting concerns (auth, logging, data models) span modules. After a few passes:

- **Dedup.** Two passes may have produced overlapping REQs/ARCHs for the same cross-cutting concern.
- **Conflict.** If two passes produced *conflicting* specs for the same concern (e.g. the auth pass says tokens expire in 1h, the API pass says 24h), surface it via the conflict-resolution protocol — don't silently keep both.

### Merge recipe (when two artifacts cover the same concern)

1. **Pick the survivor.** The artifact with more files / greater coverage wins. If both are equal, keep the first-created (lower ID number).
2. **Copy unique content.** Move any unique body text, acceptance criteria, or rationale from the losing artifact into the survivor.
3. **Expand output_files.** Add the losing artifact's globs/paths to the survivor's `output_files` list.
4. **Re-link.** Find all artifacts that link to the losing artifact (via `specflow trace <losing-ID>`) and repoint them to the survivor: `specflow update <linked-ID> --links '[{"target":"<survivor-ID>","role":"derives_from"}]'`.
5. **Delete or archive** the losing artifact. Move it to a `_specflow/archive/` dir or delete it.
6. **Lint.** `specflow artifact-lint` to catch broken links or orphaned references.

### ID collisions (parallel fan-out)

If parallel agents independently create artifacts with the same ID (e.g. both create `ARCH-001` for different components), the synthesis pass must renumber one before merging. Use `specflow renumber <old-ID> <new-ID>` to update all cross-references. To prevent collisions in the first place, assign non-overlapping ID ranges to each parallel agent (e.g. agent A uses ARCH-001–ARCH-050, agent B uses ARCH-051–ARCH-100).

A periodic `/specflow-audit` across the whole backfilled graph catches cross-boundary seams.

## Optional: parallel fan-out

For hosts that support multi-agent orchestration (e.g. a `/workflows`-style fan-out), each boundary's backfill can run as a separate parallel agent — one agent per module — followed by a synthesis pass that merges and resolves cross-boundary conflicts. This accelerates adoption of very large repos.

**Caveats:** the fan-out is an *accelerator*, never a requirement — the sequential single-pass core works at any scale, just slower. And each parallel agent must still follow the conflict-resolution protocol (surface, don't guess) and the framing conversation for its boundary. The pack stays host-agnostic: nothing in the skill depends on a specific orchestration tool.
