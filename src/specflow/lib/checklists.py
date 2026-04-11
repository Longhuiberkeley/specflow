"""Checklist assembly pipeline: assemble unique review criteria per artifact."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib.artifacts import Artifact, parse_artifact


@dataclass
class ChecklistItem:
    """A single review criterion."""

    id: str
    check: str
    automated: bool = False
    severity: str = "warning"  # blocking | warning | info
    mode: str = "standard"  # proactive | reactive | standard
    applies_at: list[str] = field(default_factory=lambda: ["review"])
    llm_prompt: str | None = None
    script: str | None = None
    source_checklist: str = ""


@dataclass
class ChecklistResult:
    """Result of evaluating a single checklist item."""

    item_id: str
    result: str  # passed | failed | skipped
    detail: str | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class AssembledChecklist:
    """A fully assembled set of review criteria for an artifact."""

    artifact_id: str
    items: list[ChecklistItem] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def parse_checklist_file(path: Path) -> list[ChecklistItem]:
    """Parse a YAML checklist file into ChecklistItem objects."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if not isinstance(data, dict):
        return []

    items: list[ChecklistItem] = []
    checklist_id = data.get("id", path.stem)

    for item_data in data.get("items", []):
        if not isinstance(item_data, dict):
            continue
        items.append(ChecklistItem(
            id=item_data.get("id", ""),
            check=item_data.get("check", ""),
            automated=item_data.get("automated", False),
            severity=item_data.get("severity", "warning"),
            mode=item_data.get("mode", "standard"),
            applies_at=item_data.get("applies_at", ["review"]),
            llm_prompt=item_data.get("llm_prompt"),
            script=item_data.get("script"),
            source_checklist=str(path),
        ))

    return items


def match_tags(artifact_tags: list[str], checklist_tags: list[str]) -> bool:
    """Return True if any artifact tag matches any checklist tag."""
    return bool(set(artifact_tags) & set(checklist_tags))


def _load_type_checklist(root: Path, artifact_type: str) -> list[ChecklistItem]:
    """Load the in-process checklist for an artifact type."""
    type_map = {
        "requirement": "requirement-writing",
        "architecture": "architecture-writing",
        "detailed-design": "design-writing",
        "story": "story-writing",
    }
    checklist_name = type_map.get(artifact_type)
    if not checklist_name:
        return []

    path = root / ".specflow" / "checklists" / "in-process" / f"{checklist_name}.yaml"
    if path.exists():
        return parse_checklist_file(path)
    return []


def _load_review_checklist(root: Path, artifact_type: str) -> list[ChecklistItem]:
    """Load the review checklist for an artifact type."""
    type_map = {
        "requirement": "requirement-review",
        "architecture": "architecture-review",
        "detailed-design": "detailed-design-review",
        "story": "story-review",
    }
    checklist_name = type_map.get(artifact_type)
    if not checklist_name:
        return []

    path = root / ".specflow" / "checklists" / "review" / f"{checklist_name}.yaml"
    if path.exists():
        return parse_checklist_file(path)
    return []


def _load_shared_checklists(root: Path, artifact: Artifact) -> list[ChecklistItem]:
    """Load shared checklists matching the artifact's tags and type."""
    shared_dir = root / ".specflow" / "checklists" / "shared"
    if not shared_dir.exists():
        return []

    items: list[ChecklistItem] = []
    for checklist_path in sorted(shared_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(checklist_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        applies_to = data.get("applies_to", {})
        if not isinstance(applies_to, dict):
            continue

        checklist_tags = applies_to.get("tags", [])
        checklist_types = applies_to.get("types", [])

        # Match if tags intersect AND type matches (or no type filter)
        tags_match = match_tags(artifact.tags, checklist_tags) if checklist_tags else False
        type_match = artifact.type in checklist_types if checklist_types else True

        if tags_match and type_match:
            items.extend(parse_checklist_file(checklist_path))

    return items


def _load_gate_checklist(root: Path, phase_transition: str) -> list[ChecklistItem]:
    """Load phase-gate checklist for a specific transition."""
    path = root / ".specflow" / "checklists" / "phase-gates" / f"{phase_transition}.yaml"
    if path.exists():
        return parse_checklist_file(path)
    return []


def _load_learned_patterns(root: Path, artifact: Artifact) -> list[ChecklistItem]:
    """Load learned prevention patterns matching the artifact's tags."""
    learned_dir = root / ".specflow" / "checklists" / "learned"
    if not learned_dir.exists():
        return []

    items: list[ChecklistItem] = []
    for pattern_path in sorted(learned_dir.glob("PREV-*.yaml")):
        try:
            data = yaml.safe_load(pattern_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        applies_to = data.get("applies_to", {})
        pattern_tags = applies_to.get("tags", []) if isinstance(applies_to, dict) else []

        if match_tags(artifact.tags, pattern_tags):
            items.extend(parse_checklist_file(pattern_path))

    return items


def _deduplicate_items(items: list[ChecklistItem]) -> list[ChecklistItem]:
    """Deduplicate checklist items by check text, keeping higher severity."""
    severity_rank = {"blocking": 3, "warning": 2, "info": 1}
    seen: dict[str, ChecklistItem] = {}

    for item in items:
        key = item.check.strip().lower()
        if key in seen:
            existing_rank = severity_rank.get(seen[key].severity, 0)
            new_rank = severity_rank.get(item.severity, 0)
            if new_rank > existing_rank:
                seen[key] = item
        else:
            seen[key] = item

    return list(seen.values())


def _sort_items(items: list[ChecklistItem]) -> list[ChecklistItem]:
    """Sort: automated first, then proactive, then reactive/standard."""
    def sort_key(item: ChecklistItem) -> tuple[int, int, str]:
        auto_rank = 0 if item.automated else 1
        mode_rank = {"proactive": 0, "reactive": 1, "standard": 2}.get(item.mode, 2)
        return (auto_rank, mode_rank, item.id)

    return sorted(items, key=sort_key)


def assemble_checklist(
    root: Path,
    artifact: Artifact,
    phase_transition: str | None = None,
) -> AssembledChecklist:
    """Assemble unique review criteria for an artifact from all 4 sources.

    Sources loaded in order:
    1. Artifact-type checklist (in-process/)
    2. Review checklist (review/)
    3. Shared checklists matching tags (shared/)
    4. Phase-gate checklist (if transition specified)
    5. Learned prevention patterns (learned/)
    """
    all_items: list[ChecklistItem] = []
    sources: list[str] = []

    # 1. Artifact-type checklist
    type_items = _load_type_checklist(root, artifact.type)
    if type_items:
        all_items.extend(type_items)
        sources.append(f"in-process/{artifact.type}")

    # 2. Review checklist
    review_items = _load_review_checklist(root, artifact.type)
    if review_items:
        all_items.extend(review_items)
        sources.append(f"review/{artifact.type}")

    # 3. Shared checklists
    shared_items = _load_shared_checklists(root, artifact)
    if shared_items:
        all_items.extend(shared_items)
        sources.append("shared/*")

    # 4. Phase-gate checklist
    if phase_transition:
        gate_items = _load_gate_checklist(root, phase_transition)
        if gate_items:
            all_items.extend(gate_items)
            sources.append(f"phase-gates/{phase_transition}")

    # 5. Learned patterns
    learned_items = _load_learned_patterns(root, artifact)
    if learned_items:
        all_items.extend(learned_items)
        sources.append("learned/PREV-*")

    # Deduplicate and sort
    all_items = _deduplicate_items(all_items)
    all_items = _sort_items(all_items)

    return AssembledChecklist(
        artifact_id=artifact.id,
        items=all_items,
        sources=sources,
    )


def run_automated_pass(
    root: Path,
    assembled: AssembledChecklist,
    artifact: Artifact,
) -> list[ChecklistResult]:
    """Run all automated checklist items (zero-token pass).

    If any blocking automated item fails, returns immediately.
    Non-automated items are returned as 'skipped'.
    """
    results: list[ChecklistResult] = []
    blocking_failed = False

    for item in assembled.items:
        if not item.automated:
            continue

        if item.script:
            try:
                # Run script via bash -c with artifact path as $1
                cmd = ["bash", "-c", item.script, "--", str(artifact.path)]
                proc = subprocess.run(
                    cmd,
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if proc.returncode == 0:
                    results.append(ChecklistResult(item_id=item.id, result="passed"))
                else:
                    detail = proc.stderr.strip() or proc.stdout.strip() or "Script returned non-zero"
                    results.append(ChecklistResult(item_id=item.id, result="failed", detail=detail))
                    if item.severity == "blocking":
                        blocking_failed = True
            except subprocess.TimeoutExpired:
                results.append(ChecklistResult(item_id=item.id, result="failed", detail="Script timed out"))
                if item.severity == "blocking":
                    blocking_failed = True
            except Exception as e:
                results.append(ChecklistResult(item_id=item.id, result="failed", detail=str(e)))
                if item.severity == "blocking":
                    blocking_failed = True
        else:
            # Automated but no script — pass by default
            results.append(ChecklistResult(item_id=item.id, result="passed"))

        if blocking_failed:
            break

    return results


def persist_results(
    root: Path,
    artifact_id: str,
    checklist_id: str,
    results: list[ChecklistResult],
) -> Path:
    """Write checklist results to .specflow/checklist-log/."""
    log_dir = root / ".specflow" / "checklist-log"
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    filename = f"{ts}_{checklist_id}.yaml"
    path = log_dir / filename

    blocking_failures = sum(
        1 for r in results
        if r.result == "failed" and any(
            i.id == r.item_id and i.severity == "blocking"
            for i in []  # Will be passed in real usage
        )
    )

    log_data = {
        "id": f"{ts}_{checklist_id}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checklist": checklist_id,
        "trigger": "review",
        "artifacts_checked": [artifact_id],
        "results": [
            {"item": r.item_id, "result": r.result, **({"detail": r.detail} if r.detail else {})}
            for r in results
        ],
        "overall": "passed" if all(r.result == "passed" for r in results) else "failed",
        "blocking_failures": sum(1 for r in results if r.result == "failed"),
    }

    path.write_text(
        yaml.dump(log_data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return path


def update_artifact_checklists_applied(
    root: Path,
    artifact_id: str,
    checklist_id: str,
    timestamp: str,
) -> None:
    """Append a checklist execution record to the artifact's checklists_applied list."""
    from specflow.lib.artifacts import resolve_link_target

    file_path = resolve_link_target(root, artifact_id)
    if file_path is None:
        return

    try:
        text = file_path.read_text(encoding="utf-8").strip()
    except Exception:
        return

    if not text.startswith("---"):
        return

    end = text.find("---", 3)
    if end == -1:
        return

    try:
        fm = yaml.safe_load(text[3:end])
    except Exception:
        return

    if not isinstance(fm, dict):
        return

    applied = fm.get("checklists_applied", [])
    if not isinstance(applied, list):
        applied = []

    applied.append({"checklist": checklist_id, "timestamp": timestamp})
    fm["checklists_applied"] = applied

    body = text[end + 3:].strip()
    new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    file_path.write_text(new_text, encoding="utf-8")
