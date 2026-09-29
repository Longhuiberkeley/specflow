"""Impact analysis engine: fingerprint change detection, suspect propagation, reverse impact, and impact logging."""

from __future__ import annotations

import fnmatch
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
    """Write an impact event to .specflow/impact-log/ as a timestamped YAML file.

    Names are allocated by exclusive create (DEC-093): two events for the
    same artifact in the same second get ``..._<ID>.yaml`` and
    ``..._<ID>-2.yaml`` instead of the second silently replacing the first.
    """
    from specflow.lib import locks as locks_lib

    log_dir = root / ".specflow" / "impact-log"
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    text = yaml.dump(event.to_dict(), default_flow_style=False, sort_keys=False)
    with locks_lib.mutation_lock(root, holder="impact-log"):
        n = 1
        while True:
            suffix = "" if n == 1 else f"-{n}"
            path = log_dir / f"{ts}_{event.changed}{suffix}.yaml"
            if locks_lib.exclusive_write(path, text):
                return path
            n += 1


def _write_artifact_file(file_path: Path, text: str) -> None:
    """Atomic artifact rewrite under the mutation lock of its project."""
    from specflow.lib import artifacts as art_lib

    root = art_lib._project_root_of(file_path) or file_path.parent
    art_lib.write_artifact_text(root, file_path, text)


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


def _find_all_downstream_recursive(root: Path, changed_id: str) -> list[Artifact]:
    """Find all artifacts transitively downstream of *changed_id* via BFS."""
    visited: set[str] = {changed_id}
    queue = [changed_id]
    result: list[Artifact] = []
    while queue:
        current = queue.pop(0)
        for art in _find_downstream_artifacts(root, current):
            if art.id not in visited:
                visited.add(art.id)
                result.append(art)
                queue.append(art.id)
    return result


def find_downstream_union(
    root: Path,
    source_ids: list[str],
    artifacts: list[Artifact] | None = None,
) -> list[Artifact]:
    """Union of the transitive downstream cones of all *source_ids*.

    Equivalent to the union of ``_find_all_downstream_recursive`` over each
    source, but with ONE artifact-discovery pass and an in-memory
    reverse-adjacency BFS — the recursive variant re-discovers the whole tree
    at every hop, which is far too slow for hot paths (``brief --next``), and
    summing per-source cone lengths double-counts artifacts downstream of
    several sources. Shared downstream artifacts are counted once here.

    Callers that already discovered artifacts should pass them via
    ``artifacts`` to avoid a redundant full-tree scan.
    """
    all_artifacts = artifacts if artifacts is not None else discover_artifacts(root)
    by_id = {a.id: a for a in all_artifacts}
    reverse: dict[str, list[str]] = {}
    for art in all_artifacts:
        for link in art.links:
            reverse.setdefault(link.target, []).append(art.id)

    # All sources are queued up-front so each cone is traversed once. Keep a
    # separate result set: a source may itself be downstream of another source
    # and therefore belongs in the union even though it is already visited.
    visited: set[str] = set(source_ids)
    result_ids: set[str] = set()
    queue = list(source_ids)
    result: list[Artifact] = []
    while queue:
        current = queue.pop(0)
        for nid in reverse.get(current, ()):
            if nid not in result_ids and nid in by_id:
                result_ids.add(nid)
                result.append(by_id[nid])
            if nid not in visited:
                visited.add(nid)
                queue.append(nid)
    return result


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
    _write_artifact_file(file_path, new_text)
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
    _write_artifact_file(file_path, new_text)
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
                if not any(s.get("artifact") == artifact_id for s in suspects):
                    continue
                resolved_suspects = data.get("resolved_suspects", [])
                if artifact_id not in resolved_suspects:
                    resolved_suspects.append(artifact_id)
                data["resolved_suspects"] = resolved_suspects
                all_resolved = all(
                    s.get("artifact") in resolved_suspects
                    for s in suspects
                )
                if all_resolved:
                    data["resolved"] = True
                    data["resolved_by"] = resolved_by
                    data["resolved_at"] = now
                from specflow.lib import locks as locks_lib

                locks_lib.locked_write(
                    root, event_file,
                    yaml.dump(data, default_flow_style=False, sort_keys=False),
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

    Writes no status. Runs under the mutation lock with atomic file writes,
    so a crash followed by a re-run converges (DDD-034 I5).
    """
    from specflow.lib import locks as locks_lib

    with locks_lib.mutation_lock(root, holder=f"split:{source_id}"):
        return _split_locked(root, source_id, new_id, reassign_links)


def _split_locked(
    root: Path, source_id: str, new_id: str, reassign_links: list[str]
) -> dict[str, Any]:
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
        if _retarget_links(art_path, source_id, new_id, drop=False):
            rewritten.append(art_id)

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


def _retarget_links(art_path: Path, old: str, new: str, *, drop: bool) -> bool:
    """Point links at ``old`` to ``new`` (or drop them); dedupe; True if changed."""
    try:
        text = art_path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    end = text.find("---", 3)
    if not text.startswith("---") or end == -1:
        return False
    try:
        fm = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return False
    if not isinstance(fm, dict):
        return False
    changed = False
    out: list[Any] = []
    seen: set[tuple[Any, Any]] = set()
    for link in fm.get("links") or []:
        if isinstance(link, dict) and link.get("target") == old:
            changed = True
            if drop:
                continue
            link = {**link, "target": new}
        if isinstance(link, dict):
            key = (link.get("target"), link.get("role"))
            if key in seen:
                changed = True
                continue
            seen.add(key)
        out.append(link)
    if not changed:
        return False
    fm["links"] = out
    body = text[end + 3:].strip()
    new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    _write_artifact_file(art_path, new_text)
    return True


#: Terminal statuses merge may give the source, most specific first.
#: ``superseded`` is used only with the paired ``supersedes`` link.
_MERGE_TERMINAL = ("superseded", "deprecated", "cancelled")


def _schema_of(root: Path, art_type: str) -> dict[str, Any]:
    path = root / ".specflow" / "schema" / f"{art_type}.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def merge_artifact(
    root: Path,
    source_id: str,
    target_id: str,
) -> dict[str, Any]:
    """Merge source_id into target_id: rewrite all links referencing source to target.

    Writes only schema-legal statuses (DEC-093, STORY-697): the target gains
    a ``supersedes`` link to the source when its schema allows that role,
    then the source moves to ``superseded`` — or, when that pairing is not
    available or not legal from its current status, to ``deprecated`` or
    ``cancelled``; if none is legal the status is left unchanged and the
    result says so. Status changes go through ``update_artifact``.
    """
    from specflow.lib import locks as locks_lib

    with locks_lib.mutation_lock(root, holder=f"merge:{source_id}"):
        return _merge_locked(root, source_id, target_id)


def _merge_locked(root: Path, source_id: str, target_id: str) -> dict[str, Any]:
    from specflow.lib import artifacts as art_lib

    source_path = resolve_link_target(root, source_id)
    target_path = resolve_link_target(root, target_id)

    if source_path is None:
        return {"ok": False, "error": f"Source artifact '{source_id}' not found"}
    if target_path is None:
        return {"ok": False, "error": f"Target artifact '{target_id}' not found"}
    if source_id == target_id:
        return {"ok": False, "error": "Cannot merge an artifact into itself"}

    rewritten = []
    for art in discover_artifacts(root):
        if art.id == source_id:
            continue
        if not any(link.target == source_id for link in art.links):
            continue
        # The target's own links to the source would become self-links.
        if _retarget_links(art.path, source_id, target_id, drop=art.id == target_id):
            rewritten.append(art.id)

    source = parse_artifact(source_path)
    current = source.status if source else ""
    allowed = _schema_of(root, source.type if source else "").get("allowed_status") or {}

    # Supersession pairing: the target links `supersedes` -> source first,
    # and only when the source can then legally move to superseded, so a
    # supersedes link never outlives a cancelled/deprecated/unchanged source
    # (DEF-019, tests/test_merge_split_status.py).
    target = parse_artifact(target_path)
    target_schema = _schema_of(root, target.type if target else "")
    # A resumed merge whose source is already superseded re-pairs: the
    # retarget pass above drops the target's own links to the source.
    can_supersede = current == "superseded" or (
        current not in _MERGE_TERMINAL
        and "superseded" in allowed
        and current in (allowed.get("superseded") or [])
    )
    paired = False
    added_link: list[dict[str, str]] | None = None  # target links before our pairing
    if target is not None and "supersedes" in (target_schema.get("allowed_link_roles") or []):
        if any(link.target == source_id and link.role == "supersedes" for link in target.links):
            paired = True
        elif can_supersede:
            before = [{"target": link.target, "role": link.role} for link in target.links]
            links = before + [{"target": source_id, "role": "supersedes"}]
            paired = bool(art_lib.update_artifact(root, target_id, links=links).get("ok"))
            if paired:
                added_link = before

    # Then the source moves to a legal terminal status.
    new_status: str | None = None
    status_note = ""
    if current in _MERGE_TERMINAL:
        # Already terminal (a resumed merge): re-sync the index entry, which
        # a crash between the file and index writes can leave behind.
        new_status = current
        art_lib.update_artifact(root, source_id, status=current)
    else:
        for candidate in _MERGE_TERMINAL:
            if candidate == "superseded" and not paired:
                continue
            if candidate in allowed and current in (allowed.get(candidate) or []):
                new_status = candidate
                break
        if new_status is None:
            status_note = (
                f"status '{current}' left unchanged: no legal terminal status "
                f"({', '.join(_MERGE_TERMINAL)}) from it"
            )
        else:
            res = art_lib.update_artifact(root, source_id, status=new_status)
            if not res.get("ok"):
                status_note = res.get("error", "status update failed")
                new_status = None
    if added_link is not None and new_status != "superseded":
        # The pairing did not complete: take back the link we added.
        art_lib.update_artifact(root, target_id, links=added_link)

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

    result: dict[str, Any] = {
        "ok": True,
        "rewritten": rewritten,
        "event_path": str(event_path),
        "source_status": new_status or current,
        "supersedes_link": paired,
    }
    if status_note:
        result["status_note"] = status_note
    return result


@dataclass
class FileArtifactMatch:
    file_path: str
    artifact_id: str
    match_type: str  # "literal" | "glob"
    pattern: str


def is_glob_pattern(path: str) -> bool:
    return any(c in path for c in "*?[")


def build_output_file_index(root: Path) -> dict[str, list[tuple[str, str, str]]]:
    """Build a reverse index mapping file paths to artifact IDs.

    Returns dict: normalized_path -> [(artifact_id, match_type, pattern)]
    """
    all_artifacts = discover_artifacts(root)
    index: dict[str, list[tuple[str, str, str]]] = {}

    for art in all_artifacts:
        output_files = art.frontmatter.get("output_files")
        if not output_files or not isinstance(output_files, list):
            continue

        for file_path in output_files:
            if not isinstance(file_path, str):
                continue

            if is_glob_pattern(file_path):
                key = file_path
                entry = (art.id, "glob", file_path)
            else:
                try:
                    key = str(Path(file_path)).rstrip("/")
                except Exception:
                    continue
                entry = (art.id, "literal", file_path)

            index.setdefault(key, []).append(entry)

    return index


def _glob_match(file_path: str, pattern: str) -> bool:
    """Match *file_path* against *pattern*, supporting ``**`` recursive globs.

    Patterns containing ``**`` are handled by converting each segment to a
    regex where ``**`` matches zero or more path segments.  Patterns without
    ``**`` are delegated to :func:`fnmatch.fnmatch`.
    """
    if "**" not in pattern:
        return fnmatch.fnmatch(file_path, pattern)

    import re
    parts = pattern.split("/")
    regex_parts: list[str] = []
    for i, part in enumerate(parts):
        if part == "**":
            if i == len(parts) - 1:
                regex_parts.append("(?:.+/)?[^/]*")
            else:
                regex_parts.append("(?:.+/)?")
        else:
            segment = re.escape(part)
            segment = segment.replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
            regex_parts.append(segment)
    joined = "".join(regex_parts)
    if not joined.startswith("(?:.+/)?"):
        joined = joined.replace("(?:.+/)?", "/(?:.+/)?", 1)
    regex = "^" + joined + "$"
    return bool(re.match(regex, file_path))


def query_reverse_impact(
    root: Path,
    changed_files: list[str],
    index: dict[str, list[tuple[str, str, str]]] | None = None,
) -> list[FileArtifactMatch]:
    """Map changed source files to governing artifacts via output_files.

    Pure query — does **not** modify any artifact files.
    """
    if not changed_files:
        return []

    if index is None:
        index = build_output_file_index(root)

    matches: list[FileArtifactMatch] = []
    seen: set[tuple[str, str]] = set()

    literal_index: dict[str, list[tuple[str, str, str]]] = {}
    glob_entries: list[tuple[str, str, str]] = []

    for key, entries in index.items():
        for entry in entries:
            art_id, match_type, pattern = entry
            if match_type == "glob":
                glob_entries.append(entry)
            else:
                literal_index.setdefault(key, []).append(entry)

    for changed_file in changed_files:
        normalized = changed_file.rstrip("/")

        if normalized in literal_index:
            for art_id, match_type, pattern in literal_index[normalized]:
                pair = (normalized, art_id)
                if pair not in seen:
                    seen.add(pair)
                    matches.append(FileArtifactMatch(
                        file_path=normalized,
                        artifact_id=art_id,
                        match_type="literal",
                        pattern=pattern,
                    ))

        for art_id, match_type, pattern in glob_entries:
            if _glob_match(normalized, pattern):
                pair = (normalized, art_id)
                if pair not in seen:
                    seen.add(pair)
                    matches.append(FileArtifactMatch(
                        file_path=normalized,
                        artifact_id=art_id,
                        match_type="glob",
                        pattern=pattern,
                    ))

    return matches


def flag_suspects_from_matches(
    root: Path,
    matches: list[FileArtifactMatch],
) -> list[str]:
    """Flag matched artifacts and all their transitive downstream as suspect.

    Returns a list of all artifact IDs that were flagged (deduplicated).
    """
    flagged: list[str] = []
    affected_ids = {m.artifact_id for m in matches}
    for art_id in affected_ids:
        art_path = resolve_link_target(root, art_id)
        if art_path is not None:
            _update_frontmatter_field(art_path, "suspect", True)
            flagged.append(art_id)
            for ds_art in _find_all_downstream_recursive(root, art_id):
                _update_frontmatter_field(ds_art.path, "suspect", True)
                flagged.append(ds_art.id)
    return list(dict.fromkeys(flagged))


def reverse_impact(
    root: Path,
    changed_files: list[str],
    index: dict[str, list[tuple[str, str, str]]] | None = None,
) -> list[FileArtifactMatch]:
    """Map changed source files to governing artifacts and flag them as suspect.

    Convenience wrapper that queries matches then flags.  For read-only usage,
    call :func:`query_reverse_impact` instead.
    """
    matches = query_reverse_impact(root, changed_files, index)
    flag_suspects_from_matches(root, matches)
    return matches
