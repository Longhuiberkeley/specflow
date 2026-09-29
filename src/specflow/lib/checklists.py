"""Checklist assembly pipeline: assemble unique review criteria per artifact."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib.artifacts import Artifact, _normalize_str_list


@dataclass
class ChecklistItem:
    """A single review criterion."""

    id: str
    check: str
    automated: bool = False
    severity: str = "warning"  # blocking | warning | info
    mode: str = "standard"  # proactive | reactive | standard
    applies_at: list[str] = field(default_factory=lambda: ["review"])
    applies_types: list[str] | None = None
    llm_prompt: str | None = None
    script: str | None = None
    source_checklist: str = ""


@dataclass
class ChecklistResult:
    """Result of evaluating a single checklist item."""

    item_id: str
    result: str  # passed | failed | error | skipped
    detail: str | None = None
    timestamp: str = ""
    # Severity of the originating item (blocking | warning | info). None means
    # unknown (e.g. a hand-built result) and is treated as blocking so an
    # unknown severity can never silently downgrade a failure.
    severity: str | None = None

    @property
    def is_nonpass(self) -> bool:
        """True for a failed or errored result (anything that is not a pass/skip)."""
        return self.result in ("failed", "error")

    @property
    def is_blocking(self) -> bool:
        """True when this non-pass result blocks (blocking or unknown severity)."""
        return self.is_nonpass and (self.severity or "blocking") == "blocking"

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class AssembledChecklist:
    """A fully assembled set of review criteria for an artifact."""

    artifact_id: str
    items: list[ChecklistItem] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    # "<path>: <reason>" for every checklist file that could not be parsed —
    # its items did not run, so the outcome cannot be reported as passed.
    parse_errors: list[str] = field(default_factory=list)


# Parse errors already written to stderr in this process — `checklist-run
# --all` would otherwise repeat the same broken-file warning per artifact.
_REPORTED_PARSE_ERRORS: set[str] = set()


def _record_parse_error(path: Path, reason: str, errors: list[str] | None) -> None:
    """Report an unparseable checklist loudly (stderr) and record it (STORY-682)."""
    message = f"{path}: {reason}"
    if message not in _REPORTED_PARSE_ERRORS:
        _REPORTED_PARSE_ERRORS.add(message)
        print(f"Warning: cannot parse checklist {message} — its items will not run "
              "(for a shipped checklist, run `specflow refresh --checklists` to restore it)", file=sys.stderr)
    if errors is not None and message not in errors:
        errors.append(message)


def _load_checklist_yaml(path: Path, errors: list[str] | None = None) -> dict | None:
    """Load a checklist YAML mapping, or report why it cannot be used and return None."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # yaml.YAMLError, OSError, UnicodeDecodeError
        reason = " ".join(str(exc).split()) or type(exc).__name__
        _record_parse_error(path, reason, errors)
        return None
    if not isinstance(data, dict):
        _record_parse_error(path, "top-level YAML is not a mapping", errors)
        return None
    return data


def parse_checklist_file(path: Path, errors: list[str] | None = None) -> list[ChecklistItem]:
    """Parse a YAML checklist file into ChecklistItem objects.

    A file that fails to parse is reported on stderr (path + reason) and
    appended to ``errors`` when given, instead of silently yielding no items.
    """
    data = _load_checklist_yaml(path, errors)
    if data is None:
        return []

    items: list[ChecklistItem] = []
    checklist_id = data.get("id", path.stem)

    for item_data in data.get("items", []):
        if not isinstance(item_data, dict):
            continue
        item_applies_to = item_data.get("applies_to")
        item_types = None
        if isinstance(item_applies_to, dict):
            t = item_applies_to.get("types")
            if isinstance(t, list) and t:
                item_types = t
        items.append(ChecklistItem(
            id=item_data.get("id", ""),
            check=item_data.get("check", ""),
            automated=item_data.get("automated", False),
            severity=item_data.get("severity", "warning"),
            mode=item_data.get("mode", "standard"),
            applies_at=item_data.get("applies_at", ["review"]),
            applies_types=item_types,
            llm_prompt=item_data.get("llm_prompt"),
            script=item_data.get("script"),
            source_checklist=str(path),
        ))

    return items


def match_tags(artifact_tags: list[str], checklist_tags: list[str]) -> bool:
    """Return True if any artifact tag matches any checklist tag."""
    return bool(set(artifact_tags) & set(checklist_tags))


# Artifact type → in-process/ checklist name.
TYPE_CHECKLIST_TYPE_MAP: dict[str, str] = {
    "requirement": "requirement-writing",
    "architecture": "architecture-writing",
    "detailed-design": "design-writing",
    "story": "story-writing",
}


def _load_type_checklist(
    root: Path, artifact_type: str, errors: list[str] | None = None
) -> list[ChecklistItem]:
    """Load the in-process checklist for an artifact type."""
    type_map = TYPE_CHECKLIST_TYPE_MAP
    checklist_name = type_map.get(artifact_type)
    if not checklist_name:
        return []

    path = root / ".specflow" / "checklists" / "in-process" / f"{checklist_name}.yaml"
    if path.exists():
        return parse_checklist_file(path, errors)
    return []


# Artifact type → review/ checklist name. The three V-model test types share
# implementation-review (STORY-687: it was shipped but unreachable before).
REVIEW_CHECKLIST_TYPE_MAP: dict[str, str] = {
    "requirement": "requirement-review",
    "architecture": "architecture-review",
    "detailed-design": "detailed-design-review",
    "story": "story-review",
    "unit-test": "implementation-review",
    "integration-test": "implementation-review",
    "qualification-test": "implementation-review",
}


def _load_review_checklist(
    root: Path, artifact_type: str, errors: list[str] | None = None
) -> list[ChecklistItem]:
    """Load the review checklist for an artifact type."""
    type_map = REVIEW_CHECKLIST_TYPE_MAP
    checklist_name = type_map.get(artifact_type)
    if not checklist_name:
        return []

    path = root / ".specflow" / "checklists" / "review" / f"{checklist_name}.yaml"
    if path.exists():
        return parse_checklist_file(path, errors)
    return []


def _load_shared_checklists(
    root: Path, artifact: Artifact, errors: list[str] | None = None
) -> list[ChecklistItem]:
    """Load shared checklists matching the artifact's tags and type."""
    shared_dir = root / ".specflow" / "checklists" / "shared"
    if not shared_dir.exists():
        return []

    items: list[ChecklistItem] = []
    for checklist_path in sorted(shared_dir.glob("*.yaml")):
        data = _load_checklist_yaml(checklist_path, errors)
        if data is None:
            continue

        applies_to = data.get("applies_to", {})
        if not isinstance(applies_to, dict):
            continue

        checklist_tags = _normalize_str_list(applies_to.get("tags", []))
        checklist_types = applies_to.get("types", [])

        # Match if tags intersect AND type matches (or no type filter)
        tags_match = match_tags(artifact.tags, checklist_tags) if checklist_tags else False
        type_match = artifact.type in checklist_types if checklist_types else True

        if tags_match and type_match:
            items.extend(parse_checklist_file(checklist_path, errors))

    return items


def _load_gate_checklist(
    root: Path, phase_transition: str, errors: list[str] | None = None
) -> list[ChecklistItem]:
    """Load phase-gate checklist for a specific transition."""
    path = root / ".specflow" / "checklists" / "phase-gates" / f"{phase_transition}.yaml"
    if path.exists():
        return parse_checklist_file(path, errors)
    return []


def _load_domain_checklist(
    root: Path, domain: str, artifact_type: str, errors: list[str] | None = None
) -> list[ChecklistItem]:
    """Load domain-specific checklist items if a domain is set in config.yaml.

    Looks for .specflow/checklists/domain/{domain}.yaml. Items are filtered by
    per-item `applies_to.types` if present, falling back to the top-level
    `applies_to.types`. Items without any type filter apply to all artifact
    types.
    """
    if not domain:
        return []

    path = root / ".specflow" / "checklists" / "domain" / f"{domain}.yaml"
    if not path.exists():
        return []

    data = _load_checklist_yaml(path, errors)
    if data is None:
        return []

    top_applies_to = data.get("applies_to") or {}
    top_type_filter = top_applies_to.get("types") if isinstance(top_applies_to, dict) else None
    # Top-level type filter gates the entire checklist
    if top_type_filter and artifact_type not in top_type_filter:
        return []

    all_items = parse_checklist_file(path, errors)
    filtered: list[ChecklistItem] = []
    for item in all_items:
        # Per-item type filter overrides top-level for this item
        item_types = item.applies_types
        if item_types is None:
            item_types = top_type_filter
        if item_types and artifact_type not in item_types:
            continue
        filtered.append(item)

    return filtered


def _load_learned_patterns(
    root: Path, artifact: Artifact, errors: list[str] | None = None
) -> list[ChecklistItem]:
    """Load learned prevention patterns matching the artifact's tags."""
    learned_dir = root / ".specflow" / "checklists" / "learned"
    if not learned_dir.exists():
        return []

    items: list[ChecklistItem] = []
    for pattern_path in sorted(learned_dir.glob("PREV-*.yaml")):
        data = _load_checklist_yaml(pattern_path, errors)
        if data is None:
            continue

        applies_to = data.get("applies_to", {})
        pattern_tags = _normalize_str_list(applies_to.get("tags", [])) if isinstance(applies_to, dict) else []

        if match_tags(artifact.tags, pattern_tags):
            items.extend(parse_checklist_file(pattern_path, errors))

    return items


def _extract_bp_check(body: str, title: str, bp_id: str) -> str:
    """Turn a BP body into a verifiable checklist check.

    Prefers the `## Verification` section (how to confirm the practice is followed);
    falls back to the title. BPs are prose (Practice/Rationale/Verification), so each
    becomes one proactive item rather than a parse of structured checks.
    """
    capturing = False
    out: list[str] = []
    for ln in (body or "").splitlines():
        s = ln.strip()
        if s.lower().startswith("## verification"):
            capturing = True
            continue
        if capturing and s.startswith("## "):
            break
        if capturing and s:
            out.append(s)
    text = " ".join(out).strip()
    return text or title or bp_id


def _load_best_practices(root: Path, artifact: Artifact) -> list[ChecklistItem]:
    """Convert matching best-practice artifacts into proactive checklist items."""
    from specflow.lib.ci import load_active_best_practices

    items: list[ChecklistItem] = []
    for bp in load_active_best_practices(root, artifact):
        check = _extract_bp_check(bp.body or "", bp.title or "", bp.id)
        items.append(
            ChecklistItem(
                id=f"{bp.id}-bp",
                check=f"[{bp.id}] {check}",
                automated=False,
                severity="warning",
                mode="proactive",
                source_checklist=f"best-practices/{bp.id}",
            )
        )
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
    """Assemble unique review criteria from seven ordered sources.

    Sources loaded in order:
    1. Artifact-type checklist (in-process/)
    2. Review checklist (review/)
    3. Shared checklists matching tags (shared/)
    4. Phase-gate checklist (if transition specified)
    5. Best-practice artifacts matching tags/applies_to (best-practices/)
    6. Learned prevention patterns (learned/)
    7. Project-domain checklist (domain/)
    """
    all_items: list[ChecklistItem] = []
    sources: list[str] = []
    parse_errors: list[str] = []

    # 1. Artifact-type checklist
    type_items = _load_type_checklist(root, artifact.type, parse_errors)
    if type_items:
        all_items.extend(type_items)
        sources.append(f"in-process/{artifact.type}")

    # 2. Review checklist
    review_items = _load_review_checklist(root, artifact.type, parse_errors)
    if review_items:
        all_items.extend(review_items)
        sources.append(f"review/{artifact.type}")

    # 3. Shared checklists
    shared_items = _load_shared_checklists(root, artifact, parse_errors)
    if shared_items:
        all_items.extend(shared_items)
        sources.append("shared/*")

    # 4. Phase-gate checklist
    if phase_transition:
        gate_items = _load_gate_checklist(root, phase_transition, parse_errors)
        if gate_items:
            all_items.extend(gate_items)
            sources.append(f"phase-gates/{phase_transition}")

    # 5. Best-practice artifacts (proactive domain guidance; mirrors ci.py matching)
    bp_items = _load_best_practices(root, artifact)
    if bp_items:
        all_items.extend(bp_items)
        sources.append("best-practices/BP-*")

    # 6. Learned patterns
    learned_items = _load_learned_patterns(root, artifact, parse_errors)
    if learned_items:
        all_items.extend(learned_items)
        sources.append("learned/PREV-*")

    # 7. Domain checklist (project-level domain set via `specflow domain set`)
    from specflow.lib.config import get_domain
    domain, _ = get_domain(root)
    domain_items = _load_domain_checklist(root, domain, artifact.type, parse_errors)
    if domain_items:
        all_items.extend(domain_items)
        sources.append(f"domain/{domain}")

    # Deduplicate and sort
    all_items = _deduplicate_items(all_items)
    all_items = _sort_items(all_items)

    return AssembledChecklist(
        artifact_id=artifact.id,
        items=all_items,
        sources=sources,
        parse_errors=parse_errors,
    )


def run_automated_pass(
    root: Path,
    assembled: AssembledChecklist,
    artifact: Artifact,
) -> list[ChecklistResult]:
    """Run all automated checklist items (zero-token pass).

    Each result carries its item's severity. If a blocking-severity automated
    item fails (or errors), returns immediately. An automated item with no
    script is an ``error`` result — a definition fault, never a silent pass.
    Non-automated items are not evaluated here.
    """
    results: list[ChecklistResult] = []

    for item in assembled.items:
        if not item.automated:
            continue

        def _result(result: str, detail: str | None = None) -> ChecklistResult:
            return ChecklistResult(item_id=item.id, result=result, detail=detail, severity=item.severity)

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
                    results.append(_result("passed"))
                else:
                    detail = proc.stderr.strip() or proc.stdout.strip() or "Script returned non-zero"
                    results.append(_result("failed", detail))
            except subprocess.TimeoutExpired:
                results.append(_result("failed", "Script timed out"))
            except Exception as e:
                results.append(_result("error", str(e)))
        else:
            # Automated but no script: the item can never be evaluated. Report
            # it as an error (STORY-682) rather than a vacuous pass.
            results.append(_result("error", "Automated item has no script — fix the checklist definition"))

        if results[-1].is_blocking:
            break

    return results


def persist_results(
    root: Path,
    artifact_id: str,
    checklist_id: str,
    results: list[ChecklistResult],
    parse_errors: list[str] | None = None,
) -> Path:
    """Write checklist results to .specflow/checklist-log/.

    ``blocking_failures`` counts only non-pass results whose item severity is
    blocking (or unknown). Unparseable checklist files (``parse_errors``) are
    recorded and keep an otherwise-passing outcome at ``incomplete``.
    """
    log_dir = root / ".specflow" / "checklist-log"
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    filename = f"{ts}_{checklist_id}.yaml"
    path = log_dir / filename

    blocking_failures = sum(1 for r in results if r.is_blocking)

    # Honest overall: an empty result list (no automated items ran) must NOT
    # be reported as "passed" — vacuous truth (all() over []) is dishonest
    # because nothing was actually verified. Empty → "incomplete"; non-empty
    # all-passed → "passed"; otherwise (any failed) → "failed". A checklist
    # file that failed to parse means some items never ran → not "passed".
    if any(r.is_nonpass for r in results):
        overall = "failed"
    elif not results or parse_errors:
        overall = "incomplete"
    else:
        overall = "passed"

    log_data = {
        "id": f"{ts}_{checklist_id}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checklist": checklist_id,
        "trigger": "review",
        "artifacts_checked": [artifact_id],
        "results": [
            {
                "item": r.item_id,
                "result": r.result,
                **({"severity": r.severity} if r.is_nonpass and r.severity else {}),
                **({"detail": r.detail} if r.detail else {}),
            }
            for r in results
        ],
        "overall": overall,
        "blocking_failures": blocking_failures,
    }
    if parse_errors:
        log_data["parse_errors"] = list(parse_errors)

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
    """Upsert a checklist execution record (updates timestamp if already present, appends if new)."""
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

    existing = next((e for e in applied if e.get("checklist") == checklist_id), None)
    if existing is not None:
        existing["timestamp"] = timestamp
    else:
        applied.append({"checklist": checklist_id, "timestamp": timestamp})
    fm["checklists_applied"] = applied

    body = text[end + 3:].strip()
    new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    file_path.write_text(new_text, encoding="utf-8")
