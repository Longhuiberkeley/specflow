# Stakeholder Lens Catalog (Wing B)

8 adversarial lenses that probe stakeholder concerns, risk perception, and real-world usage.

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

### 1. Devil's advocate

Assume the project is fundamentally flawed, mistaken, misguided, or unnecessary. Find evidence that requirements are solving the wrong problem, designs are over-engineered, or stories are implementing features nobody needs.

### 2. Premortem

Fast-forward six months: the project's implementation failed. What caused it? Enumerate plausible failure modes and their precursors. Focus on: technical debt accumulation, scope creep, integration failures, and organizational drift.

### 3. Red team / blue team

Attacker vs. defender. Red identifies exploits, security gaps, and misuse vectors. Blue identifies defenses, mitigations, and monitoring. Both perspectives persist as findings. Especially valuable on security-adjacent REQs and trust boundaries.

### 4. Worst-case user

Who abuses this feature? Who misunderstands it? Who uses it in a way we didn't anticipate? Think about: confused users, malicious actors, power users hitting edge cases, and users from different cultural/technical backgrounds.

### 5. Regulator / auditor

What would a compliance auditor flag? What questions would they ask for which there is no documented answer? Check for: missing rationale, incomplete traceability, undocumented decisions, and gaps in the audit trail.

### 6. Outside view (base-rate reasoning)

Ignore project-specific details. How often do projects of this class succeed? What's the reference-class failure rate? Does this project's plan reflect that? Look for: optimism bias, planning fallacy, and survivorship bias in the project's assumptions.

### 7. Competitor framing

How would a competitor solve this? What would they do differently? Often surfaces trade-offs the current design doesn't acknowledge. Consider: alternative architectures, simpler solutions, different prioritization, and missed opportunities.

### 8. Cost-scaling

At 10x usage, is cost linear? Sublinear? Superlinear? Where are the cost nonlinearities? Check for: per-request costs, storage growth patterns, compute scaling characteristics, and operational costs that grow with team size.
