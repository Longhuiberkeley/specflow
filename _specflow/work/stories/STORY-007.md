---
id: STORY-007
title: Orchestrate parallel subagent execution with isolated context per story
type: story
status: draft
priority: high
tags:
- execution
- orchestration
- subagents
- P5
suspect: false
links:
- target: REQ-004
  role: implements
- target: REQ-001
  role: implements
- target: ARCH-003
  role: guided_by
- target: DDD-002
  role: specified_by
created: '2026-04-11'
---

# Orchestrate parallel subagent execution with isolated context per story

# Orchestrate parallel subagent execution with isolated context per story

## Description

Implement the specflow go command that spawns subagents per story wave, provides each with isolated context (only the story + relevant design docs), tracks progress in state.yaml, auto-commits after each wave, and reports progress to the user.

## Acceptance Criteria

1. Given 3 approved stories in Wave 1, when specflow go runs, then each story is assigned to a separate subagent, each subagent receives only its story file + linked DDD + linked ARCH interfaces + AGENTS.md, and the subagents execute in parallel

2. Given Wave 1 completes successfully with all 3 stories implemented, when the orchestrator processes results, then each story's status is updated to implemented, a git commit is created with the wave number and story IDs in the message, state.yaml shows wave: 1 completed, and the user sees a wave summary

3. Given one subagent fails (timeout or error) while others succeed, when Wave 1 completes, then the failed story is marked as failed in state.yaml, successful stories are committed normally, and the failed story does not block subsequent waves

4. Given a story's artifact is locked by another process, when the orchestrator tries to execute it, then the story is moved to the next wave's queue with a message explaining the lock, and other stories in the current wave proceed normally

## Out of Scope

- Wave computation algorithm (STORY-006)
- Review and challenge engine (STORY-008/009)

## Dependencies

- STORY-005 (filesystem locks)
- STORY-006 (wave computation)
