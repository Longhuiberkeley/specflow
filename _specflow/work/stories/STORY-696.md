---
id: STORY-696
title: 'Index store: exclusive-create allocation, index as cache, one mutation lock,
  crash-safe renumber'
type: story
status: verified
tags:
- v1.17.0
- engine
- p1c
- index
suspect: false
links:
- target: REQ-002
  role: implements
- target: DDD-034
  role: specified_by
- target: DEC-093
  role: guided_by
- target: DEF-006
  role: derives_from
- target: DEF-007
  role: derives_from
- target: DEF-008
  role: derives_from
- target: DEF-009
  role: derives_from
- target: DEF-010
  role: derives_from
- target: DEF-013
  role: derives_from
- target: DEF-015
  role: derives_from
- target: DEF-012
  role: derives_from
created: '2026-09-30'
fingerprint: sha256:d5cd75b097f6
modified: '2026-09-30'
output_files:
- src/specflow/lib/locks.py
- src/specflow/lib/artifacts.py
- src/specflow/commands/renumber_drafts.py
- src/specflow/lib/draft_ids.py
- src/specflow/lib/learning.py
- src/specflow/lib/baselines.py
- src/specflow/lib/impact.py
- src/specflow/templates/skills/shared/specflow-execute/references/wave-computation.md
- tests/formal/index_store_support.py
- tests/formal/test_index_store_crash.py
- tests/formal/test_index_store_barriers.py
- tests/formal/test_index_store_allocators.py
- tests/formal/test_index_store_cli_parallel.py
- tests/formal/test_index_store_model_traces.py
- tests/test_single_index_writer.py
- tests/test_safety_claims_cite_tests.py
---

# Index store: exclusive-create allocation, index as cache, one mutation lock, crash-safe renumber

## Acceptance Criteria

1. create allocates by exclusive file creation with retry; the candidate id is max(ids on disk, quarantine, targets reserved by a crashed renumber's journal, index next_id) + 1; an unparsable or conflict-marked index is rebuilt under the lock and never yields next_id 1.
2. One repo-wide mutation lock wraps every writer of _index.yaml, state.yaml, PREV patterns, baselines and impact-log files through a single atomic_write primitive that asserts the lock is held, and read-modify-write callers (close_phase, set_phase) hold it across the read; a test bans any other writer.
3. The PREV, baseline and impact-log allocators use exclusive create.
4. renumber-drafts refuses target collisions and feature branches, journals its plan, and a run crashed at any write converges to the clean result when re-run, also when a create ran between the crash and the re-run; a resumed run whose target another artifact holds refuses before its first write.
5. The mutation lock is a kernel lock (fcntl.flock on POSIX, msvcrt.locking on Windows) with no stale-lock break; barrier tests on both paths show at most one holder. Per-artifact locks keep the file-lock path and are advisory.
6. tests/formal/ crash-at-k (raise and torn-write) and subprocess barrier harnesses assert I1 to I6 with test names pinned to the DDD-034 invariant list.
7. False safety claims in locks.py, renumber_drafts.py and wave-computation.md are corrected and tests/test_safety_claims_cite_tests.py requires any such claim to cite a test.
8. DEF-006 to DEF-010, DEF-012 (merge status write), DEF-013 and DEF-015 are filed from failing tests and closed by this story. DEF-014 (an id erased from every working-tree record is reallocated) stays open, pinned by a strict xfail.
