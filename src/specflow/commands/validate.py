"""specflow validate — Run all validation checks on SpecFlow artifacts."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib import standards as standards_lib
from specflow.lib import validation as val_lib

# ANSI color codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"  # No Color

CHECK_NAMES = ["schema", "links", "status", "ids", "fingerprints", "acceptance"]


def _run_check(
    artifacts: list[art_lib.Artifact],
    root: Path,
    check_name: str,
) -> dict[str, str | int]:
    """Run a validation check using Python logic and return summary.

    Returns dict with: status_icon, detail, blocking_count, warning_count.
    """
    schema_dir = root / ".specflow" / "schema"

    if check_name == "schema":
        return _check_schema(artifacts, schema_dir)
    elif check_name == "links":
        return _check_links(artifacts, root)
    elif check_name == "status":
        return _check_status(artifacts, schema_dir)
    elif check_name == "ids":
        return _check_ids(artifacts, schema_dir)
    elif check_name == "fingerprints":
        return _check_fingerprints(artifacts)
    elif check_name == "acceptance":
        return _check_acceptance(artifacts)

    return {"status_icon": "?", "detail": f"Unknown check: {check_name}",
            "blocking_count": 0, "warning_count": 0}


def _check_schema(
    artifacts: list[art_lib.Artifact],
    schema_dir: Path,
) -> dict[str, str | int]:
    """Validate all artifacts against their schemas."""
    schemas = val_lib.load_schemas(schema_dir)
    blocking = 0
    warnings = 0
    details: list[str] = []

    for art in artifacts:
        schema = schemas.get(art.type)
        if not schema:
            warnings += 1
            details.append(f"  ⚠ Unknown type '{art.type}': {art.id}")
            continue

        issues = val_lib.validate_artifact_schema(art, schema)
        for issue in issues:
            if issue["severity"] == "blocking":
                blocking += 1
                details.append(f"  ✗ [{art.id}] {issue['message']}")
            elif issue["severity"] == "warning":
                warnings += 1
                details.append(f"  ⚠ [{art.id}] {issue['message']}")

    return {
        "status_icon": GREEN + "✓" + NC if blocking == 0 else RED + "✗" + NC,
        "detail": "; ".join(details) if details else f"All {len(artifacts)} artifacts pass schema validation",
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def _check_links(
    artifacts: list[art_lib.Artifact],
    root: Path,
) -> dict[str, str | int]:
    """Validate link integrity."""
    id_index = art_lib.build_id_index(artifacts)
    blocking = 0
    warnings = 0
    details: list[str] = []

    # Clause IDs from installed standards are valid targets for `complies_with` links.
    standard_clause_ids: set[str] = set()
    for standard in standards_lib.load_standards(root):
        for clause in standard.get("clauses", []) or []:
            if isinstance(clause, dict) and clause.get("id"):
                standard_clause_ids.add(clause["id"])

    for art in artifacts:
        for link in art.links:
            if link.target in id_index:
                continue
            if link.role == "complies_with" and link.target in standard_clause_ids:
                continue
            blocking += 1
            details.append(f"  ✗ [{art.id}] broken link: {link.target} (not found)")

    # Orphans
    orphans = art_lib.find_orphans(artifacts)
    if orphans:
        warnings += len(orphans)
        orphan_ids = ", ".join(a.id for a in orphans[:5])
        if len(orphans) > 5:
            orphan_ids += f" (+{len(orphans) - 5} more)"
        details.append(f"  ⚠ {len(orphans)} orphan(s) with no links: {orphan_ids}")

    # Missing V-model pairs
    missing_pairs = art_lib.find_missing_v_pairs(artifacts)
    if missing_pairs:
        warnings += len(missing_pairs)
        pair_details = ", ".join(f"{a.id} (no {p} verification)" for a, p in missing_pairs[:3])
        details.append(f"  ⚠ {len(missing_pairs)} missing verification pair(s): {pair_details}")

    icon = GREEN + "✓" + NC if blocking == 0 else RED + "✗" + NC
    detail_msg = "; ".join(details) if details else "All links valid"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def _check_status(
    artifacts: list[art_lib.Artifact],
    schema_dir: Path,
) -> dict[str, str | int]:
    """Validate status consistency."""
    schemas = val_lib.load_schemas(schema_dir)
    blocking = 0
    warnings = 0
    details: list[str] = []

    for art in artifacts:
        schema = schemas.get(art.type)
        if schema:
            allowed = schema.get("allowed_status", {})
            if art.status and art.status not in allowed:
                blocking += 1
                details.append(f"  ✗ [{art.id}] invalid status '{art.status}'")

    # Hierarchy checks
    hierarchy_issues = val_lib.validate_status_hierarchy(artifacts)
    for issue in hierarchy_issues:
        if issue["severity"] == "blocking":
            blocking += 1
            details.append(f"  ✗ {issue['message']}")

    icon = GREEN + "✓" + NC if blocking == 0 else RED + "✗" + NC
    detail_msg = "; ".join(details) if details else "All statuses valid"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def _check_ids(
    artifacts: list[art_lib.Artifact],
    schema_dir: Path,
) -> dict[str, str | int]:
    """Validate ID uniqueness and format."""
    schemas = val_lib.load_schemas(schema_dir)
    blocking = 0
    warnings = 0
    details: list[str] = []

    # Uniqueness
    seen: dict[str, str] = {}
    for art in artifacts:
        if art.id in seen:
            blocking += 1
            details.append(f"  ✗ Duplicate ID: {art.id} ({art.path.name} and {seen[art.id]})")
        else:
            seen[art.id] = art.path.name

    # Format
    for art in artifacts:
        schema = schemas.get(art.type)
        if schema:
            id_fmt = schema.get("id_format")
            if id_fmt and not art_lib.validate_id_format(art.id, id_fmt):
                blocking += 1
                details.append(f"  ✗ [{art.id}] invalid format (expected: {id_fmt})")

        # Dot-notation depth
        depth = art_lib.check_dot_notation_depth(art.id)
        if depth > 3:
            warnings += 1
            details.append(f"  ⚠ [{art.id}] dot-notation depth {depth} exceeds maximum of 3")

    icon = GREEN + "✓" + NC if blocking == 0 else RED + "✗" + NC
    detail_msg = "; ".join(details) if details else "All IDs unique and well-formed"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def _check_fingerprints(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Validate content fingerprints."""
    blocking = 0
    warnings = 0
    stale: list[str] = []

    for art in artifacts:
        if not art.fingerprint:
            # No fingerprint stored — will be computed on next save
            continue

        result = val_lib.validate_fingerprint(art)
        if not result["match"]:
            warnings += 1
            stale.append(art.id)

    if stale:
        stale_str = ", ".join(stale[:5])
        if len(stale) > 5:
            stale_str += f" (+{len(stale) - 5} more)"
        detail = f"{len(stale)} fingerprint(s) stale: {stale_str}"
    else:
        detail = "All fingerprints match"

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC

    return {
        "status_icon": icon,
        "detail": detail,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def _check_acceptance(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Check that every REQ has acceptance criteria."""
    blocking = 0
    warnings = 0
    details: list[str] = []

    # Find REQ artifacts by ID prefix (more reliable than type field)
    reqs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "REQ"]
    for art in reqs:
        if not val_lib.has_acceptance_criteria(art):
            blocking += 1
            details.append(f"  ✗ [{art.id}] no acceptance criteria found")

    icon = GREEN + "✓" + NC if blocking == 0 else RED + "✗" + NC
    detail_msg = "; ".join(details) if details else f"All {len(reqs)} requirement(s) have acceptance criteria"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def run(root: Path, args: dict) -> int:
    """Execute specflow validate.

    Args:
        root: Project root directory
        args: Parsed arguments with optional keys:
            - type: Run only a specific check (schema, links, status, ids, fingerprints, acceptance, gate)
            - gate: Phase-gate checklist name (required when type=gate)
            - fix: Auto-fix what's possible

    Returns:
        Exit code (0 = all pass, 1 = blocking issues found)
    """
    root = root.resolve()

    # Check initialization
    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        print(f"{YELLOW}⚠ No _specflow/ directory found{NC}")
        print("   Run 'uv run specflow init' first.")
        return 1

    # Handle --gate mode
    check_type = args.get("type")
    if check_type == "gate":
        gate_name = args.get("gate")
        if not gate_name:
            print(f"{RED}✗ --gate <name> is required when --type gate is used{NC}")
            return 1
        return _run_gate_check(root, gate_name)

    # Determine which checks to run
    do_fix = args.get("fix", False)

    if check_type:
        if check_type not in CHECK_NAMES:
            print(f"{RED}✗ Unknown check type: {check_type}{NC}")
            print(f"   Available: {', '.join(CHECK_NAMES)}")
            return 1
        checks_to_run = [check_type]
    else:
        checks_to_run = CHECK_NAMES

    # --fix mode: rebuild _index.yaml and recompute fingerprints
    if do_fix:
        print(f"{CYAN}Running in fix mode — rebuilding indexes and recomputing fingerprints{NC}\n")
        _auto_fix(root)

    # Discover artifacts
    artifacts = art_lib.discover_artifacts(root)

    # Run checks
    print(f"\n{CYAN}SpecFlow Validate{NC}")
    print(f"{CYAN}{'─' * 50}{NC}")

    total_blocking = 0
    total_warnings = 0
    results: list[tuple[str, dict]] = []

    for check_name in checks_to_run:
        result = _run_check(artifacts, root, check_name)
        results.append((check_name, result))
        total_blocking += result["blocking_count"]
        total_warnings += result["warning_count"]

    # Display results
    label_width = 12
    for check_name, result in results:
        label = check_name.capitalize() + ":"
        label_padded = label.ljust(label_width)
        print(f"  {label_padded} {result['status_icon']} {result['detail']}")

    # Summary
    print(f"{CYAN}{'─' * 50}{NC}")
    if total_blocking > 0:
        print(f"  Result: {RED}FAIL{NC} ({total_blocking} blocking, {total_warnings} warnings)")
        print()
        return 1
    elif total_warnings > 0:
        print(f"  Result: {YELLOW}PASS{NC} ({total_warnings} warnings)")
        print()
        return 0
    else:
        print(f"  Result: {GREEN}PASS{NC} (all checks clean)")
        print()
        return 0


def _run_gate_check(root: Path, gate_name: str) -> int:
    """Run a phase-gate checklist and report pass/fail per item.

    Returns exit code: 0 = all automated items pass, 1 = blocking failure.
    """
    import yaml

    gate_dir = root / ".specflow" / "checklists" / "phase-gates"
    gate_file = gate_dir / f"{gate_name}.yaml"

    if not gate_file.exists():
        print(f"{RED}✗ Gate checklist not found: {gate_name}{NC}")
        available = [f.stem for f in gate_dir.glob("*.yaml")] if gate_dir.exists() else []
        if available:
            print(f"   Available: {', '.join(sorted(available))}")
        return 1

    try:
        data = yaml.safe_load(gate_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"{RED}✗ Failed to parse {gate_file.name}: {e}{NC}")
        return 1

    items = data.get("items", [])
    gate_id = data.get("id", gate_name)
    gate_label = data.get("name", gate_name)

    print(f"\n{CYAN}Phase Gate: {gate_label}{NC}")
    print(f"{CYAN}{'─' * 50}{NC}")

    blocking_failures = 0
    for item in items:
        item_id = item.get("id", "?")
        check_desc = item.get("check", "")
        severity = item.get("severity", "info")
        automated = item.get("automated", False)

        if not automated:
            print(f"  {YELLOW}○{NC} [{item_id}] {check_desc} (LLM-judged, skipped)")
            continue

        # Run the automated script check
        script = item.get("script", "")
        if not script:
            print(f"  {YELLOW}○{NC} [{item_id}] {check_desc} (no script)")
            continue

        import subprocess
        try:
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            passed = result.returncode == 0
        except Exception:
            passed = False

        if passed:
            print(f"  {GREEN}✓{NC} [{item_id}] {check_desc}")
        else:
            icon = RED + "✗" + NC if severity == "blocking" else YELLOW + "⚠" + NC
            print(f"  {icon} [{item_id}] {check_desc}")
            if severity == "blocking":
                blocking_failures += 1

    print(f"{CYAN}{'─' * 50}{NC}")
    if blocking_failures > 0:
        print(f"  Result: {RED}FAIL{NC} ({blocking_failures} blocking)")
        print()
        return 1
    else:
        print(f"  Result: {GREEN}PASS{NC}")
        print()
        return 0


def _auto_fix(root: Path) -> None:
    """Auto-fix what's possible: rebuild _index.yaml, recompute fingerprints."""
    import yaml

    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        return

    # Rebuild _index.yaml files
    for d in sorted(specflow_dir.rglob("*")):
        if d.is_dir() and d.name not in ("specs", "work"):
            index_file = d / "_index.yaml"
            artifacts_in_dir = []
            for md in sorted(d.glob("*.md")):
                if md.name.startswith("_"):
                    continue
                art = art_lib.parse_artifact(md)
                if art:
                    artifacts_in_dir.append({
                        "id": art.id,
                        "title": art.title,
                        "status": art.status,
                        "tags": art.tags,
                        "fingerprint": art.fingerprint,
                    })

            next_id = len(artifacts_in_dir) + 1
            index_data = {
                "artifacts": {a["id"]: a for a in artifacts_in_dir},
                "next_id": next_id,
            }
            index_file.write_text(yaml.dump(index_data, default_flow_style=False))
            print(f"  ✓ Rebuilt {index_file.relative_to(root)}")

    # Recompute fingerprints
    artifacts = art_lib.discover_artifacts(root)
    fixed_count = 0
    for art in artifacts:
        actual = art_lib.compute_fingerprint(art.body)
        if art.fingerprint and art.fingerprint != actual:
            # Read, update frontmatter, write back
            text = art.path.read_text(encoding="utf-8")
            if text.strip().startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    try:
                        fm = yaml.safe_load(text[3:end])
                        if isinstance(fm, dict):
                            fm["fingerprint"] = actual
                            body = text[end + 3:]
                            new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n" + body
                            art.path.write_text(new_text, encoding="utf-8")
                            fixed_count += 1
                    except Exception:
                        pass

    if fixed_count > 0:
        print(f"  ✓ Recomputed {fixed_count} stale fingerprint(s)")

