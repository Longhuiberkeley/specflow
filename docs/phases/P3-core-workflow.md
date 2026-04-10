# P3: Core Workflow

## Goal

Enable the full conversational lifecycle: discover requirements through AI-driven conversation, plan architecture and stories, create and manage artifacts. The LLM agent conducts structured conversations guided by skill files, while shell scripts handle all deterministic operations.

## Deliverables

### 1. SKILL.md files for conversational commands

```
src/
├── templates/
│   └── skills/
│       ├── discover/
│       │   ├── SKILL.md          # Discovery workflow (specflow-new)
│       │   ├── references/       # Supporting docs loaded on demand
│       │   │   ├── readiness-assessment.md
│       │   │   ├── domain-checklists/   # Per-domain question sets
│       │   │   │   ├── web-app.md
│       │   │   │   ├── cli-tool.md
│       │   │   │   ├── api-service.md
│       │   │   │   ├── data-pipeline.md
│       │   │   │   └── library.md
│       │   │   └── cross-cutting.md     # Error handling, security, etc.
│       │   └── scripts/
│       │       └── create-artifact.sh
│       ├── plan/
│       │   ├── SKILL.md          # Planning workflow (specflow-plan)
│       │   ├── references/
│       │   │   ├── spidr-decomposition.md
│       │   │   └── story-writing.md
│       │   └── scripts/
│       │       └── create-story.sh
│       ├── execute/
│       │   ├── SKILL.md          # Execution workflow (specflow-go) - stub for P4
│       │   └── references/
│       ├── check/
│       │   ├── SKILL.md          # Review workflow (specflow-check) - stub for P4
│       │   └── references/
│       └── done/
│           ├── SKILL.md          # Closure workflow (specflow-done) - stub for P4
│           └── references/
```

### 2. `specflow-new` — Discovery conversation

**3-phase progressive disclosure:**

**Phase 1 — Context-free discovery:**
- Agent asks domain-agnostic questions one at a time
- Questions: What problem? Who are users? What does success look like? Timeline? Hard constraints?
- Each answer refines the next question
- Questions are NOT batched — one at a time per LLMREI research findings

**Phase 2 — Domain-specific deep-dive:**
- Agent classifies project type from Phase 1 answers
- Loads corresponding domain checklist from `references/domain-checklists/`
- Presents bounded-choice questions with opinionated defaults
- "For your use case (small team, read-heavy), SQLite is simplest, PostgreSQL handles growth best — which fits?"

**Phase 3 — Cross-cutting concerns:**
- Fires only relevant checklist items (CLI tool skips auth checklist, data pipeline skips UX questions)
- Covers: error handling, security, observability, scalability, deployment
- After completion, generates requirements summary for user approval

**Readiness assessment:**
After each user response, agent silently evaluates readiness:

```yaml
dimensions:
  - dimension: "Problem clarity"
    weight: required
  - dimension: "User identification"
    weight: required
  - dimension: "Scope boundary"
    weight: required
  - dimension: "Success criteria"
    weight: required
  - dimension: "Technical constraints"
    weight: recommended
  - dimension: "Data model"
    weight: recommended
  - dimension: "Non-functional requirements"
    weight: recommended
threshold:
  required: all
  recommended: 2_of_3
```

If all required + threshold met within first exchange -> lean artifacts (REQ + STORY, auto-approved, minimal metadata). Otherwise -> full discovery -> full artifact chain.

**Output:** Generates `REQ-*.md` files in `_specflow/specs/requirements/`, updates `_index.yaml`.

### 3. `specflow-plan` — Architecture and story breakdown

**Conversation flow:**
1. Agent reads all approved requirements from `_index.yaml`
2. Discusses architecture approach with user
3. Generates ARCH artifacts with component interfaces, dependencies, data flow
4. Decomposes into stories using SPIDR framework (Spike, Path, Interface, Data, Rules)
5. Stories use vertical slicing — each delivers testable user value through full stack
6. Each story gets minimum 3 acceptance criteria (happy path + 2 error cases)
7. Generates DDD artifacts for components needing algorithmic detail
8. User reviews, iterates, approves

**Output:** Populates `specs/architecture/`, `specs/detailed-design/`, `work/stories/`, `work/spikes/` with linked artifacts.

### 4. Artifact CRUD operations

Shell scripts for programmatic artifact management:

```
scripts/
├── create-artifact.sh       # Create artifact, assign next ID, update _index.yaml
├── update-artifact.sh       # Update frontmatter fields, bump version
├── update-index.sh          # Rebuild _index.yaml from directory contents
└── compute-fingerprint.sh   # SHA256 of title + body (excludes frontmatter)
```

`create-artifact.sh`:
- Reads artifact type from argument
- Looks up schema from `.specflow/schema/<type>.yaml`
- Gets next ID from `_index.yaml` (`next_id` field, increments)
- Validates required fields are present
- Computes initial fingerprint
- Writes file and updates `_index.yaml`
- Returns artifact ID

### 5. `_index.yaml` management

The `_index.yaml` in each artifact directory serves as the local registry:

```yaml
artifacts:
  REQ-001:
    title: "User Authentication"
    status: approved
    tags: [security, auth]
    fingerprint: "sha256:abc..."
    children: []
  REQ-001.1:
    title: "OAuth 2.0 Flow"
    parent: REQ-001
    status: approved
    tags: [security, auth]
    fingerprint: "sha256:def..."
    children: []
next_id: 2
```

The index is always rebuilt from filesystem by `update-index.sh` — it's a cache, not a source of truth. If it's deleted, `specflow-validate` detects the mismatch and rebuilds it.

### 6. Link management

When creating artifacts, the agent or user specifies links. Links are stored in frontmatter. The framework:

- Validates that link targets exist (`validate-links.sh`)
- Validates that link roles are allowed for the source artifact type (from schema)
- Maintains bidirectional awareness (if REQ-001 links to ARCH-001 with `refined_by`, the system knows ARCH-001 is downstream of REQ-001)

### 7. Status transitions

Status changes are validated against the schema's `allowed_status` map. Invalid transitions are rejected by `update-artifact.sh`. The state machine for the overall project is tracked in `.specflow/state.yaml`:

```yaml
current: specifying
history:
  - phase: discovering
    entered: 2026-03-15
    exited: 2026-03-16
  - phase: specifying
    entered: 2026-03-16
```

### 8. Decision records

`_specflow/work/decisions/` captures the "why" behind every choice:

```yaml
---
id: DEC-001
type: design-choice        # design-choice | course-correction | scope-change | priority-shift
title: "Chose SQLite over PostgreSQL"
rationale: "Single-user CLI, no concurrent access needed"
alternatives_considered: ["PostgreSQL", "DuckDB"]
links:
  - target: ARCH-002
    role: guided_by
created: 2026-03-15
---
```

### 9. Defect Tracking

`_specflow/work/defects/` captures production issues or bugs that need to be resolved:

```yaml
---
id: DEF-AUTH-b8c1
title: "Token refresh fails under concurrent requests"
status: open          # open -> investigating -> fixing -> verified -> closed
severity: major
priority: high
links:
  - target: REQ-AUTH-a7b9
    role: fails_to_meet
  - target: UT-003
    role: exposed_by
created: 2026-03-22
---
```
Defects link to the V-model to show what is broken (`fails_to_meet`). They undergo their own lifecycle until closed by a STORY or PR.

## Acceptance Criteria

- [ ] `specflow-new "My App"` starts a discovery conversation
- [ ] Agent asks questions one at a time, adapts based on answers
- [ ] Project type classification triggers domain-specific checklist
- [ ] Simple changes ("add dark mode") produce lean artifacts within 1-2 exchanges
- [ ] Complex features produce full REQ artifacts with acceptance criteria
- [ ] Requirements are generated with hash-based Draft IDs (e.g., `REQ-AUTH-a7b9`) to avoid collisions
- [ ] `_index.yaml` is updated after each artifact creation
- [ ] `specflow-plan` produces ARCH, DDD, and STORY artifacts linked to REQs
- [ ] Stories have acceptance criteria (minimum 3 per story)
- [ ] Status transitions follow schema rules (draft -> approved -> implemented -> verified)
- [ ] Defect artifacts can be created and transitioned through their lifecycle
- [ ] Invalid status transitions are rejected with clear error message
- [ ] `specflow-status` shows current phase and artifact counts
- [ ] Fingerprints are computed on artifact creation
- [ ] Links between artifacts are stored in frontmatter and validated for existence

## Dependencies

- P0, P1, P2 (Schemas, manually authored artifacts, and validation engine must exist)

## Verification Gate

The "Self-Planning" Gate:
- We invoke the newly built `specflow-plan` AI skill and point it at the `_specflow/specs/` folder we populated in P1 and validated in P2. If the AI successfully reads the specs and generates valid `STORY-*` and `DDD-*` artifacts for P4-P8, we know the AI context loading and generation work.
