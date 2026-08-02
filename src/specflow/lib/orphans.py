"""Orphan code detection — find source files not referenced by any SpecFlow artifact.

Provides:
  find_orphan_code()           — scan project for unreferenced source files
  retro_link()                 — retroactively link an orphan file to an artifact's output_files
  capture_phase_output_files() — `specflow done` auto-capture of phase source files

Code-linking model (D-20): `output_files` may live on STORY (forward action),
ARCH (component / adoption custody), DDD (detailed-design), or REQ. The orphan
meter credits all four. Glob patterns in `output_files` are expanded via
`lib.files.expand_output_files` so a single ARCH can cover a whole package.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import files as files_lib


# auto_commit_wave (lib/executor.py) writes commit subjects of the form:
#   "specflow: wave {n} prepared [STORY-001, STORY-002]"
# capture_phase_output_files parses the bracketed STORY ids back out of these.
_WAVE_COMMIT_RE = re.compile(
    r"^specflow:\s+wave\s+\d+\s+prepared\s*\[(.*)\]", re.IGNORECASE
)
# Field separators for the `git log --format` used by the capture walk. \x1f
# (ASCII unit separator) prefixes each commit-header line so it is reliably
# distinguishable from the file lines that follow it under `--name-only`.
_COMMIT_MARK = "\x1f"
_FIELD_MARK = "\x1f"


def parse_wave_commit_stories(subject: str) -> list[str]:
    """Parse STORY ids embedded in an ``auto_commit_wave`` commit subject.

    Returns the parsed ids (e.g. ``["STORY-001", "STORY-002"]``), or an empty
    list when ``subject`` is not a wave-commit. Pure function so it is unit-
    testable without git.
    """
    m = _WAVE_COMMIT_RE.match((subject or "").strip())
    if not m:
        return []
    return [s.strip() for s in m.group(1).split(",") if s.strip()]


def _phase_entered_date(root: Path) -> str | None:
    """Best-effort: the current phase's ``entered`` date from state.yaml.

    Returns ``None`` when there is no state, no current phase, or no open
    history entry for it. Never raises.
    """
    try:
        state_path = root / ".specflow" / "state.yaml"
        if not state_path.exists():
            return None
        state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
        if not isinstance(state, dict):
            return None
        current = state.get("current")
        history = state.get("history") or []
        if not isinstance(history, list):
            return None
        for entry in reversed(history):
            if (isinstance(entry, dict)
                    and entry.get("phase") == current
                    and entry.get("entered")):
                return str(entry["entered"])
    except Exception:
        return None
    return None


# Artifact types whose `output_files` count as "referencing" code. STORY covers
# forward action; ARCH/DDD cover adoption custody of existing components; REQ
# is kept for backward compatibility (its schema doesn't bless output_files,
# but some projects set it and we don't want to orphan their code on upgrade).
REFERENCING_TYPES: set[str] = {"story", "requirement", "architecture", "detailed-design"}


def find_orphan_code(root: Path) -> dict:
    """Find source code files not referenced by any STORY/REQ/ARCH/DDD artifact.

    A file is "referenced" if it appears in any referencing artifact's
    `output_files` (literal path OR glob match) or is cited via a backtick-quoted
    path at the start of a body line (best-effort heuristic).

    Returns:
        dict with keys:
          orphan_files: list of Path objects (unreferenced source files)
          referenced_count: count of referenced source files
          total_count: total source files scanned
    """
    root = Path(root).resolve()
    artifacts = art_lib.discover_artifacts(root)
    source_files = files_lib.scan_source_files(root)
    source_set = {f.resolve() for f in source_files}
    referenced = _collect_referenced_files(artifacts, root)

    orphans = [f for f in source_files if f.resolve() not in referenced]

    # Keep numerator on the same scope as the denominator: a declared output_file
    # outside the scanned scope must not push coverage past 100%.
    referenced_in_scope = referenced & source_set

    return {
        "orphan_files": orphans,
        "referenced_count": len(referenced_in_scope),
        "total_count": len(source_files),
    }


def _collect_referenced_files(artifacts, root: Path) -> set[Path]:
    """Collect all output_files (frontmatter) and body-referenced files from artifacts.

    Globs in `output_files` are expanded via `expand_output_files`. Only the
    four referencing types contribute (see REFERENCING_TYPES).
    """
    referenced: set[Path] = set()
    for art in artifacts:
        if art.type not in REFERENCING_TYPES:
            continue
        expanded = files_lib.expand_output_files(root, art.frontmatter.get("output_files"))
        referenced.update(expanded)
        # Body heuristic: backtick-quoted paths anywhere on a line. Best-effort;
        # the primary mechanism is the frontmatter output_files field above.
        # This previously only matched paths at the START of a line, missing the
        # dominant inline-prose citation style ("Code: `src/foo.py`"), which
        # marked genuinely-traced files as orphans. The exists()+is_file() guard
        # filters backtick tokens that are not real file paths.
        body = art.body or ""
        for line in body.splitlines():
            for fname in re.findall(r"`([^`]+)`", line):
                candidate = (root / fname).resolve()
                if candidate.exists() and candidate.is_file():
                    referenced.add(candidate)
    return referenced


def retro_link(root: Path, filepath: str, target_id: str) -> bool:
    """Retroactively link an orphan file to an artifact's output_files.

    Args:
        root: Project root
        filepath: Path to the orphan source file (relative or absolute)
        target_id: Artifact ID (e.g. "ARCH-003", "STORY-042", "DDD-007").
            The artifact's directory is resolved from its prefix, so any
            artifact type that owns output_files can be a target.

    Returns:
        True if successful, False if target not found or file doesn't exist
    """
    root = Path(root).resolve()

    # Resolve the target artifact's path from its ID prefix.
    target_path = art_lib.resolve_link_target(root, target_id)
    if target_path is None or not Path(target_path).exists():
        # Fall back to the legacy STORY-only path for any caller that passed a
        # bare STORY id we couldn't resolve through the link graph.
        legacy = root / "_specflow" / "work" / "stories" / f"{target_id}.md"
        if legacy.exists():
            target_path = legacy
        else:
            return False
    target_path = Path(target_path)

    file_path = Path(filepath)
    if file_path.is_absolute():
        try:
            rel_path = file_path.relative_to(root)
        except ValueError:
            return False
    else:
        rel_path = file_path
        file_path = (root / filepath).resolve()

    if not file_path.exists():
        return False

    text = target_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    end = text.find("---", 3)
    if end == -1:
        return False

    fm = yaml.safe_load(text[3:end]) or {}
    output_files = fm.get("output_files") or []
    if not isinstance(output_files, list):
        output_files = []

    rel_str = str(rel_path).replace("\\", "/")
    if rel_str not in output_files:
        output_files.append(rel_str)
        fm["output_files"] = output_files

    new_fm = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    new_text = f"---\n{new_fm}---{text[end+3:]}"
    target_path.write_text(new_text, encoding="utf-8")

    return True


def capture_phase_output_files(
    root: Path, since: str | None = None
) -> dict[str, object]:
    """Best-effort: retro_link phase source files to their owning STORYs.

    Walks ``git log --name-only`` back to the phase-start commit (the current
    phase's ``entered`` date in ``.specflow/state.yaml``, or ``since`` when
    given), parses the STORY ids embedded in wave-commit messages by
    ``auto_commit_wave`` (``lib/executor.py``), and for each new/modified file
    within the ``scan_source_files`` scope that is not already referenced,
    appends it to the owning STORY's ``output_files`` via :func:`retro_link`.

    Defensive by design (mirrors the audit orphan lens): the whole body is
    wrapped so attribution errors NEVER propagate to the caller — ``specflow
    done`` must still exit 0 when git history is empty/absent or a STORY cannot
    be resolved. Returns a summary dict::

        {"captured": int, "stories": int,
         "unattributed": int, "unattributed_files": list[str]}

    where ``captured`` is the number of newly-linked source files, ``stories``
    the number of distinct STORYs linked to, and ``unattributed`` the count of
    in-scope phase files touched by non-wave commits (printed by the caller,
    never fatal).
    """
    summary: dict[str, object] = {
        "captured": 0,
        "stories": 0,
        "unattributed": 0,
        "unattributed_files": [],
    }
    try:
        from specflow.lib import git_utils

        root = Path(root).resolve()
        if not git_utils.is_git_repo(root):
            return summary

        # Determine the phase-start point: explicit `since` arg, else the current
        # phase's entered date. When neither is available, walk the whole history
        # (retro_link is idempotent, so re-walking already-traced files is safe).
        if since is None:
            since = _phase_entered_date(root)

        fmt = f"{_COMMIT_MARK}%H{_FIELD_MARK}%s"
        log_args = ["log", "--name-only", f"--format={fmt}"]
        if since:
            log_args.append(f"--since={since}")
        proc = git_utils._run_git(root, log_args)
        if proc.returncode != 0:
            return summary

        source_scope = {f.resolve() for f in files_lib.scan_source_files(root)}
        referenced = _collect_referenced_files(
            art_lib.discover_artifacts(root), root
        )

        # file -> ordered unique STORY ids (from the wave commit(s) that touched it)
        file_to_stories: dict[str, list[str]] = {}
        non_wave_files: set[str] = set()
        current_stories: list[str] = []

        for raw in proc.stdout.splitlines():
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if line.startswith(_COMMIT_MARK):
                # commit header: "\x1f<sha>\x1f<subject>"
                parts = line.split(_FIELD_MARK)
                subject = parts[2] if len(parts) > 2 else ""
                current_stories = parse_wave_commit_stories(subject)
            else:
                rel = line.strip()
                if not rel:
                    continue
                if current_stories:
                    bucket = file_to_stories.setdefault(rel, [])
                    for sid in current_stories:
                        if sid not in bucket:
                            bucket.append(sid)
                else:
                    # touched by a non-wave commit inside the phase window
                    resolved = (root / rel).resolve()
                    if resolved in source_scope:
                        non_wave_files.add(rel)

        linked_stories: set[str] = set()
        for rel, story_ids in sorted(file_to_stories.items()):
            resolved = (root / rel).resolve()
            if resolved not in source_scope or resolved in referenced:
                continue
            linked_any = False
            for sid in story_ids:
                if retro_link(root, rel, sid):
                    linked_stories.add(sid)
                    linked_any = True
            if linked_any:
                summary["captured"] = int(summary["captured"]) + 1  # type: ignore[arg-type]

        # Unattributed: in-scope phase files with no wave-commit story and not
        # already referenced. Printed by the caller, never fatal.
        unattributed = sorted(
            rel for rel in non_wave_files
            if rel not in file_to_stories
            and (root / rel).resolve() not in referenced
        )
        summary["stories"] = len(linked_stories)
        summary["unattributed"] = len(unattributed)
        summary["unattributed_files"] = unattributed
    except Exception:
        # Accounting-not-policing (BP-006): an attribution error must never
        # fail `done`. The summary stays at its zero default.
        pass
    return summary
