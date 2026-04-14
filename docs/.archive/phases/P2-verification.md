# P2: Verification

## Goal

Build the validation layer that ensures artifact integrity, enforces phase gates, and provides a status dashboard. All programmatic — zero LLM tokens.

## Deliverables

### 1. Validation checks (Python CLI)

All validation logic lives in Python `lib/` modules (`lib/validation.py`, `lib/artifacts.py`), exposed via `specflow validate`. Shell scripts in `scripts/` are thin CI/CD wrappers (see D-16). The checks:

| Check | CLI flag | Implementation | What it validates |
|-------|---------|----------------|-------------------|
| Schema | `--type schema` | `lib/validation.py` | YAML frontmatter vs artifact schema: required fields, allowed enums, ID format regex |
| Links | `--type links` | `lib/artifacts.py` | Link integrity, orphan detection, V-model pairing (REQ/QT, ARCH/IT, DDD/UT) |
| Status | `--type status` | `lib/validation.py` | Status values vs allowed map, parent/child hierarchy consistency |
| IDs | `--type ids` | `lib/artifacts.py` | ID uniqueness, format compliance, dot-notation depth |
| Fingerprints | `--type fingerprints` | `lib/artifacts.py` | SHA256 recomputation, stale fingerprint detection |
| Gate | `--type gate --gate <name>` | `commands/validate.py` | Phase-gate checklist execution (automated items only) |
| Acceptance | `--type acceptance` | `lib/validation.py` | Every REQ has acceptance criteria |

Shell scripts in `scripts/` are thin CI/CD wrappers (3 lines each) that delegate to the CLI. See D-16.

### 2. Phase-gate checklists

Checklist definitions are authored in `src/specflow/templates/checklists/` (framework source) and copied to `.specflow/checklists/` during `specflow init`. P2 populates:

```
.specflow/checklists/
├── phase-gates/
│   ├── idle-to-discovering.yaml
│   ├── discovering-to-specifying.yaml
│   ├── specifying-to-planning.yaml
│   ├── planning-to-executing.yaml
│   ├── executing-to-verifying.yaml
│   └── verifying-to-complete.yaml
└── in-process/
    ├── requirement-writing.yaml
    ├── architecture-writing.yaml
    ├── design-writing.yaml
    └── story-writing.yaml
```

Each phase-gate checklist follows the standard format:

```yaml
id: CKL-GATE-002
name: "Requirements to Planning Gate"
phase_from: specifying
phase_to: planning
version: 1

items:
  - id: CKL-GATE-002-01
    check: "All REQ-* artifacts have status: approved"
    automated: true
    script: "uv run specflow validate --type status"
    severity: blocking

  - id: CKL-GATE-002-02
    check: "Every requirement has at least one acceptance criterion"
    automated: true
    script: "uv run specflow validate --type acceptance"
    severity: blocking

  - id: CKL-GATE-002-03
    check: "Non-functional requirements are quantified"
    automated: false
    llm_prompt: "Review each REQ tagged 'nonfunctional'. Flag qualitative terms without measurable thresholds."
    severity: warning
```

### 3. In-process checklists

Loaded during artifact generation to enforce level boundaries:

**`requirement-writing.yaml`:**
- No implementation details (technology, code, algorithms) present
- Every statement uses SHALL/SHOULD/MAY (normative language)
- Every requirement has acceptance criteria

**`architecture-writing.yaml`:**
- No user-facing behavior described (belongs in REQ)
- No algorithmic detail described (belongs in DDD)
- Every component defines its public interface
- Failure modes addressed

**`design-writing.yaml`:**
- Every function specifies preconditions
- Data structures defined
- Error handling at system boundaries

### 4. `specflow validate` command

The Python CLI subcommand that orchestrates all validation checks:

```bash
specflow validate                  # Run all checks
specflow validate --type schema    # Run only schema checks
specflow validate --type links     # Run only link checks
specflow validate --fix            # Auto-fix what's possible (rebuild _index.yaml, recompute fingerprints)
```

Output:

```
SpecFlow Validate
─────────────────
Schema:    ✓ All 12 artifacts pass schema validation
Links:     ✗ 1 broken link: DDD-003 references ARCH-005 (not found)
Status:    ✓ All statuses valid
IDs:       ✓ All IDs unique and well-formed
Fprints:   ⚠ 2 fingerprints stale: REQ-002, ARCH-001
─────────────────
Result: FAIL (1 blocking, 2 warnings)
```

### 5. `specflow status` command (enhanced)

Reads state.yaml, scans artifacts, produces dashboard:

```
SpecFlow Status
───────────────
Phase: specifying

Specs:   5 REQ | 0 ARCH | 0 DDD | 0 UT | 0 IT | 0 QT
Work:    0 STORY | 0 SPIKE | 1 DEC | 0 DEF

Status:  5 draft | 0 approved | 0 implemented | 0 verified
Links:   0 broken | 3 orphans (no downstream verification)

→ Run `specflow-plan` to create architecture and stories
```

Suggests next action based on current phase and artifact state.

### 6. Readiness assessment templates

```
.specflow/checklists/
└── readiness/
    ├── discovery-readiness.yaml     # Before generating REQs
    ├── planning-readiness.yaml      # Before creating architecture
    ├── architecture-readiness.yaml  # Before detailed design
    └── review-readiness.yaml        # Before reviewing artifacts
```

These are loaded by skill files during conversational commands. The agent evaluates readiness silently after each user exchange.

### 7. Phase-gate validation

Runs a specific phase-gate checklist and outputs results:

```bash
specflow validate --type gate --gate specifying-to-planning
```

Returns exit code 0 if all blocking items pass, 1 otherwise. Used by CI and by conversational commands before phase transitions.

## Acceptance Criteria

- [x] All 6 validation checks run independently and as a group via `specflow validate`
- [x] Schema validation catches missing required fields and invalid status values
- [x] Link validation detects broken links and orphaned artifacts
- [x] Status validation catches invalid transitions and parent/child inconsistencies
- [x] ID validation catches duplicates and format violations
- [x] Fingerprint validation detects modified artifacts with stale fingerprints
- [x] `specflow validate` on a well-formed project returns exit code 0
- [x] `specflow validate` on a project with issues returns exit code 1 with clear messages
- [x] Phase-gate checklists exist for all 6 transitions in `.specflow/checklists/phase-gates/`
- [x] In-process checklists exist for REQ, ARCH, DDD, and STORY writing in `.specflow/checklists/in-process/`
- [x] `specflow validate --type gate --gate <name>` runs any specific phase-gate transition
- [x] `specflow status` displays phase, artifact counts, link health, and suggested next action
- [x] All validation is programmatic — zero LLM tokens consumed

## Remediation (2026-04-11)

Review identified structural issues (see `P2-verification-review.md`). Resolved:
- Deleted dead modules: `lib/schema_validator.py`, `lib/fingerprint.py`
- Removed dead code: `_run_script()` and `CHECKS` dict from `commands/validate.py`
- Converted 8 shell scripts (~1000 lines) to thin 3-line CLI wrappers
- Added `--gate` flag to `specflow validate` CLI
- Recorded decisions D-16 (Python-primary) and D-17 (skills-first UI) in `docs/decisions.md`
- Updated architecture doc and all future phase docs (P3, P4, P7, P8) to reflect Python-primary approach

## Dependencies

- P0 (schemas, directory structure)
- P1 (manually authored artifacts to validate, `_index.yaml` files)

## Verification Gate

The "Self-Validation" Gate:
- We run our P2 `specflow validate` command against our P1 manually written specs. If P2 throws errors, we know either our P1 specs violated our own rules, or our P0 schemas/P2 validators are broken. We don't move on until `specflow validate` passes on its own codebase.
