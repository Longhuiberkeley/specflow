# Adoption Pack

Bring an **existing** codebase into SpecFlow — without pretending you're at day zero.

SpecFlow's core lifecycle is greenfield: `init → discover → plan → execute → ship`. That serves a project that starts with SpecFlow. But most real codebases are *brownfield* — they already have code, docs, tests, and history. The adoption pack is the guided path for those projects.

## What it does

`/specflow-adopt` records the **current state** of your project as SpecFlow artifacts, then hands off to the normal lifecycle for forward work:

1. **Frame** — asks what the project aims to do, the scope of this adoption pass, and the key decisions you want captured.
2. **Inventory + detect conflicts** — scans code, docs, tests, and commit history. When sources disagree (README vs code, doc vs test), it **asks you** which is authoritative rather than guessing.
3. **Backfill (D-20 model)** — creates **one ARCH per component** (with `output_files` as a package glob linking the code), plus REQ/DDD/DEC where they add value. **STORY is NOT backfilled** — it's reserved for forward action and appears only when someone changes adopted code. Each artifact is tagged `backfilled` with honest status (`implemented`/`verified` for code that exists) and provenance in `rationale`.
4. **As-built baseline** — `specflow baseline create adoption-v0 --evidence`. From here, drift is measured against this snapshot, not from zero.
5. **Retro-link & completeness check** — wires remaining orphan files to their backfilled ARCH; runs `specflow adopt status` to confirm coverage rose and to surface any artifacts whose completeness is in doubt.
6. **Hand off** — forward work uses `/specflow-discover` → plan → execute as normal. Any future change to an adopted component creates a real STORY `specified_by` that component's ARCH.

## Why a pack, not a core skill

Greenfield users (who started with `/specflow-init`) never need this. Only brownfield adopters install it. Keeping it out of the core keeps SpecFlow lean for the common case. Install with:

```
/specflow-init --preset adoption
```

## It scales

A single pass can't adopt a large codebase — context can't hold it, you can't review hundreds of artifacts at once, and the team won't freeze development while adoption runs. So adoption is **boundary-scoped, resumable, and skeleton-first**:

- **Skeleton-first** is the default huge-repo strategy: one ARCH per component (with a package glob) across the *whole* project gets every component under coverage with 15-30 artifacts, not 300. Then **deepen** (add REQ/DDD/tests) for the components `specflow adopt status` flags as high-churn, thin, or unverified.
- One subsystem per pass; `specflow adopt status` is the boundary dashboard; interim baselines are checkpoints. It interleaves with forward work — new features keep flowing through `/specflow-discover`, tagged apart from `backfilled` records. See `skills/specflow-adopt/references/incremental-adoption-protocol.md`.

## What it does NOT add

No new artifact types, no new directories, no new status values, no schema changes. Adoption reuses the core artifact model — it records reality, it doesn't extend the vocabulary.
