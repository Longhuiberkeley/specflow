# Status Lifecycle

## Standard Lifecycle (Most Artifact Types)

```
draft → approved → implemented → verified
```

| Status | Meaning | Allowed transition from |
|--------|---------|------------------------|
| `draft` | Work in progress, not yet reviewed | (initial creation) |
| `approved` | Reviewed and accepted, ready for downstream work | `draft` |
| `implemented` | Code exists, awaiting verification | `approved` |
| `verified` | Corresponding test level confirms compliance | `implemented` |

## Terminal Lifecycle States (Retiring an Artifact)

When an artifact is no longer the live truth, model that as a **status change — not a
relationship role.** There are three distinct ends, and choosing the right one preserves
traceability:

| Status | Meaning | How to express |
|--------|---------|----------------|
| `superseded` | Replaced by a successor that carries the intent forward | Set the *successor's* link to `supersedes` the old artifact, and set the old artifact's `status: superseded` |
| `cancelled` | Terminated outright — no replacement, the intent is dropped | Set `status: cancelled` (e.g. a DEC cancels the work) |
| `deprecated` | Still technically valid but discouraged — don't build on it | Set `status: deprecated` |

Do **not** invent link roles like `cancelled_by`, `deprecates`, or `superseded_by`. The
"who replaced/cancelled me" question is answered by querying backlinks with
`specflow trace <ID>` (links are stored once and traversed both ways) plus the `supersedes`
edge on the successor. `cancelled`/`deprecated` are reachable from any active state;
`superseded` follows the `supersedes` link.

## Defect Lifecycle

```
open → investigating → fixing → verified → closed
```

| Status | Meaning |
|--------|---------|
| `open` | Defect reported, not yet triaged |
| `investigating` | Root cause analysis in progress |
| `fixing` | Fix is being implemented |
| `verified` | Fix confirmed by test |
| `closed` | Resolved (by STORY or commit) |

## Transition Rules

1. **Forward-only:** Status can only advance through the lifecycle. No backward transitions (e.g., `approved` cannot go back to `draft`).
2. **Parent/child consistency:** A parent artifact cannot be `verified` until all its children are `verified`. A child cannot be ahead of its parent in the lifecycle.
3. **Validation enforced:** `specflow update` rejects invalid transitions with a clear error message.

## Bulk Status Operations

To approve multiple artifacts:
```bash
uv run specflow update REQ-001 --status approved
uv run specflow update REQ-002 --status approved
```

To check status of all artifacts:
```bash
uv run specflow status
```

To validate status consistency:
```bash
uv run specflow validate --type status
```
