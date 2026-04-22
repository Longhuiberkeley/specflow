"""specflow generate-tests — Create V-model test stubs from implemented spec artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, GREEN, YELLOW, YELLOW_DIM, CYAN, NC

TYPE_LABELS = {
    "requirement": "QT",
    "architecture": "IT",
    "detailed-design": "UT",
}

TEST_TYPE_NAMES = {
    "requirement": "qualification-test",
    "architecture": "integration-test",
    "detailed-design": "unit-test",
}

TEST_LEVEL_LABELS = {
    "requirement": "Qualification Test",
    "architecture": "Integration Test",
    "detailed-design": "Unit Test",
}


def _find_missing_pairs(
    artifacts: list[art_lib.Artifact],
    id_index: dict[str, art_lib.Artifact],
) -> list[tuple[art_lib.Artifact, str, str]]:
    """Return (spec_artifact, test_type, test_level_label) for specs missing verification."""
    missing = []

    for art in artifacts:
        spec_type = art.type
        if spec_type not in art_lib.V_MODEL_PAIRS:
            continue
        if art.status not in ("implemented", "verified"):
            continue

        has_verification = False
        for other in artifacts:
            for link in other.links:
                if link.target == art.id and link.role == "verified_by":
                    has_verification = True
                    break
            if has_verification:
                break

        if not has_verification:
            test_type = TEST_TYPE_NAMES[spec_type]
            label = TEST_LEVEL_LABELS[spec_type]
            missing.append((art, test_type, label))

    return missing


def _extract_acceptance_criteria(body: str) -> list[str]:
    """Extract acceptance criteria lines from artifact body."""
    criteria = []
    in_ac = False
    for line in body.splitlines():
        stripped = line.strip()
        if "acceptance criteria" in stripped.lower():
            in_ac = True
            continue
        if in_ac:
            if stripped.startswith("#") or (not stripped and criteria):
                break
            if stripped and stripped[0] in "0123456789" and "." in stripped[:4]:
                criteria.append(stripped)
            elif stripped.startswith("- ") or stripped.startswith("* "):
                criteria.append(stripped)
            elif stripped.startswith("Given ") or stripped.startswith("When ") or stripped.startswith("Then "):
                criteria.append(stripped)
    return criteria


def _build_test_body(art: art_lib.Artifact, test_level: str) -> str:
    """Build placeholder test body from spec artifact."""
    lines = [f"# {test_level} for {art.id}: {art.title}\n"]

    criteria = _extract_acceptance_criteria(art.body)
    if criteria:
        lines.append("## Test Cases\n")
        for c in criteria:
            lines.append(f"- [ ] {c}")
        lines.append("")
    else:
        lines.append("## Test Cases\n")
        lines.append("- [ ] TODO: Define test cases\n")

    return "\n".join(lines)


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    from_id = args.get("from")
    dry_run = args.get("dry_run", False)

    artifacts = art_lib.discover_artifacts(root)
    id_index = art_lib.build_id_index(artifacts)

    if not artifacts:
        print(f"{YELLOW}⚠ No artifacts found. Run 'uv run specflow init' to initialize "
              f"the project, then create spec artifacts.{NC}")
        return 0

    if from_id:
        art = id_index.get(from_id)
        if not art:
            print(f"{RED}✗ Artifact '{from_id}' not found. "
                  f"Run 'specflow status' to see all artifacts.{NC}")
            return 1
        if art.type not in art_lib.V_MODEL_PAIRS:
            print(f"{YELLOW}⚠ Artifact type '{art.type}' has no V-model test pair. "
                  f"Expected one of: requirement, architecture, detailed-design.{NC}")
            return 1
        if art.status not in ("implemented", "verified"):
            print(f"{YELLOW}⚠ Artifact '{from_id}' has status '{art.status}', "
                  f"but test stubs require 'implemented' or 'verified'. "
                  f"Run 'specflow update {from_id} --status implemented' first.{NC}")
            return 1

        has_verification = False
        for other in artifacts:
            for link in other.links:
                if link.target == art.id and link.role == "verified_by":
                    has_verification = True
                    break
            if has_verification:
                break

        if has_verification:
            print(f"{YELLOW_DIM}Artifact '{from_id}' already has a verification test. "
                  f"Use --dry-run to inspect or skip this artifact.{NC}")
            return 0

        test_type = TEST_TYPE_NAMES[art.type]
        test_level = TEST_LEVEL_LABELS[art.type]
        pairs = [(art, test_type, test_level)]
    else:
        pairs = _find_missing_pairs(artifacts, id_index)

    if not pairs:
        print(f"{GREEN}All spec artifacts have verification tests. Nothing to generate.{NC}")
        return 0

    if dry_run:
        print(f"{CYAN}Dry run — {len(pairs)} test stub(s) would be created:{NC}\n")
        for spec_art, test_type, test_level in pairs:
            test_prefix = TYPE_LABELS[spec_art.type]
            print(f"  {test_prefix} -> {spec_art.id} ({test_level} for \"{spec_art.title}\")")
        return 0

    created = 0
    skipped = 0
    for spec_art, test_type, test_level in pairs:
        test_prefix = TYPE_LABELS[spec_art.type]
        title = f"{test_level} for {spec_art.id}: {spec_art.title}"
        body = _build_test_body(spec_art, test_level)
        links = [{"target": spec_art.id, "role": "verified_by"}]

        if dry_run:
            continue

        result = art_lib.create_artifact(
            root=root,
            artifact_type=test_type,
            title=title,
            status="draft",
            links=links,
            body=body,
        )

        if result["ok"]:
            print(f"{GREEN}✓ Created {result['id']} ({test_type}) verifying {spec_art.id}{NC}")
            created += 1
        else:
            print(f"{RED}✗ Failed to create test for {spec_art.id}: "
                  f"{result['error']}. Check artifact data and try again.{NC}")
            skipped += 1

    print(f"\n{CYAN}Generated {created} test stub(s), {skipped} skipped.{NC}")
    return 0
