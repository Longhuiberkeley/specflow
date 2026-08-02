"""Python-backed validation logic for SpecFlow artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import artifacts as art_lib


__all__ = [
    "load_schemas",
    "validate_artifact_schema",
    "validate_status_hierarchy",
    "validate_fingerprint",
    "has_acceptance_criteria",
    "acceptance_criteria_text",
    "count_acceptance_criteria_items",
    "recompute_fingerprint",
    "discover_checklists",
    "run_automated_checklist",
]


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

def load_schemas(schema_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all schema YAML files from the schema directory.

    Returns a dict mapping type name -> schema dict.
    """
    schemas: dict[str, dict[str, Any]] = {}
    if not schema_dir.exists():
        return schemas

    for f in sorted(schema_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "type" in data:
                schemas[data["type"]] = data
        except Exception:
            # Skip malformed schemas — they will be reported elsewhere
            pass

    return schemas


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def validate_artifact_schema(
    artifact: art_lib.Artifact,
    schema: dict[str, Any],
    all_canonical_roles: set[str] | None = None,
) -> list[dict[str, str]]:
    """Validate a single artifact against its schema.

    Returns a list of issue dicts with keys: severity, message.
    severity is one of: 'blocking', 'warning', 'info'

    ``all_canonical_roles`` (optional) is the union of every type's
    ``allowed_link_roles``. When provided, a link role that is canonical on
    *some* type but absent from *this* type's whitelist is treated as
    legitimate cross-type usage and accepted silently — never mislabeled
    "Unknown" (see the link-role block below).
    """
    issues: list[dict[str, str]] = []
    fm = artifact.frontmatter

    # Required fields
    for field_name in schema.get("required_fields", []):
        if field_name not in fm:
            issues.append({
                "severity": "blocking",
                "message": f'Missing required field "{field_name}"',
            })

    # ID format — accept either the schema's format or the draft-ID format.
    # Draft IDs (e.g. REQ-AUTH-a7b9) are generated on feature branches and
    # renumbered to sequential integers by `specflow renumber-drafts` on merge.
    art_id = fm.get("id", "")
    id_fmt = schema.get("id_format")
    if id_fmt and art_id and not re.match(id_fmt, art_id):
        from specflow.lib import draft_ids as _draft
        if not _draft.is_draft_id(art_id):
            issues.append({
                "severity": "blocking",
                "message": f'Invalid ID format "{art_id}" (expected pattern: {id_fmt})',
            })

    # Status allowed values
    status = fm.get("status", "")
    allowed = schema.get("allowed_status", {})
    if status and status not in allowed:
        issues.append({
            "severity": "blocking",
            "message": f'Invalid status "{status}" (allowed: {", ".join(allowed)})',
        })

    # Link role validation. Non-canonical/unknown roles are a warning, never a
    # blocker (accounting, not policing). Three cases for a role outside this
    # type's ``allowed_link_roles``:
    #   - canonical on SOME other type (in ``all_canonical_roles``) → accepted
    #     silently. It's legitimate cross-type usage; warning here is itself a
    #     cry-wolf. D-18 stays frozen — we recognize existing canonical roles,
    #     never bless new ones (e.g. ``derives_from`` on a CHL/REVIEW/AUD).
    #   - recognized near-miss (role_normalize maps it) → "Non-canonical" with
    #     an actionable hint, so the message stops self-contradicting.
    #   - everything else → truly "Unknown".
    # Repeated same-role links on one artifact collapse into a single counted
    # warning; the cross-artifact collapse happens in check_schema().
    allowed_roles = schema.get("allowed_link_roles", [])
    if allowed_roles:
        from specflow.lib import role_normalize
        noncanonical: dict[str, list[str]] = {}
        for link in artifact.links:
            if not link.role or link.role in allowed_roles:
                continue
            if all_canonical_roles and link.role in all_canonical_roles:
                continue
            noncanonical.setdefault(link.role, []).append(link.target)
        for role, targets in noncanonical.items():
            suggestion = role_normalize.suggest_canonical(role)
            if suggestion:
                label = "Non-canonical"
                hint = f" — {suggestion.hint}"
            else:
                label = "Unknown"
                hint = ""
            issues.append({
                "severity": "warning",
                "message": (
                    f'{label} link role "{role}" on {len(targets)} link(s) '
                    f'(e.g. {targets[0]}){hint}'
                ),
                "code": "link_role",
                "role": role,
            })

    # review_status validation
    review_status = fm.get("review_status")
    allowed_review = schema.get("allowed_review_status", [])
    if review_status and allowed_review and review_status not in allowed_review:
        issues.append({
            "severity": "blocking",
            "message": f'Invalid review_status "{review_status}" '
                       f'(allowed: {", ".join(allowed_review)})',
        })

    # Unknown fields (warning only)
    known_fields = set(schema.get("required_fields", [])) | set(schema.get("optional_fields", []))
    for key in fm:
        if key not in known_fields and key not in ("id", "title", "type", "status"):
            # Only flag if it looks like a user field (not a known meta field)
            known_meta = {"created", "modified", "version", "priority", "rationale",
                          "tags", "suspect", "fingerprint", "links", "upstream",
                          "checklists_applied", "edge_cases_identified", "execution_wave",
                          "non_functional_category", "output_files", "thinking_techniques",
                          "verify_command", "verify_evidence", "verify_exit_code",
                          "verify_run_exit_code", "verify_run_out_hash", "verify_run_at",
                          "verify_run_git_ref", "verify_run_command_hash",
                          "verify_run_evidence_hash", "verify_run_evidence_mtime"}
            if key not in known_meta:
                issues.append({
                    "severity": "info",
                    "message": f'Unknown field "{key}"',
                })

    return issues


# ---------------------------------------------------------------------------
# Status validation
# ---------------------------------------------------------------------------

VALID_STATUS_ORDER = ["draft", "approved", "implemented", "verified"]

# Terminal states sit outside the linear lifecycle: the artifact is retired, not
# in flight. A retired child must not hold its parent back, and ordering
# comparisons against a retired parent are meaningless.
TERMINAL_STATUSES = {"cancelled", "deprecated", "superseded"}


def _validate_status_transition(current: str, expected: str) -> bool:
    """Check if a status is valid (exists in the lifecycle)."""
    return expected in VALID_STATUS_ORDER


def validate_status_hierarchy(artifacts: list[art_lib.Artifact]) -> list[dict[str, str]]:
    """Validate parent/child status consistency.

    Rule: parent can't be 'verified' unless all children are 'verified'.
    """
    issues: list[dict[str, str]] = []
    id_index = art_lib.build_id_index(artifacts)

    for art in artifacts:
        parent_id = art_lib.get_base_id(art.id)
        if parent_id == art.id:
            # This is a root artifact, check its children
            children = [
                a for a in artifacts
                if a.id != art.id and art_lib.get_base_id(a.id) == art.id
            ]
            if children and art.status == "verified":
                non_verified = [
                    c.id for c in children
                    if c.status != "verified" and c.status not in TERMINAL_STATUSES
                ]
                if non_verified:
                    issues.append({
                        "severity": "blocking",
                        "message": (
                            f"{art.id} is 'verified' but children are not: "
                            f"{', '.join(non_verified)}"
                        ),
                    })
        else:
            # This is a child — check its own status isn't ahead of parent
            parent = id_index.get(parent_id)
            if parent and parent.status not in TERMINAL_STATUSES:
                parent_idx = VALID_STATUS_ORDER.index(parent.status) if parent.status in VALID_STATUS_ORDER else -1
                child_idx = VALID_STATUS_ORDER.index(art.status) if art.status in VALID_STATUS_ORDER else -1
                if child_idx > parent_idx:
                    issues.append({
                        "severity": "blocking",
                        "message": (
                            f"{art.id} status '{art.status}' is ahead of "
                            f"parent {parent_id} status '{parent.status}'"
                        ),
                    })

    return issues


# ---------------------------------------------------------------------------
# Fingerprint validation
# ---------------------------------------------------------------------------

def validate_fingerprint(artifact: art_lib.Artifact) -> dict[str, Any]:
    """Validate the content fingerprint of an artifact.

    Returns dict with keys: match (bool), expected (str), actual (str).
    """
    stored = artifact.fingerprint
    actual = art_lib.compute_fingerprint(artifact.body)

    return {
        "match": stored == actual,
        "expected": stored,
        "actual": actual,
    }


def recompute_fingerprint(artifact: art_lib.Artifact) -> str:
    """Recompute and return the fingerprint string for an artifact."""
    return art_lib.compute_fingerprint(artifact.body)


# ---------------------------------------------------------------------------
# Acceptance criteria check
# ---------------------------------------------------------------------------

_AC_MARKERS = (
    "## acceptance criteria",
    "##acceptance criteria",
    "### acceptance criteria",
    "###acceptance criteria",
    "acceptance criteria:",
    "acceptance criteria\n",
)

_AC_GIVEN_PATTERN = re.compile(r"^\d+\.\s+given", re.MULTILINE | re.IGNORECASE)

# Section boundary: the next ##-level heading after the Acceptance Criteria
# marker. Mirrors the convention already used by _check_story_size in
# artifact_lint.py for locating the end of an AC section.
_NEXT_HEADING_RE = re.compile(r"^##\s", re.MULTILINE)


def has_acceptance_criteria(artifact: art_lib.Artifact) -> bool:
    """Check if a REQ artifact has acceptance criteria in its body."""
    if artifact.type != "requirement":
        return True  # Non-REQ artifacts don't need acceptance criteria

    body_lower = artifact.body.lower()
    # Check for common acceptance criteria headers
    for marker in _AC_MARKERS:
        if marker in body_lower:
            return True

    # Also check for numbered criteria patterns
    if _AC_GIVEN_PATTERN.search(artifact.body):
        return True

    return False


def acceptance_criteria_text(artifact: art_lib.Artifact) -> str:
    """Return the raw text of the Acceptance Criteria section, or "" if absent.

    Locates the earliest Acceptance Criteria marker (same markers as
    ``has_acceptance_criteria``) and returns everything up to the next
    ##-level heading. Used to detect empty sections (header with no content
    below it) and to inspect NFR criteria for measurable thresholds.
    """
    body = artifact.body
    body_lower = body.lower()

    start = -1
    for marker in _AC_MARKERS:
        idx = body_lower.find(marker)
        if idx != -1 and (start == -1 or idx < start):
            start = idx

    if start == -1:
        return ""

    # Skip past the rest of the marker's own line.
    line_end = body.find("\n", start)
    rest = body[line_end + 1:] if line_end != -1 else ""

    next_heading = _NEXT_HEADING_RE.search(rest)
    return rest[:next_heading.start()] if next_heading else rest


def count_acceptance_criteria_items(artifact: art_lib.Artifact) -> int:
    """Count content items under the Acceptance Criteria section.

    An item is any non-empty, non-heading line under the section — a
    markdown list entry (``- ``, ``* ``, ``+ ``), a numbered entry
    (``1.`` etc.), or a plain non-empty paragraph line. Deterministic and
    simple by design: this is a presence/emptiness check, not a semantic
    quality judgement (that belongs to a REQ review checklist).

    Falls back to counting numbered "Given ..." lines anywhere in the body
    when no explicit header marker is found, matching the fallback already
    used by ``has_acceptance_criteria``.
    """
    section = acceptance_criteria_text(artifact)
    if not section:
        return len(_AC_GIVEN_PATTERN.findall(artifact.body))

    count = 0
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


# ---------------------------------------------------------------------------
# Checklist loading and execution
# ---------------------------------------------------------------------------

def discover_checklists(checklists_dir: Path, category: str = "") -> list[Path]:
    """Discover checklist YAML files in a category subdirectory.

    Args:
        checklists_dir: Base checklists directory (.specflow/checklists)
        category: Subdirectory (phase-gates, in-process, readiness, etc.)

    Returns:
        Sorted list of checklist file paths.
    """
    target = checklists_dir / category if category else checklists_dir
    if not target.exists():
        return []
    return sorted(target.glob("*.yaml"))


def run_automated_checklist(checklist: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    """Run all automated items in a checklist.

    Returns a list of result dicts with keys: id, check, passed, severity, output.
    """
    import subprocess

    results = []
    for item in checklist.get("items", []):
        if not item.get("automated", False):
            continue

        script = item.get("script", "")
        if not script:
            results.append({
                "id": item.get("id", "unknown"),
                "check": item.get("check", ""),
                "passed": False,
                "severity": item.get("severity", "blocking"),
                "output": "No script defined",
            })
            continue

        try:
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            results.append({
                "id": item.get("id", "unknown"),
                "check": item.get("check", ""),
                "passed": result.returncode == 0,
                "severity": item.get("severity", "blocking"),
                "output": result.stdout.strip() or result.stderr.strip(),
            })
        except subprocess.TimeoutExpired:
            results.append({
                "id": item.get("id", "unknown"),
                "check": item.get("check", ""),
                "passed": False,
                "severity": item.get("severity", "blocking"),
                "output": "Script timed out after 60s",
            })
        except Exception as e:
            results.append({
                "id": item.get("id", "unknown"),
                "check": item.get("check", ""),
                "passed": False,
                "severity": item.get("severity", "blocking"),
                "output": str(e),
            })

    return results
