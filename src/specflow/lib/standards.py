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


def _standards_dir(root: Path) -> Path:
    return root / ".specflow" / "standards"


def list_installed_standards(root: Path) -> list[str]:
    """Return the names of installed standards (file stems, sorted)."""
    d = _standards_dir(root)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.yaml"))


def load_standard(root: Path, standard_name: str) -> dict[str, Any] | None:
    """Load a single standard file by name (without .yaml extension)."""
    path = _standards_dir(root) / f"{standard_name}.yaml"
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def load_standards(
    root: Path, standard_name: str | None = None
) -> list[dict[str, Any]]:
    """Load one or all standards installed in the project."""
    if standard_name:
        data = load_standard(root, standard_name)
        return [data] if data else []

    results: list[dict[str, Any]] = []
    for name in list_installed_standards(root):
        data = load_standard(root, name)
        if data:
            results.append(data)
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
        return {
            "ok": False,
            "error": (
                "No standards installed in this project. "
                "Run 'specflow init --preset <preset>' to install a standards pack."
            ),
            "available": [],
        }

    if standard_name is None:
        if len(installed) == 1:
            standard_name = installed[0]
        else:
            return {
                "ok": False,
                "error": (
                    "Multiple standards installed; specify --standard <name>."
                ),
                "available": installed,
            }

    standard = load_standard(root, standard_name)
    if standard is None:
        return {
            "ok": False,
            "error": f"Standard '{standard_name}' not found.",
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
        entry = {
            "clause_id": clause_id,
            "clause_title": clause_title,
        }
        if artifact_ids:
            entry["artifacts"] = sorted(artifact_ids)
            covered.append(entry)
        else:
            uncovered.append(entry)

    return {
        "ok": True,
        "standard": standard_name,
        "title": standard.get("title", ""),
        "version": standard.get("version", ""),
        "total_clauses": len(clauses),
        "covered": covered,
        "uncovered": uncovered,
    }
