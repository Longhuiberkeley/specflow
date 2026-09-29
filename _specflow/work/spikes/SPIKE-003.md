---
id: SPIKE-003
title: 'Model-check the index store: allocation under concurrency, crash and git'
type: spike
status: completed
rationale: 'Event trigger T3/T1: false safety claims in locks.py and renumber_drafts.py;
  defects A-F reproduced.'
tags:
- formal
- tla
- concurrency
- index
suspect: false
links:
- target: DEC-090
  role: guided_by
- target: REQ-002
  role: derives_from
created: '2026-09-30'
timebox: 2d
fingerprint: sha256:c0024f880158
modified: '2026-09-30'
version: 2
---

# Model-check the index store: allocation under concurrency, crash and git

## Trigger
T3 and T1: code and docs asserted that the id race was nanosecond-scale and that re-running renumber-drafts is safe; both claims are false. Defects A, B, C, E, D and F were reproduced at HEAD 965ac21 on 2026-09-30 (scratchpad angleA/repro.py, repro2.py; re-run by the owner's session).

## Question
Which invariants must the index store keep under parallel agents, crashes between writes, git merges and clones, and does the fixed protocol in DEC-093 keep them?

## Invariants
DDD-034 section Invariants, I1 to I6. The human-reviewed statement is that list, not the model.

## Recipe (the reusable asset)
1. Write the invariants in the DDD first.
2. Model the CURRENT protocol; require the checker to reproduce the known bugs (fidelity canary; assert the checker's violation exit code, 12 for TLC, verified against the pinned jar).
3. Model the fix; check it.
4. Replay every trace as a failing pytest on the shipped code before filing a DEF; the DEF names that test.
5. Fix; re-check both.
6. Record states explored, exit code, model sha and assumptions here; dispose of the model.

## Part 1: real-code harness (tests/formal/)
Crash-at-k over every write primitive (raise and torn variants) for create, update, rebuild-index, renumber-drafts, lint --fix, merge, split and practices migrate; subprocess barrier tests at the known windows; environment fixtures (conflict markers, deleted highest id, nested file, detached HEAD). Producers of real concurrency: execute waves, generate-tests, parallel verify, the artifact-review lens fan-out, the autoresearch LOOP gate.

## Part 2: TLA+ model of the fixed protocol (formal/tla/, disposable)
Actions: Create, Update, Rebuild, Renumber with a Crash step between each write, Delete, GitMerge (index conflict, ours, theirs, union; files unioned), BranchKind (main, feature, detached). A history variable supports NoReuse. Fidelity first on the current protocol. Hard cap one day; if the DEC-093 fix has no multi-step recovery, replace the model with a paragraph argument below.

## Model to code table
Each action of the fixed-protocol model `formal/tla/IdAllocation.tla`, the code that implements it (DEC-093; line numbers in the v1.17.0 working tree), and the real-code test that exercises it (part 1). `formal/tla/IdAllocation_Current.tla` models the pre-fix code at 965ac21 with the same action names (CRead/CFile/CIdx, URead/UWrite, RRead/RWrite, NPlan/NRewrite/NMove/NCommit).

| Model action | Code (fixed protocol) | Real-code test (tests/formal/) |
|---|---|---|
| CreateAlloc (heal, allocate, linearise) | `lib/artifacts.py:1450` takes `locks.mutation_lock`; `_create_locked` (1469): `_read_index` heals a conflicted index (1128), `_heal_index` (1279), candidate = `_highest_allocated` (1256: stems by rglob, index keys, quarantine, next_id - 1) + 1, skip loop over `locks.exclusive_write` (`lib/locks.py:620`, temp + `os.link`) at 1524-1531 | `test_I2_create_with_conflict_marked_index_never_overwrites`, `test_I1_explicit_id_that_exists_on_disk_is_refused`, `test_I4_parallel_cli_creates_updates_rebuilds_keep_invariants` |
| CreateIdx | `_write_index` (1544) through `locks.atomic_write` (`lib/locks.py:596`, temp + `os.replace`) | `test_I5_crash_at_every_write_then_rerun_converges[create-*]` |
| Update (heal only, abstractly) | `update_artifact` (1549) under the lock (1564); `_update_locked` reads the index (1660, heals) and writes it (1666) | `test_I4_update_rmw_vs_create_loses_no_create`, `test_I4_parallel_verify_vs_generate_tests_create` |
| Rebuild | `rebuild_index` (1671) under the lock (1687); `_rebuild_dir_index` (1701) quarantines fileless keys (`_quarantine_entries`, 1200) and floors next_id on the quarantine and the old next_id (1790-1800) | `test_I2_rebuild_vs_create_never_overwrites`, `test_I3_deleted_highest_id_never_reused_after_rebuild`, `test_I4_index_is_rebuildable_cache_after_mixed_sequence` |
| RnStart (refuse, resume or plan) | `commands/renumber_drafts.py` `run` (200): feature-branch refusal (204, `draft_ids.is_feature_branch`, `lib/draft_ids.py:51`), lock (211); `_run_locked` (149): resume when the journal exists (152), else `_plan_id_map` (44, floor = `_highest_allocated`) and `_collisions` (86) | `test_renumber_refuses_on_feature_branch`, `test_renumber_refuses_a_target_collision` |
| RnJournal | `locks_lib.atomic_write(journal_path, ...)` (177) | `test_I5_crash_at_every_write_then_rerun_converges[renumber-drafts-*]` |
| RnRewrite (each *.md, then each _index.yaml) | `draft_ids.rewrite_references` (`lib/draft_ids.py:111`), one `atomic_write` per file | same |
| RnMove, RnUnlink | `_rename_files` (95): an existing target on the same inode is the resumed tail of a link, so unlink the source (106-110); any other existing target raises `_Collision`; `os.link` (113) then `md.unlink()` (119) | same; `test_I2_renumber_vs_create_never_overwrites` |
| RnRebuild, RnDone | `_apply` (134): `rebuild_index` per touched type (144), then `journal_path.unlink()` (145) | same |
| Crash (between any two writes) | every guarded write is `atomic_write` or `exclusive_write`; the kernel drops the flock of a dead holder (`locks._acquire_raw`, 475) | `test_I5_crash_at_every_write_then_rerun_converges[*]`, `test_I5_harness_counts_every_write_primitive`, `test_I6_killed_holder_releases_the_mutation_lock` |
| Delete (environment) | no allocator forgets the id: quarantine on rebuild, index next_id without rebuild | `test_I3_deleted_highest_id_never_reused_after_rebuild`, `test_I3_deleted_highest_id_never_reused_without_rebuild` |
| GitMerge, Fork (environment) | `_read_index_raw` (1076) salvages both conflict sides; `_read_index` rebuilds under the lock; nested files counted by rglob | `test_I2_create_with_conflict_marked_index_never_overwrites`, `test_I1_nested_file_id_not_reallocated` |
| BranchKind (environment) | `draft_ids.is_feature_branch`: drafts on a feature branch, sequential ids on main and detached HEAD | `test_I1_detached_head_allocates_sequential_ids`, `test_renumber_refuses_on_feature_branch` |
| `lock` variable (I6) | `locks.mutation_lock` (550): `fcntl.flock` on POSIX; the Windows file lock and its payload-verified stale break (`_break_stale_verified`, 221) are not modelled | `test_I6_stale_break_unlink_vs_second_acquirer_single_holder` |
| (not modelled) PREV, baseline, impact-log allocation | `learning.persist_prevention_pattern`, `baselines.create_baseline`, `impact.create_impact_event` through `exclusive_write`, one step each | `test_index_store_allocators.py::test_I2_*` |

## Assumptions
### Part 1 (real-code harness)
- File system: POSIX `rename`/`os.replace` atomic within a directory, `os.link` and `O_EXCL` fail on an existing name, `fcntl.flock` released by the kernel when the holder dies (APFS and ext4 checked; network file systems out of scope). Windows keeps the file-lock fallback and its documented stale-break window.
- One machine per working tree; processes share one clock only for lock-age heuristics, which the flock path does not use.
- Crash model: the k-th call to `Path.write_text`, `Path.write_bytes`, `os.replace`, `os.rename`/`Path.rename` or `os.link` raises a BaseException either before writing or after writing half its payload (torn). Fsync and power loss (reordered writes, lost directory entries) are not modelled.
- Re-run model: the same command with the same arguments, once, after the crash; the comparison normalises timestamps and ignores lock files and temp debris.
- Barrier windows are widened with file barriers and sleeps at the known read-modify-write points; they demonstrate that an interleaving is reachable, not how likely it is.
- Git abstraction: a merge may leave conflict markers in `_index.yaml` (either side, or diff3 with a base section) but never in artifact files; artifact files from both branches are unioned. Detached HEAD behaves as main.
- Bounds: crash-at-k runs every k over one clean run of each command on a 2-4 artifact fixture; races run 8-25 processes per side.

### Part 2 (TLA+ model)
- Bounds (CONSTANTS): 2 actors (1 in the current-model B and E variants, to isolate them from races), one artifact type, canonical ids 1..3, 2 draft ids, at most 4 files ever created, at most 1 crash. Actors are symmetric (SYMMETRY).
- Abstraction: a file is its name mapped to (frontmatter id, inode); bodies, links, fingerprints and statuses are not modelled, and update reduces to its index heal. A locked command is one atomic step except where the code performs guarded writes a crash can separate: create (file, then index) and renumber (journal, each *.md rewrite, the index rewrite, link, unlink, rebuild, journal delete). A rebuild is one step (the quarantine is written first and only grows).
- Crash: the process dies between two writes and the kernel drops its flock. Torn writes are part 1's domain (every guarded write is atomic).
- Environment: Delete, Fork, GitMerge and BranchKind happen only while no command runs. A merge brings one new draft file and leaves `_index.yaml` conflicted (the salvage of both sides), ours, theirs (the fork-point index plus the draft) or union. Draft ids are never generated twice. Git never leaves markers in artifact files.
- History variable: an id counts as allocated once it is durable: a create that reported success, a written renumber journal (fixed protocol), or a target a pre-fix rewrite wrote into a file. A create killed before it reported, whose file is then deleted, handed its id to nobody.
- I4 is checked only when every actor is idle, the index is not conflicted, and no crash or environment edit happened since the last rebuild (DDD-034: "without a crash"). I5 is checked when a renumber run ends (every name carries its own id and no journalled draft survives) and when a resume stops on a collision.
- Safety only; no fairness or liveness properties.
- Toolchain: `tla2tools.jar` from https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar, "TLC2 Version 2.19 of 08 August 2024 (rev: 5a47802)", sha256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`; OpenJDK 21.0.6 (Temurin). Breadth-first search; `-workers 1` for the violation runs (deterministic counts), `-workers auto` for the exhaustive ones. TLC's violation exit code on this jar is 12, as observed on every violating run below.

## Fidelity result
The current-protocol model reproduces the known defects. Model `formal/tla/IdAllocation_Current.tla`, sha256 `90192d2dbad4cc8246e29a98d49cd66d5d225ebea430457f964fbbd53918dceb`. Every run exits 12.

| Config | Violated | Distinct states | Trace | Defect |
|---|---|---|---|---|
| `IdAllocation_Current.cfg` (all actions) | I3_NoReuse | 518 | GitMerge, NPlan, NRewrite, CRead | renumber rewrote a draft to REQ-001 with no lock; a racing create allocates REQ-001 (DEF-008/DEF-009 family) |
| `IdAllocation_Current_A.cfg` | I3_NoReuse | 21 | CRead, CFile, CIdx, GitMerge (conflict), CRead | A (DEF-006): a conflicted index reads as next_id 1 |
| `IdAllocation_Current_B.cfg` | I4_IndexIsCache | 14 | CRead, CFile, CIdx, Delete, RRead, RWrite | B (DEF-007): rebuild sets next_id to 1 after the highest id was deleted |
| `IdAllocation_Current_C.cfg` | I4_IndexIsCache | 20 | CRead, CFile, CIdx, CRead, CFile, URead, CIdx, UWrite | C (DEF-008): the unlocked update write-back loses REQ-002 |
| `IdAllocation_Current_E.cfg` | I1_NoDupId | 126 | GitMerge, NPlan, NRewrite, Crash, GitMerge, NPlan, NRewrite | E (DEF-009): the re-run plans from the unchanged next_id and gives a second draft the id the first already carries |

## Result
Decision gate: the DEC-093 fix does contain a multi-step recovery protocol (the renumber journal, resume and link-then-unlink tail), so the model was written rather than the paragraph argument.

Fixed-protocol model `formal/tla/IdAllocation.tla`, sha256 `e40588d4640c898154d2068dbf4d1ecc78b4217aec102e78132226df5a1b0d95`, checking TypeOK and I1-I6:

| Config | Exit | Result | Distinct states | Trace |
|---|---|---|---|---|
| `IdAllocation.cfg` (all actions) | 12 | I3_NoReuse violated (M2) | 902 | CreateAlloc, CreateIdx, Delete, GitMerge (theirs), CreateAlloc |
| `IdAllocation_NoTheirs.cfg` | 12 | I3_NoReuse violated (M1) | 1,483 | GitMerge, RnStart, RnJournal, Crash, CreateAlloc |
| `IdAllocation_NoCrash.cfg` | 12 | I3_NoReuse violated (M2) | 691 | as the full run |
| `IdAllocation_NoCrashNoTheirs.cfg` | 0 | no error, complete | 286,958 (1,206,556 generated), depth 33-34 | none |
| `IdAllocation_CandidateFix.cfg` (M1 repair, no theirs) | 0 | no error, complete | 4,359,816 (16,326,720 generated), depth 36 | none |

With I3 and then I4 removed from the NoTheirs run, TLC continued M1 to an I4 violation (a rebuild after the crash sets next_id below the journalled targets) and then an I1 violation (GitMerge, RnStart, RnJournal, RnRewrite, Crash, CreateAlloc: the crashed run had already rewritten the draft file's frontmatter to REQ-001, but `_heal_index` skips a file whose stem is an index key, so the create writes a second REQ-001).

The fixed protocol keeps I1-I6 across the whole bounded space when no crash is followed by a different command and no index conflict is resolved to the older side. Two new trace families (M1, M2; named apart from the triggers T1-T4) break it:
- M1, DEF-013 (major): after a renumber crash, any create before the re-run can take a journalled target (I3) or an id a file already carries (I1), and the resume then stops on a collision (I5). The protocol assumed the documented re-run comes first; the released flock lets any writer in. A repair that also floors every allocator on the journal targets and on every frontmatter id (`CandidateFix`) checks clean.
- M2, DEF-014 (minor, environment): a hand or git delete that never went through rebuild-index, followed by a merge conflict on `_index.yaml` resolved with the side that forked before the id existed, leaves no working-tree record of the id, and create hands it out again. The conflict-marker path itself is safe (salvage of both sides).

Both traces were replayed as failing pytests on the shipped code before the DEFs were filed (recipe step 4); they are recorded as strict xfails in `tests/formal/test_index_store_model_traces.py` (UT-132) and are not fixed here.

## Reproductions
Planned DEF-001..005 were filed as DEF-006..010 (DEF-001..005 were taken by other v1.17.0 stories). Each failed on the shipped code (HEAD 965ac21 source, run 2026-09-30) and passes after STORY-696.

| DEF | Defect | Failing-then-passing tests |
|---|---|---|
| DEF-006 | A: conflict-marked `_index.yaml` makes create return REQ-001 and overwrite it; explicit `--id` on disk overwritten | `tests/formal/test_index_store_barriers.py::test_I2_create_with_conflict_marked_index_never_overwrites`, `::test_I1_explicit_id_that_exists_on_disk_is_refused` |
| DEF-007 | B: deleted highest id reused after rebuild, re-binding links; nested file id re-allocated | `::test_I3_deleted_highest_id_never_reused_after_rebuild`, `::test_I1_nested_file_id_not_reallocated`, `::test_I4_index_is_rebuildable_cache_after_mixed_sequence` |
| DEF-008 | C: unlocked index read-modify-write in update and rebuild loses concurrent creates | `::test_I4_update_rmw_vs_create_loses_no_create` (9 of 25 creates survived), `::test_I4_parallel_verify_vs_generate_tests_create`, `::test_I2_rebuild_vs_create_never_overwrites` |
| DEF-009 | E: crash mid-command does not converge on re-run (renumber duplicates, torn writes) | `tests/formal/test_index_store_crash.py::test_I5_crash_at_every_write_then_rerun_converges` [update-torn, rebuild-index-torn, renumber-drafts-raise, renumber-drafts-torn, artifact-lint--fix-torn, merge-torn, split-torn, practices-migrate-torn]; `test_index_store_barriers.py::test_I2_renumber_vs_create_never_overwrites`, `::test_renumber_refuses_on_feature_branch`, `::test_renumber_refuses_a_target_collision` |
| DEF-010 | Stale-break unlink admits two holders (the barrier fired: both held for the 0.8 s window) | `::test_I6_stale_break_unlink_vs_second_acquirer_single_holder` |

Also red on the shipped code without a DEF of their own (AC3 design change): `tests/formal/test_index_store_allocators.py::test_I2_prev_allocator_never_replaces_a_pattern`, `::test_I2_baseline_create_is_exclusive`, `::test_I2_impact_events_in_one_second_are_both_kept`. Defect F (merge wrote `merged_into`) is pinned by `tests/test_merge_split_status.py` (STORY-697). `tests/formal/test_index_store_cli_parallel.py` passed on the shipped code in the recorded run (the CLI race is intermittent there).

Traces from the fixed-protocol model (part 2), open, reproduced on the v1.17.0 working tree and pinned as strict xfails (run with `--runxfail` to see them fail):

| DEF | Trace | Failing test (tests/formal/test_index_store_model_traces.py, UT-132) |
|---|---|---|
| DEF-013 | M1: create between a renumber crash and its re-run | `::test_I3_create_after_renumber_crash_never_takes_a_journalled_target`, `::test_I1_create_after_renumber_crash_mid_rewrite_never_duplicates_an_id`, `::test_I5_renumber_resume_after_interleaved_create_converges` |
| DEF-014 | M2: deleted id forgotten after a merge conflict on `_index.yaml` is resolved with the older side | `::test_I3_theirs_resolved_index_after_deleting_an_id_never_reuses_it` |

## Disposition
The models in `formal/tla/` are disposable: each file's header reads "valid as of 965ac21; not maintained". They are not verify contracts, are not shipped, and never run in CI. To re-run one: `java -cp tla2tools.jar tlc2.TLC -workers 1 -config <cfg> <module>.tla` from `formal/tla/`. Recipe step 5 for DEF-013: when its fix STORY lands, fold the fix into `IdAllocation.tla` (the `CandidateFix` floor), re-check `IdAllocation.cfg` and `IdAllocation_Current*.cfg`, and remove the xfail marks so UT-132 verifies the fix. Promote a model to a maintained artifact only if a trigger recurs on the same mechanism. The learned practice is recorded as BP-008 (draft, awaiting owner approval).
