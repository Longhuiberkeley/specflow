---
id: STORY-035
title: "Project convention checklists \u2014 scaffold and enforce project structure"
type: story
status: draft
priority: medium
tags:
- UX
- conventions
- checklists
suspect: false
links:
- target: STORY-033
  role: depends_on
created: '2026-04-17'
fingerprint: sha256:5d458c39e8b8
version: 1
---

# Project convention checklists — scaffold and enforce project structure

## Description

SpecFlow validates its own artifacts (REQ, ARCH, STORY, etc.) but does nothing to help users keep their **actual project codebase** well-organized. When a user runs `specflow init` in a Python project, nothing checks whether `src/`, `tests/`, or module boundaries follow good practice. A Rust project gets no help with `src/lib.rs` vs `src/bin/`, and a Java project gets no guidance on package structure.

The same problem repeats at every level: directory layout, file naming, function and variable naming, interface contracts between modules, test pairing, import hygiene. These are universal concerns — the patterns are the same, the specifics differ by language.

This story ships a **convention-checklist system**: generalized starter templates plus LLM prompts so the AI generates project-type-specific convention checks during `specflow init`. The templates are language-agnostic skeletons; the LLM fills in language-specific details (Python's `test_*.py`, Rust's `mod.rs`, Java's `camelCase`) based on the detected project type. Enforcement is deterministic via the existing `checklist-run` automated `script:` mechanism — no new CLI commands or artifact types needed.

## Design Principle

We don't ship rigid opinions. We ship **templates** and **prompts** that help the LLM generate the right conventions per project type. A Python library, a Rust CLI, and a Java web service all have different conventions — the LLM adapts, the user can customize or skip.

## Convention Patterns (reference for LLM generation)

The LLM should draw from these patterns when generating project-specific convention checklists. Each pattern is language-agnostic; the LLM fills in language-specific details during init.

| # | Pattern | What it enforces | Python example | Rust example | Java example |
|---|---------|------------------|----------------|-------------|-------------|
| A | **Directory layout** | Standard structure per project type | `src/{pkg}/`, `tests/` | `src/lib.rs`, `src/bin/` | `src/main/java/{pkg}/` |
| B | **Module boundary rules** | Dependency direction, no circular imports | `core` may not import `ui` | `lib` may not depend on `bin` | `service` may not import `controller` |
| C | **Naming conventions** | File, class, function, variable naming | `snake_case` functions, `PascalCase` classes | `snake_case` functions, `CamelCase` types | `camelCase` methods, `PascalCase` classes |
| D | **Test structure pairing** | Test dirs mirror source structure (V-model) | `tests/unit/test_foo.py` mirrors `src/foo.py` | `tests/foo_test.rs` mirrors `src/foo.rs` | `FooTest.java` mirrors `Foo.java` |
| E | **Interface contracts** | Public API surface is documented and stable | Protocols/ABCs define module boundaries | `pub trait` for inter-module contracts | `interface` for service boundaries |
| F | **Configuration management** | Where configs live, env var naming | `.env`, `pyproject.toml` | `Cargo.toml`, `.env` | `application.yaml` |
| G | **Documentation coverage** | Public APIs have documentation | Docstrings on all public functions | `///` on all `pub` items | Javadoc on all public methods |
| H | **Import hygiene** | No banned imports, no star imports | No `import *`, no direct DB in handlers | No `use super::*` in pub modules | No `import foo.*` |

## Deliverables

### 1. Convention checklist templates

Create `src/specflow/templates/checklists/conventions/` with starter YAML files:

- **`directory-layout.yaml`** — Automated checks that the project follows the declared directory structure. Uses `script:` fields with `test -d` / `find` commands. Items are generalized placeholders (e.g., "source directory exists", "test directory exists") that the LLM customizes per project type during init.

- **`test-mirroring.yaml`** — Automated checks that test directories mirror source structure. Maps to V-model pairing (REQ→QT, ARCH→IT, DDD→UT). Scripts compare directory trees.

- **`naming-conventions.yaml`** — Automated checks for file, function, class, and variable naming. Script-based `grep` / regex checks. Templates have placeholder patterns the LLM fills per language.

- **`module-boundaries.yaml`** — Template with placeholder forbidden-import rules. LLM fills in during init based on ARCH decomposition. Scripts use `grep` or language-specific import linters.

- **`interface-contracts.yaml`** — Checks that public modules define stable interfaces (protocols, traits, interfaces) and that inter-module calls go through declared contracts rather than reaching into internals. Mix of automated (`grep` for direct internal access) and manual review items.

Each checklist item follows the existing schema: `id`, `check`, `automated`, `script`, `severity`.

### 2. Convention reference document

Add `convention-patterns.md` to the `/specflow-init` skill's `references/` directory (created by STORY-033). Contains the A-H pattern table above with examples and guidance for the LLM on when to generate which conventions.

### 3. `/specflow-init` skill enhancement

Modify the `/specflow-init` SKILL.md (created by STORY-033) to add a convention-scaffolding step after project type detection:

1. After determining project type (web-app, CLI, library, etc.), the LLM generates convention checklists matching the project's language and structure
2. Present a summary: "Based on your Python library project, I'll create these convention checks: directory layout (src/pkg, tests/), naming (snake_case, test_*), ..."
3. User can accept, modify, or skip
4. Checklists are written to `.specflow/checklists/conventions/`

### 4. `/specflow-discover` skill enhancement

Modify the `/specflow-discover` SKILL.md to include optional guidance: when discovering requirements for a new module or subsystem, also consider generating convention checklist items for its structure, boundaries, and interface contracts. This is a hint, not forced — the skill suggests it when relevant.

### 5. Scaffolding and engine wiring

Add `conventions` to the checklist pipeline:

- `scaffold.py` `copy_checklists()` — add `conventions` to the category list so `specflow init` copies convention templates to `.specflow/checklists/conventions/`
- `checklists.py` `assemble_checklist()` — add `conventions` as a loadable category so `checklist-run` picks up convention checks when relevant

## Acceptance Criteria

1. `templates/checklists/conventions/` contains at least 5 starter checklist YAML files (layout, test-mirroring, naming, boundaries, interface-contracts)
2. Every checklist item with `automated: true` has a working `script:` field that runs deterministically (zero tokens)
3. Convention checklist YAML files are loaded and executed by `specflow checklist-run` when run against relevant artifacts
4. Convention checklists are copied to `.specflow/checklists/conventions/` during `specflow init` — `scaffold.py` `copy_checklists()` includes `conventions` in its category list
5. `checklists.py` `assemble_checklist()` loads convention checklists from `.specflow/checklists/conventions/`
6. The convention-patterns reference doc exists in the `/specflow-init` skill's `references/` directory (after STORY-033 creates it)
7. `/specflow-init` SKILL.md contains a `## Step: Generate Convention Checklists` section (or equivalently named heading) that: (a) reads the project type detected in the prior step, (b) consults `references/convention-patterns.md` for the A-H pattern table, (c) generates language-specific YAML files and writes them to `.specflow/checklists/conventions/`, (d) presents a summary listing the generated files and accepts user-modify/skip
8. `/specflow-discover` SKILL.md contains a guidance block (3-5 lines) inside the new-module / new-subsystem flow that suggests scaffolding convention items for the module's directory layout, module boundaries, and naming. The guidance is opt-in (a hint, not forced); the existing discover flow is otherwise untouched
9. No new CLI commands, no new artifact types — purely checklist + prompt + engine wiring
10. Convention checklists are generalized (not Python-specific) — language specifics come from LLM generation during init

## Out of Scope

- New artifact types (CONV or otherwise)
- New CLI commands beyond existing `checklist-run`
- Changes to `artifact-lint` engine
- Language-specific static analysis integration (ruff, eslint, clippy, etc.)
- Enforcing conventions in CI (that's the adapter framework's job)
- Shipping pre-built checklists for specific languages (the LLM generates them)

## Dependencies

- STORY-033 (creates the `/specflow-init` skill, the `shared/` template directory, and the `/specflow-discover` skill that gets the enhancement)
