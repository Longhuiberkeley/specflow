# V-Model Test Pairing

## Pairing Rules

Each specification artifact has a verification counterpart:

```
    REQ (WHAT)  ←→  QT (Qualification Test)
   ARCH (HOW-structured)  ←→  IT (Integration Test)
    DDD (HOW-detailed)  ←→  UT (Unit Test)
```

| Spec Level | Answers | Test Level | Verifies |
|------------|---------|------------|----------|
| Requirement | WHAT must the system do? | Qualification Test | End-to-end system behavior against requirements |
| Architecture | HOW is the system structured? | Integration Test | Component interfaces and interactions |
| Detailed Design | HOW does each part work? | Unit Test | Individual functions and algorithms |

## Creating Verification Tests

When a spec artifact reaches `status: implemented`, its verification test should be created:

### Unit Test (verifies DDD)
```
uv run specflow create \
  --type unit-test \
  --title "UT for <DDD component>" \
  --links "[{\"target\": \"DDD-001\", \"role\": \"verified_by\"}]" \
  --body "<test cases covering DDD-001's function signatures and edge cases>"
```

### Integration Test (verifies ARCH)
```
uv run specflow create \
  --type integration-test \
  --title "IT for <ARCH component>" \
  --links "[{\"target\": \"ARCH-001\", \"role\": \"verified_by\"}]" \
  --body "<test cases covering ARCH-001's interfaces and data flow>"
```

### Qualification Test (verifies REQ)
```
uv run specflow create \
  --type qualification-test \
  --title "QT for <REQ>" \
  --links "[{\"target\": \"REQ-001\", \"role\": \"verified_by\"}]" \
  --body "<test cases covering REQ-001's acceptance criteria>"
```

## Test Body Template

```markdown
## Test Cases

1. **<Test case name>**
   - Precondition: <setup required>
   - Steps: <actions to perform>
   - Expected: <what should happen>
   - Actual: <filled during execution>

2. **<Error case name>**
   - Precondition: <setup with invalid state>
   - Steps: <actions that should fail gracefully>
   - Expected: <error handling behavior>
   - Actual: <filled during execution>
```

## Traceability

When a test is created and linked to a spec, the validation engine can:
- Detect missing verification pairs (`specflow artifact-lint --type links` reports warnings)
- Verify that every spec has at least one test artifact linked via `verified_by`

This is the core of the V-model compliance proof: every specification has corresponding verification evidence.
