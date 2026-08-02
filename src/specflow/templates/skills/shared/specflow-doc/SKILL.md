---
name: specflow-doc
description: SCOPE = the docs/ knowledge surface (README, docs/, adr/, CONTRIBUTING, root markdown). Use to write or revise project documentation, cite spec artifacts from a doc via inline @ID markers (e.g. @ARCH-007, @DEC-018), sync the docs index, and check whether docs still cite current (non-superseded) artifacts. Triggers when the user says "write the docs," "document this," "update the README," "explain the architecture in the docs," "cite the spec from the docs," "link this doc to the spec," "sync the docs index," or "are the docs stale / out of date." NOT for recording a decision (use /specflow-plan → DEC), capturing a requirement (use /specflow-discover → REQ), throwaway research (use a SPIKE), reproducible experiments (use the **autoresearch pack**'s `/specflow-autoresearch EXPT`, if installed), or authoring/reviewing a SpecFlow artifact itself (use create commands or /specflow-artifact-review). Docs are a knowledge SURFACE, not an artifact type — editing a doc never creates a REQ/ARCH/DEC; git history is the change log.
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the message to choose the mode:

- **"write/document/update the docs"** → author or revise the doc; add `@ID` citations where it references a spec.
- **"cite the spec / link this doc"** → add `@ID` markers, then sync the index.
- **"sync / refresh the docs index"** → run `specflow rebuild-index`.
- **"are the docs stale / what's outdated"** → run `specflow detect stale-docs`.
- **A question** ("how do docs relate to specs?") → answer from the deterministic core, no edits.

## Disambiguation

If the user's intent is really one of these, redirect (one question if unsure):

- **A decision / "why we chose X"** → `/specflow-plan` and a **DEC** (a doc can *cite* `@DEC-018`, but the decision itself is a DEC).
- **A requirement / "the system must do X"** → `/specflow-discover` and a **REQ**.
- **Throwaway research / a spike** → a **SPIKE**.
- **A reproducible experiment** → the **autoresearch pack** (`/specflow-autoresearch`, if installed — EXPT/LOOP/FIND).
- **Reviewing an artifact** → `/specflow-artifact-review`.

Docs are prose that *explains and cites* the spec graph; they are not part of it.

---

# SpecFlow Doc

`docs/` (and root markdown — README, AGENTS, CHANGELOG, …) is a recognized **knowledge surface**: indexed and shown in `specflow brief`, citable both ways with the spec graph, and flagged when stale — but **never** a lifecycle artifact. This is "accounting, not policing" extended to prose.

## Two rules

1. **Doc edits are git-history-only.** Editing a doc never creates a REQ/ARCH/DEC, never writes an artifact `_index.yaml` entry, and never emits a change record. You just edit and commit. Git is the change log.
2. **Staleness is surfaced, never enforced.** `specflow detect stale-docs` and `/specflow-audit` warn when a doc cites a superseded/cancelled/deprecated artifact. Staleness is an *accounting* lens — those warnings never block a commit and never escalate an audit exit code. (Structural signals like coverage gaps or orphan code do escalate to exit 2; see BP-006.)

## Workflow

1. **Author / revise.** Edit the doc normally. Wherever it references a spec, cite the artifact with an inline marker: `@ARCH-007`, `@DEC-018`, `@REQ-001`, `@DEC-018.2` (sub-id). See `references/citation-syntax.md`.
2. **(Optional) metadata.** A doc may carry a tiny `specflow-doc:` frontmatter block (`title`, `audience`, `last_reviewed`) — purely metadata, no status/lifecycle. Plain docs work fully without it. See `references/docs-frontmatter.md`.
3. **Sync the index.**
   ```bash
   specflow rebuild-index
   ```
   Writes the derived `_specflow/docs-index.yaml` (doc → citations reverse index) — an inspectable, greppable, git-diffable materialization. Every command recomputes live from disk, so files on disk remain the source of truth.
4. **Check recall.**
   ```bash
   specflow brief
   ```
   Shows a **Docs surface** block: count, areas, how many cite an artifact, top-cited docs.
5. **Check staleness.**
   ```bash
   specflow detect stale-docs      # names docs citing superseded artifacts
   specflow project-audit          # same, as a non-blocking audit concern
   ```
   Resolve by updating the citation or re-confirming the reference. See `references/staleness-rules.md`.

## Configuring the surface

The `docs:` block in `.specflow/config.yaml` sets `roots` (default `docs/`), `extra_files`, and `exclude`. Root-level `*.md` is always recognized. A project using `doc/` or `wiki/` overrides `roots`. See `references/docs-config.md`.

## References

- `references/citation-syntax.md` — the `@ID` grammar, code-fence exclusion, reverse-index behavior.
- `references/staleness-rules.md` — which statuses trigger a warning; warning-only; how to resolve.
- `references/docs-config.md` — the `docs:` config block; pointing at `doc/`/`wiki/`; `extra_files`/`exclude`.
- `references/docs-frontmatter.md` — the optional `specflow-doc:` block shape (metadata only).
