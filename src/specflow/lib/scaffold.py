"""Directory and file scaffolding for SpecFlow init."""

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import platform

# Spec directories under _specflow/
SPEC_DIRS = [
    "specs/requirements",
    "specs/architecture",
    "specs/detailed-design",
    "specs/unit-tests",
    "specs/integration-tests",
    "specs/qualification-tests",
    "specs/reviews",
    "work/stories",
    "work/spikes",
    "work/decisions",
    "work/defects",
    "specs/best-practices",
]

# Internal directories under .specflow/
INTERNAL_DIRS = [
    "schema",
    "impact-log",
    "checklist-log",
    "baselines",
    "locks",
    "standards",
    "checklists/phase-gates",
    "checklists/in-process",
    "checklists/review",
    "checklists/shared",
    "checklists/learned",
    "checklists/domain",
]

# Machine-local scratch under .specflow/: nothing reads these back, so they
# stay out of a consumer's git via a per-directory `.gitignore` (same pattern
# as `locks/`, which lib/locks.py writes lazily). Listed here, not in the
# consumer's root .gitignore, which init never touches.
SCRATCH_DIRS = [
    "checklist-log",
    "locks",
]

_INDEX_STUB = {"artifacts": {}, "next_id": 1}


# Ignore everything in a scratch dir EXCEPT the ignore file itself, so the
# file is committed with the scaffold and still applies in a teammate's or
# CI clone (a bare ``*`` would ignore the .gitignore too and never ship).
SCRATCH_GITIGNORE = "*\n!.gitignore\n"

# The pre-v1.17.2 machine-written form (also what lib/locks.py lazily writes).
# It is upgraded in place; any other content is the user's and is kept.
_LEGACY_SCRATCH_GITIGNORE = "*\n"


def ensure_scratch_gitignore(directory: Path) -> bool:
    """Write ``<directory>/.gitignore`` (``*`` + ``!.gitignore``) unless one exists.

    Returns True when a file was written. An existing file is left alone
    unless it is exactly the legacy self-ignoring ``*`` form, which is
    upgraded so the file survives a clone; any other content may be the
    user's own choice.
    """
    directory.mkdir(parents=True, exist_ok=True)
    ignore = directory / ".gitignore"
    if ignore.exists():
        try:
            current = ignore.read_text(encoding="utf-8")
        except OSError:
            return False
        if current != _LEGACY_SCRATCH_GITIGNORE:
            return False
    # Atomic: a crash mid-write must leave either no file or the whole file
    # (the index-store crash harness replays every write).
    tmp = ignore.with_name(".gitignore.tmp")
    tmp.write_text(SCRATCH_GITIGNORE, encoding="utf-8")
    os.replace(tmp, ignore)
    return True

# Project-local packs (authored by /specflow-pack-author) live here.
LOCAL_PACKS_DIR = Path(".specflow") / "packs"


def bundled_packs_dir() -> Path:
    """Directory of the packs shipped inside the SpecFlow package."""
    return Path(__file__).parent.parent / "packs"


def resolve_packs_dir(root: Path, pack_name: str) -> Path:
    """Return the packs directory that holds ``pack_name``.

    STORY-681 / REQ-055 AC5: a project-local ``.specflow/packs/<name>/`` with a
    ``pack.yaml`` wins over the bundled pack of the same name. Falls back to the
    bundled directory (whose own lookup reports "not found" when absent).
    """
    local = root / LOCAL_PACKS_DIR
    if (local / pack_name / "pack.yaml").is_file():
        return local
    return bundled_packs_dir()


def available_pack_names(root: Path, packs_dir: Path | None = None) -> list[str]:
    """Names of every pack with a ``pack.yaml`` in the local, bundled, and
    (when given) explicit packs directories — sorted, deduplicated."""
    names: set[str] = set()
    for base in (root / LOCAL_PACKS_DIR, bundled_packs_dir(), packs_dir):
        if base is None or not base.is_dir():
            continue
        for entry in base.iterdir():
            if (entry / "pack.yaml").is_file():
                names.add(entry.name)
    return sorted(names)


def pack_owned_schema_names(root: Path, active_packs: list[str]) -> set[str]:
    """Schema type names that one of ``active_packs`` owns.

    A pack owns a name when its manifest lists it under
    ``adds_artifact_types`` or it ships ``schemas/<name>.yaml``. Core
    schema-drift accounting (``refresh --schemas``, ``brief``) skips these so a
    pack that reuses an optional core name such as ``control`` or ``hazard``
    is never reported as a drifted core schema or overwritten by
    ``refresh --schemas --force``; ``refresh --packs`` owns that file.
    """
    owned: set[str] = set()
    for pack_name in active_packs or []:
        pack_root = resolve_packs_dir(root, pack_name) / pack_name
        manifest_path = pack_root / "pack.yaml"
        if manifest_path.is_file():
            try:
                manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            except (yaml.YAMLError, OSError, UnicodeDecodeError):
                manifest = None
            if isinstance(manifest, dict):
                owned.update(str(t) for t in manifest.get("adds_artifact_types", []) or [])
        schemas_dir = pack_root / "schemas"
        if schemas_dir.is_dir():
            owned.update(f.stem for f in schemas_dir.glob("*.yaml"))
    return owned


def pack_not_found_error(root: Path, pack_name: str, packs_dir: Path | None = None) -> str:
    """One message naming every lookup location plus the names that exist.

    The resolver checks ``.specflow/packs/<name>/pack.yaml`` first, then the
    bundled packs; an error that names only the bundled path (inside
    site-packages) sent users looking in the wrong place.
    """
    local_dir = root / LOCAL_PACKS_DIR / pack_name
    looked = [f"{LOCAL_PACKS_DIR.as_posix()}/{pack_name}/pack.yaml"]
    if packs_dir is not None and packs_dir != root / LOCAL_PACKS_DIR and packs_dir != bundled_packs_dir():
        looked.append(str(packs_dir / pack_name / "pack.yaml"))
    looked.append(str(bundled_packs_dir() / pack_name / "pack.yaml"))
    msg = f"Pack '{pack_name}' not found: looked for " + ", ".join(looked)
    if local_dir.is_dir():
        msg += f" ({LOCAL_PACKS_DIR.as_posix()}/{pack_name}/ exists but has no pack.yaml)"
    names = available_pack_names(root, packs_dir)
    near = [n for n in names if n.lower() == pack_name.lower() and n != pack_name]
    if near:
        msg += f" — did you mean '{near[0]}'?"
    if names:
        msg += f" (available: {', '.join(names)})"
    return msg


def backup_run_dir(root: Path, stamp: str | None = None) -> Path:
    """``.specflow/cache/backups/<timestamp>/`` — one directory per run.

    Callers that replace several files in one invocation pass the same
    ``stamp`` so every backup of that run lands under one directory.
    """
    stamp = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root / ".specflow" / "cache" / "backups" / stamp


def backup_file(src: Path, backup_root: Path, rel: Path | str) -> Path:
    """Copy ``src`` to ``backup_root / rel`` (creating parents) and return it."""
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))
    return dst


def _migrate_practice_provenance(root: Path) -> dict[str, Any]:
    """Apply the idempotent BP provenance migration after schema/pack writes."""
    from specflow.lib.practices import migrate_practices

    result = migrate_practices(root)
    if result.get("status_map_repaired"):
        print("  + Repaired best-practice status map to transitional values")
    if result.get("stamped"):
        print(
            f"  + Migrated provenance on {len(result['stamped'])} "
            "best-practice artifact(s)"
        )
    for warning in result.get("warnings", []):
        print(f"  ! Practice migration: {warning}")
    for error in result.get("errors", []):
        print(f"  ! Practice migration failed: {error}")
    return result


def create_spec_dirs(root: Path) -> None:
    """Create _specflow/ directory structure with _index.yaml stubs."""
    for rel in SPEC_DIRS:
        d = root / "_specflow" / rel
        d.mkdir(parents=True, exist_ok=True)
        index = d / "_index.yaml"
        if not index.exists():
            from specflow.lib import locks as locks_lib

            locks_lib.locked_exclusive_write(root, index, yaml.dump(_INDEX_STUB, default_flow_style=False))


def create_internal_dirs(root: Path, template_dir: Path, *, overwrite_schemas: bool = False) -> None:
    """Create .specflow/ internal directories and copy schemas.

    Args:
        root: Project root path.
        template_dir: Package templates directory.
        overwrite_schemas: If True, overwrite existing schemas with fresh copies
            from the package. Used by ``--force`` re-init.
    """
    specflow = root / ".specflow"
    for d in INTERNAL_DIRS:
        (specflow / d).mkdir(parents=True, exist_ok=True)
    for d in SCRATCH_DIRS:
        ensure_scratch_gitignore(specflow / d)

    schema_dst = specflow / "schema"
    schema_src = template_dir / "schemas"
    if schema_src.exists():
        schema_dst.mkdir(parents=True, exist_ok=True)
        for schema_file in schema_src.glob("*.yaml"):
            dst_file = schema_dst / schema_file.name
            if overwrite_schemas or not dst_file.exists():
                shutil.copy2(str(schema_file), str(dst_file))


def copy_adapters_config(root: Path, template_dir: Path) -> None:
    """Copy the default adapters.yaml template into .specflow/.

    Only copies if the destination doesn't already exist (preserves user edits).
    """
    src = template_dir / "adapters.yaml"
    dst = root / ".specflow" / "adapters.yaml"
    if not src.exists():
        return
    if dst.exists():
        return
    shutil.copy2(str(src), str(dst))


_CHECKLIST_CATEGORIES = ("phase-gates", "in-process", "review", "shared", "domain")


def _checklist_parses(path: Path) -> bool:
    """True when a checklist file loads as a YAML mapping (no warning printed)."""
    try:
        return isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict)
    except Exception:  # yaml.YAMLError, OSError, UnicodeDecodeError
        return False


def classify_checklists(root: Path, template_dir: Path) -> dict[str, list[str]]:
    """Compare shipped checklist templates with the project copies.

    Returns ``{"missing", "broken", "drifted"}`` lists of ``category/name``
    paths. Only SHIPPED names are classified — user-added checklists are
    never listed, so they are never replaced.
    """
    out: dict[str, list[str]] = {"missing": [], "broken": [], "drifted": []}
    checklists_src = template_dir / "checklists"
    checklists_dst = root / ".specflow" / "checklists"
    if not checklists_src.exists():
        return out
    for category in _CHECKLIST_CATEGORIES:
        src_cat = checklists_src / category
        if not src_cat.exists():
            continue
        for yaml_file in sorted(src_cat.glob("*.yaml")):
            rel = f"{category}/{yaml_file.name}"
            dst_file = checklists_dst / category / yaml_file.name
            if not dst_file.exists():
                out["missing"].append(rel)
            elif dst_file.read_bytes() == yaml_file.read_bytes():
                continue
            elif not _checklist_parses(dst_file):
                out["broken"].append(rel)
            else:
                out["drifted"].append(rel)
    return out


def copy_checklists(
    root: Path,
    template_dir: Path,
    *,
    force: bool = False,
    backup_stamp: str | None = None,
) -> dict[str, Any]:
    """Copy checklist templates from package to project instance.

    Copies from src/specflow/templates/checklists/ to .specflow/checklists/:

    - missing shipped checklists are always written;
    - a shipped-name checklist that no longer parses is replaced (its items
      could never run, so there is no user edit worth keeping in place);
    - a parseable but drifted shipped-name checklist is preserved unless
      ``force`` (user edits win by default);
    - user-added checklist names are never touched.

    Every replaced file is first backed up under
    ``.specflow/cache/backups/<timestamp>/checklists/`` (see
    :func:`backup_run_dir`). Returns the ``classify_checklists`` buckets plus
    ``replaced`` (what was overwritten) and ``backup_dir`` (relative to root,
    or ``None`` when nothing was backed up).
    """
    status = classify_checklists(root, template_dir)
    checklists_src = template_dir / "checklists"
    checklists_dst = root / ".specflow" / "checklists"
    replace = list(status["broken"]) + (list(status["drifted"]) if force else [])
    run_dir = backup_run_dir(root, backup_stamp)
    backed_up = False
    for rel in status["missing"] + replace:
        src = checklists_src / rel
        dst = checklists_dst / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            backup_file(dst, run_dir / "checklists", rel)
            backed_up = True
        shutil.copy2(str(src), str(dst))
    for category in _CHECKLIST_CATEGORIES:
        if (checklists_src / category).exists():
            (checklists_dst / category).mkdir(parents=True, exist_ok=True)
    backup_dir = run_dir.relative_to(root).as_posix() if backed_up else None
    return {**status, "replaced": replace, "backup_dir": backup_dir}


def inspect_pack_refresh(
    root: Path,
    pack_name: str,
    packs_dir: Path,
    platform_codes: list[str],
) -> dict[str, Any]:
    """Describe managed active-pack files that differ from shipped assets.

    Compares every tree ``apply_pack`` installs — schemas, checklists,
    standards (top-level ``*.yaml``, mirroring the install glob) and the
    pack's skills — so an edited pack is fully synced by ``refresh --packs``.
    """
    pack_root = packs_dir / pack_name
    manifest_path = pack_root / "pack.yaml"
    if not manifest_path.exists():
        return {"ok": False, "error": pack_not_found_error(root, pack_name, packs_dir)}
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    changes: list[tuple[Path, Path, str]] = []

    def compare_tree(src_root: Path, dst_root: Path, kind: str, pattern: str = "**/*") -> None:
        if not src_root.is_dir():
            return
        for src in sorted(path for path in src_root.glob(pattern) if path.is_file()):
            dst = dst_root / src.relative_to(src_root)
            if not dst.exists() or src.read_bytes() != dst.read_bytes():
                changes.append((src, dst, kind))

    compare_tree(pack_root / "schemas", root / ".specflow" / "schema", "schema")
    compare_tree(pack_root / "checklists", root / ".specflow" / "checklists", "checklist")
    compare_tree(pack_root / "standards", root / ".specflow" / "standards", "standard", "*.yaml")
    for platform_code in platform.unique_skill_install_codes(platform_codes):
        skills_root = platform.get_skills_install_dir(root, platform_code)
        for skill_name in manifest.get("adds_skills", []) or []:
            compare_tree(pack_root / "skills" / skill_name, skills_root / skill_name, "skill")
    return {"ok": True, "manifest": manifest, "changes": changes}


def refresh_pack(
    root: Path,
    pack_name: str,
    packs_dir: Path,
    platform_codes: list[str],
    *,
    force: bool = False,
    backup_stamp: str | None = None,
) -> dict[str, Any]:
    """Refresh generated files for an installed pack.

    Existing differing files are treated as ambiguous user edits and preserved
    unless ``force`` is explicit; a file ``force`` overwrites is first copied
    to ``.specflow/cache/backups/<timestamp>/packs/<pack>/<path>`` (same
    helper as checklists). Files below ``_specflow/`` are never targets.

    Returns ``written`` / ``preserved`` / ``backed_up`` path lists (relative
    to root) and ``backup_dir`` (relative, or ``None`` when nothing was
    backed up).
    """
    preview = inspect_pack_refresh(root, pack_name, packs_dir, platform_codes)
    if not preview.get("ok"):
        return preview
    written: list[str] = []
    preserved: list[str] = []
    backed_up: list[str] = []
    run_dir = backup_run_dir(root, backup_stamp)
    for src, dst, _kind in preview["changes"]:
        rel = dst.relative_to(root).as_posix()
        if dst.exists() and not force:
            preserved.append(rel)
            continue
        if dst.exists():
            backup_file(dst, run_dir / "packs" / pack_name, rel)
            backed_up.append(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        written.append(rel)

    manifest = preview["manifest"]
    for platform_code in platform_codes:
        inject_pack_context(root, pack_name, manifest.get("context_snippet", ""), platform_code)
    _migrate_practice_provenance(root)
    return {
        "ok": True,
        "written": written,
        "preserved": preserved,
        "backed_up": backed_up,
        "backup_dir": run_dir.relative_to(root).as_posix() if backed_up else None,
    }


def apply_pack(
    root: Path,
    pack_name: str,
    packs_dir: Path,
    platform_code: str | None = None,
) -> dict[str, Any]:
    """Apply a standards pack from packs_dir/<pack_name>/ to the project.

    Copies schemas, checklists, and standards into the project's .specflow/
    internals, and creates any new _specflow/ artifact directories declared in
    the pack manifest. Existing destination files are preserved (not overwritten).

    Pack-declared skills are installed into the platform skills directory. When
    ``platform_code`` is provided (e.g. ``specflow init --platform X``) it is used
    directly so skills install even before the platform marker directory exists
    (a fresh init applies presets before installing the shared skills). When it is
    None, the platform is auto-detected from the root's marker directories, and
    skills are skipped (with a warning) if no platform is detectable.

    Returns {"ok": True, "pack": ..., "types_added": [...], "standards_added": [...]}
    or {"ok": False, "error": str} on failure.
    """
    pack_root = packs_dir / pack_name
    manifest_path = pack_root / "pack.yaml"
    if not manifest_path.exists():
        return {"ok": False, "error": pack_not_found_error(root, pack_name, packs_dir)}

    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"Failed to parse {manifest_path}: {e}"}
    if not isinstance(manifest, dict):
        return {"ok": False, "error": f"Invalid manifest at {manifest_path}"}

    specflow_internal = root / ".specflow"
    types_added: list[str] = []
    standards_added: list[str] = []

    # 1. Copy schemas → .specflow/schema/ (no overwrite)
    src_schemas = pack_root / "schemas"
    if src_schemas.exists():
        dst_schemas = specflow_internal / "schema"
        dst_schemas.mkdir(parents=True, exist_ok=True)
        for yaml_file in src_schemas.glob("*.yaml"):
            dst_file = dst_schemas / yaml_file.name
            if not dst_file.exists():
                shutil.copy2(str(yaml_file), str(dst_file))

    # 2. Create _specflow/ directories declared in the manifest
    for rel in manifest.get("adds_directories", []) or []:
        d = root / "_specflow" / rel
        d.mkdir(parents=True, exist_ok=True)
        index = d / "_index.yaml"
        if not index.exists():
            from specflow.lib import locks as locks_lib

            locks_lib.locked_exclusive_write(root, index, yaml.dump(_INDEX_STUB, default_flow_style=False))

    # 3. Copy checklists (any subdirectory structure) → .specflow/checklists/
    src_checklists = pack_root / "checklists"
    if src_checklists.exists():
        dst_checklists_root = specflow_internal / "checklists"
        for src_file in src_checklists.rglob("*.yaml"):
            rel_path = src_file.relative_to(src_checklists)
            dst_file = dst_checklists_root / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            if not dst_file.exists():
                shutil.copy2(str(src_file), str(dst_file))

    # 4. Copy standards → .specflow/standards/ (no overwrite)
    src_standards = pack_root / "standards"
    if src_standards.exists():
        dst_standards = specflow_internal / "standards"
        dst_standards.mkdir(parents=True, exist_ok=True)
        for yaml_file in src_standards.glob("*.yaml"):
            dst_file = dst_standards / yaml_file.name
            if not dst_file.exists():
                shutil.copy2(str(yaml_file), str(dst_file))
                standards_added.append(yaml_file.stem)

    types_added = list(manifest.get("adds_artifact_types", []) or [])

    # 5. Install pack skills → platform skills dir (no overwrite)
    skills_added: list[str] = []
    declared_skills = manifest.get("adds_skills", []) or []
    if declared_skills:
        if platform_code is None:
            platform_code, _ = platform.detect_platform(root)
        if platform_code is None:
            print(f"  ⚠ Pack '{pack_name}' declares skills but no AI platform detected; install manually")
        else:
            skills_dir = platform.get_skills_install_dir(root, platform_code)
            for skill_name in declared_skills:
                src = pack_root / "skills" / skill_name
                if not src.is_dir():
                    return {
                        "ok": False,
                        "error": f"Pack declares skill '{skill_name}' but directory not found: {src}",
                    }
                dst = skills_dir / skill_name
                if not dst.exists():
                    shutil.copytree(str(src), str(dst))
                    skills_added.append(skill_name)

    _migrate_practice_provenance(root)

    return {
        "ok": True,
        "pack": pack_name,
        "types_added": types_added,
        "standards_added": standards_added,
        "skills_added": skills_added,
        "context_snippet": manifest.get("context_snippet", ""),
    }


_SENTINEL_START = "<!-- pack:{pack_name} context (auto-generated, do not edit manually) -->"
_SENTINEL_END = "<!-- end pack:{pack_name} context -->"

_BASE_SENTINEL_START = "<!-- SpecFlow section (auto-generated, do not edit manually) -->"
_BASE_SENTINEL_END = "<!-- End SpecFlow section -->"

# Old Claude-Code fallback. We never write here anymore; leftover sentinels
# are stripped so they do not rot beside AGENTS.md. Any platform whose
# instruction_file is AGENTS.md (claude-code, opencode, codex, junie, ...) can
# carry one from the old fallback path.
_LEGACY_INSTRUCTION_FILE = "CLAUDE.md"


def _get_target_instruction_file(root: Path, platform_code: str, instruction_file: str) -> Path | None:
    """Always the platform's declared instruction file. No CLAUDE.md fallback."""
    del platform_code  # kept in the signature for call-site compatibility
    return root / instruction_file


def _locate_sentinel_block(content: str, start: str, end: str) -> tuple[int, int] | None:
    """``(start_idx, end_idx)`` of a well-formed block, else ``None``.

    Well-formed means START is present and END occurs AFTER it. A missing
    END, or an END that only precedes START, is malformed: slicing from
    START to that END would raise or splice a block in front of the old one
    and grow the file on every refresh.
    """
    start_idx = content.find(start)
    if start_idx < 0:
        return None
    end_idx = content.find(end, start_idx + len(start))
    if end_idx < 0:
        return None
    return start_idx, end_idx + len(end)


def _strip_marker_lines(content: str, markers: tuple[str, ...]) -> str:
    """Drop lines that are exactly a marker; scrub any inline occurrence too.

    Only the marker text goes — every other line (including whatever sat
    between stray markers) is user text as far as we can tell and stays.
    """
    kept = [line for line in content.split("\n") if line.strip() not in markers]
    text = "\n".join(kept)
    for marker in markers:
        text = text.replace(marker, "")
    return text


def _display(root: Path, target: Path) -> str:
    try:
        return target.relative_to(root).as_posix()
    except ValueError:
        return str(target)


def _upsert_sentinel_block(
    root: Path,
    target: Path,
    start: str,
    end: str,
    block: str,
    *,
    fresh_text: str,
) -> bool:
    """Write one sentinel-bounded block into ``target`` idempotently.

    - absent file: write ``fresh_text`` (the caller's framing of ``block``);
    - no START: append ``block``;
    - well-formed block: replace in place when the content differs;
    - malformed markers (END missing, or END only before START): strip the
      dangling marker(s), keep every other line, append one fresh block and
      print a warning naming the file. The next run finds a well-formed
      block, so the file never grows.

    Returns True when the file was written.
    """
    new_block = block.strip()
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(fresh_text, encoding="utf-8")
        return True
    content = target.read_text(encoding="utf-8")
    if start not in content:
        target.write_text(content.rstrip() + "\n" + block, encoding="utf-8")
        return True
    span = _locate_sentinel_block(content, start, end)
    if span is None:
        print(
            f"  ! {_display(root, target)}: SpecFlow block markers were malformed "
            f"(end marker missing or before the start) — markers removed, block re-appended; "
            f"text from the old block may remain above the new one — review and delete it by hand"
        )
        repaired = _strip_marker_lines(content, (start, end))
        target.write_text(repaired.rstrip() + "\n" + block, encoding="utf-8")
        return True
    start_idx, end_idx = span
    if content[start_idx:end_idx] == new_block:
        return False
    target.write_text(content[:start_idx] + new_block + content[end_idx:], encoding="utf-8")
    return True


def _strip_sentinel_block(path: Path, start: str, end: str) -> bool:
    """Remove one sentinel-bounded block from ``path``. Returns True if rewritten."""
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    span = _locate_sentinel_block(content, start, end)
    if span is None:
        return False
    start_idx, end_idx = span
    # Drop a single surrounding newline so we do not leave a hole.
    if start_idx > 0 and content[start_idx - 1] == "\n":
        start_idx -= 1
    new_content = content[:start_idx] + content[end_idx:]
    if new_content.strip():
        path.write_text(new_content.lstrip("\n") if new_content.startswith("\n\n") else new_content, encoding="utf-8")
    else:
        path.write_text("", encoding="utf-8")
    return True


def _ensure_claude_code_bridge(root: Path) -> None:
    """Make Claude Code load the shared AGENTS.md via a one-line import.

    Claude Code reads ``CLAUDE.md`` only — it does not discover ``AGENTS.md``
    natively. The documented pattern (code.claude.com/docs/en/memory) is a
    ``@AGENTS.md`` import line in CLAUDE.md; Claude loads the imported file at
    session start, then the rest of CLAUDE.md. Without it, a migrated
    dual-host project's Claude Code sessions lose the shared SpecFlow guidance
    entirely. OpenCode ignores CLAUDE.md, so the line is inert for it.
    """
    claude_md = root / _LEGACY_INSTRUCTION_FILE
    agents_md = root / "AGENTS.md"
    if not claude_md.exists() or not agents_md.exists():
        return
    # The docs also bless `ln -s AGENTS.md CLAUDE.md`. That symlink already IS
    # the bridge; writing through it would prepend "@AGENTS.md" to AGENTS.md.
    if claude_md.resolve() == agents_md.resolve():
        return
    text = claude_md.read_text(encoding="utf-8")
    if any(line.strip() == "@AGENTS.md" for line in text.splitlines()):
        return  # already bridged (idempotent)
    if text.strip():
        rest = text.lstrip("\n")
        claude_md.write_text(f"@AGENTS.md\n\n{rest}", encoding="utf-8")
    else:
        # File held only the old SpecFlow block; the bridge is its whole content.
        claude_md.write_text("@AGENTS.md\n", encoding="utf-8")


def pending_claude_md_migration(root: Path, platform_code: str) -> list[str]:
    """Describe (for --dry-run and refresh summaries) pending CLAUDE.md actions."""
    cfg = platform.get_platform(platform_code)
    if not cfg or cfg.get("instruction_file") != "AGENTS.md":
        return []
    legacy = root / _LEGACY_INSTRUCTION_FILE
    target = root / "AGENTS.md"
    if not legacy.exists():
        return []
    if legacy.exists() and target.exists() and legacy.resolve() == target.resolve():
        return []  # symlinked CLAUDE.md already is the bridge
    actions: list[str] = []
    text = legacy.read_text(encoding="utf-8")
    target_text = target.read_text(encoding="utf-8") if target.exists() else ""
    # A real refresh runs inject_base_context first, which creates AGENTS.md
    # with the base sentinel — on a dry-run preview that "will exist" block
    # counts as present.
    base_will_exist = (not target.exists()) or (_BASE_SENTINEL_START in target_text)
    if _BASE_SENTINEL_START in text and base_will_exist:
        actions.append("strip legacy SpecFlow block from CLAUDE.md")
    for line in text.splitlines():
        if line.startswith("<!-- pack:") and "context (auto-generated" in line:
            pack_name = line[len("<!-- pack:"):].split(" ", 1)[0]
            if _SENTINEL_START.format(pack_name=pack_name) in target_text:
                actions.append(f"strip legacy pack block ({pack_name}) from CLAUDE.md")
    if not any(l.strip() == "@AGENTS.md" for l in text.splitlines()):
        actions.append("add @AGENTS.md import to CLAUDE.md")
    return actions


def _migrate_legacy_instruction_sentinels(root: Path, platform_code: str) -> None:
    """Strip SpecFlow / pack sentinels from a leftover CLAUDE.md, then bridge it.

    Runs whenever the platform's instruction file is AGENTS.md — the old
    CLAUDE.md fallback applied to every such host, not just claude-code.
    A block (base or pack) is stripped only once the same sentinel exists
    in AGENTS.md, so a pack-only or context-only refresh never deletes
    guidance that has not landed in the new location yet. Finally, the
    ``@AGENTS.md`` import line is added to CLAUDE.md so Claude Code keeps
    loading the shared guidance (it never reads AGENTS.md directly).
    """
    cfg = platform.get_platform(platform_code)
    if not cfg or cfg.get("instruction_file") != "AGENTS.md":
        return
    legacy = root / _LEGACY_INSTRUCTION_FILE
    if not legacy.exists():
        return
    target = root / "AGENTS.md"
    # `ln -s AGENTS.md CLAUDE.md` is the other documented Claude Code setup.
    # That symlink already IS the bridge: following it would strip the block
    # we just injected into AGENTS.md and rewrite AGENTS.md through the link.
    if legacy.resolve() == target.resolve():
        return
    target_text = target.read_text(encoding="utf-8") if target.exists() else ""
    if _BASE_SENTINEL_START in target_text:
        _strip_sentinel_block(legacy, _BASE_SENTINEL_START, _BASE_SENTINEL_END)
    text = legacy.read_text(encoding="utf-8") if legacy.exists() else ""
    for line in text.splitlines():
        if line.startswith("<!-- pack:") and "context (auto-generated" in line:
            pack_name = line[len("<!-- pack:"):].split(" ", 1)[0]
            start = _SENTINEL_START.format(pack_name=pack_name)
            end = _SENTINEL_END.format(pack_name=pack_name)
            if start in target_text:
                _strip_sentinel_block(legacy, start, end)
    _ensure_claude_code_bridge(root)


def inject_base_context(root: Path, templates_dir: Path, explicit_platform: str | None = None) -> bool:
    """Inject the base SpecFlow instructions into the platform instruction file."""
    platform_code = explicit_platform
    if platform_code is None:
        platform_code, _ = platform.detect_platform(root)
    if platform_code is None:
        return False

    cfg = platform.get_platform(platform_code)
    if not cfg:
        return False

    instruction_file = cfg.get("instruction_file")
    if not instruction_file:
        return False

    target = _get_target_instruction_file(root, platform_code, instruction_file)
    if not target:
        return False

    src = templates_dir / "agent-context.md"
    if not src.exists():
        return False

    context_snippet = src.read_text(encoding="utf-8").strip()
    block = f"\n{_BASE_SENTINEL_START}\n{context_snippet}\n{_BASE_SENTINEL_END}\n"
    fresh_text = block.lstrip()
    if instruction_file.endswith(".mdc"):
        fresh_text = f"---\ndescription: SpecFlow instructions\n---\n{block}".lstrip()

    changed = _upsert_sentinel_block(
        root, target, _BASE_SENTINEL_START, _BASE_SENTINEL_END, block, fresh_text=fresh_text,
    )
    _migrate_legacy_instruction_sentinels(root, platform_code)
    return changed


def inject_pack_context(root: Path, pack_name: str, context_snippet: str, explicit_platform: str | None = None) -> bool:
    """Inject a pack's context snippet into the platform instruction file.

    Uses sentinel markers for idempotent updates. Returns True if the file
    was modified (new injection or updated snippet).
    """
    if not context_snippet:
        return False

    platform_code = explicit_platform
    if platform_code is None:
        platform_code, _ = platform.detect_platform(root)
    if platform_code is None:
        return False

    cfg = platform.get_platform(platform_code)
    if not cfg:
        return False

    instruction_file = cfg.get("instruction_file")
    if not instruction_file:
        return False

    target = _get_target_instruction_file(root, platform_code, instruction_file)
    if not target:
        return False

    sentinel_start = _SENTINEL_START.format(pack_name=pack_name)
    sentinel_end = _SENTINEL_END.format(pack_name=pack_name)

    block = f"\n{sentinel_start}\n{context_snippet.strip()}\n{sentinel_end}\n"

    changed = _upsert_sentinel_block(
        root, target, sentinel_start, sentinel_end, block, fresh_text=block,
    )
    _migrate_legacy_instruction_sentinels(root, platform_code)
    return changed
