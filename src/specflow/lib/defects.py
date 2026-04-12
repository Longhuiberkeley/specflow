"""Defect lifecycle hooks.

When a DEF-* artifact transitions to `closed`, we trigger the reactive
challenge engine to surface a prevention-pattern candidate derived from the
defect's resolution. The extraction is best-effort — a failure here must not
block the status transition itself.

Depends on STORY-010 (prevention pattern extraction, see lib/learning.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib import learning as learn_lib


def on_closure(root: Path, defect_id: str) -> dict[str, Any]:
    """Triggered when a defect transitions to status `closed`.

    Surfaces a prompt for the operator to capture a prevention pattern and,
    when one is provided via stdin, persists it under .specflow/checklists/learned/.

    For interactive contexts (TTY) we print the prompt and return without
    blocking; for automated contexts the extraction can be driven by the
    challenge skill. Either way, we return a dict describing what happened.
    """
    defect_path = art_lib.resolve_link_target(root, defect_id)
    if defect_path is None:
        return {"ok": False, "error": f"defect '{defect_id}' not found"}
    defect = art_lib.parse_artifact(defect_path)
    if defect is None:
        return {"ok": False, "error": f"cannot parse defect '{defect_id}'"}

    broken_reqs = [lk.target for lk in defect.links if lk.role == "fails_to_meet"]
    catching_tests = [lk.target for lk in defect.links if lk.role == "exposed_by"]

    seed_pattern = _seed_description(defect, broken_reqs, catching_tests)
    seed_check = _seed_check(defect, broken_reqs, catching_tests)

    # Best-effort: build the pattern scaffold. Operator can edit the resulting
    # PREV-*.yaml or override via a challenge skill.
    try:
        pattern = learn_lib.extract_prevention_pattern(
            story=defect,
            pattern_description=seed_pattern,
            check_text=seed_check,
        )
        pattern["mode"] = "reactive"
        pattern["discovered_from"] = defect.id
        persisted = learn_lib.persist_prevention_pattern(root, pattern)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"prevention-pattern extraction failed: {exc}",
            "defect": defect.id,
        }

    return {
        "ok": True,
        "defect": defect.id,
        "broken_requirements": broken_reqs,
        "catching_tests": catching_tests,
        "pattern_path": str(persisted),
    }


def _seed_description(defect: art_lib.Artifact, broken_reqs: list[str], catching_tests: list[str]) -> str:
    title = defect.title or defect.id
    bits: list[str] = [f"Prevent recurrence of: {title}"]
    if broken_reqs:
        bits.append(f"(violated {', '.join(broken_reqs)})")
    if catching_tests:
        bits.append(f"(caught by {', '.join(catching_tests)})")
    return " ".join(bits)


def _seed_check(defect: art_lib.Artifact, broken_reqs: list[str], catching_tests: list[str]) -> str:
    if broken_reqs and catching_tests:
        return (
            f"Verify that changes touching {', '.join(broken_reqs)} are exercised "
            f"by {', '.join(catching_tests)} before approval."
        )
    if broken_reqs:
        return (
            f"Verify that changes touching {', '.join(broken_reqs)} have a "
            f"regression test covering the failure mode of {defect.id}."
        )
    return f"Capture a regression test covering the failure mode of {defect.id}."
