---
id: STORY-632
title: Dual-host skills + lean AGENTS.md + default TLDR
type: story
status: implemented
priority: high
suspect: false
links:
- target: REQ-005
  role: implements
- target: REQ-001
  role: implements
- target: DEC-077
  role: guided_by
created: '2026-08-18'
fingerprint: sha256:e0b090c6ea29
modified: '2026-08-18'
version: 2
---

# Dual-host skills + lean AGENTS.md + default TLDR

## Goal

Make dual Claude Code + OpenCode2 projects install one SpecFlow skill tree and one instruction file, shrink always-on AGENTS.md, and make TLDR the default reply style.

## Acceptance Criteria

1. OpenCode (`--platform opencode` or detected `.opencode/`) installs SpecFlow + pack skills into `.claude/skills`, not `.opencode/skills`.
2. `refresh --all-platforms` with both `.claude/` and `.opencode/` present installs skills once, to `.claude/skills`. It does not create `.opencode/skills/specflow-*`.
3. Init/refresh no longer delete `.opencode/agents` or `.opencode/commands` (those are reserved for OpenCode-only extras).
4. Dual-host warning mentions that OpenCode consumes `.claude/skills` and that leftover `.opencode/skills/specflow-*` is a silent override.
5. Instruction injection always targets `AGENTS.md` when the platform's `instruction_file` is `AGENTS.md`. Existing `CLAUDE.md` SpecFlow sentinels migrate to AGENTS.md once (a block is only removed from CLAUDE.md once the same sentinel exists in AGENTS.md — never dropped outright); `GEMINI.md` is Gemini's own instruction file and is never touched. No new fallbacks.
8. Claude Code does not discover `AGENTS.md` natively — when SpecFlow injects into `AGENTS.md` and a `CLAUDE.md` exists, an `@AGENTS.md` import line is added as its first line (idempotent, user prose preserved), so Claude Code keeps loading the shared guidance.
6. `agent-context.md` is ~30 lines, includes a 4-line default TLDR style, and still mentions `specflow transitions`, `_specflow/`, and `specflow update`.
7. `tldr-communication` pack remains installable as an opt-in extra (full 10-line snippet); init skill no longer lists it as something you must pick to get terse replies.

## Out of scope

OpenCode plugin, CLI draft→approved confirm, native OpenCode tools.
