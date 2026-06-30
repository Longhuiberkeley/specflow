# Optional Doc Frontmatter

A doc **may** carry a tiny `specflow-doc:` block in its YAML frontmatter. It is purely
metadata — no status, no lifecycle, not required. Plain docs with just `@ID` markers work
fully without it.

## Shape

```markdown
---
specflow-doc:
  title: Storage Architecture          # overrides the first H1 / filename
  audience: backend engineers          # free text
  last_reviewed: 2026-06-30            # ISO date; the only field SpecFlow reads back
---
# Storage Architecture

The object store backs onto S3 and is governed by @ARCH-007 …
```

## Field reference

| Field | Purpose | Read by SpecFlow? |
|-------|---------|-------------------|
| `title` | Display title (falls back to first H1, then filename stem) | Yes — `brief` / index |
| `audience` | Who the doc is for (free text) | Stored, not analyzed |
| `last_reviewed` | ISO date of last human review | Yes — informational |

No other fields are recognized. There is deliberately **no `status`**, no `id`, no `links`,
no `fingerprint` you write (SpecFlow computes the fingerprint from the body). This keeps
docs unambiguously *not* artifacts.

## Coexisting with other frontmatter

Docs often have frontmatter for other tools (Hugo/Docusaurus/Jekyll `title`/`slug`/`weight`,
MkDocs `nav_order`, etc.). SpecFlow only consumes the `specflow-doc:` sub-key and ignores
the rest — your static-site generator's frontmatter is left untouched.

```markdown
---
title: Storage              # MkDocs / Docusaurus
nav_order: 3
specflow-doc:               # SpecFlow's corner
  last_reviewed: 2026-06-30
---
```

## Fingerprinting

SpecFlow fingerprints the doc **body** (content after frontmatter), using the same
`compute_fingerprint` primitive as artifacts. So updating `last_reviewed` or a Docusaurus
`weight` in frontmatter does **not** look like content drift — only body edits do. The
fingerprint lives in `_specflow/docs-index.yaml`, never in the doc itself.
