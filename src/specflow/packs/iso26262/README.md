# ISO 26262 Demo Pack

**Demonstration only.** This pack provides minimal stub content to prove the
standards-pack architecture works end-to-end. It is **not** a complete or
authoritative ISO 26262 implementation and must not be used for real
functional-safety compliance work.

## What's here

- `pack.yaml` — pack manifest (adds the `hazard` artifact type and its directory)
- `schemas/hazard.yaml` — a single schema to prove pack-added artifact types
  flow through discovery, creation, and validation
- `standards/iso26262.yaml` — five stub clauses, enough to exercise
  `specflow compliance --standard iso26262`

## What a real ISO 26262 pack would need

- Complete clause lists across all parts of the standard
- ASIL classification fields on safety artifacts
- HARA / FMEA / safety-case templates
- Traceability structures mapping requirements → goals → architectural elements
- Verification and validation artifact types specific to functional safety

Treat this pack as a worked example of the machinery, not as guidance for
building a real standards pack.
