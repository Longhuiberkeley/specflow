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
uv run specflow go --dry-run

# Execute all waves
uv run specflow go

# Execute with custom timeout
uv run specflow go --timeout 300
```

## Context Isolation

Each story receives only:
- Its own story file (~500 tokens)
- Linked DDD (via `specified_by`) (~500 tokens)
- Linked ARCH interfaces (via `guided_by`) (~500 tokens)
- AGENTS.md project rules (~300 tokens)

Total budget: <4000 tokens per subagent.

## Lock Handling

- Locked artifacts cause the story to be deferred to the next wave
- Stale locks (PID no longer running) are automatically broken
- Lock files: `.specflow/locks/<ARTIFACT-ID>.lock`
