# Thinking Techniques for Planning

Structured thinking techniques to stress-test architecture and design *at creation time*. The goal is to catch structural problems before implementation begins.

## Techniques

### Premortem

Fast-forward six months: the implementation failed. What caused it?

- **When to apply:** Every new ARCH before it is finalized
- **What to ask:** "It's 6 months from now and this architecture failed. What went wrong?"
- **What it catches:** Designs that look sound but fail in practice (operational complexity, team skill gaps, underestimated integration effort)

### Dependency Shock

For each external dependency, assume it breaks.

- **When to apply:** ARCHs with external service dependencies, third-party libraries, or cross-team boundaries
- **What to ask:** "What if this library disappears? What if the API changes terms? What if the vendor degrades?"
- **What it catches:** Hidden coupling, missing fallback plans, over-reliance on external stability

### Composition

What happens when multiple features interact?

- **When to apply:** When planning multiple ARCHs or DDDs that share state, resources, or user flows
- **What to ask:** "When feature A and feature B both run, what happens? Race conditions? Conflicting invariants?"
- **What it catches:** Emergent behaviors, state conflicts, missing coordination in designs

### Stress-Scale (×100)

What breaks at 100× the stated scale?

- **When to apply:** ARCHs with stated performance or scale requirements
- **What to ask:** "At 100× current volume — users, data, requests, cost — what breaks first?"
- **What it catches:** Hard limits (throughput, latency budgets) and soft limits (operational burden, on-call load)

### Worst-Case User

Who abuses or misunderstands this feature?

- **When to apply:** DDDs for user-facing features, public APIs, or input-processing logic
- **What to ask:** "Who uses this wrong? Who abuses it? What's the most damaging thing a user could do?"
- **What it catches:** Missing input validation, unclear error paths, security-adjacent design gaps

## Default Application

For `/specflow-plan`, apply these before finalizing each ARCH and DDD:

| Technique | Default | Trigger for expansion |
|-----------|---------|----------------------|
| Premortem | Every ARCH | — |
| Dependency shock | ARCHs with external deps | Add cost-scaling for paid services |
| Composition | When multiple ARCHs interact | — |
| Stress-scale | When NFRs mention performance or scale | — |
| Worst-case user | DDDs for user-facing or API features | — |

If the user requests specific techniques by name, apply those. If the user says "go deep" or "be thorough", apply all five plus any from the full catalog in the artifact-review skill that are relevant to planning.
