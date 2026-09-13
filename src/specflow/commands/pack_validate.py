"""specflow pack-validate — deterministic pack structure validation (STORY-663).

Backstop for the pack-author skill: what `scripts/validate-pack.sh` used to
do in shell (with a broken `uv run python3` dependency) now lives in the CLI
where it is testable and dependency-correct. Checks:

1. Pack-file schema  — `pack.yaml` parses and carries `name`/`version`/
   `description`; declared list fields are lists.
2. Referenced files  — every `adds_skills` entry has `skills/<name>/SKILL.md`.
3. Structure         — `standards/*.yaml` (when present) carry
   `standard`/`title`/`clauses`; `schemas/*.yaml` (when present) carry the
   six schema fields.
4. No `uv run`       — shipped skill scripts must invoke bare `specflow`
   (AGENTS.md §Invocation Model); `uv run` only works where specflow is a
   declared project dependency, which consuming projects are not.

Exit codes: 0 = valid, 1 = invalid.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib.display import RED, GREEN, NC

_REQUIRED_PACK_FIELDS = ("name", "version", "description")
_LIST_PACK_FIELDS = ("adds_artifact_types", "adds_directories", "adds_skills")
_REQUIRED_STANDARD_FIELDS = ("standard", "title", "clauses")
_REQUIRED_SCHEMA_FIELDS = (
    "type", "prefix", "id_format", "required_fields", "allowed_status", "directory",
)
_FORBIDDEN_SCRIPT_TOKEN = "uv run"


def _load_yaml(path: Path) -> tuple[dict | None, str | None]:
    """Parse a YAML file; returns (data, error). data is None on failure."""
    if not path.exists():
        return None, None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # parse errors are validation findings, not crashes
        return None, f"{path.name}: invalid YAML — {exc}"
    if data is None:
        return None, f"{path.name}: empty YAML document"
    if not isinstance(data, dict):
        return None, f"{path.name}: top level is {type(data).__name__}, expected mapping"
    return data, None


def _check_pack_file(pack_dir: Path, errors: list[str]) -> dict:
    pack_file = pack_dir / "pack.yaml"
    if not pack_file.exists():
        errors.append(f"Missing: {pack_file.name}")
        return {}
    data, err = _load_yaml(pack_file)
    if err:
        errors.append(f"pack.yaml: {err}")
        return {}
    for field in _REQUIRED_PACK_FIELDS:
        value = data.get(field)
        if not value or not str(value).strip():
            errors.append(f"pack.yaml missing required field '{field}'")
    for field in _LIST_PACK_FIELDS:
        if field in data and not isinstance(data[field], list):
            errors.append(f"pack.yaml field '{field}' must be a list")
    return data


def _check_referenced_files(pack_dir: Path, manifest: dict, errors: list[str]) -> None:
    skills = manifest.get("adds_skills") or []
    if not isinstance(skills, list):
        return
    for entry in skills:
        if not isinstance(entry, str) or not entry.strip():
            errors.append("pack.yaml 'adds_skills' entries must be skill-directory names")
            continue
        skill_md = pack_dir / "skills" / entry / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"Referenced skill missing: skills/{entry}/SKILL.md")


def _check_standards(pack_dir: Path, errors: list[str]) -> None:
    standards_dir = pack_dir / "standards"
    if not standards_dir.is_dir():
        return  # skills-only packs (e.g. tldr-communication) ship no standards
    yaml_files = sorted(standards_dir.glob("*.yaml"))
    if not yaml_files:
        errors.append("standards/ exists but has no YAML files")
        return
    for sf in yaml_files:
        data, err = _load_yaml(sf)
        if err:
            errors.append(f"standards/{sf.name}: {err}")
            continue
        for field in _REQUIRED_STANDARD_FIELDS:
            if field not in data:
                errors.append(f"standards/{sf.name} missing '{field}'")


def _check_schemas(pack_dir: Path, errors: list[str]) -> None:
    schemas_dir = pack_dir / "schemas"
    if not schemas_dir.is_dir():
        return
    yaml_files = sorted(schemas_dir.glob("*.yaml"))
    if not yaml_files:
        return  # optional, may be empty
    for sf in yaml_files:
        data, err = _load_yaml(sf)
        if err:
            errors.append(f"schemas/{sf.name}: {err}")
            continue
        for field in _REQUIRED_SCHEMA_FIELDS:
            if field not in data:
                errors.append(f"schemas/{sf.name} missing '{field}'")


def _check_skill_scripts(pack_dir: Path, errors: list[str]) -> None:
    """Shipped skill scripts must never contain 'uv run' (STORY-663).

    `uv run specflow` only resolves where specflow is a declared project
    dependency — true in the SpecFlow repo itself, false in every consuming
    project (AGENTS.md §6, the bootstrap bug). Bare `specflow` is the contract.
    """
    skills_dir = pack_dir / "skills"
    if not skills_dir.is_dir():
        return
    for script in sorted(skills_dir.rglob("scripts/*")):
        if not script.is_file():
            continue
        try:
            text = script.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = script.relative_to(pack_dir)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _FORBIDDEN_SCRIPT_TOKEN in line:
                errors.append(
                    f"{rel}:{lineno} contains '{_FORBIDDEN_SCRIPT_TOKEN}' — "
                    f"shipped skill scripts must invoke bare `specflow`"
                )


def run(root: Path, args: dict) -> int:
    """Execute specflow pack-validate."""
    raw = str(args.get("pack_dir", "")).strip()
    if not raw:
        print(f"{RED}✗ Usage: specflow pack-validate <pack-directory>{NC}")
        return 1
    pack_dir = Path(raw).expanduser()
    if not pack_dir.is_absolute():
        pack_dir = Path.cwd() / pack_dir

    print(f"Validating pack: {raw}")
    print("---")

    errors: list[str] = []
    if not pack_dir.is_dir():
        errors.append(f"Not a directory: {raw}")
        manifest: dict = {}
    else:
        manifest = _check_pack_file(pack_dir, errors)
        _check_referenced_files(pack_dir, manifest, errors)
        _check_standards(pack_dir, errors)
        _check_schemas(pack_dir, errors)
        _check_skill_scripts(pack_dir, errors)

    print("---")
    if errors:
        for err in errors:
            print(f"  {RED}✗{NC} {err}")
        print(f"Failed: {len(errors)} error(s) found")
        return 1
    print(f"{GREEN}✓{NC} pack.yaml schema, referenced skills, and structure valid; "
          f"no '{_FORBIDDEN_SCRIPT_TOKEN}' in shipped skill scripts")
    print("Success: Pack validation passed")
    return 0
