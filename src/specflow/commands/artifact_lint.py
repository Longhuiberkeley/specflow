"""specflow artifact-lint — Run all validation checks on SpecFlow artifacts."""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import draft_ids as draft_lib
from specflow.lib import files as files_lib
from specflow.lib import standards as standards_lib
from specflow.lib import lint as lint_lib
from specflow.lib import role_normalize
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, NC
from specflow.lib.domain_constants import DOMAIN_RECOMMENDED

CHECK_NAMES = ["schema", "links", "status", "status-cascade", "story-linkage", "ids", "fingerprints", "acceptance", "conflicts", "coverage", "story-size", "chain-report", "quality", "spec-body", "output-files", "spidr-coverage", "wave-cycles", "compliance-evidence", "thinking-techniques", "autoresearch-logging", "spike-lifecycle", "source-drift"]


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
    elif check_name == "status-cascade":
        return _check_status_cascade(artifacts)
    elif check_name == "story-linkage":
        return _check_story_linkage(artifacts)
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
    elif check_name == "spec-body":
        return _check_spec_body(artifacts)
    elif check_name == "output-files":
        return _check_output_files(artifacts, root)
    elif check_name == "spidr-coverage":
        return _check_spidr_coverage(artifacts)
    elif check_name == "wave-cycles":
        return _check_wave_cycles(artifacts, root)
    elif check_name == "compliance-evidence":
        return _check_compliance_evidence(artifacts, root)
    elif check_name == "thinking-techniques":
        return _check_thinking_techniques(artifacts)
    elif check_name == "autoresearch-logging":
        return _check_autoresearch_logging(artifacts, root)
    elif check_name == "spike-lifecycle":
        return _check_spike_lifecycle(artifacts, root)
    elif check_name == "source-drift":
        return _check_source_drift(artifacts, root)

    return {"status_icon": "?", "detail": f"Unknown check: {check_name}",
            "blocking_count": 0, "warning_count": 0}


def check_schema(
    artifacts: list[art_lib.Artifact],
    schema_dir: Path,
) -> dict[str, str | int]:
    """Validate all artifacts against their schemas."""
    schemas = lint_lib.load_schemas(schema_dir)
    # The global canonical-role union (D-18 frozen vocabulary): every role that
    # is whitelisted on ANY type. Passed into per-artifact validation so a role
    # used legitimately across types (e.g. derives_from on a CHL) is accepted
    # rather than mislabeled "Unknown".
    all_canonical_roles: set[str] = set()
    for s in schemas.values():
        all_canonical_roles.update(s.get("allowed_link_roles", []))
    blocking = 0
    warnings = 0
    details: list[str] = []
    # Cross-artifact collapse for non-canonical link roles: collect every role
    # flagged on any artifact, then emit ONE summary line per distinct role
    # (with the affected artifact count) instead of one-per-artifact. A role like
    # ``relates_to`` used project-wide should surface as a single normalization
    # task, not 160 identical warnings that train users to ignore lint output.
    role_groups: dict[str, set[str]] = {}

    for art in artifacts:
        schema = schemas.get(art.type)
        if not schema:
            warnings += 1
            details.append(f"  ⚠ Unknown type '{art.type}': {art.id}")
            continue

        issues = lint_lib.validate_artifact_schema(art, schema, all_canonical_roles)
        for issue in issues:
            if issue.get("code") == "link_role":
                role_groups.setdefault(issue["role"], set()).add(art.id)
                continue
            if issue["severity"] == "blocking":
                blocking += 1
                details.append(f"  ✗ [{art.id}] {issue['message']}")
            elif issue["severity"] == "warning":
                warnings += 1
                details.append(f"  ⚠ [{art.id}] {issue['message']}")

    for role, art_ids in sorted(role_groups.items()):
        warnings += 1
        suggestion = role_normalize.suggest_canonical(role)
        label = "Non-canonical" if suggestion else "Unknown"
        hint = f" — {suggestion.hint}" if suggestion else ""
        sample_ids = sorted(art_ids)[:3]
        sample = ", ".join(sample_ids)
        more = f" (+{len(art_ids) - len(sample_ids)} more)" if len(art_ids) > len(sample_ids) else ""
        details.append(
            f'  ⚠ {label} link role "{role}" on {len(art_ids)} artifact(s) '
            f"({sample}{more}){hint}"
        )

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

    # Orphans (SPIKEs exempt — they're expected to be standalone research)
    orphans = art_lib.find_orphans(artifacts)
    spike_orphans = [a for a in orphans if art_lib.get_prefix_from_id(a.id) == "SPIKE"]
    non_spike_orphans = [a for a in orphans if art_lib.get_prefix_from_id(a.id) != "SPIKE"]
    if non_spike_orphans:
        warnings += len(non_spike_orphans)
        orphan_ids = ", ".join(a.id for a in non_spike_orphans[:5])
        if len(non_spike_orphans) > 5:
            orphan_ids += f" (+{len(non_spike_orphans) - 5} more)"
        details.append(f"  ⚠ {len(non_spike_orphans)} orphan(s) with no links: {orphan_ids}")
    if spike_orphans:
        details.append(f"  ℹ {len(spike_orphans)} SPIKE(s) with no links (expected for research artifacts)")

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


def _check_status_cascade(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Warn when a STORY is implemented/verified but linked specs lag behind.

    Also flags (as blocking) when a STORY beyond draft has linked specs still
    in draft \u2014 implementation against unapproved specs violates the no-self-
    approval rule.
    """
    id_index = art_lib.build_id_index(artifacts)
    blocking = 0
    warnings = 0
    details: list[str] = []

    stories = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "STORY"]

    for story in stories:
        # Check: STORY beyond draft with linked specs still in draft
        if story.status in ("approved", "implemented", "verified"):
            for link in story.links:
                target = id_index.get(link.target)
                if target is None:
                    continue
                target_prefix = art_lib.get_prefix_from_id(target.id)
                if target_prefix in _SPEC_PREFIXES and target.status == "draft":
                    blocking += 1
                    details.append(
                        f"  \u2717 [{story.id}] is '{story.status}' but linked "
                        f"{target.id} ({target_prefix}) is still 'draft' -- "
                        f"specs must be approved before implementation"
                    )

        if story.status not in ("implemented", "verified"):
            continue

        for link in story.links:
            target = id_index.get(link.target)
            if target is None:
                continue

            target_prefix = art_lib.get_prefix_from_id(target.id)

            if link.role == "guided_by" and target_prefix == "ARCH":
                if target.status == "approved":
                    warnings += 1
                    details.append(
                        f"  \u26a0 [{story.id}] is '{story.status}' but linked "
                        f"{target.id} (ARCH) is still 'approved' -- run "
                        f"`specflow cascade-status {story.id}`"
                    )

            elif link.role == "specified_by" and target_prefix == "DDD":
                if target.status == "approved":
                    warnings += 1
                    details.append(
                        f"  \u26a0 [{story.id}] is '{story.status}' but linked "
                        f"{target.id} (DDD) is still 'approved' -- run "
                        f"`specflow cascade-status {story.id}`"
                    )

        if story.status == "verified":
            for link in story.links:
                target = id_index.get(link.target)
                if target is None:
                    continue
                if link.role in ("implements", "derives_from") and art_lib.get_prefix_from_id(target.id) == "REQ":
                    if target.status == "approved":
                        warnings += 1
                        details.append(
                            f"  \u26a0 [{story.id}] is 'verified' but linked "
                            f"{target.id} (REQ) is still 'approved' -- update REQ status"
                        )

    icon = GREEN + "\u2713" + NC if blocking == 0 and warnings == 0 else (
        RED + "\u2717" + NC if blocking > 0 else YELLOW + "\u26a0" + NC
    )
    detail_msg = "\n".join(details) if details else "All linked spec statuses consistent with stories"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


# Spec prefixes that satisfy STORY linkage requirement.
_SPEC_PREFIXES = {"REQ", "ARCH", "DDD"}


def _check_story_linkage(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Enforce that every STORY links to at least one spec artifact (REQ/ARCH/DDD).

    STORY without spec linkage is research \u2014 it should be a SPIKE instead.
    Stories in 'draft' status are given a warning; stories beyond draft get a
    blocking error since they are being acted on without traced requirements.
    """
    blocking = 0
    warnings = 0
    details: list[str] = []

    stories = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "STORY"]

    for story in stories:
        has_spec_link = False
        for link in story.links:
            target_prefix = art_lib.get_prefix_from_id(link.target)
            if target_prefix in _SPEC_PREFIXES:
                has_spec_link = True
                break

        if not has_spec_link:
            if story.status == "draft":
                warnings += 1
                details.append(
                    f"  \u26a0 [{story.id}] has no spec linkage (link to a "
                    f"REQ/ARCH/DDD, or convert to SPIKE if this is research)"
                )
            else:
                blocking += 1
                details.append(
                    f"  \u2717 [{story.id}] '{story.status}' with no spec linkage \u2014 "
                    f"link to a REQ/ARCH/DDD or convert to SPIKE"
                )

    icon = GREEN + "\u2713" + NC if blocking == 0 and warnings == 0 else (
        RED + "\u2717" + NC if blocking > 0 else YELLOW + "\u26a0" + NC
    )
    detail_msg = "\n".join(details) if details else f"All {len(stories)} story/stories linked to spec artifacts"

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


# Leading list/numbering markers ("- ", "* ", "+ ", "1. ", "2) ") stripped
# before the NFR measurable-threshold digit scan, so an item's own ordinal
# doesn't get mistaken for a measurable value.
_AC_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)


def _check_acceptance(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Check that every REQ has non-empty acceptance criteria.

    Also warns (non-blocking) when an NFR-tagged REQ (frontmatter
    `non_functional_category` set) has acceptance criteria with no
    measurable threshold — this is a deterministic digit-presence check
    only; genuine semantic quality ("is this actually measurable?") needs
    a REQ review (CKL-REV-REQ-02), never a blocking lint gate.
    """
    blocking = 0
    warnings = 0
    details: list[str] = []

    # Find REQ artifacts by ID prefix (more reliable than type field)
    reqs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "REQ"]
    for art in reqs:
        if not lint_lib.has_acceptance_criteria(art):
            blocking += 1
            details.append(f"  ✗ [{art.id}] no acceptance criteria found")
            continue

        item_count = lint_lib.count_acceptance_criteria_items(art)
        if item_count == 0:
            blocking += 1
            details.append(f"  ✗ [{art.id}] empty Acceptance Criteria section (header only)")
            continue

        category = art.frontmatter.get("non_functional_category")
        # "functional" is not a non-functional category — some projects use the
        # field as triage bookkeeping for functional REQs; those get no NFR gate.
        if category and str(category).lower() != "functional":
            ac_text = lint_lib.acceptance_criteria_text(art)
            # Strip list/numbering markers first so "1. respond quickly" isn't
            # mistaken for a measurable threshold via its own item number.
            ac_text_stripped = _AC_LIST_MARKER_RE.sub("", ac_text)
            if not re.search(r"\d", ac_text_stripped):
                warnings += 1
                details.append(
                    f"  ⚠ [{art.id}] NFR ({category}) has no measurable threshold "
                    f"(no numeric value in AC) — deterministic check only; semantic "
                    f"quality needs a REQ review (CKL-REV-REQ-02)"
                )

    if blocking > 0:
        icon = RED + "✗" + NC
    elif warnings > 0:
        icon = YELLOW + "⚠" + NC
    else:
        icon = GREEN + "✓" + NC
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
    detail_msg = "; ".join(details) if details else (
        "No numeric-range REQ conflicts detected "
        "(semantic/logical conflicts need a REQ review: CKL-REV-REQ-03)"
    )

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def check_coverage(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Check REQ→ARCH→STORY→test coverage completeness at all V-model levels.

    STORY-anchored coverage metric (REQ-012 #2: 'STORY test coverage' = implemented
    stories with UT/IT/QT linked via ``verified_by``). This coexists BY DESIGN with
    ``find_missing_v_pairs()`` (the SPEC-anchored metric, REQ-013 / ARCH-008) —
    REQ-012 defines both; the two functions are not contradictory.

    For each approved REQ, verifies:
      - At least one ARCH links to it via 'derives_from'
      - At least one STORY links to it via 'implements'
    For each approved STORY, verifies:
      - At least one test at each required V-model level links via 'verified_by'
    """
    blocking = 0
    warnings = 0
    details: list[str] = []
    # Coverage-gap split for the project-audit exit-code gate (BP-005/006
    # accounting carve-out). Missing ARCH / missing STORY are STRUCTURAL V-model
    # gaps → stay escalating (concern="completeness" in project_audit). A STORY
    # implemented with no UT/IT/QT linked via verified_by is a TEST-VERIFICATION
    # linkage gap → accounting (concern="verification"). The combined
    # warning_count/detail below are unchanged so the `artifact-lint` CLI still
    # reports the full picture; the two *_warning_count keys let project_audit
    # route each bucket to the right concern.
    structural_warnings = 0
    structural_details: list[str] = []
    verification_warnings = 0
    verification_details: list[str] = []

    id_index = art_lib.build_id_index(artifacts)

    reqs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "REQ" and a.status in ("approved", "implemented", "verified")]
    stories = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "STORY"]
    archs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "ARCH"]
    tests_by_type: dict[str, list[art_lib.Artifact]] = {
        "unit-test": [], "integration-test": [], "qualification-test": [],
    }
    for a in artifacts:
        if a.type in tests_by_type:
            tests_by_type[a.type].append(a)

    req_to_archs: dict[str, list[art_lib.Artifact]] = {}
    for arch in archs:
        for link in arch.links:
            if link.role == "derives_from" and art_lib.get_prefix_from_id(link.target) == "REQ":
                req_to_archs.setdefault(link.target, []).append(arch)

    req_to_stories: dict[str, list[art_lib.Artifact]] = {}
    for story in stories:
        for link in story.links:
            if link.role in ("implements", "derives_from") and art_lib.get_prefix_from_id(link.target) == "REQ":
                req_to_stories.setdefault(link.target, []).append(story)

    for req in reqs:
        linked_archs = req_to_archs.get(req.id, [])
        if not linked_archs:
            msg = f"  ⚠ [{req.id}] no ARCH derives_from this approved requirement"
            warnings += 1
            structural_warnings += 1
            details.append(msg)
            structural_details.append(msg)

        linked_stories = req_to_stories.get(req.id, [])
        if not linked_stories:
            msg = f"  ⚠ [{req.id}] no STORY implements/derives_from this approved requirement"
            warnings += 1
            structural_warnings += 1
            details.append(msg)
            structural_details.append(msg)
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
                    msg = (
                        f"  ⚠ [{story.id}] no {prefix} linked via 'verified_by' "
                        f"(covers REQ {req.id})"
                    )
                    warnings += 1
                    verification_warnings += 1
                    details.append(msg)
                    verification_details.append(msg)

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "; ".join(details) if details else "All approved REQs have STORY and test coverage"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
        # Split buckets consumed by project_audit's _cross_cutting_analysis to
        # route structural vs test-verification gaps into separate concerns.
        "structural_warning_count": structural_warnings,
        "structural_detail": "; ".join(structural_details) if structural_details else "",
        "verification_warning_count": verification_warnings,
        "verification_detail": "; ".join(verification_details) if verification_details else "",
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
            # Reuse the canonical AC counter (counts bullets, checkboxes,
            # numbered, and Given/When/Then lines) so STORY and REQ agree on one
            # definition. The previous numbered-only regex flagged well-formed
            # bulleted / `- [x]` AC sections as "0 acceptance criteria", training
            # users to ignore this check.
            ac_count = lint_lib.count_acceptance_criteria_items(art)
            if ac_count > 8:
                warnings += 1
                details.append(f"  ⚠ [{art.id}] has {ac_count} acceptance criteria (max 8 recommended)")
            if ac_count < 2:
                warnings += 1
                details.append(f"  ⚠ [{art.id}] has {ac_count} acceptance criteria (minimum 2 recommended)")
        else:
            warnings += 1
            details.append(f"  ⚠ [{art.id}] has no Acceptance Criteria section")

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


_ARCH_SECTIONS = re.compile(
    r"^##\s+.*(Interface|Component|Responsibility|Data\s+Flow|Structure|Package|Module|Dependencies)",
    re.I | re.M,
)

_DDD_SECTIONS = re.compile(
    r"^##\s+.*(Function|Data\s+Structure|Algorithm|Error\s+Handling|Invariant|Precondition|Signature|Implementation)",
    re.I | re.M,
)

_ARCH_MIN_WORDS = 50
_DDD_MIN_WORDS = 100


def _check_spec_body(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Check ARCH and DDD artifacts for substantive body content.

    Warns on:
      - ARCH without structural headers (Interface, Component, etc.)
      - ARCH body under 50 words
      - DDD without design headers (Function, Algorithm, etc.)
      - DDD body under 100 words
    """
    warnings = 0
    details: list[str] = []

    for art in artifacts:
        prefix = art_lib.get_prefix_from_id(art.id)
        body = art.body.strip()
        word_count = len(body.split())

        if prefix == "ARCH":
            if word_count < _ARCH_MIN_WORDS:
                warnings += 1
                details.append(f"  ⚠ [{art.id}] body has {word_count} words (minimum {_ARCH_MIN_WORDS} for architecture)")
            if not _ARCH_SECTIONS.search(body):
                warnings += 1
                details.append(f"  ⚠ [{art.id}] missing structural headers (expected: Interface, Component, Responsibility, Data Flow, Structure, Package, Module, or Dependencies)")

        elif prefix == "DDD":
            if word_count < _DDD_MIN_WORDS:
                warnings += 1
                details.append(f"  ⚠ [{art.id}] body has {word_count} words (minimum {_DDD_MIN_WORDS} for detailed design)")
            if not _DDD_SECTIONS.search(body):
                warnings += 1
                details.append(f"  ⚠ [{art.id}] missing design headers (expected: Function, Data Structure, Algorithm, Error Handling, Invariant, Precondition, Signature, or Implementation)")

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "\n".join(details) if details else "All spec artifacts have substantive content"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": 0,
        "warning_count": warnings,
    }


def _check_output_files(
    artifacts: list[art_lib.Artifact],
    root: Path,
) -> dict[str, str | int]:
    """Verify that declared output_files exist on the filesystem.

    Literal paths resolve relative to project root. Glob patterns are expanded
    via `files.expand_output_files`; a glob that matches zero files is flagged
    (ambiguous — either the package was deleted or the pattern is a typo).
    """
    warnings = 0
    details: list[str] = []

    for art in artifacts:
        output_files = art.frontmatter.get("output_files")
        if not output_files or not isinstance(output_files, list):
            continue

        # Literal misses: declared file is gone.
        for missing in files_lib.literal_missing(root, output_files):
            warnings += 1
            details.append(f"  ⚠ [{art.id}] output file not found: {missing}")

        # Glob misses: pattern matched nothing (ambiguous; worth surfacing).
        for glob_entry in files_lib.glob_entries(output_files):
            if not files_lib.expand_output_files(root, [glob_entry]):
                warnings += 1
                details.append(f"  ⚠ [{art.id}] output_files glob matched nothing: {glob_entry}")

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "\n".join(details) if details else "All declared output files exist"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": 0,
        "warning_count": warnings,
    }


SPIDR_DIMENSIONS = {"spidr-spike", "spidr-path", "spidr-interface", "spidr-data", "spidr-rules"}


def _check_spidr_coverage(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Report when SPIDR dimensions have no stories, ensuring decomposition coverage."""
    warnings = 0
    details: list[str] = []

    stories = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "STORY"]

    if not stories:
        return {
            "status_icon": CYAN + "ℹ" + NC,
            "detail": "No stories found — SPIDR coverage check skipped",
            "blocking_count": 0,
            "warning_count": 0,
        }

    all_tags: set[str] = set()
    for s in stories:
        all_tags.update(t.lower() for t in s.tags)

    has_any_spidr = any(any(t.startswith("spidr-") for t in s.tags) for s in stories)

    for dim in sorted(SPIDR_DIMENSIONS):
        found = any(dim in t for t in all_tags)
        if not found:
            warnings += 1
            details.append(f"  ⚠ no stories found for SPIDR dimension '{dim}'. Stories may be incomplete.")

    if not has_any_spidr and stories:
        details.append("  ℹ no SPIDR dimension tags found on any story. Consider tagging stories during plan Step 5.")

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "\n".join(details) if details else f"All {len(SPIDR_DIMENSIONS)} SPIDR dimensions covered"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": 0,
        "warning_count": warnings,
    }


def _check_wave_cycles(
    artifacts: list[art_lib.Artifact],
    root: Path,
) -> dict[str, str | int]:
    """Detect circular dependencies between stories via wave computation."""
    from specflow.lib.waves import compute_waves

    warnings = 0
    details: list[str] = []

    stories = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "STORY"]

    if not stories:
        return {
            "status_icon": CYAN + "ℹ" + NC,
            "detail": "No stories found — wave cycle check skipped",
            "blocking_count": 0,
            "warning_count": 0,
        }

    result = compute_waves(stories)

    if not result.get("ok"):
        cycle = result.get("cycle", [])
        cycle_str = " -> ".join(cycle) if cycle else "unknown"
        warnings += 1
        details.append(f"  ⚠ circular dependency detected: {cycle_str}")

    if result.get("ok") and result.get("waves"):
        waves = result["waves"]
        details.append(f"  ℹ {len(stories)} stories in {len(waves)} wave(s)")
        for i, wave in enumerate(waves):
            details.append(f"    wave {i + 1}: {', '.join(wave)}")

    dep_counts: dict[str, int] = {}
    for s in stories:
        count = sum(1 for link in s.links if link.role in ("derives_from", "depends_on") and art_lib.get_prefix_from_id(link.target) == "STORY")
        if count > 0:
            dep_counts[s.id] = count

    for sid, count in sorted(dep_counts.items(), key=lambda x: -x[1]):
        if count >= 4:
            warnings += 1
            details.append(f"  ⚠ {sid} has {count} dependencies, consider restructuring")

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "\n".join(details) if details else f"All {len(stories)} stories have valid dependency ordering"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": 0,
        "warning_count": warnings,
    }


_COMPLIANCE_MIN_WORDS = 50
_KEYWORD_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "shall", "should", "may", "might", "can", "could", "must", "this", "that",
    "these", "those", "it", "its", "such", "any", "all", "each", "every",
    "no", "not", "than", "then", "so", "if", "when", "where", "which", "who",
    "whom", "whose", "what", "how", "why",
}


def _extract_clause_keywords(clause: dict) -> set[str]:
    """Pull substantive keyword tokens from a clause's title and category.

    Lowercased, alphanumeric-only, ≥4 chars, stopwords excluded. The returned
    set is used to verify a complies_with artifact's body actually addresses
    the clause rather than just linking to it.
    """
    text = " ".join([
        str(clause.get("title", "")),
        str(clause.get("category", "")),
    ])
    tokens: set[str] = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9]*", text):
        token = raw.lower()
        if len(token) < 4 or token in _KEYWORD_STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def _check_compliance_evidence(
    artifacts: list[art_lib.Artifact],
    root: Path,
) -> dict[str, str | int]:
    """Validate that complies_with links are backed by substantive content.

    Today the `links` check accepts any complies_with target that resolves to
    an installed clause ID, so an empty REQ can claim ISO conformance. This
    check raises warnings when:
      - artifact body is below _COMPLIANCE_MIN_WORDS, OR
      - body shares no substantive keyword with the clause title/category.

    Strict mode (config: lint.compliance_evidence_strict=true) escalates these
    to blocking errors; default is warning-only so existing repos don't break
    on upgrade. Clauses that resolve via standards but have no extractable
    keywords are word-count-only.
    """
    from specflow.lib import standards as standards_lib
    from specflow.lib import config as config_lib

    cfg = config_lib.read_config(root) or {}
    strict = bool(cfg.get("lint", {}).get("compliance_evidence_strict", False))

    blocking = 0
    warnings = 0
    details: list[str] = []

    clause_cache: dict[str, dict | None] = {}

    def _bump(msg: str) -> None:
        nonlocal blocking, warnings
        if strict:
            blocking += 1
            details.append(f"  ✗ {msg}")
        else:
            warnings += 1
            details.append(f"  ⚠ {msg}")

    for art in artifacts:
        complies_links = [link for link in art.links if link.role == "complies_with" and link.target]
        if not complies_links:
            continue

        body = art.body.strip()
        word_count = len(body.split())
        body_lower = body.lower()

        if word_count < _COMPLIANCE_MIN_WORDS:
            _bump(
                f"[{art.id}] complies_with present but body has only {word_count} "
                f"words (≥{_COMPLIANCE_MIN_WORDS} recommended for substantive evidence)"
            )

        for link in complies_links:
            if link.target not in clause_cache:
                clause_cache[link.target] = standards_lib.get_clause_by_id(root, link.target)
            clause = clause_cache[link.target]
            if not clause:
                continue
            keywords = _extract_clause_keywords(clause)
            if not keywords:
                continue
            if not any(kw in body_lower for kw in keywords):
                kw_sample = ", ".join(sorted(keywords)[:5])
                _bump(
                    f"[{art.id}] body does not reference any keyword from "
                    f"clause '{link.target}' (expected one of: {kw_sample})"
                )

    if blocking == 0 and warnings == 0:
        icon = GREEN + "✓" + NC
        detail_msg = "All complies_with links are backed by substantive content"
    elif blocking > 0:
        icon = RED + "✗" + NC
        detail_msg = "\n".join(details)
    else:
        icon = YELLOW + "⚠" + NC
        detail_msg = "\n".join(details)

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


def _check_thinking_techniques(
    artifacts: list[art_lib.Artifact],
) -> dict[str, str | int]:
    """Warn on approved REQ/ARCH/DDD artifacts that were never challenged."""
    SPEC_TYPES = {"requirement", "architecture", "detailed-design"}
    CHALLENGED_STATUSES = {"approved", "implemented", "verified"}
    warnings = 0
    details: list[str] = []

    for art in artifacts:
        if art.type not in SPEC_TYPES:
            continue
        if art.status not in CHALLENGED_STATUSES:
            continue
        techniques = art.frontmatter.get("thinking_techniques")
        if not techniques:
            warnings += 1
            details.append(
                f"  ⚠ {art.id} [{art.status}] has no thinking_techniques recorded "
                f"(never challenged)"
            )

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "\n".join(details) if details else "All spec artifacts challenged"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": 0,
        "warning_count": warnings,
    }


def _check_autoresearch_logging(
    artifacts: list[art_lib.Artifact],
    root: Path,
) -> dict[str, str | int]:
    """Warn when autoresearch EXPTs are missing domain-recommended logging fields.

    Checks:
      - Kept EXPTs under a COMP with `domain` should have recommended auxiliary_metrics
      - Discarded/crashed EXPTs should have failure_analysis
      - Kept EXPTs with change_category in (model, params) should have parameters logged
      - Non-draft EXPTs should record a falsifiable hypothesis; kept ones its outcome

    Strict mode (config: lint.autoresearch_logging_strict=true) escalates these
    to blocking errors; default is warning-only so existing repos don't break on
    upgrade. Mirrors the compliance_evidence_strict pattern.
    """
    from specflow.lib import config as config_lib

    cfg = config_lib.read_config(root) or {}
    strict = bool(cfg.get("lint", {}).get("autoresearch_logging_strict", False))

    blocking = 0
    warnings = 0
    details: list[str] = []

    def _bump(msg: str) -> None:
        nonlocal blocking, warnings
        if strict:
            blocking += 1
            details.append(f"  ✗ {msg}")
        else:
            warnings += 1
            details.append(f"  ⚠ {msg}")

    # Build COMP domain index
    comp_domains: dict[str, str] = {}
    for art in artifacts:
        if art_lib.get_prefix_from_id(art.id) == "COMP":
            domain = art.frontmatter.get("domain")
            if domain:
                comp_domains[art.id] = domain

    for art in artifacts:
        if art_lib.get_prefix_from_id(art.id) != "EXPT":
            continue

        comp_id = art.frontmatter.get("competition")
        if not comp_id:
            # Try to resolve via LOOP link
            loop_id = art.frontmatter.get("loop")
            if loop_id:
                for a in artifacts:
                    if a.id == loop_id:
                        comp_id = a.frontmatter.get("competition")
                        break

        domain = comp_domains.get(comp_id) if comp_id else None
        status = art.status
        aux = art.frontmatter.get("auxiliary_metrics") or {}
        cat = art.frontmatter.get("change_category", "")

        if status == "kept" and domain:
            recs = DOMAIN_RECOMMENDED.get(domain, [])
            missing = [f for f in recs if f not in aux]
            if missing:
                _bump(
                    f"[{art.id}] missing recommended aux metrics for domain '{domain}': {', '.join(missing[:3])}"
                )

        if status == "kept" and cat in ("model", "params") and not art.frontmatter.get("parameters"):
            _bump(
                f"[{art.id}] (kept, change_category={cat}) has no `parameters` logged"
            )

        if status in ("discarded", "crashed") and not art.frontmatter.get("failure_analysis"):
            _bump(
                f"[{art.id}] ({status}) has no `failure_analysis` logged"
            )

        # Structured reasoning fields: the protocol mandates a falsifiable
        # hypothesis per EXPT, and a kept result should record whether it held.
        # Without these, FIND→REQ promotion and cross-EXPT synthesis can't fire
        # (the documented recipe and suggest-finds both read them). Gated to
        # non-draft EXPTs so a mid-authoring draft isn't nagged — consistent with
        # every neighboring status-gated check and with the cry-wolf theme this
        # workstream exists to serve (ungated, this alone adds ~84 warnings on a
        # heavy autoresearch project).
        if status != "draft" and not art.frontmatter.get("hypothesis"):
            _bump(
                f"[{art.id}] has no `hypothesis` logged (state the falsifiable hypothesis)"
            )
        elif status == "kept" and not art.frontmatter.get("hypothesis_outcome"):
            _bump(
                f"[{art.id}] (kept) has no `hypothesis_outcome` logged "
                f"(supported/not_supported/inconclusive)"
            )

    if blocking == 0 and warnings == 0:
        icon = GREEN + "✓" + NC
        detail_msg = "All autoresearch EXPTs have recommended logging fields"
    elif blocking > 0:
        icon = RED + "✗" + NC
        detail_msg = "\n".join(details)
    else:
        icon = YELLOW + "⚠" + NC
        detail_msg = "\n".join(details)

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": blocking,
        "warning_count": warnings,
    }


# ── SPIKE lifecycle defaults ──────────────────────────────────────
_DEFAULT_SPIKE_AGE_DAYS = 30
_MIN_ZOMBIE_WORD_COUNT = 100
_REPEATED_TAG_THRESHOLD = 3


def _check_spike_lifecycle(
    artifacts: list[art_lib.Artifact],
    root: Path,
) -> dict[str, str | int]:
    """Detect SPIKE lifecycle issues: stale, zombie, and repeated-topic patterns.

    Sub-checks:
      - Stale: draft/approved SPIKE older than its timebox (or 30 days default).
      - Zombie: completed SPIKE with substantive body but no derives_from link
        to a non-SPIKE artifact — findings produced but never acted on.
      - Repeated topic: 3+ SPIKEs sharing the same tag — pattern of repeated
        exploration that should consolidate into a proper requirement.
    """
    warnings = 0
    details: list[str] = []
    now = datetime.now(timezone.utc)

    spikes = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "SPIKE"]

    if not spikes:
        return {
            "status_icon": GREEN + "✓" + NC,
            "detail": "No SPIKEs found",
            "blocking_count": 0,
            "warning_count": 0,
        }

    # Build a set of non-SPIKE artifact IDs for zombie detection
    non_spike_ids = {a.id for a in artifacts if art_lib.get_prefix_from_id(a.id) != "SPIKE"}

    # ── Stale detection ───────────────────────────────────────────
    for sp in spikes:
        if sp.status not in ("draft", "approved"):
            continue

        created_str = sp.frontmatter.get("created", "")
        if not created_str:
            continue

        try:
            if isinstance(created_str, datetime):
                created_dt = created_str
            else:
                raw = str(created_str)
                try:
                    created_dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    created_dt = datetime.strptime(raw, "%Y-%m-%d")
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

        age_days = (now - created_dt).days
        timebox_str = sp.frontmatter.get("timebox")
        if timebox_str:
            try:
                timebox_days = int(timebox_str)
            except (ValueError, TypeError):
                timebox_days = _DEFAULT_SPIKE_AGE_DAYS
        else:
            timebox_days = _DEFAULT_SPIKE_AGE_DAYS

        if age_days > timebox_days:
            warnings += 1
            details.append(
                f"  ⚠ [{sp.id}] stale: {sp.status} for {age_days} days "
                f"(timebox: {timebox_days}d)"
            )

    # ── Zombie detection ──────────────────────────────────────────
    for sp in spikes:
        if sp.status != "completed":
            continue

        body = sp.body or ""
        word_count = len(body.split())
        if word_count < _MIN_ZOMBIE_WORD_COUNT:
            continue  # Short body — probably a no-finding SPIKE, which is fine

        # Check if anything non-SPIKE links TO this SPIKE via derives_from
        has_downstream = False
        for art in artifacts:
            if art_lib.get_prefix_from_id(art.id) == "SPIKE":
                continue
            for link in art.links:
                if link.target == sp.id and link.role == "derives_from":
                    has_downstream = True
                    break
            if has_downstream:
                break

        if not has_downstream:
            warnings += 1
            details.append(
                f"  ⚠ [{sp.id}] zombie: completed with {word_count} words of findings "
                f"but nothing links to it via derives_from"
            )

    # ── Repeated-topic detection ──────────────────────────────────
    tag_counter: Counter[str] = Counter()
    tag_spikes: dict[str, list[str]] = {}
    for sp in spikes:
        tags = sp.frontmatter.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tags:
            tag_counter[tag] += 1
            tag_spikes.setdefault(tag, []).append(sp.id)

    for tag, count in tag_counter.items():
        if count >= _REPEATED_TAG_THRESHOLD:
            spike_ids = ", ".join(tag_spikes[tag][:5])
            details.append(
                f"  ℹ {count} SPIKEs share tag '{tag}': {spike_ids} — "
                f"consider consolidating into a requirement"
            )

    icon = GREEN + "✓" + NC if warnings == 0 else YELLOW + "⚠" + NC
    detail_msg = "\n".join(details) if details else f"All {len(spikes)} SPIKEs lifecycle-healthy"

    return {
        "status_icon": icon,
        "detail": detail_msg,
        "blocking_count": 0,
        "warning_count": warnings,
    }


# ── Source-file drift detection ────────────────────────────────────


def _hash_file_content(path: Path) -> str:
    """Compute SHA256 hex digest of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _load_source_fingerprints(root: Path) -> dict[str, dict[str, str]]:
    """Load stored source fingerprints from .specflow/source-fingerprints.yaml."""
    fp_path = root / files_lib.SOURCE_FP_FILE
    if not fp_path.exists():
        return {}
    try:
        data = yaml.safe_load(fp_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_source_fingerprints(root: Path, data: dict[str, dict[str, str]]) -> None:
    """Save source fingerprints to .specflow/source-fingerprints.yaml."""
    fp_path = root / files_lib.SOURCE_FP_FILE
    fp_path.parent.mkdir(parents=True, exist_ok=True)
    fp_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=True), encoding="utf-8")


def _check_source_drift(
    artifacts: list[art_lib.Artifact],
    root: Path,
) -> dict[str, str | int]:
    """Detect when output_files have changed but the artifact is not suspect-flagged.

    Compares current file hashes against stored source fingerprints in
    .specflow/source-fingerprints.yaml. Warns if a file hash has changed
    and the governing artifact is not already suspect.

    Glob patterns in `output_files` are expanded via `files.expand_output_files`
    so an ARCH/STORY covering a package glob is drift-checked for every file
    the glob matches. The stored fingerprint key is the glob string itself;
    all files under a glob are hashed together (any change triggers drift).

    First run: if no fingerprint file exists but at least one artifact declares
    output_files, the check silently seeds the file with current hashes and
    returns 0 warnings. Re-run on the next commit to detect drift.

    To re-seed fingerprints after reviewing changes, delete
    ``.specflow/source-fingerprints.yaml`` and re-run.
    """
    stored = _load_source_fingerprints(root)
    current: dict[str, dict[str, str]] = {}
    warnings = 0
    details: list[str] = []
    seeded = False

    for art in artifacts:
        output_files = art.frontmatter.get("output_files")
        if not output_files or not isinstance(output_files, list):
            continue

        art_hashes: dict[str, str] = {}
        # Expand globs + literals into concrete files via the shared helper.
        for resolved in files_lib.expand_output_files(root, output_files):
            try:
                rel = str(resolved.relative_to(root.resolve()))
            except ValueError:
                rel = str(resolved)
            current_hash = _hash_file_content(resolved)
            art_hashes[rel] = current_hash

            stored_hash = (stored.get(art.id) or {}).get(rel)
            if stored_hash and stored_hash != current_hash and not art.suspect:
                warnings += 1
                details.append(
                    f"  ⚠ [{art.id}] source file changed: {rel} "
                    f"(stored: {stored_hash}, now: {current_hash}) — "
                    f"artifact is not suspect-flagged"
                )

        if art_hashes:
            current[art.id] = art_hashes

    fp_path = root / files_lib.SOURCE_FP_FILE
    if not stored and current:
        _save_source_fingerprints(root, current)
        seeded = True
        details.append(
            f"  ℹ Seeded source fingerprints for {len(current)} artifact(s) "
            f"→ {fp_path.relative_to(root)}. Re-run to detect drift."
        )

    icon = GREEN + "✓" + NC if warnings == 0 and not seeded else (
        YELLOW + "⚠" + NC if warnings > 0 else CYAN + "ℹ" + NC
    )
    detail_msg = "\n".join(details) if details else "No source-file drift detected"

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
        print("   Run 'specflow init' first.")
        return 1

    # --method llm is deprecated: all checks are now self-contained and deterministic.
    # If someone passes --method llm, fall through to programmatic checks.
    method = args.get("method", "programmatic")

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
            print(f"  {YELLOW}○{NC} [{item_id}] {check_desc} (agent-judged, skipped by programmatic runner)")
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

