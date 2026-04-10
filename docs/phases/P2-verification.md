# P2: Verification

## Goal

Build the validation layer that ensures artifact integrity, enforces phase gates, and provides a status dashboard. All programmatic — zero LLM tokens.

## Deliverables

### 1. Validation shell scripts

```
scripts/
├── validate.sh              # Master orchestrator: runs all checks
├── validate-schema.sh       # YAML frontmatter vs artifact schema
├── validate-links.sh        # Link integrity + orphan detection
├── validate-status.sh       # Status consistency + transition rules
├── validate-ids.sh          # ID uniqueness + format compliance
├── validate-fingerprints.sh # Content fingerprint freshness
├── validate-gate.sh         # Run a specific phase-gate checklist
└── check-acceptance-criteria.sh  # Every REQ has acceptance criteria
```

**`validate-schema.sh`:**
- Reads artifact file's YAML frontmatter
- Loads corresponding `.specflow/schema/<type>.yaml`
- Checks all required fields present
- Checks field values against allowed enums (status, link roles)
- Checks ID format matches `id_format` regex
- Reports: blocking (missing required field), warning (unknown field), info

**`validate-links.sh`:**
- Walks every artifact's `links` array
- Verifies each `target` resolves to an existing file
- Detects orphans: artifacts with no incoming or outgoing links
- Detects broken V-model pairing: REQ without QT, ARCH without IT, DDD without UT
- Reports: blocking (broken link), warning (orphan), info (missing verification pair)

**`validate-status.sh`:**
- Checks status values against schema's `allowed_status` map
- For hierarchical artifacts: parent can't be `verified` unless all children are `verified`
- Checks project phase in `state.yaml` matches artifact statuses (e.g., can't have `executing` phase if REQs are still `draft`)

**`validate-ids.sh`:**
- Scans all artifact directories for ID uniqueness
- Validates ID format matches schema regex (e.g., `REQ-\d{3}(\.\d{1,3})?$`)
- Checks dot-notation depth doesn't exceed 3 levels
- Checks children reference valid parents in `_index.yaml`

**`validate-fingerprints.sh`:**
- Recomputes SHA256 for each artifact's title + body
- Compares against stored `fingerprint` in frontmatter
- Reports mismatches (artifact modified without framework awareness)

**`validate-gate.sh`:**
- Reads a phase-gate checklist (e.g., `specifying-to-planning.yaml`)
- Executes the `script` defined for each `automated: true` item
- Returns exit code 0 if all blocking items pass, 1 otherwise
- Used by both the CI pipeline and conversational skills before phase transitions

### 2. Phase-gate checklists

```
checklists/
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
    script: "scripts/validate-status.sh --type REQ --expected approved"
    severity: blocking

  - id: CKL-GATE-002-02
    check: "Every requirement has at least one acceptance criterion"
    automated: true
    script: "scripts/check-acceptance-criteria.sh"
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

### 4. `specflow-validate` command

The Python CLI orchestrator that runs all underlying validation scripts:

```bash
specflow-validate                  # Run all checks
specflow-validate --type schema    # Run only schema checks
specflow-validate --type links     # Run only link checks
specflow-validate --fix            # Auto-fix what's possible (rebuild _index.yaml, recompute fingerprints)
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

### 5. `specflow-status` command (enhanced)

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
checklists/
└── readiness/
    ├── discovery-readiness.yaml     # Before generating REQs
    ├── planning-readiness.yaml      # Before creating architecture
    ├── architecture-readiness.yaml  # Before detailed design
    └── review-readiness.yaml        # Before reviewing artifacts
```

These are loaded by skill files during conversational commands. The agent evaluates readiness silently after each user exchange.

### 7. `validate-gate.sh` script

Runs a specific phase-gate checklist and outputs results:

```bash
specflow-validate-gate specifying-to-planning
```

Returns exit code 0 if all blocking items pass, 1 otherwise. Used by CI and by conversational commands before phase transitions.

## Acceptance Criteria

- [ ] All 6 validation scripts run independently and as a group via `specflow-validate`
- [ ] Schema validation catches missing required fields and invalid status values
- [ ] Link validation detects broken links and orphaned artifacts
- [ ] Status validation catches invalid transitions and parent/child inconsistencies
- [ ] ID validation catches duplicates and format violations
- [ ] Fingerprint validation detects modified artifacts with stale fingerprints
- [ ] `specflow-validate` on a well-formed project returns exit code 0
- [ ] `specflow-validate` on a project with issues returns exit code 1 with clear messages
- [ ] Phase-gate checklists exist for all 6 transitions
- [ ] In-process checklists exist for REQ, ARCH, DDD, and STORY writing
- [ ] `validate-gate.sh` can be run for any specific transition
- [ ] `specflow-status` displays phase, artifact counts, link health, and suggested next action
- [ ] All validation is programmatic — zero LLM tokens consumed

## Dependencies

- P0 (schemas, directory structure)
- P1 (manually authored artifacts to validate, `_index.yaml` files)

## Verification Gate

The "Self-Validation" Gate:
- We run our P2 `specflow-validate` command against our P1 manually written specs. If P2 throws errors, we know either our P1 specs violated our own rules, or our P0 schemas/P2 validators are broken. We don't move on until `specflow-validate` passes on its own codebase.
