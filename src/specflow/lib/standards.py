"""Standards pack loader and compliance gap analysis.

Standards live as YAML files under .specflow/standards/<name>.yaml, each
containing a flat list of clauses. Artifacts declare coverage via
`complies_with` links whose target is a clause ID. Gap analysis reports
which clauses are covered and which are not.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from specflow.lib import artifacts as art_lib

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Shown when `.specflow/standards/` holds no YAML. Deliberately neutral: no
# shipped preset carries a standard, so pointing at `init --preset` was a dead
# end. The only route to a standard is authoring (or copying) a pack.
NO_STANDARDS_MESSAGE = (
    "No standards installed in this project (nothing under .specflow/standards/). "
    "Author a standards pack with /specflow-pack-author; it is written to "
    ".specflow/packs/<name>/."
)

REMEDIATION_MAP: dict[str, str] = {
    "safety": "Consider creating a requirement with tags: [hazard, safety]",
    "security": "Consider creating a requirement with tags: [security, threat-model]",
    "functional": "Consider creating a requirement or detailed-design",
    "process": "Consider creating a decision or story",
}


# ASPICE-style process-area mapping.
# SpecFlow phase / artifact-type → process area. Used by the handbook synthesizer
# so the LLM gets the right "shape" of guidance regardless of whether the
# project installs an ASPICE pack.
PHASE_TO_PROCESS_AREA: dict[str, str] = {
    # Discover-time phases
    "discover": "SYS.1 / SWE.1 — system & software requirements elicitation",
    "discover-req": "SWE.1 — software requirements analysis",
    # Plan-time phases
    "plan": "SWE.2 — software architectural design",
    "plan-arc": "SWE.2 — software architectural design",
    "plan-ddd": "SWE.3 — software detailed design",
    "plan-story": "SWE.2/SWE.3 — story decomposition (architecture + detailed design)",
    # Execute-time phases
    "execute": "SWE.4 — software construction (unit implementation)",
    "execute-impl": "SWE.4 — software construction",
    # Verify-time phases
    "verify-unit": "SWE.5 — software unit verification",
    "verify-integration": "SWE.6 — software integration & integration test",
    "verify-qual": "SWE.7 — software qualification test",
    # Cross-cutting
    "review": "SUP.4 — joint review (artifact-level)",
}


def process_area_for(phase: str) -> str:
    """Return the ASPICE-style process-area label for a SpecFlow phase.

    Falls back to SUP.4 (joint review) for unknown phases — the synthesis is
    still useful at the review level even without a phase-specific mapping.
    """
    if not phase:
        return PHASE_TO_PROCESS_AREA["review"]
    return PHASE_TO_PROCESS_AREA.get(phase, PHASE_TO_PROCESS_AREA["review"])


def get_clause_by_id(root: Path, clause_id: str) -> dict[str, Any] | None:
    """Look up a clause across all installed standards. Returns None if not found."""
    if not clause_id:
        return None
    for standard in load_standards(root):
        clauses = standard.get("clauses", []) or []
        for clause in clauses:
            if isinstance(clause, dict) and clause.get("id") == clause_id:
                enriched = dict(clause)
                enriched["_standard"] = standard.get("title") or standard.get("id") or ""
                return enriched
    return None


def remediation_command(clause_id: str) -> str:
    """The deterministic CLI command that scaffolds a draft REQ for a clause."""
    return f"specflow create --from-standard {clause_id}"


def suggest_remediation(clause: dict[str, Any]) -> str:
    category = clause.get("category", "functional")
    severity = clause.get("severity", "medium")
    base = REMEDIATION_MAP.get(category, REMEDIATION_MAP["functional"])
    if severity == "high":
        base += " (high severity — prioritize)"
    clause_id = clause.get("id", "")
    if clause_id:
        base += f" → {remediation_command(clause_id)}"
    return base


def _sort_uncovered(uncovered: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(entry: dict[str, Any]) -> tuple:
        sev = entry.get("severity", "medium")
        pri = entry.get("priority", 999)
        return (_SEVERITY_ORDER.get(sev, 1), pri)

    return sorted(uncovered, key=_key)


def _standards_dir(root: Path) -> Path:
    return root / ".specflow" / "standards"


def _display_path(path: Path, root: Path) -> str:
    """Render ``path`` relative to ``root`` for messages.

    Compliance errors are copied into evidence packs, so an absolute path would
    make the exported pack machine-specific.
    """
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def list_installed_standards(root: Path) -> list[str]:
    """Return the names of installed standards (file stems, sorted)."""
    d = _standards_dir(root)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.yaml"))


def load_standard_checked(
    root: Path, standard_name: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Load a single standard file by name, reporting why it could not be used.

    Returns ``(data, None)`` on success, otherwise ``(None, error)`` where the
    error names the file and distinguishes a missing file from a YAML parse
    failure and from a file whose top level is not a mapping. ``load_standard``
    is the error-blind convenience wrapper around this.
    """
    path = _standards_dir(root) / f"{standard_name}.yaml"
    shown = _display_path(path, root)
    if not path.exists():
        return None, f"Standard '{standard_name}' not found ({shown})."
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
        detail = " ".join(str(exc).split())
        return None, f"Standard '{standard_name}' is unreadable ({shown}): {detail}"
    if not isinstance(data, dict):
        return None, (
            f"Standard '{standard_name}' must be a YAML mapping with a "
            f"'clauses' list ({shown}); got {type(data).__name__}."
        )
    return data, None


def load_standard(root: Path, standard_name: str) -> dict[str, Any] | None:
    """Load a single standard file by name (without .yaml extension)."""
    data, _error = load_standard_checked(root, standard_name)
    return data


def load_standards_checked(
    root: Path, standard_name: str | None = None
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Load one or all installed standards, returning ``(loaded, errors)``.

    ``errors`` maps the name of every installed standard that could not be
    loaded to its error message, so callers can surface a malformed file
    instead of silently treating it as absent.
    """
    names = [standard_name] if standard_name else list_installed_standards(root)
    results: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for name in names:
        data, error = load_standard_checked(root, name)
        if data is not None:
            results.append(data)
        elif error:
            errors[name] = error
    return results, errors


def load_standards(
    root: Path, standard_name: str | None = None
) -> list[dict[str, Any]]:
    """Load one or all standards installed in the project.

    Unreadable files are left out of the result; use ``load_standards_checked``
    to learn which ones and why.
    """
    results, _errors = load_standards_checked(root, standard_name)
    return results


def _collect_complies_with_targets(
    root: Path,
) -> dict[str, list[str]]:
    """Map clause-id → list of artifact IDs that link to it via complies_with."""
    mapping: dict[str, list[str]] = {}
    for art in art_lib.discover_artifacts(root):
        for link in art.links:
            if link.role == "complies_with" and link.target:
                mapping.setdefault(link.target, []).append(art.id)
    return mapping


def check_compliance(
    root: Path, standard_name: str | None = None
) -> dict[str, Any]:
    """Run compliance gap analysis against an installed standard.

    Returns:
      - {"ok": True, "standard": str, "title": str, "covered": [...], "uncovered": [...]}
      - {"ok": False, "error": str, "available": [str]} on error
    """
    installed = list_installed_standards(root)
    if not installed:
        # Not an error: a project without standards is healthy. Callers that
        # print this should stay neutral and exit 0 (accounting, not policing).
        return {
            "ok": False,
            "none_installed": True,
            "error": NO_STANDARDS_MESSAGE,
            "available": [],
        }

    if standard_name is None:
        if len(installed) == 1:
            standard_name = installed[0]
        else:
            _loaded, errors = load_standards_checked(root)
            message = "Multiple standards installed; specify --standard <name>."
            if errors:
                message += " Unreadable: " + "; ".join(errors[n] for n in sorted(errors))
            return {
                "ok": False,
                "error": message,
                "available": installed,
                "unreadable": errors,
            }

    standard, load_error = load_standard_checked(root, standard_name)
    if standard is None:
        return {
            "ok": False,
            "error": load_error or f"Standard '{standard_name}' not found.",
            "available": installed,
        }

    clauses = standard.get("clauses", []) or []
    targets_map = _collect_complies_with_targets(root)

    covered: list[dict[str, Any]] = []
    uncovered: list[dict[str, Any]] = []

    for clause in clauses:
        if not isinstance(clause, dict):
            continue
        clause_id = clause.get("id", "")
        if not clause_id:
            continue
        clause_title = clause.get("title", "")
        artifact_ids = targets_map.get(clause_id, [])
        entry: dict[str, Any] = {
            "clause_id": clause_id,
            "clause_title": clause_title,
            "severity": clause.get("severity", "medium"),
            "category": clause.get("category", "functional"),
            "priority": clause.get("priority", 999),
        }
        if artifact_ids:
            entry["artifacts"] = sorted(artifact_ids)
            covered.append(entry)
        else:
            entry["remediation"] = suggest_remediation(clause)
            entry["command"] = remediation_command(clause_id)
            uncovered.append(entry)

    uncovered = _sort_uncovered(uncovered)

    total = len(covered) + len(uncovered)
    score = round(len(covered) / max(total, 1) * 100, 1)

    return {
        "ok": True,
        "standard": standard_name,
        "title": standard.get("title", ""),
        "version": standard.get("version", ""),
        "total_clauses": total,
        "covered": covered,
        "uncovered": uncovered,
        "score": score,
    }
