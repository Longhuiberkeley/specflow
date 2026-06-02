---
name: specflow-plan
description: REQUIRED after discover when REQs are approved. Breaks approved requirements into architecture (ARCH), detailed design (DDD), and stories (STORY). Triggers when the user says "design the architecture," "plan the implementation," "break this down," or when REQs are approved and the user is ready to move forward. This is step 2 of the core lifecycle — use it BEFORE any implementation begins. NOT for: quick bug fixes (use specflow-execute with lean path), research tasks, or infrastructure setup.
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full LLM analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Plan

Break down approved requirements into architecture, detailed design, and user stories.

## Workflow

### Step 1: Phase Gate Check

1. Read all REQ artifacts from `_specflow/specs/requirements/`.
2. Verify all REQs have `status: approved`. If any are still `draft`, tell the user which ones need approval before planning can proceed.
3. Run the phase gate: `uv run specflow artifact-lint --type gate --gate specifying-to-planning`. Run it by default — only skip if the user explicitly declines.
4. If gate fails, report blockers and stop.

### Step 2: Read & Understand Requirements

1. Read every approved REQ artifact in full — body and acceptance criteria, not just titles.
2. **Read domain context** from `.specflow/config.yaml`:
   - Read `project.domain` (set during discover via `specflow domain set`).
   - Read `project.domain_tags` list.
   - If domain is set: prefix the summary with "This is a \<domain\> project with focus on \<tags\>. Domain-specific decomposition considerations apply."
3. **Load decision artifacts** created during discovery. Read any DEC artifacts from `_specflow/work/decisions/` that were produced by the discover skill's challenge step. These contain assumptions, risks, and dropped requirements that inform architectural choices.
4. Identify:
   - Core domain concepts and entities
   - Cross-cutting concerns (auth, logging, error handling)
   - External system integrations
   - Non-functional constraints (performance, scale, compliance)
5. Summarize your understanding back to the user: "Here's what I see as the system scope. Correct?"

### Step 2.5: Generate Planning Best Practices

Before starting architecture work, generate phase-level best practices for the planning phases. These are domain-specific and complement any installed standards packs:

```
uv run specflow handbook generate plan-arc
uv run specflow handbook generate plan-ddd
uv run specflow handbook generate plan-story
```

Read the generated BPs with `uv run specflow handbook show plan-arc`. 

**Proactive Enforcement Loop:** Do not just passively read the BPs or thinking techniques. You must actively audit your own output against them.
1. Draft your architecture/design internally.
2. Run a self-audit against the generated BPs and `thinking-techniques.md`.
3. If your draft violates a BP (e.g., missed a security boundary, failed a coupling check), revise it *before* presenting it to the user.
4. When presenting to the user, briefly explain *how* the BPs and techniques shaped your proposal (e.g., *"Following the domain BP to separate data from rules, I split X and Y. I also ran a premortem check and added Z as a fallback."*). This shows your work and guides the user toward better architectural decisions.

If no API key is configured, this step is skipped gracefully.

### Step 2.5: Parallel Architecture Candidate Generation (Optional, for complex systems)

For systems with 3+ REQs, multiple external integrations, or cross-cutting concerns spanning security/performance/compliance, generate 2-3 alternative architecture decompositions before committing to one. This prevents single-approach myopia.

**Trigger conditions** (any one of):
- 5+ approved REQs in scope
- REQs span 2+ domains (e.g., web + data pipeline + auth)
- Architecture will have 4+ components
- User explicitly asks for alternatives or says "what are my options?"

**Pattern** (if your platform supports spawning subagents):
1. Prepare a brief with: all approved REQ summaries, domain context, external system constraints, and NFRs.
2. Spawn 2-3 subagents with different decomposition seeds:
   - **Seed A (domain-driven):** Decompose by business domain / bounded context
   - **Seed B (technical-layers):** Decompose by technical layer (API → Service → Data)
   - **Seed C (risk-first):** Decompose by what's most likely to fail — isolate risky components
3. Each subagent returns: component list with responsibilities, interfaces between components, rationale for the decomposition.
4. The parent agent presents the 2-3 alternatives to the user as a comparison, highlighting trade-offs (coupling, deployability, team fit). The user picks one; the parent proceeds with detailed ARCH creation.

**Fallback (no subagent support):** Generate alternatives sequentially — draft Seed A, then deliberately re-think from Seed B's perspective, then Seed C. Present the same comparison.

**Subagent prompt template:**
> "You are a software architect using a [SEED] decomposition strategy. Design an architecture for [system summary]. Approved REQs: [summaries]. Constraints: [NFRs, external systems, domain]. Return: component list with responsibilities, interface map, rationale for this decomposition vs alternatives."

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

Not every ARCH component needs a DDD. **Read `references/ddd-selection.md`** for the 6-question decision checklist to determine which ARCHs need DDD artifacts. Create DDD artifacts only for components that answer YES to at least one question — complex logic, state machines, data transformations, protocol handling, concurrent access, or error recovery.

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

### Step 4.5: Stress-Test Architecture

Before finalizing ARCHs and DDDs, apply planning-stage thinking techniques from `references/thinking-techniques.md`:

| Technique | When to apply | What it catches |
|-----------|--------------|-----------------|
| Premortem | Every ARCH | Sound designs that fail in practice |
| Dependency shock | ARCHs with external deps | Hidden coupling, missing fallbacks |
| Composition | When ARCHs share state or resources | Emergent conflicts between features |
| Stress-scale (×100) | When NFRs mention performance | Hard and soft scaling limits |
| Worst-case user | DDDs for user-facing or API features | Missing validation, security gaps |

For each ARCH, briefly: "6 months from now this failed — what went wrong? Any dependencies that could vanish? What breaks at 100× scale?"

Present concerns and let the user revise before creating artifacts.

If the user requested specific techniques or said "go deep", expand the selection accordingly.

After applying thinking techniques, record which techniques were applied to each artifact — even if they passed cleanly:

```
uv run specflow update <ARCH-ID> --thinking-techniques <technique1,technique2>
uv run specflow update <DDD-ID> --thinking-techniques <technique1,technique2>
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

- **Gate severity:**
  - `blocking` → Stop. Report the failure. Ask the user to fix before proceeding.
  - `warning` → Present. Ask whether to proceed. Do not proceed silently.
  - `info` → Note for awareness. Proceed.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a `blocking` item, articulate: "Proceeding past [specific blocking item]. Risk: [what could go wrong]. Noted."
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
- `references/thinking-techniques.md` — Planning-stage adversarial thinking techniques (points to shared catalog at `../specflow-references/references/adversarial-lenses.md`).
