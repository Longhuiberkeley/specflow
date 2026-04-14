"""Python-backed validation logic for SpecFlow artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import artifacts as art_lib


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


def load_schema_for_type(schema_dir: Path, artifact_type: str) -> dict[str, Any] | None:
    """Load a single schema by type name or prefix."""
    schemas = load_schemas(schema_dir)
    if artifact_type in schemas:
        return schemas[artifact_type]

    # Try resolving from prefix
    if artifact_type.upper() in art_lib.PREFIX_TO_TYPE:
        type_name = art_lib.PREFIX_TO_TYPE[artifact_type.upper()]
        return schemas.get(type_name)

    return None


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def validate_artifact_schema(
    artifact: art_lib.Artifact,
    schema: dict[str, Any],
) -> list[dict[str, str]]:
    """Validate a single artifact against its schema.

    Returns a list of issue dicts with keys: severity, message.
    severity is one of: 'blocking', 'warning', 'info'
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

    # Link role validation
    allowed_roles = schema.get("allowed_link_roles", [])
    if allowed_roles:
        for link in artifact.links:
            if link.role and link.role not in allowed_roles:
                issues.append({
                    "severity": "warning",
                    "message": f'Unknown link role "{link.role}" on link to {link.target}',
                })

    # Unknown fields (warning only)
    known_fields = set(schema.get("required_fields", [])) | set(schema.get("optional_fields", []))
    for key in fm:
        if key not in known_fields and key not in ("id", "title", "type", "status"):
            # Only flag if it looks like a user field (not a known meta field)
            known_meta = {"created", "modified", "version", "priority", "rationale",
                          "tags", "suspect", "fingerprint", "links", "upstream",
                          "checklists_applied", "edge_cases_identified", "execution_wave"}
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


def validate_status_transition(current: str, expected: str) -> bool:
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
                non_verified = [c.id for c in children if c.status != "verified"]
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
            if parent:
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

def has_acceptance_criteria(artifact: art_lib.Artifact) -> bool:
    """Check if a REQ artifact has acceptance criteria in its body."""
    if artifact.type != "requirement":
        return True  # Non-REQ artifacts don't need acceptance criteria

    body_lower = artifact.body.lower()
    # Check for common acceptance criteria headers
    markers = [
        "## acceptance criteria",
        "##acceptance criteria",
        "### acceptance criteria",
        "###acceptance criteria",
        "acceptance criteria:",
        "acceptance criteria\n",
    ]
    for marker in markers:
        if marker in body_lower:
            return True

    # Also check for numbered criteria patterns
    if re.search(r"^\d+\.\s+given", artifact.body, re.MULTILINE | re.IGNORECASE):
        return True

    return False


# ---------------------------------------------------------------------------
# Checklist loading and execution
# ---------------------------------------------------------------------------

def load_checklist(path: Path) -> dict[str, Any] | None:
    """Load a checklist YAML file."""
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


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
