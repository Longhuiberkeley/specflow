# Wave Computation

`specflow go` computes parallel execution waves from story dependencies: stories in a wave run simultaneously, waves run sequentially. `specflow go --dry-run` previews the plan; circular dependencies are detected and reported.

## Dependency Rules

| Link pattern | Interpretation |
|-------------|----------------|
| STORY-B `derives_from` STORY-A | Hard dependency: B after A |
| STORY-B `depends_on` STORY-A | Hard dependency: B after A (ordering only — no decomposition implied) |
| STORY-B and STORY-C both `specified_by` DDD-001 | Soft dependency: B before C (by ID order, likely touch same code) |
| STORY-B and STORY-C both `guided_by` ARCH-001 | No dependency (different implementations of same interface) |

## Locks

Parallel stories may create and update artifacts at the same time: one repo-wide mutation lock serialises every write of the indexes, `state.yaml`, learned patterns, baselines and impact-log files, and ID allocation never hands one ID to two stories, including between a crashed `specflow renumber-drafts` and its re-run (the renumber journal reserves its target IDs). One known gap (DEF-014): an ID whose file was deleted without a rebuild, and whose `_index.yaml` entry was lost by resolving a merge conflict to the other side, can be handed out again; run `specflow rebuild-index` after deleting artifact files. A story whose touched artifact holds a per-artifact lock (`.specflow/locks/<ARTIFACT-ID>.lock`) is reported as deferred and left queued; it is not re-run in a later wave, and nothing breaks such locks automatically. `specflow locks` lists current locks and `specflow unlock <ARTIFACT-ID>` breaks one whose process is gone. Lock files are machine-managed, never hand-edited.
