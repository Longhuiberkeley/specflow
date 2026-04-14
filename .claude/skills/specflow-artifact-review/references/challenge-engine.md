# Challenge Engine

## Overview

The challenge engine operates in two modes:
- **Proactive**: During review, asks "What could go wrong? What's missing?"
- **Reactive**: After completion, extracts prevention patterns from past work

## Proactive Mode

Proactive challenges are checklist items with `mode: proactive`. They trigger during `specflow checklist-run --proactive`.

### What proactive challenges do:
1. Enumerate every branching path for each artifact:
   - What if input is null/empty/malformed?
   - What if an external system is slow/down?
   - What if the user acts out of order?
2. Flag any path without a defined handling strategy
3. Persist findings in the artifact's `edge_cases_identified` frontmatter field

### Decision artifacts

When proactive challenges identify alternative approaches, a DEC (decision) artifact is created documenting:
- Context and constraints
- Options considered
- Chosen approach with rationale

## Reactive Mode (Learning)

After work completes, `specflow done` extracts prevention patterns.

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
1. Read all `PREV-*.yaml` from `.specflow/checklists/learned/`
2. If the artifact's tags intersect with the pattern's `applies_to.tags`
3. Include the pattern's items in the assembled checklist
4. Items appear in the "reactive" section of the review

## Usage

```bash
# Run check with proactive challenges
uv run specflow checklist-run --proactive STORY-001

# Close phase and extract patterns
uv run specflow done

# Skip pattern extraction
uv run specflow done --no-patterns
```
