"""Defect lifecycle hooks.

When a DEF-* artifact transitions to `closed`, we trigger the reactive
challenge engine to surface a prevention-pattern candidate derived from the
defect's resolution. The extraction is best-effort — a failure here must not
block the status transition itself.

Also provides `create_defect_from_suspect` (suspect → DEF pipeline) and
`create_defect_from_monitor` (ops outcome → DEF pipeline), which auto-link a
defect to the upstream REQ (`fails_to_meet`) and the source artifact that
surfaced the drift (`exposed_by`). Both share the `_create_linked_defect`
backbone; the monitor path additionally freezes ephemeral MONITOR evidence
into the body so a breached observation survives the append-only journal.
The DEF then flows through the existing on_closure → PREV path with zero new
PREV code.

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


def _create_linked_defect(
    root: Path,
    source_id: str,
    source_kind: str,
    upstream_req_id: str,
    body_blocks: list[str],
    severity: str = "medium",
    title: str | None = None,
) -> dict[str, Any]:
    """Shared backbone for the suspect→DEF and monitor→DEF pipelines.

    Creates a DEF through `artifacts.create_artifact` (so it is registered in
    `_index.yaml`, gets a fingerprint, is schema-validated, and uses the draft-ID
    scheme on feature branches) with full traceability links:

        fails_to_meet → upstream_req_id   (the REQ no longer satisfied)
        exposed_by    → source_id         (the suspect artifact or MONITOR)

    Both roles are allowed by the defect schema (templates/schemas/defect.yaml).
    The caller renders the body blocks; this helper joins them with "\n" and tags
    the DEF ``{source_kind}-derived``.

    Args:
        root: Project root directory.
        source_id: The artifact that exposed the drift (suspect ID or MON-NNN).
        source_kind: Short label driving the tag — "suspect" or "monitor".
        upstream_req_id: The upstream REQ whose change/breach caused the defect.
        body_blocks: Pre-rendered body lines; joined with "\n".
        severity: Defect severity (low, medium, high, critical) → DEF priority.
        title: Optional override title; callers generate a default if omitted.

    Returns:
        Dict with ok status and the created DEF id/path, or error details
        (passed through from `create_artifact`).
    """
    links = [
        {"target": upstream_req_id, "role": "fails_to_meet"},
        {"target": source_id, "role": "exposed_by"},
    ]
    return art_lib.create_artifact(
        root,
        "defect",
        title=title,
        status="open",
        priority=severity,
        tags=[f"{source_kind}-derived"],
        links=links,
        body="\n".join(body_blocks),
    )


def create_defect_from_suspect(
    root: Path,
    suspect_artifact_id: str,
    upstream_req_id: str,
    impact_event_path: str | None = None,
    severity: str = "medium",
    title: str | None = None,
) -> dict[str, Any]:
    """Create a DEF artifact linked to a suspect event for the suspect → DEF pipeline.

    This is the programmatic helper called when a human approves creating a DEF
    from an unresolved suspect flag. It auto-populates the linkage fields so the
    DEF carries full traceability back to the upstream change that caused the drift.

    Behavior is unchanged after the `_create_linked_defect` extraction — the
    links, tag, priority, and body bytes are identical to the pre-refactor path
    (pinned by tests/test_defects.py::TestCreateDefectFromSuspect).

    Args:
        root: Project root directory.
        suspect_artifact_id: The artifact flagged as suspect (e.g., "ARCH-001").
        upstream_req_id: The upstream artifact whose change caused the suspect flag.
        impact_event_path: Path to the impact-log YAML event, recorded in the body
            for traceability back to the causing change.
        severity: Defect severity (low, medium, high, critical).
        title: Optional override title; auto-generated if not provided.

    Returns:
        Dict with ok status and the created DEF id/path, or error details.
    """
    suspect_path = art_lib.resolve_link_target(root, suspect_artifact_id)
    if suspect_path is None:
        return {"ok": False, "error": f"suspect artifact '{suspect_artifact_id}' not found"}

    suspect = art_lib.parse_artifact(suspect_path)
    if suspect is None:
        return {"ok": False, "error": f"cannot parse suspect artifact '{suspect_artifact_id}'"}

    if not title:
        title = f"{suspect_artifact_id} no longer satisfies {upstream_req_id} after upstream change"

    body_lines = [
        "## Context",
        "",
        f"Artifact **{suspect_artifact_id}** was flagged `suspect` after "
        f"**{upstream_req_id}** changed. This defect tracks the resolution of that "
        f"suspect flag.",
    ]
    if impact_event_path:
        body_lines += ["", f"Impact event: `{impact_event_path}`"]
    body_lines += [
        "",
        "## Resolution",
        "",
        "(To be filled when the defect is resolved.)",
    ]

    return _create_linked_defect(
        root,
        source_id=suspect_artifact_id,
        source_kind="suspect",
        upstream_req_id=upstream_req_id,
        body_blocks=body_lines,
        severity=severity,
        title=title,
    )


def create_defect_from_monitor(
    root: Path,
    monitor_id: str,
    upstream_req_id: str,
    severity: str = "medium",
    title: str | None = None,
) -> dict[str, Any]:
    """Create a DEF from a breached MONITOR (ops pack) for the outcome → DEF pipeline.

    Freezes the MONITOR's ephemeral evidence (metrics/signals/captures/observed_at/
    health) verbatim into a ``## Observed at breach`` body block, because the
    MONITOR journal is append-only and the breach snapshot would otherwise be
    irrecoverable once the operator hand-resolves it. The DEF is linked
    ``fails_to_meet → upstream_req_id`` and ``exposed_by → monitor_id`` (both
    schema-blessed) and then flows through the EXISTING on_closure → PREV path.

    Accounting, not policing, and never mutates the source:

    - WARN-AND-PROCEED: if the MONITOR is not flagged/breached (status != flagged
      and health != breached per the ops MONITOR schema), a warning is attached to
      the result dict but the DEF is STILL created. The caller prints the warning.
    - NEVER mutates the MONITOR — no status change, no auto-resolve. The journal
      stays append-only.

    Args:
        root: Project root directory.
        monitor_id: The MONITOR artifact ID (e.g., "MON-001").
        upstream_req_id: The upstream REQ the breach indicates is unsatisfied.
        severity: Defect severity (low, medium, high, critical).
        title: Optional override title; auto-generated if not provided.

    Returns:
        Dict with ok status, the created DEF id/path, and optionally a
        ``warning`` key when the source MONITOR was healthy at capture.
    """
    monitor_path = art_lib.resolve_link_target(root, monitor_id)
    if monitor_path is None:
        return {"ok": False, "error": f"monitor artifact '{monitor_id}' not found"}

    monitor = art_lib.parse_artifact(monitor_path)
    if monitor is None:
        return {"ok": False, "error": f"cannot parse monitor artifact '{monitor_id}'"}

    fm = monitor.frontmatter or {}
    is_breached = monitor.status == "flagged" or fm.get("health") == "breached"

    if not title:
        title = f"{monitor_id} breach — {upstream_req_id} not satisfied (ops outcome)"

    # ── Ephemeral-evidence freeze ─────────────────────────────────────
    # Copy the MONITOR's observation fields verbatim. The ops MONITOR schema
    # (packs/ops/schemas/monitor.yaml) lists metrics/signals/captures/observed_at/
    # health as the live-snapshot fields; be defensive if any are absent.
    body_lines = [
        "## Context",
        "",
        f"Defect materialized from live-operations observation **{monitor_id}** "
        f"that no longer satisfies **{upstream_req_id}**.",
        "",
        "## Observed at breach",
        "",
    ]
    any_present = False
    for field in ("observed_at", "health", "metrics", "signals", "captures"):
        val = fm.get(field)
        if val is None or val == "":
            continue
        any_present = True
        # Render dicts/lists faithfully (their keys/values must survive in the
        # frozen record); scalars inline.
        rendered = repr(val) if isinstance(val, (dict, list)) else str(val)
        body_lines.append(f"- **{field}**: `{rendered}`")
    if not any_present:
        body_lines.append("(MONITOR carried no metrics/signals/captures fields at capture.)")
    body_lines += [
        "",
        f"Frozen from {monitor_id} at creation; the MONITOR journal is "
        f"append-only — see it for later corrections.",
        "",
        "## Resolution",
        "",
        "(To be filled when the defect is resolved.)",
    ]

    result = _create_linked_defect(
        root,
        source_id=monitor_id,
        source_kind="monitor",
        upstream_req_id=upstream_req_id,
        body_blocks=body_lines,
        severity=severity,
        title=title,
    )

    # WARN-AND-PROCEED: attach the warning for the caller to print. Never refuse,
    # never mutate the MONITOR.
    if result.get("ok") and not is_breached:
        result["warning"] = (
            f"source MONITOR {monitor_id} was healthy at capture — recorded anyway"
        )
    return result
