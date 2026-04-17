# Link Role Reference

## Complete Vocabulary

| Role | Direction | Usage | Example |
|------|-----------|-------|---------|
| `derives_from` | artifact → upstream | This artifact was derived from the target | ARCH-001 derives_from REQ-001 |
| `refined_by` | spec → downstream spec | Cross-level refinement | DDD-001 refined_by ARCH-001 |
| `verified_by` | spec → test | V-model verification pairing | REQ-001 verified_by QT-001 |
| `implements` | story → REQ | Story implements a requirement | STORY-001 implements REQ-001 |
| `guided_by` | story → ARCH | Story follows architecture | STORY-001 guided_by ARCH-001 |
| `specified_by` | story → DDD | Story implements a design | STORY-001 specified_by DDD-001 |
| `validated_by` | spec → checklist | Validated by a checklist | REQ-001 validated_by CKL-GATE-002 |
| `complies_with` | spec → standard | Satisfies a standard clause | REQ-001 complies_with ISO-26262-8.4.3 |
| `mitigates` | safety goal → hazard | Safety context | SG-001 mitigates HAZ-001 |
| `satisfies` | safety req → safety goal | Safety context | SR-001 satisfies SG-001 |
| `fails_to_meet` | defect → spec | Defect shows broken requirement | DEF-001 fails_to_meet REQ-001 |
| `addresses` | CR → defect/spec | Change request scope | CR-001 addresses DEF-001 |
| `executes` | test-run → test | Test execution record | TR-001 executes QT-001 |

## Allowed Roles Per Artifact Type

### Requirement (REQ)
- `refined_by` — linked from ARCH downstream
- `verified_by` — linked from QT downstream
- `derives_from` — linked from other REQ upstream (optional)
- `complies_with` — linked from standard clause
- `validated_by` — linked from checklist

### Architecture (ARCH)
- `refined_by` — linked from DDD downstream
- `verified_by` — linked from IT downstream
- `derives_from` — linked from REQ upstream
- `guided_by` — linked from STORY
- `complies_with` — linked from standard clause

### Detailed Design (DDD)
- `refined_by` — linked from UT downstream
- `derives_from` — linked from ARCH upstream
- `complies_with` — linked from standard clause

### Story (STORY)
- `implements` — links to a REQ
- `guided_by` — links to an ARCH
- `specified_by` — links to a DDD
- `derives_from` — links to another STORY (optional decomposition)

### Defect (DEF)
- `fails_to_meet` — links to the broken REQ or spec
- `exposed_by` — links to the test that caught it (not in standard vocab, but common usage)

### Decision (DEC)
- `guided_by` — links to relevant ARCH or spec

## Common Linking Patterns

### Full chain (REQ → ARCH → DDD → STORY)
```
REQ-001 ←[derives_from]← ARCH-001 ←[refined_by]← DDD-001
REQ-001 ←[implements]← STORY-001
ARCH-001 ←[guided_by]← STORY-001
DDD-001 ←[specified_by]← STORY-001
```

### V-model verification
```
REQ-001 ←[verified_by]← QT-001
ARCH-001 ←[verified_by]← IT-001
DDD-001 ←[verified_by]← UT-001
```

### Multiple REQs → single ARCH
```
ARCH-001 ←[derives_from]← REQ-001
ARCH-001 ←[derives_from]← REQ-002
ARCH-001 ←[derives_from]← REQ-003
```
This is normal — one architectural component serves multiple requirements.

### Single REQ → multiple STORYs
```
REQ-001 ←[implements]← STORY-001
REQ-001 ←[implements]← STORY-002
```
This is normal — one requirement may need multiple stories to implement.
