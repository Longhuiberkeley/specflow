# Wave Computation

`specflow go` computes parallel execution waves from story dependencies: stories in a wave run simultaneously, waves run sequentially. `specflow go --dry-run` previews the plan; circular dependencies are detected and reported.

## Dependency Rules

| Link pattern | Interpretation |
|-------------|----------------|
| STORY-B `derives_from` STORY-A | Hard dependency: B after A |
| STORY-B and STORY-C both `specified_by` DDD-001 | Soft dependency: B before C (by ID order, likely touch same code) |
| STORY-B and STORY-C both `guided_by` ARCH-001 | No dependency (different implementations of same interface) |

## Locks

Locked artifacts defer their story to the next wave; stale locks (PID no longer running) are broken automatically. Lock files: `.specflow/locks/<ARTIFACT-ID>.lock` — machine-managed, never hand-edited.
