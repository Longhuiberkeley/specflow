# Structural Lens Catalog (Wing A)

8 adversarial lenses that probe structural integrity, scalability, and compositional soundness.

## Instructions

Apply ALL 8 lenses below to the provided project context. For each lens, identify 0-3 findings. Output each finding as:

```
- title: <short title>
  rationale: <explanation>
  severity: warn | error | info
  lens: <lens-name>
```

Do not duplicate findings already covered by the deterministic core audit (schema, links, status, coverage checks).

## Lenses

### 1. Stress-scale (x100)

What breaks at 100x the stated scale — data volume, users, request rate, cost? Surface both hard limits (throughput, latency budgets) and soft limits (operational burden, on-call load).

### 2. Dependency shock

For each external dependency (library, API, team, vendor): what if it disappears, changes terms, degrades in performance, or gets deprecated? What is the blast radius?

### 3. Composition

What happens when multiple features interact? Race conditions, conflicting invariants, emergent behaviors between independently-specified artifacts. Look for overlapping ownership, shared mutable state, or conflicting constraints across artifacts.

### 4. Inversion (Munger)

What would guarantee failure? Identify the failure patterns, then check whether the design avoids them. Invert each requirement: "to fail at this, we would need to..."

### 5. Five-whys

Recursively ask "why" of each requirement's rationale. Usually exposes either a deeper root cause or a specious justification. Stop when you hit an assumption that is unvalidated.

### 6. Temporal drift

Is what's true today going to be true in 2 years? 5 years? What temporal assumptions are baked in? Check for: hardcoded dates, version-specific APIs, regulatory deadlines, technology deprecation timelines.

### 7. Assumption surfacing

Enumerate every implicit assumption the project rests on. For each, attack it: what if it's false? What if it changes mid-project? Look for assumptions about: team size, budget, timeline, technology choices, user behavior, regulatory environment.

### 8. Reversal

What if we did the opposite of each key decision? Sometimes reveals that the "obvious" direction is a bias rather than a reasoned choice. For each major architectural or design decision, argue the opposite case.
