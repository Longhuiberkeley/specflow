---
id: STORY-638
title: 'v1.14.3: atomic create locking (race-safe ID allocation)'
type: story
status: verified
tags:
- review-hardening
suspect: false
links:
- target: REQ-003
  role: implements
created: '2026-08-27'
fingerprint: sha256:d2a28767e509
authorization_note: UT+IT+QT contracts created and stamped green; full suite 1421
  green; gates clean (owner-pre-authorized overnight run 2026-08-27). Listed in morning
  report.
modified: '2026-08-27'
output_files:
- src/specflow/lib/locks.py
- src/specflow/lib/artifacts.py
- src/specflow/commands/unlock.py
- src/specflow/lib/executor.py
- tests/test_create_locking.py
version: 1
review_note: 'Post-implementation review (fix pass 1): stale-break now payload-reverified
  (cannot unlink a lock a concurrent acquirer just placed across the parse gap), release
  ownership-checked, PermissionError reads as live PID, docstring claims scoped honestly.
  +4 regression tests.'
---

# v1.14.3: atomic create locking (race-safe ID allocation)

Concurrent `specflow create` calls race on next_id read→write (lib/artifacts.py:1181-1215, no lock; lib/locks.py acquire is check-then-write, not atomic). Two workers can allocate the same ID, overwrite files, or lose the next_id bump.

## Acceptance Criteria

1. `acquire_lock` becomes atomic (O_CREAT|O_EXCL); check-then-write race eliminated.
2. A type-scoped create lock covers ID allocation, duplicate-check, file write, next_id bump, and index write inside `create_artifact` (draft-ID title branch included); released via try/finally.
3. Stale create locks auto-break (pid liveness + age); `specflow unlock` can break type-scoped create locks.
4. Dead `acquire_lock`/`release_lock` import in executor.py:14 cleaned up.
5. Subprocess-based concurrency regression test: two workers creating the same type concurrently produce distinct IDs and an intact index.
