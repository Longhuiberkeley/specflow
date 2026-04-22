"""specflow artifact-lint — Run all validation checks on SpecFlow artifacts."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import draft_ids as draft_lib
from specflow.lib import standards as standards_lib
from specflow.lib import lint as lint_lib
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, NC

CHECK_NAMES = ["schema", "links", "status", "ids", "fingerprints", "acceptance", "conflicts", "coverage", "story-size", "chain-report", "quality"]


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
        return check_schema(artifacts, schema_dir)
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
    elif check_name == "conflicts":
        return _check_conflicts(artifacts)
    elif check_name == "coverage":
        return check_coverage(artifacts)
    elif check_name == "story-size":
        return _check_story_size(artifacts)
    elif check_name == "chain-report":
        return _check_chain_report(artifacts)
    elif check_name == "quality":
        return _check_quality(artifacts)

    return {"status_icon": "?", "detail": f"Unknown check: {check_name}",
            "blocking_count": 0, "warning_count": 0}


def check_schema(
    artifacts: list[art_lib.Artifact],
    schema_dir: Path,
) -> dict[str, str | int]:
    """Validate all artifacts against their schemas."""
    schemas = lint_lib.load_schemas(schema_dir)
    blocking = 0
    warnings = 0
    details: list[str] = []

    for art in artifacts:
        schema = schemas.get(art.type)
        if not schema:
            warnings += 1
            details.append(f"  ⚠ Unknown type '{art.type}': {art.id}")
            continue

        issues = lint_lib.validate_artifact_schema(art, schema)
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
    schemas = lint_lib.load_schemas(schema_dir)
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
    hierarchy_issues = lint_lib.validate_status_hierarchy(artifacts)
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
    schemas = lint_lib.load_schemas(schema_dir)
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

    # Format (draft IDs are always accepted; renumbered by `specflow renumber-drafts`)
    for art in artifacts:
        schema = schemas.get(art.type)
        if schema:
            id_fmt = schema.get("id_format")
            if id_fmt and not art_lib.validate_id_format(art.id, id_fmt):
                if draft_lib.is_draft_id(art.id):
                    continue
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

        result = lint_lib.validate_fingerprint(art)
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
        if not lint_lib.has_acceptance_criteria(art):
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


def _check_conflicts(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Detect contradictory constraints between requirements.

    Uses zero-token pattern matching to find numeric constraints in REQ bodies,
    groups them by system element (extracted from title keywords and tags),
    and flags pairs specifying contradictory ranges on the same metric.
    """
    blocking = 0
    warnings = 0
    details: list[str] = []

    reqs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "REQ"]

    _NUM_PATTERN = re.compile(
        r"(?P<metric>[\w\s]{3,40}?)"
        r"\s*(?P<op><|<=|>=|>|==|=|!=|at\s+least|at\s+most|under|over|below|above)"
        r"\s*(?P<value>\d+\.?\d*)\s*(?P<unit>%|ms|s|sec|seconds?|min|minutes?|mb|gb|kb|bytes?|rpm|rps)?",
        re.IGNORECASE,
    )

    _HEADING_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)

    constraints_by_req: dict[str, list[dict]] = {}
    for art in reqs:
        found = []
        for m in _NUM_PATTERN.finditer(art.body):
            metric = m.group("metric").strip().lower()
            op = m.group("op").strip().lower()
            val = float(m.group("value"))
            unit = (m.group("unit") or "").strip().lower()
            if not metric:
                continue
            found.append({"metric": metric, "op": op, "value": val, "unit": unit, "id": art.id})
        if found:
            title_words = set(art.title.lower().split())
            tag_words = set(t.lower() for t in art.tags)
            heading_words: set[str] = set()
            for hm in _HEADING_PATTERN.finditer(art.body):
                for w in hm.group(1).lower().split():
                    if len(w) > 3:
                        heading_words.add(w)
            key = frozenset(title_words | tag_words | heading_words)
            for c in found:
                c["element_key"] = key
            constraints_by_req[art.id] = found

    _OP_BOUNDS = {
        "<": ("upper", False), "<=": ("upper", True),
        ">": ("lower", False), ">=": ("lower", True),
        "at least": ("lower", True), "at most": ("upper", True),
        "under": ("upper", False), "over": ("lower", False),
        "below": ("upper", False), "above": ("lower", False),
    }

    seen_pairs: set[frozenset[str]] = set()
    for req_id_a, constraints_a in constraints_by_req.items():
        for c_a in constraints_a:
            for req_id_b, constraints_b in constraints_by_req.items():
                if req_id_a >= req_id_b:
                    continue
                pair_key = frozenset({req_id_a, req_id_b})
                if pair_key in seen_pairs:
                    continue
                for c_b in constraints_b:
                    if c_a["element_key"] != c_b["element_key"]:
                        continue
                    if c_a["metric"] != c_b["metric"]:
                        continue
                    if c_a["unit"] != c_b["unit"]:
                        continue

                    bounds_a = _OP_BOUNDS.get(c_a["op"])
                    bounds_b = _OP_BOUNDS.get(c_b["op"])
                    if not bounds_a or not bounds_b:
                        continue

                    def _bound_val(bound_type: str, inclusive: bool, val: float) -> float:
                        eps = 1e-9
                        if bound_type == "upper":
                            return val if inclusive else val - eps
                        return val if inclusive else val + eps

                    if bounds_a[0] == "upper" and bounds_b[0] == "lower":
                        upper = _bound_val("upper", bounds_a[1], c_a["value"])
                        lower = _bound_val("lower", bounds_b[1], c_b["value"])
                        if upper < lower:
                            seen_pairs.add(pair_key)
                            warnings += 1
                            details.append(
                                f"  ⚠ [{req_id_a}] vs [{req_id_b}] conflicting: "
                                f"'{c_a['metric']} {c_a['op']} {c_a['value']}{c_a['unit']}' "
                                f"vs '{c_b['metric']} {c_b['op']} {c_b['value']}{c_b['unit']}'"
                            )
                    elif bounds_a[0] == "lower" and bounds_b[0] == "upper":
                        lower = _bound_val("lower", bounds_a[1], c_a["value"])
                        upper = _bound_val("upper", bounds_b[1], c_b["value"])
                        if upper < lower:
                            seen_pairs.add(pair_key)
                            warnings += 1
                            details.append(
                                f"  ⚠ [{req_id_a}] vs [{req_id_b}] conflicting: "
                                f"'{c_a['metric']} {c_a['op']} {c_a['value']}{c_a['unit']}' "
                                f"vs '{c_b['metric']} {c_b['op']} {c_b['value']}{c_b['unit']}'"
                            )

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "; ".join(details) if details else "No conflicting REQ constraints detected"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def check_coverage(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Check REQ→STORY→test coverage completeness at all V-model levels.

    For each approved REQ, verifies:
      - At least one STORY links to it via 'implements'
    For each approved STORY, verifies:
      - At least one test at each required V-model level links via 'verified_by'
    """
    blocking = 0
    warnings = 0
    details: list[str] = []

    id_index = art_lib.build_id_index(artifacts)

    reqs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "REQ" and a.status in ("approved", "implemented", "verified")]
    stories = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "STORY"]
    tests_by_type: dict[str, list[art_lib.Artifact]] = {
        "unit-test": [], "integration-test": [], "qualification-test": [],
    }
    for a in artifacts:
        if a.type in tests_by_type:
            tests_by_type[a.type].append(a)

    req_to_stories: dict[str, list[art_lib.Artifact]] = {}
    for story in stories:
        for link in story.links:
            if link.role == "implements" and art_lib.get_prefix_from_id(link.target) == "REQ":
                req_to_stories.setdefault(link.target, []).append(story)

    for req in reqs:
        linked_stories = req_to_stories.get(req.id, [])
        if not linked_stories:
            warnings += 1
            details.append(f"  ⚠ [{req.id}] no STORY implements this approved requirement")
            continue

        for story in linked_stories:
            if story.status not in ("approved", "implemented", "verified"):
                continue

            test_links_by_type: dict[str, list[art_lib.Artifact]] = {
                "unit-test": [], "integration-test": [], "qualification-test": [],
            }
            for t_type, t_arts in tests_by_type.items():
                for t_art in t_arts:
                    for t_link in t_art.links:
                        if t_link.target == story.id and t_link.role == "verified_by":
                            test_links_by_type[t_type].append(t_art)
                            break

            for t_type in ("unit-test", "integration-test", "qualification-test"):
                prefix = art_lib.TYPE_TO_PREFIX.get(t_type, "")
                if not test_links_by_type[t_type]:
                    warnings += 1
                    details.append(
                        f"  ⚠ [{story.id}] no {prefix} linked via 'verified_by' "
                        f"(covers REQ {req.id})"
                    )

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "; ".join(details) if details else "All approved REQs have STORY and test coverage"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def _check_story_size(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Warn on stories exceeding size heuristics.

    Flags stories with >8 acceptance criteria or >5 distinct subsystem references.
    """
    blocking = 0
    warnings = 0
    details: list[str] = []

    stories = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "STORY"]

    for art in stories:
        ac_section = re.search(
            r"##\s*Acceptance\s+Criteria\s*\n(.*)",
            art.body,
            re.IGNORECASE | re.DOTALL,
        )
        if ac_section:
            ac_text = ac_section.group(1)
            next_header = re.search(r"^##\s", ac_text, re.MULTILINE)
            if next_header:
                ac_text = ac_text[:next_header.start()]
            ac_items = re.findall(r"^\d+\.\s+", ac_text, re.MULTILINE)
            ac_count = len(ac_items)
            if ac_count > 8:
                warnings += 1
                details.append(f"  ⚠ [{art.id}] has {ac_count} acceptance criteria (max 8 recommended)")

        subsystem_refs = set(
            re.findall(r"\bsrc/[\w./-]+", art.body)
            + re.findall(r"\blib/[\w./-]+", art.body)
            + re.findall(r"commands/[\w./-]+", art.body)
        )
        if len(subsystem_refs) > 5:
            warnings += 1
            details.append(f"  ⚠ [{art.id}] references {len(subsystem_refs)} distinct subsystems (max 5 recommended)")

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "; ".join(details) if details else f"All {len(stories)} story/stories within size limits"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def _check_chain_report(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Produce an informational chain-depth survey across all approved spec artifacts.

    This is NOT a pass/fail check. It reports chain depth distribution
    so users can assess whether their traceability coverage is appropriate
    for their standard. Always returns 0 blocking / 0 warnings.
    """
    id_index = art_lib.build_id_index(artifacts)

    spec_types = {"requirement", "architecture", "detailed-design"}
    for atype in list(art_lib.TYPE_TO_DIR.keys()):
        prefix = art_lib.TYPE_TO_PREFIX.get(atype, "")
        if prefix and prefix not in ("REQ", "ARCH", "DDD", "UT", "IT", "QT", "STORY", "SPIKE", "DEC", "DEF"):
            spec_types.add(atype)

    approved_specs = [
        a for a in artifacts
        if a.type in spec_types and a.status in ("approved", "implemented", "verified")
    ]

    depth_counts: dict[int, int] = {}
    partial_chains: list[str] = []

    for spec in approved_specs:
        path = art_lib.compute_chain_depth(spec.id, id_index)
        depth = len(path)
        depth_counts[depth] = depth_counts.get(depth, 0) + 1

        has_verification = False
        for link_target in path[1:]:
            target_art = id_index.get(link_target)
            if target_art and target_art.type in ("unit-test", "integration-test", "qualification-test"):
                has_verification = True
                break

        if not has_verification and depth > 1:
            partial_chains.append(
                f"  ℹ {spec.id}: chain depth {depth}, no verification test ({' -> '.join(path)})"
            )

    details: list[str] = []
    if depth_counts:
        details.append("  Chain depth distribution:")
        for d in sorted(depth_counts.keys()):
            label = "link" if d == 1 else "links"
            details.append(f"    depth {d} ({d} {label}): {depth_counts[d]} chain(s)")
    else:
        details.append("  No approved spec artifacts found")

    if partial_chains:
        details.append("  Partial chains (informational):")
        details.extend(partial_chains)

    return {
        "status_icon": CYAN + "ℹ" + NC,
        "detail": "\n".join(details),
        "blocking_count": 0,
        "warning_count": 0,
    }


_AMBIGUITY_WORDS = re.compile(
    r"\b(fast|slow|quickly|efficiently|responsive|performant|real-time"
    r"|user-friendly|robust|flexible|scalable|maintainable|reliable|stable|safe"
    r"|approximately|roughly|several|etc\.?"
    r"|should be able to|it would be nice if|ideally|preferably"
    r"|properly|correctly|appropriately|as expected|as needed|if possible"
    r"|easy|simple|straightforward|intuitive|seamless|effortless"
    r"|frequently|often|rarely|sometimes|occasionally|regularly"
    r"|reasonable|adequate|sufficient|appropriate)\b",
    re.IGNORECASE,
)

_PASSIVE_VOICE = re.compile(
    r"\*\*(?:shall|should|may)\*\*\s+be\s+"
    r"(?:validated|processed|handled|managed|stored|sent|notified|logged"
    r"|updated|created|deleted|returned|displayed|generated|executed"
    r"|performed|checked|verified|approved|rejected|enabled|disabled)",
    re.IGNORECASE,
)

_COMPOUND_SHALL = re.compile(
    r"[^.]*\*{0,2}shall\*{0,2}[^.]*\*{0,2}shall\*{0,2}[^.]*",
    re.IGNORECASE,
)

_MISSING_THRESHOLD = re.compile(
    r"\b(?:respond|responds|response|latency|perform|complete|finish|process)"
    r"\s+(?:quickly|fast|rapidly|in a timely manner|efficiently|promptly)\b",
    re.IGNORECASE,
)


def _check_quality(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Check REQ bodies for quality issues using zero-token regex analysis.

    Detects: ambiguity words, passive voice, compound shall, missing thresholds.
    All findings are reported as warnings (non-blocking).
    """
    warnings = 0
    details: list[str] = []

    reqs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "REQ"]

    _STRIP_CODE = re.compile(r"`[^`]+`")

    for art in reqs:
        findings: list[str] = []
        body = _STRIP_CODE.sub("", art.body)

        for m in _AMBIGUITY_WORDS.finditer(body):
            word = m.group(1)
            findings.append(f"ambiguity word '{word}'")

        for m in _PASSIVE_VOICE.finditer(body):
            phrase = m.group(0)
            findings.append(f"passive voice '{phrase}'")

        for m in _COMPOUND_SHALL.finditer(body):
            snippet = m.group(0).strip()[:60]
            findings.append(f"compound shall in '{snippet}...'")

        for m in _MISSING_THRESHOLD.finditer(body):
            phrase = m.group(0)
            findings.append(f"missing threshold in '{phrase}'")

        if findings:
            warnings += len(findings)
            sample = findings[:3]
            suffix = f" (+{len(findings) - 3} more)" if len(findings) > 3 else ""
            details.append(
                f"  \u26a0 [{art.id}] {'; '.join(sample)}{suffix}"
            )

    icon = GREEN + "\u2713" + NC if warnings == 0 else YELLOW + "\u26a0" + NC
    detail_msg = "\n".join(details) if details else f"All {len(reqs)} requirement(s) pass quality checks"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": 0,
        "warning_count": warnings,
    }


def run(root: Path, args: dict) -> int:
    """Execute specflow artifact-lint.

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

    # --method llm: delegate to the Pass-2 orchestrator (non-blocking summary).
    method = args.get("method", "programmatic")
    if method == "llm":
        from specflow.lib import ci as ci_lib
        outcome = ci_lib.run_pass_two(root)
        report = ci_lib.format_pass_two_report(outcome)
        print(f"\n{CYAN}SpecFlow Artifact Lint — Pass 2 (LLM-judged){NC}")
        print(f"{CYAN}{'─' * 50}{NC}")
        print(report)
        print(f"{CYAN}{'─' * 50}{NC}")
        # Pass 2 never blocks: always exit 0 so CI can post the comment.
        return 0

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
    print(f"\n{CYAN}SpecFlow Artifact Lint{NC}")
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

