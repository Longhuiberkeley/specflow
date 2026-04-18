---
name: specflow-discover
description: Use when the user wants to discover, capture, or author new requirements. Triggers a progressive disclosure conversation to extract specifications and create REQ artifacts.
---

# SpecFlow Discover

Conduct a structured discovery conversation to capture requirements as REQ artifacts.

## Workflow

### Step 0: Initialize

1. Read `.specflow/state.yaml` to confirm the project phase. If `current` is `idle` or `discovering`, proceed. Otherwise, warn the user that discovery may conflict with the current phase.
2. Run `uv run specflow status` silently to see existing artifact counts.
3. If artifacts already exist, ask: "Do you want to add new requirements, or refine existing ones?"

### Step 1: Readiness Assessment (Silent, After Every Exchange)

After each user response, silently evaluate readiness dimensions:

| Dimension | Weight | How to assess |
|-----------|--------|---------------|
| Problem clarity | required | Can you state what problem this solves in one sentence? |
| User identification | required | Are the primary users or stakeholders identified? |
| Scope boundary | required | Is what's IN vs OUT of scope clear? |
| Success criteria | required | Are measurable success conditions stated? |
| Technical constraints | recommended | Are technology, platform, or integration constraints known? |
| Data model | recommended | Is the core data or domain model discussed? |
| Non-functional requirements | recommended | Are performance, security, or scalability needs mentioned? |

**Threshold:** All `required` dimensions satisfied + at least 2 of 3 `recommended`.

**If threshold met within 1 exchange:** Take the **lean path** (Step 2L).
**Otherwise:** Continue to the **full discovery** (Step 2F).

### Step 1.5: Standards Gap Check (Silent, Auto-Run)

1. After the initial readiness assessment, silently run `uv run specflow standards gaps`.
2. If the command returns uncovered standard clauses:
   - Present: "You have N uncovered standard clauses (e.g., ISO26262-3.7: Hazard analysis). Want me to scaffold REQs for them? (Recommended: Yes)"
   - Allow the user to accept all, pick specific clauses, or skip.
   - For each accepted clause, run `uv run specflow create --from-standard <clause-id>` to create a draft REQ pre-populated with the clause's title, description, and a `complies_with` link.
   - The user then adapts these draft REQs during the normal discovery flow.
3. If no uncovered clauses are found, proceed normally without mentioning standard gaps.

### Step 2L: Lean Path (Simple Changes)

For bounded changes like "add dark mode" or "fix the login redirect":

1. Generate a single REQ artifact with minimal metadata.
2. Generate a single STORY artifact linked to the REQ via `implements`.
3. Auto-approve both (set `status: approved`).
4. Skip to Step 5 (Artifact Creation).

### Step 2F: Full Discovery — Phase 1: Context-Free Questions

Ask domain-agnostic questions **one at a time**. Each answer refines the next question. Never batch questions.

Core questions (ask in order, skip if already answered):
1. "What problem are you trying to solve?"
2. "Who are the primary users?"
3. "What does success look like?"
4. "What's the timeline or hard deadline?"
5. "Are there hard constraints I should know about? (technology, compliance, budget)"

After each answer, update your readiness assessment silently.

### Step 3F: Full Discovery — Phase 2: Domain Deep-Dive

1. Classify the project type from Phase 1 answers. Categories:
   - `web-app` — Browser-based application
   - `cli-tool` — Command-line interface
   - `api-service` — Backend service / REST or gRPC API
   - `data-pipeline` — ETL, data processing, streaming
   - `library` — Reusable package / SDK
   - `embedded` — Firmware / hardware-adjacent
   - `mobile` — iOS / Android application

2. Read `references/domain-checklists/<project-type>.md` for the domain-specific question set.

3. Present questions from the domain checklist. These should offer **bounded choices with opinionated defaults**:
   - "For your use case (small team, read-heavy), SQLite is simplest, PostgreSQL handles growth best — which fits?"
   - Not: "What database do you want?"

4. Continue until domain checklist is exhausted or user signals readiness to proceed.

### Step 3F: Full Discovery — Phase 3: Cross-Cutting Concerns

1. Read `references/cross-cutting.md`.
2. Fire **only relevant** checklist items based on project type:
   - CLI tool → skip auth, UX, deployment complexity
   - Web app → skip hardware constraints
   - API service → include auth, rate limiting, API versioning
3. Cover applicable items from: error handling, security, observability, scalability, deployment.

### Step 4: Requirements Summary & Approval

1. Present a numbered summary of all discovered requirements to the user.
2. Ask: "Does this capture everything? Anything missing or incorrect?"
3. Iterate until user approves.

### Step 5: Artifact Creation

For each approved requirement, create a REQ artifact:

```
uv run specflow create \
  --type requirement \
  --title "<requirement title>" \
  --priority "<high|medium|low>" \
  --tags "<comma-separated>" \
  --body "<markdown with acceptance criteria>"
```

**Body format for each REQ:**
```markdown
<One-line summary using normative language>

## Acceptance Criteria

1. Given <context>, when <action>, then <expected result>
2. Given <context>, when <action>, then <expected result>
3. Given <context>, when <action>, then <expected result>
```

Every REQ must have **at least 2 acceptance criteria** (happy path + at least one error/edge case).

After creating all REQs, run validation:
```
uv run specflow artifact-lint
```

Report results to user.

### Step 5.5: Human-Review Summary

Before transitioning phases, present a structured summary so the user can validate the discovery outcome:

```
## Summary for Human Review

### Key Decisions Made
- Path taken: lean vs. full discovery — and why
- Scope boundaries: what was explicitly declared IN / OUT of scope
- Accepted constraints: hard constraints the user confirmed (tech, timeline, compliance)

### Assumptions That Need Validation
- Stakeholders / primary users identified — risk if wrong: requirements target the wrong audience
- Success criteria interpretation — risk if wrong: acceptance criteria miss the real goal
- Any domain-checklist answer taken as a default — risk if wrong: downstream ARCH/DDD is built on a bad premise

### Please Review
- For each REQ: do the acceptance criteria cover happy path + at least one error/edge case?
- Any cross-cutting concern you skipped (auth, observability, scalability) that should be a REQ?
- Any requirement that feels like HOW (implementation) rather than WHAT (behavior)?
```

Wait for user acknowledgement before proceeding to phase transition.

### Step 6: Phase Transition

If this was the first discovery and the project was in `idle` state, update state:
- Edit `.specflow/state.yaml`: set `current: specifying`, add history entry.

**Exit message:** Report the REQ (and STORY, for lean path) IDs created, and recommend the next skill — `/specflow-plan` for the full path, `/specflow-execute` for the lean path.

## Rules

- Requirements answer **"WHAT must the system do?"** — never HOW.
- Use normative language: "The system **shall**..." (mandatory), "The system **should**..." (recommended), "The system **may**..." (optional).
- No implementation details, technology choices, or architectural decisions in REQs.
- Each REQ must have acceptance criteria.
- One question at a time — never batch.
- **Escape Hatch Rule**: If the user signals they've provided enough context (e.g., 'that's enough', 'move on', 'skip'), immediately proceed to artifact generation with what you have.
- **Question Cap**: Limit the discovery conversation to 15-20 questions total. If more are needed, suggest the user may want to refine requirements first (which likely means the discover->plan pipeline needs restructuring).
- Every skill that offers the user a choice must include "(Recommended)" labels on the suggested default.
- When in doubt about level boundaries, read `references/level-boundaries.md`.

## References

- `references/readiness-assessment.md` — Full readiness dimensions and evaluation guidance.
- `references/level-boundaries.md` — REQ vs ARCH vs DDD boundary rules with examples.
- `references/normative-language.md` — Proper requirement phrasing (SHALL/SHOULD/MAY).
- `references/domain-checklists/<type>.md` — Per-domain question sets for Phase 2.
- `references/cross-cutting.md` — Cross-cutting concern checklists for Phase 3.
