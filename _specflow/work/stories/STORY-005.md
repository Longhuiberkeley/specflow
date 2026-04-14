---
id: STORY-005
title: Implement filesystem locks for concurrent artifact modification
type: story
status: implemented
priority: medium
tags:
- concurrency
- locks
- P4
suspect: false
links:
- target: REQ-003
  role: implements
- target: ARCH-002
  role: guided_by
created: '2026-04-11'
modified: '2026-04-14'
fingerprint: sha256:c26bcff9ced0
checklists_applied:
- checklist: check-STORY-005
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-STORY-005
  timestamp: '2026-04-14T17:03:22Z'
---

# Implement filesystem locks for concurrent artifact modification

## Description

Implement a PID-based filesystem locking mechanism that prevents concurrent modification of the same artifact by multiple subagents or processes. Locks are stored in .specflow/locks/ and automatically cleaned up.

## Acceptance Criteria

1. Given no lock exists for REQ-001, when a process acquires the lock, then a file .specflow/locks/REQ-001.lock is created containing the PID, and subsequent attempts to acquire the lock fail with a message showing the holding PID

2. Given REQ-001.lock exists with PID 12345 but process 12345 is no longer running, when a new process attempts to acquire the lock, then the stale lock is broken with a warning message, the new PID replaces the old one, and the operation proceeds

3. Given a process holds the lock for REQ-001, when the process completes its work and releases the lock, then .specflow/locks/REQ-001.lock is deleted and other processes can immediately acquire it

## Out of Scope

- Distributed locking (multi-machine)
- Lock timeout enforcement

## Dependencies

- None
