# Wave Computation

## Overview

`specflow go` computes parallel execution waves from story dependencies. Stories within a wave can execute simultaneously; waves execute sequentially.

## Dependency Rules

| Link pattern | Interpretation |
|-------------|----------------|
| STORY-B `derives_from` STORY-A | Hard dependency: B after A |
| STORY-B and STORY-C both `specified_by` DDD-001 | Soft dependency: B before C (by ID order, likely touch same code) |
| STORY-B and STORY-C both `guided_by` ARCH-001 | No dependency (different implementations of same interface) |

## Algorithm

1. Build directed graph from story links
2. Kahn's topological sort (BFS-based)
3. Stories at same topological level form a wave
4. Circular dependencies are detected and reported

## Usage

```bash
# Preview the wave plan
specflow go --dry-run

# Execute all waves
specflow go

# Execute with custom timeout
specflow go --timeout 300
```

## Context Isolation

Each story receives only:
- Its own story file (~500 tokens)
- Linked DDD (via `specified_by`) (~500 tokens)
- Linked ARCH interfaces (via `guided_by`) (~500 tokens)
- AGENTS.md project rules (~300 tokens)

Total budget: <4000 tokens per subagent.

This is the standard fan-out pattern (see `../../specflow-references/references/adversarial-lenses.md` § Multi-Agent Strategy): on Claude Code/OpenCode, stories within a wave run as parallel subagents (each <4000 tokens); on hosts without native subagents, `specflow go` executes stories sequentially within a wave. Output is identical either way — the wave topology is deterministic (computed by the algorithm above); only the execution parallelism differs.

## Lock Handling

- Locked artifacts cause the story to be deferred to the next wave
- Stale locks (PID no longer running) are automatically broken
- Lock files: `.specflow/locks/<ARTIFACT-ID>.lock`
