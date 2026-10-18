# Severity Levels

## Definitions

An agent or lens finding is `blocking` only with `measured` evidence; `inferred` evidence caps it at warning and `guess` evidence caps it at info (labels: `../../specflow-references/references/evidence-labels.md`).

### Blocking (must fix)

The artifact violates a core rule and cannot proceed in its lifecycle until fixed — missing required frontmatter fields, broken links, invalid status, REQ with no acceptance criteria, implementation detail in a requirement, missing public interface in an architecture.

**Action required:** fix before moving forward. `specflow artifact-lint` returns exit code 1.

### Warning (should fix)

A quality issue that doesn't block progress — unquantified non-functional terms ("fast", "reliable"), draft or approved story with fewer than 2 acceptance criteria, orphaned artifact with no links, missing V-model verification pair, stale fingerprint.

**Action recommended:** fix when convenient; resolve warnings before baselines and phase transitions.

### Info (nice to know)

Observations that may improve quality with no compliance impact — "should" where "shall" fits better, consolidation candidates, an applicable learned pattern, naming suggestions.

**Action optional:** review and decide.

## Escalation & Override

1. Gate warnings stay warnings: nothing runs a gate on a status or phase transition (`phase-set` never gates), so only an item authored `severity: blocking` blocks.
2. On a full `specflow artifact-lint` run, an escalating warning not recorded in the committed `.specflow/findings-baseline.yaml` is **blocking**; recorded ones are known debt. Accounting warnings (heuristics such as quality, conflicts, AC observability, SPIKE staleness) never escalate. Only `specflow findings-baseline update` writes the baseline; recording new debt needs `--accept-new` and the user's approval.
3. Info items never escalate automatically.
4. **User override:** the user can manually escalate or de-escalate any finding.

## Audit and CHL vocabulary

`specflow project-audit` findings, and the CHLs it creates, use `error`/`warn`/`info`. They map onto this file's levels one-to-one (the engine's typed-findings mapping in `specflow.core.findings`):

| Audit / CHL severity | Level here |
|----------------------|------------|
| `error` | `blocking` |
| `warn` | `warning` |
| `info` | `info` |

A CHL you file by hand SHOULD use `blocking`/`warning`/`info`.
