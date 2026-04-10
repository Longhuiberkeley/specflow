# P5: Execution & Review

## Goal

Enable parallel subagent execution of stories, context-specific review that assembles unique criteria per artifact, and the challenge engine that catches problems proactively and learns from completed work.

## Deliverables

### 1. `specflow-go` — Parallel subagent orchestration

**Orchestration logic:**

1. Read all stories with `status: approved` from `_index.yaml`
2. Analyze dependencies between stories (links, shared artifacts)
3. Group stories into parallel waves (no dependencies within a wave)
4. For each wave:
   - Spawn subagent per story
   - Each subagent receives: the story file, relevant design doc, coding conventions, constitution rules
   - Each subagent does NOT receive: full requirements tree, unrelated stories, other subagent context
   - Subagent returns condensed result (~1-2K tokens) after completing work
5. After each wave: commit completed tasks, update artifact statuses
6. Handle locked artifacts: if subagent hits a lock, queue for next wave
7. Report progress to user between waves

**Context isolation per subagent:**

```
Subagent receives:
  - STORY-001a.md (full content)
  - DDD-001.md (linked detailed design)
  - AGENTS.md project rules
  - Relevant coding conventions
  - Constitution constraints

Subagent does NOT receive:
  - Other stories or their designs
  - Unrelated requirements
  - Full _index.yaml
  - Other subagent outputs
```

**Execution state tracking:**

```yaml
# .specflow/state.yaml (during execution)
current: executing
execution:
  wave: 2
  total_waves: 4
  completed: [STORY-001a, STORY-001b]
  in_progress: [STORY-001c, STORY-002a]
  queued: [STORY-001d, STORY-003a]
```

### 2. `specflow-check` — Context-specific review

**Review assembly pipeline:**

1. Identify artifact type and domain tags from frontmatter
2. Load applicable post-task checklist from `checklists/review/`
3. Load any shared checklists matching via `applies_to` tags/types
4. Load domain-specific review rules
5. Load learned patterns from `checklists/learned/` matching artifact tags (reactive mode)
6. Run automated items first (zero tokens) — schema, links, status, fingerprints
7. Run proactive challenge items — "What's missing? What branches unhandled?"
8. Run reactive challenge items — "Does this repeat a past mistake?"
9. Record results in `.specflow/checklist-log/` and update artifact `checklists_applied`
10. Discuss findings with user — blocking must resolve, warnings advisory

**What the LLM receives:**

```
Reviewing: REQ-001 "User Authentication"
Type: requirement | Tags: [security, auth]

THINK about:
  - Is this requirement testable without knowing implementation?
  - Are acceptance criteria unambiguous and measurable?
  - Are error cases covered?
  - [Domain-specific: OWASP auth considerations]

CHECK:
  - [CKL-GATE-002-01] All REQs have status: approved → PASS (automated)
  - [CKL-GATE-002-02] Non-functional requirements quantified → (LLM-judged)
  - [CKL-HTTP-001-04] Error responses defined → (from shared checklist)
  - [PREV-001] Concurrent refresh handled? → (from learned patterns)
```

**Review is never generic** — it's assembled from artifact type + domain + shared + learned, producing unique criteria each time.

### 3. Challenge engine — proactive mode

Before approval gates and during artifact generation, proactive challenges ask: "What could go wrong? What's missing?"

**Implemented as checklist items with `mode: proactive`:**

```yaml
items:
  - id: CKL-GATE-003-05
    check: "All error branches have defined handling"
    mode: proactive
    automated: false
    applies_at: [decomposition, review]
    llm_prompt: |
      For each requirement, enumerate every branching path:
      - What if input is null/empty/malformed?
      - What if external system is slow/down?
      - What if user acts out of order?
      Flag any path without a defined handling strategy.

  - id: CKL-GATE-003-06
    check: "Assumptions explicitly stated, not implicit"
    mode: proactive
    automated: false
    severity: warning
```

**Proactive outputs persist:**

| Output | Where it lives |
|--------|---------------|
| Edge cases found | Story frontmatter `edge_cases_identified: [...]` |
| Alternatives explored | `work/decisions/DEC-*.md` |
| Review findings | `.specflow/checklist-log/` + artifact frontmatter |

### 4. Challenge engine — reactive mode (learning)

After work completes, reactive challenges extract prevention patterns:

**`checklists/learned/` directory grows over time:**

```yaml
# checklists/learned/PREV-001.yaml
id: PREV-001
name: "Token Rotation Race Condition"
discovered_from: STORY-003
mode: reactive
pattern: "When implementing authentication with token rotation, always check concurrent refresh handling"
applies_to:
  tags: [auth, security]
items:
  - check: "Concurrent refresh token requests handled (race condition)"
    severity: warning
```

**`specflow-done` triggers pattern extraction:**
1. Review completed story for patterns worth remembering
2. If pattern found: create `checklists/learned/PREV-*.yaml`
3. Next time any artifact with matching tags is reviewed, the pattern auto-loads

### 5. `specflow-done` — Phase closure

1. Review all completed work in current phase
2. Extract prevention patterns into `checklists/learned/`
3. Update all artifact statuses as appropriate
4. Archive phase in `state.yaml` history
5. Tag git release if all verification complete
6. Suggest next phase with any outstanding flags or warnings

### 6. Checklist log (individual files)

One file per execution, timestamp-first naming for unique IDs:

```
.specflow/checklist-log/
├── 2026-03-20T14-30-00Z_CKL-GATE-002.yaml
├── 2026-03-22T10-00-00Z_CKL-HTTP-001.yaml
```

```yaml
# 2026-03-20T14-30-00Z_CKL-GATE-002.yaml
id: 2026-03-20T14-30-00Z_CKL-GATE-002
timestamp: 2026-03-20T14:30:00Z
checklist: CKL-GATE-002
trigger: phase-gate
artifacts_checked: [REQ-001, REQ-002, REQ-003]
results:
  - item: CKL-GATE-002-01
    result: passed
  - item: CKL-GATE-002-02
    result: failed
    detail: "REQ-003 uses 'fast' without quantified threshold"
overall: failed
blocking_failures: 1
```

### 7. Review checklists

```
checklists/
└── review/
    ├── requirement-review.yaml
    ├── architecture-review.yaml
    ├── detailed-design-review.yaml
    ├── story-review.yaml
    └── implementation-review.yaml
```

Each defines context-specific THINK and CHECK items for its artifact type.

### 8. Shared checklists with auto-matching

```
checklists/
└── shared/
    ├── http-client.yaml
    ├── database-access.yaml
    ├── authentication.yaml
    └── error-handling.yaml
```

Auto-matched by `applies_to` tags and types when reviewing or generating artifacts.

## Acceptance Criteria

- [ ] `specflow-go` spawns subagents per story wave with isolated context
- [ ] Subagents receive only their story + relevant design + conventions
- [ ] Stories are grouped into parallel waves respecting dependencies
- [ ] Locked artifacts cause subagent to queue for next wave, not fail
- [ ] Progress is reported between waves
- [ ] `specflow-check` assembles unique review criteria per artifact
- [ ] Review loads artifact type + domain tags + shared checklists + learned patterns
- [ ] Automated checks run before LLM-judged checks
- [ ] Checklist results are persisted to `.specflow/checklist-log/`
- [ ] Proactive challenges persist edge cases in story frontmatter
- [ ] Reactive mode extracts prevention patterns to `checklists/learned/`
- [ ] `specflow-done` triggers pattern extraction and phase archival
- [ ] Review is never generic — always assembled from context-specific sources

## Dependencies

- P3 (artifacts, stories, skill files)
- P4 (impact data provides review context, suspect flags inform review priorities)

## Verification Gate

The "Autonomous Execution" Gate:
- We use `specflow-go` to autonomously execute the stories for P6 (Compliance). If the subagent can read the isolated story, write the Python code, and pass the `specflow-check` review, the execution engine is fully operational.
