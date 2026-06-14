# Backfill Extraction Checklist

How to draft each artifact type from existing reality, plus the framing questions to ask the user up front. Mirror `/specflow-discover`'s readiness style: one question at a time, confirm before moving on.

## Framing questions (Phase 1 — ask these first)

Ask one at a time; let the user's answers shape the inventory:

1. **Purpose** — "In 2-3 sentences, what does this project (or this subsystem) do, and what's its primary goal?"
2. **Scope this pass** — "I see these candidate boundaries: `<list>`. Which one should we adopt this pass?" (For a small repo: "This is small enough to adopt whole — confirm?")
3. **Key decisions** — "What are the 2-5 decisions you most want captured as DEC/ARCH? (Framework choices, data model, auth model, deployment topology…)"
4. **Authoritative vs stale** — "Are there sources I should treat as authoritative, and any that are known-stale? (e.g. 'the README is out of date; trust the code')"
5. **Depth** — "For this boundary, do you want full V-model (REQ→ARCH→DDD + tests) or a leaner record (ARCH only)?" Default lean (skeleton) unless the subsystem is complex or actively changing. STORY is not part of the depth choice — adoption never creates STORYs (D-20).

Record the answers; they seed extraction so you're not blindly reverse-engineering.

## Per-type extraction prompts

### REQ (Requirement) — from requirements docs + README intent
- **Read:** `README.md`, `REQUIREMENTS*.md`, product docs in `docs/`, the project's stated goals from the framing conversation.
- **Draft:** what the system must do, as behavioral requirements with Given/When/Then acceptance criteria where you can infer them.
- **Status:** `approved` (matches shipped reality) or `verified` (if a QT confirms it).
- **Provenance:** `"Backfilled from README §Features + framing interview"`.

### ARCH (Architecture) — the PRIMARY code-linking home (D-20)
- **Read:** top-level directory layout (`git ls-files` grouped), public interfaces (API routers, exported package surfaces, schemas), deployment configs, module/workspace markers.
- **Draft:** component structure and the interfaces between them. **One ARCH per component** — the component is the unit of adoption, not the capability and not the file.
- **Code-link (the key field):** set `output_files` to a **package glob** covering the whole component, e.g. `src/main/java/com/acme/payments/**/*.java` or `src/auth/**/*`. One entry covers hundreds of files. This is how adopted code gets traced, coverage gets measured, and drift gets detected.
- **Status:** `implemented` (built) or `verified` (if an IT confirms it).
- **Provenance:** `"Backfilled from src/ structure + openapi.yaml"`.

**Generated code:** exclude from `output_files` globs. Generated files (protobuf `*.pb.go` / `*_pb2.py`, OpenAPI clients `openapi_client/`, `__generated__/` dirs, GraphQL codegen) inflate coverage and create noise in drift detection. Use more-specific globs that skip the generated directory (e.g. `src/auth/**/*.py` rather than `src/**/*` if `src/auth/generated/` exists). Record the generator as a DEC. If generated code is checked in and hand-edited (rare), include it — note this in `rationale`.

### DDD (Detailed Design) — only where genuinely complex
- **Read:** the internals of a component that's non-trivial (algorithms, state machines, data flows).
- **Draft:** only for components where the detail aids future change. **Skip DDD for simple CRUD wrappers, config loaders, etc.** — don't over-document.
- **Code-link:** `output_files` is the specific subset of files this DDD details (finer-grained than the parent ARCH's glob).
- **Status:** `implemented`/`verified`.

### STORY — NOT backfilled (reserved for forward action, D-20)
- **Do not create STORYs during adoption.** STORY records the *action side* — the doing — and in adoption the action already happened years ago. A backfilled `status: verified` STORY for shipped code is a zombie action-artifact.
- STORY appears only when **forward work** changes adopted code: a real (non-`backfilled`) STORY, `specified_by` the existing ARCH, `output_files` = the specific files the change touched (a subset of the ARCH's glob).
- If you catch yourself writing "STORY: implement X" for code that already exists → that's an ARCH. Re-Author it.

### DEC (Decision) — from ADRs, commits, and obvious choices
- **Read:** any `adr/` or `docs/decisions/` dir; `git log` for "why" commits; framework/dependency choices in manifests (`package.json`, `pyproject.toml`, `go.mod`).
- **Draft:** the consequential decisions (framework X over Y, sync vs async, monolith vs services). If there's an existing ADR, lift it nearly verbatim.
- **Status:** `approved`.
- **Provenance:** `"Backfilled from docs/adr/0007-why-postgres.md"` or `"Inferred from pyproject.toml + framing interview"`.

### UT / IT / QT (Tests) — from existing tests where they map
- **Read:** existing test files; map each to the spec level it actually verifies (UT→DDD/unit, IT→ARCH/integration, QT→REQ/acceptance).
- **Draft:** backfill a test artifact only where an existing test maps cleanly to a backfilled spec. Link `derives_from` the spec and set the spec `verified` if the test confirms it.
- **Status:** `verified` (the test exists and presumably passes) — but flag in `rationale` if you couldn't run it.
- **Don't fabricate** test artifacts for tests that don't exist.

## General rules

- **The component is the unit.** One ARCH per component, `output_files` = component glob. Don't go file-by-file (ceremony) and don't go capability-by-capability (zombie STORYs).
- **Summarize, don't copy.** Capture the normative behavior in 1-3 sentences + criteria, not verbatim source dumps. Provenance links back to the file.
- **Reuse, don't retype.** An existing ADR is already a DEC. An existing requirements doc is already REQ material. Lift and adapt, don't paraphrase from scratch.
- **Link as you go.** ARCH `derives_from` REQ; DDD `derives_from` ARCH; tests `verified_by` the spec they verify. The graph is the point.
- **Flag uncertainty in `rationale`.** If you inferred something the user didn't confirm, say so: `"Inferred from code; not confirmed in framing"` — `specflow adopt status` surfaces these as "inference debt," and consider surfacing it as a conflict to verify.
