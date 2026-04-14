# Checklist Assembly

## Assembly Algorithm

When reviewing artifacts, checklists are assembled from four sources in priority order:

### 1. Artifact Type Checklists (In-Process)

Load from `.specflow/checklists/in-process/` based on the artifact type being reviewed:

| Artifact type | Checklist file |
|---------------|---------------|
| requirement | `requirement-writing.yaml` |
| architecture | `architecture-writing.yaml` |
| detailed-design | `design-writing.yaml` |
| story | `story-writing.yaml` |

These enforce level boundaries and writing quality for each artifact type.

### 2. Shared Checklists (Tag-Matched)

Load from `.specflow/checklists/shared/`. Each shared checklist declares `applies_to` with `tags` and `types`:

```yaml
id: CKL-HTTP-001
name: "HTTP Client Requirements"
applies_to:
  tags: [http, api-client, web-scraping]
  types: [story, detailed-design]
```

A checklist matches if the artifact has ANY overlapping tags AND the artifact type is in the `types` list.

### 3. Phase-Gate Checklists (If Transition Pending)

Load from `.specflow/checklists/phase-gates/`. Only loaded if:
- The review is happening before a phase transition
- The user explicitly requests a gate check

Gate checklists have `phase_from` and `phase_to` fields that match `.specflow/state.yaml`.

### 4. Learned Checklists (Prevention Patterns)

Load from `.specflow/checklists/learned/`. These are auto-generated from past defects and corrections. They are always included as `info` severity unless the pattern matches exactly.

## Assembly Order

1. Start with artifact type checklist (blocking items)
2. Add matching shared checklists (warning items by default)
3. Add phase-gate checklist if applicable (blocking items)
4. Add learned checklists (info items by default)
5. Deduplicate overlapping items (keep the higher severity)

## Running Order

```
For each artifact being reviewed:
  1. Load all applicable checklists
  2. Run automated items first (zero tokens)
  3. If all automated items pass, run LLM-judged items
  4. Collect results, organize by severity
```

## Checklist File Format

```yaml
id: CKL-REQ-001
name: "Requirement Writing Constraints"
category: in-process
version: 1

items:
  - id: CKL-REQ-001-01
    check: "No implementation details present"
    automated: false
    llm_prompt: "Scan the requirement body for technology names, code snippets, or algorithmic detail. These belong in ARCH or DDD."
    severity: blocking

  - id: CKL-REQ-001-02
    check: "Uses normative language (SHALL/SHOULD/MAY)"
    automated: false
    llm_prompt: "Check for informal phrases like 'needs to', 'has to', 'should be able to'. These should use RFC 2119 keywords."
    severity: warning

  - id: CKL-REQ-001-03
    check: "Has acceptance criteria section"
    automated: true
    script: "uv run specflow artifact-lint --type acceptance"
    severity: blocking
```
