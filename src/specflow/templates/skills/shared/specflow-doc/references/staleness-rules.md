# Staleness Rules

Docs go stale when the spec they cite moves on. SpecFlow surfaces this; it never enforces it.

## What triggers a staleness warning

A doc is flagged when it cites (via `@ID`) an artifact whose `status` is:

| Status | Meaning |
|--------|---------|
| `superseded` | Replaced by a newer artifact (e.g. a DEC overturned by a later DEC) |
| `cancelled` | Withdrawn |
| `deprecated` | Retired but kept for reference |

A doc citing an `approved` / `implemented` / `verified` / `draft` artifact is **not** stale.

## Severity: warning, always

- `specflow detect stale-docs` and the `docs-staleness` concern in `specflow project-audit`
  emit findings at severity **`warn`** (or `info` when all citations are current).
- Stale docs **never** escalate an audit exit code, **never** appear in the commit hook,
  and **never** block a commit. This is accounting, not policing — docs are prose, and a
  stale citation is a nudge to review, not a defect.

## Dangling citations (cited ID not found)

A doc that cites an ID with **no matching artifact** (typo, deleted artifact, or an
unloaded pack type) is **not** flagged as stale. Missing ≠ superseded, and unloaded pack
types would make "dangling" noisy. If you suspect typos, `grep -rn '@' docs/` and
eyeball the IDs against `specflow status`.

## Resolving a staleness warning

Pick whichever fits:

1. **Update the citation** to the superseding artifact (e.g. `@DEC-018` → `@DEC-023` if
   DEC-023 supersedes DEC-018). Find the successor via `specflow trace DEC-018`.
2. **Re-confirm the reference** if the old artifact is still the right thing to cite
   (e.g. historical context). The warning is advisory; you may leave it.
3. **Rewrite the prose** if the doc no longer needs the reference.

After resolving, run `specflow rebuild-index` then `specflow detect stale-docs` to confirm.

## How staleness relates to drift

Doc *content* drift (a doc changed since it was fingerprinted) is recorded in
`_specflow/docs-index.yaml` fingerprints but is informational only — there's no "doc
suspect" cascade. Staleness is specifically about the **citation → artifact-status**
relationship, which is the part SpecFlow can reason about deterministically.
