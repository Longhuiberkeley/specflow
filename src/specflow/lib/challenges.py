"""Shared CHL artifact creation logic used by artifact-review and project-audit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib.display import YELLOW_DIM, NC
from specflow.lib.techniques import TechniqueFinding


def create_chl_artifacts(
    root: Path,
    findings: list[TechniqueFinding],
    target_id: str,
    *,
    link_role: str = "challenges",
    review_id: str | None = None,
    dedup: bool = False,
    technique_override: str | None = None,
) -> list[dict[str, str]]:
    """Create CHL artifacts for non-info findings.

    Args:
        root: Project root.
        findings: TechniqueFinding objects to materialise as CHLs.
        target_id: The artifact these CHLs are about.
        link_role: Link role connecting CHL to target (default ``"challenges"``).
        review_id: Optional REVIEW artifact ID to backlink via ``refers_to``.
        dedup: If True, skip findings whose title matches an existing CHL.
        technique_override: If set, override each finding's technique field.

    Returns:
        List of dicts ``{"id", "severity", "technique", "title"}`` for created CHLs.
    """
    if dedup:
        existing = art_lib.discover_artifacts(root, artifact_type="challenge")
        seen_titles = {a.title for a in existing}
    else:
        seen_titles = set()

    created: list[dict[str, str]] = []
    for f in findings:
        if f.severity == "info":
            continue
        if f.title in seen_titles:
            continue

        links: list[dict[str, str]] = [{"target": target_id, "role": link_role}]
        if review_id:
            links.append({"target": review_id, "role": "refers_to"})

        try:
            art = art_lib.create_artifact(
                root,
                artifact_type="challenge",
                title=f.title[:100],
                status="open",
                rationale=f.rationale,
                links=links,
                body=f.body,
            )
            if not art.get("ok"):
                print(f"  {YELLOW_DIM}⚠ Failed to create CHL: {art.get('error', 'Unknown error')}{NC}")
                continue

            technique = technique_override or f.technique
            art_lib.update_artifact(
                root,
                art["id"],
                severity=f.severity,
                technique=technique,
            )
            created.append({
                "id": art["id"],
                "severity": f.severity,
                "technique": technique,
                "title": f.title[:100],
            })
            print(f"  Created {art['id']} [{f.severity}] from {technique}")
        except Exception as e:
            print(f"  {YELLOW_DIM}⚠ Failed to create CHL: {e}{NC}")

    return created
