# Link Role Reference

## Complete Vocabulary

Every link is stored on exactly one artifact (the **holder**) and points at a **target**. The
examples read `HOLDER role TARGET`.

| Role | Direction | Usage | Example |
|------|-----------|-------|---------|
| `refined_by` | upstream spec → downstream spec | Cross-level refinement; the **upstream** spec holds the link. Canonical: `specflow update <REQ-ID> --add-link <ARCH-ID>:refined_by`, then `specflow update <ARCH-ID> --add-link <DDD-ID>:refined_by` | REQ-001 refined_by ARCH-001; ARCH-001 refined_by DDD-001 |
| `derives_from` | artifact → upstream source | Generic provenance: a REQ from a prerequisite REQ, a STORY from the STORY it decomposes or the DEF it fixes, a DEC/SPIKE/BP from what it draws on. `ARCH derives_from REQ` is the legacy refinement shape: still legal, reported by lint as accounting only — author `refined_by` on the REQ instead | REQ-002 derives_from REQ-001 |
| `verified_by` | test → spec/STORY | V-model verification pairing. `specflow generate-tests` writes the link on the test, pointing at the spec; a spec or STORY may also name its own tests (both shapes satisfy lint's v-pair coverage; `specflow rtm` follows only the test-held link) | UT-001 verified_by DDD-001 |
| `implements` | STORY → REQ | Story implements a requirement | STORY-001 implements REQ-001 |
| `guided_by` | STORY → ARCH | Story follows architecture | STORY-001 guided_by ARCH-001 |
| `guided_by` | REQ/ARCH/STORY → BP | Artifact is shaped by an approved best practice (link on the artifact, pointing at the BP) | ARCH-001 guided_by BP-004 |
| `specified_by` | STORY → DDD | Story implements a design | STORY-001 specified_by DDD-001 |
| `depends_on` | STORY → STORY | Hard ordering dependency without decomposition (B runs after A); `specflow go` treats it exactly like `derives_from` | STORY-002 depends_on STORY-001 |
| `supersedes` | successor → retired artifact | Replacement carrying the intent forward; pair with `status: superseded` on the old artifact | REQ-010 supersedes REQ-003 |
| `applies_to` | BP → artifact | Legacy scoping of a best practice to named artifacts (newer BPs carry an `applicability` field instead) | BP-004 applies_to ARCH-001 |
| `validated_by` | spec → checklist/test | Validated by a checklist run or an experiment | REQ-001 validated_by CKL-GATE-002 |
| `complies_with` | spec → standard | Satisfies a standard clause | REQ-001 complies_with ISO-26262-8.4.3 |
| `fails_to_meet` | DEF → spec | Defect shows a broken requirement | DEF-001 fails_to_meet REQ-001 |
| `exposed_by` | DEF → test/artifact | What surfaced the defect: the failing test, or the suspect artifact for `specflow defect-from-suspect` | DEF-001 exposed_by UT-004 |
| `addresses` | DEC/DEF → defect/spec/STORY | What the decision or fix resolves | DEC-001 addresses DEF-001 |
| `challenges` | CHL → artifact | The artifact a challenge questions (written by the audit and review commands) | CHL-001 challenges ARCH-001 |
| `review_of` | REV → artifact | The artifact a `specflow artifact-review` run examined | REV-001 review_of STORY-001 |
| `refers_to` | AUD/CHL/REV → artifact | Informational back-reference (an AUD to what it covered, a CHL to its REV) | CHL-001 refers_to REV-001 |
| `executes` | test-run → test | Test execution record | TR-001 executes QT-001 |
| `mitigated_by` | hazard/risk → control | Safety context — only with the optional `hazard` / `risk` / `control` types | HAZ-001 mitigated_by CTRL-001 |

> **The vocabulary is frozen and behavior-paired.** A link role only exists when a query or
> validation actually consumes it (a frozen vocabulary). Don't invent new roles — if the
> role you want isn't listed, run `specflow artifact-lint` and it will suggest the canonical
> equivalent. The `mitigated_by` row exists only when the optional safety types are installed
> (`specflow init --with-types hazard,risk,control`); packs may add their own roles (the
> autoresearch pack's `belongs_to` / `condenses` / `operates_on` / `informs`), documented in
> the pack's skill.

### Don't author inverse roles — query backlinks instead

Every link is stored once and traversed **both ways**. To answer "what supersedes / implements
/ refines X?", run `specflow trace <ID>` (it shows upstream *and* downstream) rather than
hand-authoring `superseded_by` / `implemented_by` / `refines`. Inverse roles double-author the
graph and double-count coverage.

### Retiring an artifact is a status, not a role

Use `status: superseded` (plus the successor's `supersedes` link), `status: cancelled`
(terminated, no replacement), or `status: deprecated` (still valid but discouraged). Never
`cancels` / `cancelled_by` / `deprecates` as link roles — see the execute skill's
`status-lifecycle.md` reference.

## Allowed Roles Per Artifact Type

### Requirement (REQ)
- `refined_by` — links to the ARCH that refines it (the REQ holds the link — canonical)
- `verified_by` — names its QT (optional; `generate-tests` writes the QT-side link)
- `derives_from` — links to a prerequisite REQ (optional; drives story wave ordering)
- `complies_with` — links to a standard clause
- `validated_by` — links to a checklist
- `guided_by` — links to an in-scope approved BP
- `supersedes` — links to the REQ it replaces

### Architecture (ARCH)
- `refined_by` — links to the DDD (or sub-ARCH) that refines it (the ARCH holds the link)
- `verified_by` — names its IT (optional; `generate-tests` writes the IT-side link)
- `derives_from` — legacy link to the REQ upstream (lint accounting only; prefer `refined_by` on the REQ)
- `guided_by` — links to a DEC or an in-scope approved BP
- `complies_with` — links to a standard clause
- `supersedes` — links to the ARCH it replaces

### Detailed Design (DDD)
- `verified_by` — names its UT (optional; `generate-tests` writes the UT-side link)
- `refined_by` — legacy concrete→abstract link to its ARCH (still legal; prefer `refined_by` on the ARCH pointing here)
- `derives_from` — provenance, e.g. the SPIKE it was promoted from
- `specified_by` — links to the ARCH or REQ it specifies (optional)
- `complies_with`, `supersedes` — as for ARCH
- (no `guided_by`: the DDD schema does not allow it today — hang DEC/BP guidance on the ARCH)

### Story (STORY)
- `implements` — links to a REQ
- `guided_by` — links to an ARCH, or to an in-scope approved BP
- `specified_by` — links to a DDD
- `derives_from` — links to the STORY it decomposes (hard wave dependency) or the DEF it fixes
- `depends_on` — links to a STORY that must finish first (hard wave dependency, no decomposition implied)
- `verified_by` — names its own UT/IT/QT (optional; the test-side link also counts)

### Tests (UT / IT / QT)
- `verified_by` — links to the spec or STORY this test verifies (what `generate-tests` writes)
- `executes` — links to the test a run record executed
- `derives_from` — provenance

### Defect (DEF)
- `fails_to_meet` — links to the broken REQ or spec
- `exposed_by` — links to the test (or suspect artifact) that surfaced it
- `addresses` — links to what the fix resolves
- `derives_from` — provenance

### Decision (DEC)
- `derives_from` — links to the spec/work the decision draws on
- `addresses` — links to the defect, spec, or STORY the decision resolves

### Best Practice (BP)
- `guided_by`, `derives_from`, `complies_with` — what shaped the practice
- `supersedes` — the BP it replaces
- `applies_to` — legacy explicit scope (prefer the `applicability` field)

### Spike (SPIKE)
- `derives_from` — what the spike probes
- `guided_by` — a DEC or BP that framed it

### Review artifacts (AUD / CHL / REV) — written by the commands, never by hand
- AUD: `refers_to` the artifacts it covered
- CHL: `challenges` the questioned artifact, `refers_to` its REV
- REV: `review_of` the reviewed artifact, `refers_to` related artifacts

## Common Linking Patterns

Diagram convention: `A ←[role]← B` means **B holds** a link `role` whose target is A.

### Full chain (REQ → ARCH → DDD → STORY)
```
ARCH-001 ←[refined_by]← REQ-001      # the REQ holds the link (canonical)
DDD-001  ←[refined_by]← ARCH-001     # the ARCH holds the link
REQ-001  ←[implements]← STORY-001
ARCH-001 ←[guided_by]← STORY-001
DDD-001  ←[specified_by]← STORY-001
```
```
specflow update REQ-001 --add-link ARCH-001:refined_by
specflow update ARCH-001 --add-link DDD-001:refined_by
```

### V-model verification
```
REQ-001  ←[verified_by]← QT-001      # the test holds the link (what generate-tests writes)
ARCH-001 ←[verified_by]← IT-001
DDD-001  ←[verified_by]← UT-001
```

### Multiple REQs → single ARCH
```
ARCH-001 ←[refined_by]← REQ-001
ARCH-001 ←[refined_by]← REQ-002
ARCH-001 ←[refined_by]← REQ-003
```
This is normal — one architectural component serves multiple requirements; each REQ holds its own `refined_by` link.

### Single REQ → multiple STORYs
```
REQ-001 ←[implements]← STORY-001
REQ-001 ←[implements]← STORY-002
```
This is normal — one requirement may need multiple stories to implement.
