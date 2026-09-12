# Status Lifecycle

Status maps are **type-specific** — never assume a universal one. Before any transition, read the real map:

```bash
specflow transitions <ID>
```

`specflow update` rejects invalid transitions and names the command; `specflow artifact-lint --type status` validates consistency project-wide. Transitions are forward-only; a parent cannot be `verified` before its children are.

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

## Terminal States (Retiring an Artifact)

When an artifact is no longer the live truth, model that as a **status change — not a relationship role**:

| Status | Meaning | How to express |
|--------|---------|----------------|
| `superseded` | Replaced by a successor carrying the intent forward | Successor links `supersedes` the old artifact; old artifact gets `status: superseded` |
| `cancelled` | Terminated outright — no replacement, intent dropped | `status: cancelled` |
| `deprecated` | Still technically valid but discouraged — don't build on it | `status: deprecated` |

Do **not** invent link roles like `cancelled_by` or `deprecates` — query backlinks with `specflow trace <ID>`; the `supersedes` edge on the successor answers "who replaced me".
