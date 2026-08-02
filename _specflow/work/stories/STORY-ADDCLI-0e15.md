---
id: STORY-ADDCLI-0e15
title: Add CLI subcommand specflow autoresearch with plan/run/review/leaderboard
type: story
status: draft
suspect: false
links:
- target: REQ-AUTORESE-d684
  role: implements
created: '2026-05-16'
fingerprint: sha256:90a19484fc11
---

# Add CLI subcommand specflow autoresearch with plan/run/review/leaderboard

## Acceptance Criteria

1. `specflow autoresearch plan` creates or updates a LOOP artifact with mode, budget, and knowledge_input
2. `specflow autoresearch run` executes the autonomous loop protocol against a COMP
3. `specflow autoresearch review` displays FINDs and EXPTs for a given COMP with status summaries
4. `specflow autoresearch leaderboard` ranks EXPTs by metric value with grouping support
