---
name: specflow-plan
description: Use when requirements are approved and the user wants to break them down into architecture, design, and stories. Triggers architecture discussion and artifact population.
---

# SpecFlow Plan

Break down approved requirements into architecture, detailed design, and user stories.

## Workflow

### Step 1: Phase Gate Check

1. Read all REQ artifacts from `_specflow/specs/requirements/`.
2. Verify all REQs have `status: approved`. If any are still `draft`, tell the user which ones need approval before planning can proceed.
3. Optionally run the phase gate: `uv run specflow artifact-lint --type gate --gate specifying-to-planning`.
4. If gate fails, report blockers and stop.

### Step 2: Read & Understand Requirements

1. Read every approved REQ artifact in full — body and acceptance criteria, not just titles.
2. Identify:
   - Core domain concepts and entities
   - Cross-cutting concerns (auth, logging, error handling)
   - External system integrations
   - Non-functional constraints (performance, scale, compliance)
3. Summarize your understanding back to the user: "Here's what I see as the system scope. Correct?"

### Step 3: Architecture Proposal

Discuss component structure with the user. For each component:

1. **Name and responsibility** — What does this component own?
2. **Public interface** — What does it expose to other components?
3. **Dependencies** — What does it consume from other components or external systems?
4. **Data flow** — How does data enter and leave this component?

Present the architecture as a discussion, not a fait accompli. Ask:
- "Does this decomposition make sense for your team structure?"
- "Are there existing components or services that must be preserved?"
- "Any components that should be isolated for independent deployment?"

For each agreed component, create an ARCH artifact:

```
uv run specflow create \
  --type architecture \
  --title "<component name>" \
  --priority "<high|medium|low>" \
  --tags "<comma-separated>" \
  --links "[{\"target\": \"REQ-001\", \"role\": \"derives_from\"}]" \
  --body "<architecture description with interfaces and data flow>"
```

### Step 4: Detailed Design (Where Needed)

Not every ARCH component needs a DDD. Create DDD artifacts only for components that need algorithmic detail — complex logic, state machines, data transformations, or protocol handling.

For each DDD:
1. Specify function signatures with input/output types
2. Define data structures and their relationships
3. Describe error handling at system boundaries
4. Note preconditions and invariants

```
uv run specflow create \
  --type detailed-design \
  --title "<design name>" \
  --links "[{\"target\": \"ARCH-001\", \"role\": \"refined_by\"}]" \
  --body "<detailed design with function signatures, data structures, error handling>"
```

### Step 5: Story Breakdown (SPIDR)

Read `references/spidr-decomposition.md` for the full SPIDR framework. Decompose requirements into stories using the five sources:

1. **Spike** — Research stories for uncertain areas
2. **Path** — End-to-end user journeys through the system
3. **Interface** — Stories for each external boundary
4. **Data** — Stories for each core entity and its lifecycle
5. **Rules** — Stories for business logic and constraints

**Story writing rules:**
- Each story delivers **testable user value** through the full stack (vertical slice).
- Each story has **minimum 3 acceptance criteria**: happy path + 2 error/edge cases.
- Stories are independent and can be implemented in any order within a wave.
- Read `references/story-writing.md` for the story template.
- **Use all applicable link roles** on each STORY: `implements` → the REQ it realizes, `guided_by` → each ARCH it touches, `specified_by` → any DDD that constrains its internals. Omit a role only if there is no corresponding artifact.

For each story:

```
uv run specflow create \
  --type story \
  --title "<story title>" \
  --priority "<high|medium|low>" \
  --links "[{\"target\": \"REQ-001\", \"role\": \"implements\"}, {\"target\": \"ARCH-001\", \"role\": \"guided_by\"}]" \
  --body "<story description with acceptance criteria>"
```

### Step 6: Validation

Run full validation:
```
uv run specflow artifact-lint
```

Report any issues. Fix broken links or schema violations.

### Step 7: User Review

Present the complete artifact set to the user:
- X ARCH artifacts (architecture)
- Y DDD artifacts (detailed design)
- Z STORY artifacts (stories)
- W SPIKE artifacts (research)

Ask user to review and approve. Iterate as needed.

### Step 7.5: Human-Review Summary

Before flipping the phase, present a structured summary so the user can catch any silent decisions baked in during planning:

```
## Summary for Human Review

### Key Decisions Made
- Component decomposition rationale (why these boundaries and not others)
- Which ARCHs got DDDs vs. which were left interface-only, and why
- SPIDR dimensions that drove the story split (Spike / Path / Interface / Data / Rules)

### Assumptions That Need Validation
- Each ARCH's deployment/isolation assumption — risk if wrong: coupling surprises at integration time
- Story sizing assumptions (each story fits one sprint / wave) — risk if wrong: waves stall
- Non-functional targets carried forward from REQs (latency, scale, cost) — risk if wrong: the plan is solving the wrong problem

### Please Review
- Is every approved REQ covered by at least one STORY? (flag any REQ with no `implements` link)
- Any STORY that should be a SPIKE because the answer is genuinely unknown?
- Any ARCH with a public interface that has no corresponding DDD and probably needs one?
```

Wait for user acknowledgement before the phase transition.

### Step 8: Phase Transition

Update `.specflow/state.yaml`: set `current: planning`, add history entry.

**Exit message:** Report artifact counts (ARCH / DDD / STORY / SPIKE) and recommend the next skill — `/specflow-execute`.

## Rules

- ARCH answers "HOW is the system structured?" — defines interfaces between components, not user-facing behavior.
- DDD answers "HOW does each part work internally?" — implementation-level detail for developers.
- STORY references specs, doesn't replace them. Use link roles: `implements` (→ REQ), `guided_by` (→ ARCH), `specified_by` (→ DDD).
- Respect level boundaries — no user-facing behavior in ARCH, no code-level detail in REQ.
- Stories must be vertically sliced — each delivers end-to-end value.
- When unsure about link roles, read `references/link-roles.md`.
- When unsure about level boundaries, read `references/level-boundaries.md`.

## References

- `references/spidr-decomposition.md` — SPIDR story decomposition framework.
- `references/story-writing.md` — Story template and acceptance criteria patterns.
- `references/link-roles.md` — Complete link role vocabulary with usage examples.
- `references/level-boundaries.md` — REQ vs ARCH vs DDD boundary rules with examples.
