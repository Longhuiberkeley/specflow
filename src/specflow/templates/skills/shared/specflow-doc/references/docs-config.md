# Docs Surface Configuration

The docs surface is configurable in `.specflow/config.yaml` under the `docs:` key:

```yaml
docs:
  roots: ["docs/"]        # directories (or single files) treated as docs
  extra_files: []         # loose files outside roots + root (e.g. examples/guide.md)
  exclude: []             # glob denylist subtracted from the surface last
```

## Defaults

- **`roots: ["docs/"]`** — the conventional docs tree, enumerated recursively.
- **Root-level `*.md` is always recognized**, regardless of config. Any markdown sitting
  directly at the project root is documentation: `README.md`, `AGENTS.md`, `CHANGELOG.md`,
  `ROADMAP.md`, `CONTRIBUTING.md`, `SECURITY.md`, … You don't list these.
- **`extra_files: []`** — for a doc that lives outside `roots` and outside the project root
  (e.g. `examples/guide.md`, `docs/../NOTES.md`). Add explicit paths here.
- **`exclude: []`** — a glob denylist (same syntax as `source_scope.exclude`) subtracted
  from the surface last. Use it to drop archived/generated docs.

## Common overrides

Your docs live somewhere else:

```yaml
docs:
  roots: ["doc/", "wiki/"]
```

You have a big archive you don't want indexed:

```yaml
docs:
  exclude: ["docs/.archive/**", "docs/generated/**"]
```

A monorepo with per-package docs (not project docs — leave those as code-adjacent):

```yaml
docs:
  roots: ["docs/"]          # only the top-level project docs
  # per-package READMEs under packages/*/ stay out of the surface
```

## What the surface affects

- **Excluded from the code orphan scan** — docs are not counted as orphan "code", so
  coverage metrics reflect real code, not prose. (This fixes the historical miscount where
  `docs/*.md` + `README.md` showed up as uncovered source.)
- **Indexed** by `specflow rebuild-index` into `_specflow/docs-index.yaml`.
- **Shown** in `specflow brief` (Docs surface block) and `specflow adopt status`.
- **`@ID` citations** are scanned across the whole surface for the reverse index and
  staleness checks.

## What the surface does NOT do

Docs in the surface are **never** treated as artifacts: no `_index.yaml` lifecycle entry,
no status, no link role, no DEC on edit, no commit-hook checks. Editing a doc is a plain
git-tracked edit.
