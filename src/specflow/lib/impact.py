"""Impact analysis engine: fingerprint change detection, suspect propagation, and impact logging."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib.artifacts import (
    Artifact,
    compute_fingerprint,
    discover_artifacts,
    parse_artifact,
    resolve_link_target,
)


@dataclass
class ImpactEvent:
    """Records a single artifact change and its downstream effects."""

    changed: str
    change_type: str  # content_modified | status_changed | created | deleted | split | merged
    fingerprint_old: str
    fingerprint_new: str
    update_type: str  # semantic | minor
    flagged_suspects: list[dict[str, str]] = field(default_factory=list)
    resolved: bool = False
    resolved_by: str | None = None
    resolved_at: str | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "changed": self.changed,
            "change_type": self.change_type,
            "fingerprint_old": self.fingerprint_old,
            "fingerprint_new": self.fingerprint_new,
            "update_type": self.update_type,
            "flagged_suspects": self.flagged_suspects,
            "resolved": self.resolved,
            "timestamp": self.timestamp,
        }
        if self.resolved_by:
            d["resolved_by"] = self.resolved_by
        if self.resolved_at:
            d["resolved_at"] = self.resolved_at
        return d


def create_impact_event(root: Path, event: ImpactEvent) -> Path:
    """Write an impact event to .specflow/impact-log/ as a timestamped YAML file."""
    log_dir = root / ".specflow" / "impact-log"
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    filename = f"{ts}_{event.changed}.yaml"
    path = log_dir / filename
    path.write_text(
        yaml.dump(event.to_dict(), default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return path


def load_impact_events(root: Path) -> list[ImpactEvent]:
    """Read all impact events from .specflow/impact-log/."""
    log_dir = root / ".specflow" / "impact-log"
    if not log_dir.exists():
        return []

    events: list[ImpactEvent] = []
    for f in sorted(log_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                events.append(ImpactEvent(
                    changed=data.get("changed", ""),
                    change_type=data.get("change_type", ""),
                    fingerprint_old=data.get("fingerprint_old", ""),
                    fingerprint_new=data.get("fingerprint_new", ""),
                    update_type=data.get("update_type", "semantic"),
                    flagged_suspects=data.get("flagged_suspects", []),
                    resolved=data.get("resolved", False),
                    resolved_by=data.get("resolved_by"),
                    resolved_at=data.get("resolved_at"),
                    timestamp=data.get("timestamp", ""),
                ))
        except Exception:
            continue
    return events


def _find_downstream_artifacts(root: Path, changed_id: str) -> list[Artifact]:
    """Find all artifacts that link TO the changed artifact (reverse traversal)."""
    all_artifacts = discover_artifacts(root)
    downstream = []
    for art in all_artifacts:
        for link in art.links:
            if link.target == changed_id:
                downstream.append(art)
                break
    return downstream


def _update_frontmatter_field(file_path: Path, field_name: str, value: Any) -> bool:
    """Update a single frontmatter field in an artifact file."""
    try:
        text = file_path.read_text(encoding="utf-8").strip()
    except Exception:
        return False

    if not text.startswith("---"):
        return False

    end = text.find("---", 3)
    if end == -1:
        return False

    try:
        fm = yaml.safe_load(text[3:end])
    except Exception:
        return False

    if not isinstance(fm, dict):
        return False

    fm[field_name] = value
    body = text[end + 3:].strip()
    new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    file_path.write_text(new_text, encoding="utf-8")
    return True


def _remove_frontmatter_field(file_path: Path, field_name: str) -> bool:
    """Remove a frontmatter field from an artifact file."""
    try:
        text = file_path.read_text(encoding="utf-8").strip()
    except Exception:
        return False

    if not text.startswith("---"):
        return False

    end = text.find("---", 3)
    if end == -1:
        return False

    try:
        fm = yaml.safe_load(text[3:end])
    except Exception:
        return False

    if not isinstance(fm, dict) or field_name not in fm:
        return False

    del fm[field_name]
    body = text[end + 3:].strip()
    new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    file_path.write_text(new_text, encoding="utf-8")
    return True


def _read_frontmatter(file_path: Path) -> dict[str, Any] | None:
    """Read frontmatter from an artifact file."""
    try:
        text = file_path.read_text(encoding="utf-8").strip()
    except Exception:
        return None

    if not text.startswith("---"):
        return None

    end = text.find("---", 3)
    if end == -1:
        return None

    try:
        fm = yaml.safe_load(text[3:end])
        return fm if isinstance(fm, dict) else None
    except Exception:
        return None


def propagate_suspects(
    root: Path,
    changed_artifact_id: str,
    force_minor: bool = False,
) -> dict[str, Any]:
    """Core propagation: detect fingerprint change, flag downstream suspects, log event.

    Args:
        root: Project root.
        changed_artifact_id: ID of the artifact that was modified.
        force_minor: If True, treat as minor change (skip cascade). Used by specflow fingerprint-refresh.

    Returns:
        dict with ok, event_path, flagged_count, update_type keys.
    """
    file_path = resolve_link_target(root, changed_artifact_id)
    if file_path is None:
        return {"ok": False, "error": f"Artifact '{changed_artifact_id}' not found"}

    artifact = parse_artifact(file_path)
    if artifact is None:
        return {"ok": False, "error": f"Cannot parse artifact at {file_path}"}

    # Recompute fingerprint
    new_fingerprint = compute_fingerprint(artifact.body)
    old_fingerprint = artifact.fingerprint

    if new_fingerprint == old_fingerprint and not force_minor:
        return {"ok": True, "changed": False, "message": "No fingerprint change detected"}

    # Update fingerprint in the artifact
    _update_frontmatter_field(file_path, "fingerprint", new_fingerprint)

    # Bump version
    fm = _read_frontmatter(file_path)
    current_version = fm.get("version", 0) if fm else 0
    _update_frontmatter_field(file_path, "version", current_version + 1)

    # Determine update type via 3-tier defense
    update_type = "semantic"

    if force_minor:
        update_type = "minor"
    elif fm and fm.get("update_type") == "minor":
        # Tier 1: explicit update_type: minor
        update_type = "minor"
        _remove_frontmatter_field(file_path, "update_type")
    elif fm and not fm.get("update_type"):
        # Tier 3: magnitude heuristic
        update_type = classify_change_magnitude(old_fingerprint, new_fingerprint, artifact)

    if fm and fm.get("update_type") == "semantic":
        _remove_frontmatter_field(file_path, "update_type")

    # Propagate suspect flags downstream (only if semantic)
    flagged: list[dict[str, str]] = []

    if update_type == "semantic":
        downstream = _find_downstream_artifacts(root, changed_artifact_id)
        for ds_art in downstream:
            _update_frontmatter_field(ds_art.path, "suspect", True)
            # Find the link role
            link_role = ""
            for link in ds_art.links:
                if link.target == changed_artifact_id:
                    link_role = link.role
                    break
            flagged.append({"artifact": ds_art.id, "link_role": link_role})

    # Create impact-log event
    event = ImpactEvent(
        changed=changed_artifact_id,
        change_type="content_modified",
        fingerprint_old=old_fingerprint,
        fingerprint_new=new_fingerprint,
        update_type=update_type,
        flagged_suspects=flagged,
    )
    event_path = create_impact_event(root, event)

    return {
        "ok": True,
        "changed": True,
        "event_path": str(event_path),
        "flagged_count": len(flagged),
        "update_type": update_type,
        "flagged": flagged,
    }


def classify_change_magnitude(
    old_fingerprint: str,
    new_fingerprint: str,
    artifact: Artifact,
) -> str:
    """Tier 3: heuristic-based change magnitude classification.

    Design decision: Without access to git diff data or the previous body content
    at this call site, we cannot compute the line-level change ratio described in
    DDD-001. We default to "semantic" (conservative — triggers cascade). Users
    should use Tier 1 (update_type: minor in frontmatter) or Tier 2 (specflow fingerprint-refresh)
    to explicitly classify known minor changes.
    """
    if old_fingerprint == new_fingerprint:
        return "minor"

    # Conservative default per DDD-001: treat as semantic when ratio is unknown.
    return "semantic"


def resolve_suspect(
    root: Path,
    artifact_id: str,
    resolved_by: str = "user",
) -> dict[str, Any]:
    """Resolve a suspect flag on an artifact and update the corresponding impact-log event."""
    file_path = resolve_link_target(root, artifact_id)
    if file_path is None:
        return {"ok": False, "error": f"Artifact '{artifact_id}' not found"}

    artifact = parse_artifact(file_path)
    if artifact is None:
        return {"ok": False, "error": f"Cannot parse artifact at {file_path}"}

    if not artifact.suspect:
        return {"ok": True, "message": f"{artifact_id} is not suspect"}

    # Clear suspect flag
    _update_frontmatter_field(file_path, "suspect", False)

    # Update impact-log events that flagged this artifact
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_dir = root / ".specflow" / "impact-log"
    if log_dir.exists():
        for event_file in log_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(event_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or data.get("resolved", False):
                    continue
                suspects = data.get("flagged_suspects", [])
                if any(s.get("artifact") == artifact_id for s in suspects):
                    data["resolved"] = True
                    data["resolved_by"] = resolved_by
                    data["resolved_at"] = now
                    event_file.write_text(
                        yaml.dump(data, default_flow_style=False, sort_keys=False),
                        encoding="utf-8",
                    )
            except Exception:
                continue

    return {"ok": True, "resolved": artifact_id, "resolved_by": resolved_by, "resolved_at": now}


def split_artifact(
    root: Path,
    source_id: str,
    new_id: str,
    reassign_links: list[str],
) -> dict[str, Any]:
    """Reassign selected downstream links from source_id to new_id after a split.

    Args:
        root: Project root.
        source_id: The original artifact being split.
        new_id: The new artifact that receives some of the links.
        reassign_links: List of artifact IDs whose links should be rewritten.
    """
    source_path = resolve_link_target(root, source_id)
    new_path = resolve_link_target(root, new_id)

    if source_path is None:
        return {"ok": False, "error": f"Source artifact '{source_id}' not found"}
    if new_path is None:
        return {"ok": False, "error": f"New artifact '{new_id}' not found"}

    rewritten = []
    for art_id in reassign_links:
        art_path = resolve_link_target(root, art_id)
        if art_path is None:
            continue

        art = parse_artifact(art_path)
        if art is None:
            continue

        # Rewrite links targeting source_id to target new_id
        try:
            text = art_path.read_text(encoding="utf-8").strip()
            end = text.find("---", 3)
            fm = yaml.safe_load(text[3:end])
            if not isinstance(fm, dict):
                continue

            changed = False
            for link in fm.get("links", []):
                if isinstance(link, dict) and link.get("target") == source_id:
                    link["target"] = new_id
                    changed = True

            if changed:
                body = text[end + 3:].strip()
                new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
                art_path.write_text(new_text, encoding="utf-8")
                rewritten.append(art_id)
        except Exception:
            continue

    # Log split event
    source_art = parse_artifact(source_path)
    event = ImpactEvent(
        changed=source_id,
        change_type="split",
        fingerprint_old=source_art.fingerprint if source_art else "",
        fingerprint_new=source_art.fingerprint if source_art else "",
        update_type="semantic",
        flagged_suspects=[],
    )
    event_path = create_impact_event(root, event)

    return {"ok": True, "rewritten": rewritten, "event_path": str(event_path)}


def merge_artifact(
    root: Path,
    source_id: str,
    target_id: str,
) -> dict[str, Any]:
    """Merge source_id into target_id: rewrite all links referencing source to target."""
    source_path = resolve_link_target(root, source_id)
    target_path = resolve_link_target(root, target_id)

    if source_path is None:
        return {"ok": False, "error": f"Source artifact '{source_id}' not found"}
    if target_path is None:
        return {"ok": False, "error": f"Target artifact '{target_id}' not found"}

    all_artifacts = discover_artifacts(root)
    rewritten = []

    for art in all_artifacts:
        if art.id == source_id:
            continue

        has_link = any(link.target == source_id for link in art.links)
        if not has_link:
            continue

        try:
            text = art.path.read_text(encoding="utf-8").strip()
            end = text.find("---", 3)
            fm = yaml.safe_load(text[3:end])
            if not isinstance(fm, dict):
                continue

            for link in fm.get("links", []):
                if isinstance(link, dict) and link.get("target") == source_id:
                    link["target"] = target_id

            body = text[end + 3:].strip()
            new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
            art.path.write_text(new_text, encoding="utf-8")
            rewritten.append(art.id)
        except Exception:
            continue

    # Update source artifact status
    _update_frontmatter_field(source_path, "status", "merged_into")
    _update_frontmatter_field(source_path, "merged_target", target_id)

    # Log merge event
    source_art = parse_artifact(source_path)
    event = ImpactEvent(
        changed=source_id,
        change_type="merged",
        fingerprint_old=source_art.fingerprint if source_art else "",
        fingerprint_new="",
        update_type="semantic",
        flagged_suspects=[],
    )
    event_path = create_impact_event(root, event)

    return {"ok": True, "rewritten": rewritten, "event_path": str(event_path)}
