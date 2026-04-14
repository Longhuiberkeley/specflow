# SpecFlow — Implementation Plan

## Vision

SpecFlow is a cross-CLI spec-driven development framework that combines proactive requirement acquisition, ASPICE-grade traceability, context-efficient execution, and cross-platform portability in a lightweight, filesystem-based package. It ships as a Python package managed by `uv`, lives entirely in the repository, stores all state in human-readable Markdown and YAML, and targets under 200 tokens of always-loaded context.

## Design Principles

1. **Modeless.** The framework is an accounting system, not a police system. The full V-model structure always exists and tracking is always on. The user's behavior is the toggle.
2. **Filesystem-native.** Markdown + YAML frontmatter. No databases, no cloud dependencies, no proprietary runtime.
3. **Programmatic-first.** Python CLI for deterministic work (zero tokens). LLM for judgment only. See D-16, D-17.
4. **Ceremony adapts to ambiguity.** Not to which command you typed. The readiness assessment detects scope automatically.
5. **Bring-Your-Own-Standard.** Artifact types are schema-driven. Users author their own compliance packs via LLM-assisted `/specflow-pack-author` (from PDF/URL/text) or manually via YAML, documented in `docs/authoring-a-pack.md` (pending).
6. **Cross-platform.** AGENTS.md (universal) + SKILL.md (portable) + platform adapters. Works on Claude Code, OpenCode, Gemini CLI, and degrades gracefully on Cursor, Windsurf, Cline.

## Phase Overview (Bootstrapped Sequence)

| Phase | Name | Delivers | Depends on | Est. Release |
|-------|------|----------|------------|-------------|
| P0 | Foundation | Python CLI (`uv`), `specflow init`, directory scaffolding, config, schemas | — | v0.1.0 |
| P1 | Self-Specification | Manual authoring of SpecFlow's specs using its own format (Dogfooding) | P0 | v0.1.0 |
| P2 | Verification | Zero-token validation scripts, `specflow status`, phase-gate checklists | P0, P1 | v0.1.0 |
| P3 | Core Workflow | AI-driven discovery conversation, planning, artifact CRUD, `_index.yaml` | P0, P1, P2 | v0.2.0 |
| P4 | Traceability | Impact analysis, suspect flags, fingerprints, cross-artifact consistency | P2, P3 | v0.2.0 |
| P5 | Execution & Review | `specflow go` orchestration, `specflow check` context-specific review | P3, P4 | v0.2.0 |
| P6 | Compliance & Standards| PDF standard ingestion, gap analysis, baselines, retroactive CRs | P4 | v0.3.0 |
| P7 | Team & Enterprise | RBAC via git, draft IDs + CI renumbering, defect lifecycle, test records | P5, P6 | v1.0.0 |
| P8 | Intelligence & Scaling| 3-tier dedup (tag Jaccard, TF-IDF, LLM), dead-code and similarity detection | P7 | v1.x |

## Dependency Graph

```
P0 ──→ P1 ──→ P2 ──→ P3 ──→ P4 ──→ P5 ──→ P6 ──→ P7 ──→ P8
       │      │      │      │      │      │
       └──────┴──────┴──────┴──────┴──────┘
               (Verification Gates)
```

Within phases, work flows:
- **P0** is standalone — scaffolding only.
- **P1** tests P0 schemas manually.
- **P2** depends on P1 specs to validate them (Self-Validation Gate).
- **P3** depends on P2 to ensure valid specs before AI plans them (Self-Planning Gate).
- **P4** depends on P3's output to verify impact cascades (Impact Cascade Gate).
- **P5** depends on P4's context and P3's stories to orchestrate execution (Autonomous Execution Gate).
- **P6** depends on P4 (traceability engine needed for compliance).
- **P7** depends on P5 (team execution) and P6 (compliance hooks).
- **P8** depends on P7 (scaling the enterprise features).

## Release Strategy

| Release | Includes | Milestone |
|---------|----------|-----------|
| v0.1.0 | P0 + P1 + P2 | Scaffolding, manual specification, and zero-token validation engine |
| v0.2.0 | P3 + P4 + P5 | Full AI lifecycle with discovery, traceability, execution, and review |
| v0.3.0 | P6 | Compliance-ready: Industry standards and gap analysis |
| v1.0.0 | P7 | Team-ready: RBAC, defect tracking, CI integration |
| v1.x | P8 | Dedup pipeline and project-hygiene detect commands |

Each release is a tagged Python package version managed by `uv`. Phases within a release can ship incrementally as minor bumps (v0.1.1, v0.1.2, etc.).

## Supporting Documents

- [Architecture](architecture.md) — technical design reference
- [Design Decisions](decisions.md) — resolved trade-offs with rationale