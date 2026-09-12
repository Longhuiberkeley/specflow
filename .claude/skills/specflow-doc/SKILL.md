---
name: specflow-doc
description: "Maintain artifact-embedded knowledge, or generate/sync a derived rendering from artifacts."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Doc

Per DEC-082, durable knowledge lives **in artifacts** (DEC, ARCH, DDD, artifact-attached references) — never only in docs. `docs/` and root markdown (README, AGENTS, CHANGELOG, …) are a **derived rendering** of the artifact graph: indexed in `specflow brief`, citable both ways, flagged when stale — never a lifecycle artifact, never the source of truth.

## What this skill does

- **Maintain artifact-embedded knowledge:** the decision/requirement content itself belongs in a DEC/REQ — create it there first; a doc may then *cite* it.
- **Generate/sync derived docs:** render human-facing output from artifacts, keeping docs downstream of the graph so drift is detectable rather than silent.
- **Cite:** where a doc references a spec, mark it inline — `@ARCH-007`, `@DEC-018.2` (sub-id); backtick'd and fenced `@ID`s don't count. See `references/citation-syntax.md`.

## Commands

```bash
specflow rebuild-index        # write the derived _specflow/docs-index.yaml (doc → citations reverse index)
specflow brief                # Docs surface block: counts, areas, top-cited docs
specflow detect stale-docs    # docs citing superseded/cancelled/deprecated artifacts (warning only)
specflow project-audit        # same staleness signal inside a whole-project audit
```

Staleness is surfaced, never enforced: warnings never block a commit and never escalate an audit exit code. Resolve by updating the citation or re-confirming the reference (`references/staleness-rules.md`). Docs carry no status; doc edits are git-history-only.

Optional per-doc metadata: a tiny `specflow-doc:` frontmatter block (`title`, `audience`, `last_reviewed`) — metadata only (`references/docs-frontmatter.md`). The surface itself is configured via the `docs:` block in `.specflow/config.yaml` (`roots`, `extra_files`, `exclude` — `references/docs-config.md`).

## Disambiguation

- A decision / "why we chose X" → `/specflow-plan` and a **DEC** (a doc can cite `@DEC-018`; the decision is not a doc).
- A requirement → `/specflow-discover` and a **REQ**.
- Throwaway research → a **SPIKE**; reproducible experiments → the autoresearch pack.
- Reviewing an artifact → `/specflow-artifact-review`.

## References

- `references/citation-syntax.md` — the `@ID` grammar, code-fence exclusion, reverse-index behavior.
- `references/staleness-rules.md` — which statuses trigger a warning; how to resolve.
- `references/docs-config.md` — the `docs:` config block (`roots`, `extra_files`, `exclude`).
- `references/docs-frontmatter.md` — the optional `specflow-doc:` metadata block.
