# P1: Self-Specification

## Goal

To test the foundational directory structure, schemas, and markdown format manually before building any automation. We will "dogfood" the project by writing SpecFlow's own specifications using the SpecFlow format.

## Deliverables

### 1. SpecFlow Requirements

Manually author `REQ-*` markdown files in `_specflow/specs/requirements/` that describe:
- The `specflow` command line interface
- The artifact structure
- The trace and suspect flag propagation rules
- The AI execution boundaries

### 2. SpecFlow Architecture

Manually author `ARCH-*` markdown files in `_specflow/specs/architecture/` that describe:
- The programmatic CLI core
- The Python package structure
- The `.specflow` framework machinery

### 3. Links and Dependencies

Ensure that all manually authored files:
- Use correct YAML frontmatter
- Adhere to the schemas defined in P0
- Have properly formatted draft IDs
- Link to each other correctly (e.g., ARCH files `refined_by` REQ files)

## Acceptance Criteria

- [ ] A complete set of `REQ-*` files exists describing SpecFlow's MVP features.
- [ ] A complete set of `ARCH-*` files exists describing SpecFlow's architecture.
- [ ] All files are manually placed in their correct directories.
- [ ] All files adhere strictly to the YAML schema frontmatter rules.

## Dependencies

- P0 (The `.specflow/` schema and `_specflow/` directory structures must exist).

## Verification Gate

Manual Review:
- We will visually inspect the output to ensure it matches the design intentions of the project. Once P2 is completed, these manually created files will serve as the test data for the verification engine.

## Estimated Effort

Small. Pure documentation writing using the new markdown standard.