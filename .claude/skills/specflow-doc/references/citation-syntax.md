# Citation Syntax

Docs cite spec artifacts with inline **`@ID` markers**. This is the only mechanism
that connects prose to the spec graph — and it is intentionally lightweight: no
frontmatter required, no link role, no schema change (respects frozen vocabulary D-18).

## Grammar

```
@<PREFIX>-<NUMBER>[.<SUB>]
```

- `PREFIX` is any registered artifact prefix, read live from `.specflow/schema/*.yaml`
  (so pack-added types count): `REQ`, `ARCH`, `DDD`, `UT`, `IT`, `QT`, `BP`, `STORY`,
  `SPIKE`, `DEC`, `DEF`, `AUD`, `CHL`, `REVIEW`, plus pack prefixes (e.g. `HAZ`, `RUN`).
- `NUMBER` is 3–5 digits.
- `.<SUB>` is an optional child id (e.g. `@REQ-001.2`).

Valid: `@ARCH-007`, `@DEC-018`, `@REQ-001.2`, `@DEC-018.2`.
Rejected: `@user`, `email@host.com`, `DEC-019` (no `@`).

## Where citations are detected

- Citations are scanned in the doc **body** (content after any frontmatter).
- **Code is stripped first** — fenced blocks (``` ``` ``` / `~~~`), 4-space/tab
  indented blocks, and inline spans of any backtick-run length (`` `…` ``, `` ``…`` ``).
  An `` `@ARCH-007` `` in backticks is almost always a *syntax example*, not a real
  reference, so it is not counted. To make a citation, write the `@ID` in plain prose
  (no backticks, not indented).
- A negative lookbehind prevents matches inside email-style or identifier text
  (`user@host`).

## The reverse index

`specflow rebuild-index` builds `_specflow/docs-index.yaml`, which includes:

```yaml
reverse:
  ARCH-007: [docs/architecture.md]
  DEC-018: [docs/architecture.md, docs/decisions.md]
```

So "which docs cite this artifact?" is a single lookup against the materialized file.
`specflow brief` surfaces the top-cited docs and `specflow detect stale-docs` flags
staleness — both recompute live from disk (the cache is for inspection, not their input).

## The other direction (artifact → doc)

Citation is primarily doc → artifact (the `@ID` markers above). The reverse direction
is optional: an artifact may name related docs via an optional `doc_refs:` frontmatter
field (a list of repo-relative paths). `doc_refs` is metadata, not a link role — it
never affects traceability or the link validator.

## Why `@ID` and not free text?

Spec docs frequently mention `DEC-018` in prose without meaning "this doc is *about*
DEC-018." The `@` prefix makes a citation an intentional act — explicit, greppable, and
low-false-positive. `grep -rn '@DEC-' docs/` lists every doc citing a decision.
