# Challenge Engine

## Overview

The challenge engine operates in two modes:
- **Proactive**: During review, asks "What could go wrong? What's missing?"
- **Reactive**: After completion, extracts prevention patterns from past work

## Proactive Mode

Proactive challenges are checklist items with `mode: proactive`. They trigger during `specflow checklist-run --proactive` (and `specflow artifact-review --proactive`): when no blocking automated check failed, each item prints as `⚡ [severity] <check>` followed by a `Hint:` line carrying its `llm_prompt` (when it has one). The host agent evaluates the hint itself — there is no separate prompt builder and no external call.

### What proactive challenges do:
1. Enumerate every branching path for each artifact:
   - What if input is null/empty/malformed?
   - What if an external system is slow/down?
   - What if the user acts out of order?
2. Flag any path without a defined handling strategy
3. Record the findings in the artifact's `edge_cases_identified` frontmatter field (`specflow update <ID> --set edge_cases_identified=...`) — the agent writes it; the command only prints the hints

### Decision artifacts

When proactive challenges identify alternative approaches, a DEC (decision) artifact is created documenting:
- Context and constraints
- Options considered
- Chosen approach with rationale

## Reactive Mode (Learning)

Prevention patterns (PREVs) are seeded from three sources:

- **DEF closure** — `specflow update <DEF-ID> --status closed` seeds a PREV that inherits the DEF's tags and the tags of the REQs it `fails_to_meet` (the main source).
- **`specflow done`** — extracts patterns from implemented STORY bodies, tagged with the STORY's own tags.
- **`specflow verify --seed-prev`** — opt-in outcome feedback from a verify run.

### PREV-*.yaml format

```yaml
id: PREV-001
name: "Token Rotation Race Condition"
discovered_from: STORY-003
mode: reactive
pattern: "When implementing token rotation, check concurrent refresh handling"
applies_to:
  tags: [auth, security]
items:
  - id: PREV-001-01
    check: "Concurrent refresh token requests handled"
    severity: warning
    automated: false
    mode: reactive
```

### How learned patterns auto-load

When `specflow checklist-run` reviews an artifact:
1. Read every `PREV-*.yaml` from `.specflow/checklists/learned/`, skipping any with `retired: true`
2. If the artifact's tags intersect with the pattern's `applies_to.tags`
3. Include the pattern's items in the assembled checklist
4. Items are listed under "Agent-judged checks" with a `[reactive]` label

### Maintenance

A PREV with empty `applies_to.tags` is inert: it never matches an artifact (`brief` and `project-audit` report it). Repair it with `specflow patterns update <PREV-ID> --tags a,b` (replaces the list); retire it with `specflow patterns retire <PREV-ID>` (the file stays; listing and assembly skip it).

## Usage

```bash
# Run check with proactive challenges
specflow checklist-run --proactive STORY-001

# Close phase and extract patterns
specflow done

# Skip pattern extraction
specflow done --no-patterns
```
