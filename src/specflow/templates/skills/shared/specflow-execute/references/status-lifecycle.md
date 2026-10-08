# Status Lifecycle

Status maps are **type-specific** — never assume a universal one. Before any transition, read the real map:

```bash
specflow transitions <ID>
```

`specflow update` rejects invalid transitions and names the command; `specflow artifact-lint --type status` validates consistency project-wide. Transitions are forward-only; a parent cannot be `verified` before its children are.

## Defect Lifecycle

```
open → investigating → fixing → verified → closed
open → fixing                      (legal when the cause is already known)
open | investigating → wontfix     (terminal)
```

| Status | Meaning |
|--------|---------|
| `open` | Defect reported, not yet triaged |
| `investigating` | Root cause analysis in progress (optional — skip it when the cause is known) |
| `fixing` | Fix is being implemented; reachable from `open` or `investigating` |
| `verified` | Fix confirmed by test |
| `closed` | Resolved (by STORY or commit) |
| `wontfix` | Terminal: will not be fixed — put the reason in `--rationale`; reachable from `open` or `investigating` |

A bug against an approved REQ is a DEF, not a new REQ: `specflow create --type defect --title "<symptom>" --add-link <REQ-ID>:fails_to_meet` (plus `--add-link <TEST-ID>:exposed_by` when a test caught it); the fix STORY links both the REQ and the DEF — `specflow create --type story --title "<fix>" --add-link <REQ-ID>:implements --add-link <DEF-ID>:derives_from` (`implements` satisfies the blocking story-linkage check; `derives_from` alone does not).

## Terminal States (Retiring an Artifact)

When an artifact is no longer the live truth, model that as a **status change — not a relationship role**:

| Status | Meaning | How to express |
|--------|---------|----------------|
| `superseded` | Replaced by a successor carrying the intent forward | Successor links `supersedes` the old artifact; old artifact gets `status: superseded` |
| `cancelled` | Terminated outright — no replacement, intent dropped | `status: cancelled` |
| `deprecated` | Still technically valid but discouraged — don't build on it | `status: deprecated` |

Do **not** invent link roles like `cancelled_by` or `deprecates` — query backlinks with `specflow trace <ID>`; the `supersedes` edge on the successor answers "who replaced me".
