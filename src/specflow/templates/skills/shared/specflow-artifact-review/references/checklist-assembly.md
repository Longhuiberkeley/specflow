# Checklist Assembly

**Assembly is owned by `specflow checklist-run`** — the command assembles the full set (artifact-type, shared/tag-matched, phase-gate, learned, and matching best-practice sources), deduplicates, sorts automated-first, runs, persists to `.specflow/checklist-log/`, and updates `checklists_applied`. This file documents what it composes from and how to author items — it does not restate the algorithm.

- `specflow checklist-run <ID>` — assembled checklist for one artifact; `--all` for every artifact; `--proactive` adds challenge items; `--dedup` runs the tier-1 + tier-2 duplicate-detection pipeline (review the generated candidates — similarity is not automatic duplication).
- Sources live in `.specflow/checklists/`: `in-process/` (per artifact type), `review/` (per artifact type), `shared/` (matched via `applies_to` tags/types; none ship by default — bring your own), `phase-gates/` (matched by filename `<from>-to-<to>.yaml`, loaded with `--gate` or before a transition; `phase_from`/`phase_to` in the file are metadata only), `domain/` (the `domain` set in `config.yaml`), `learned/` (prevention patterns from past defects). Other directories are not read.

## Item Modes

- **standard** (default) — normal review items
- **proactive** — edge-case discovery ("what could go wrong?"); included with `--proactive`
- **reactive** — prevention patterns learned from past work; auto-load by tag match

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

  - id: CKL-REQ-001-03
    check: "Has acceptance criteria section"
    automated: true
    script: "specflow artifact-lint --type acceptance"
    severity: blocking
```
