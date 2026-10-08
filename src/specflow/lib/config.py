"""Configuration reading and writing for SpecFlow."""

import copy
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

import specflow


CONFIG_FILENAME = "config.yaml"
STATE_FILENAME = "state.yaml"

# STORY-678 / REQ-057: on-disk format version — the only version stamp in
# config.yaml (the release ``version`` key was dropped in v1.17.1). Bump FORMAT_VERSION only with a migration; an engine refuses
# to trust a repository whose format_version exceeds SUPPORTED_FORMAT_VERSION.
FORMAT_VERSION = 1
SUPPORTED_FORMAT_VERSION = 1
UPGRADE_INSTRUCTION = (
    "uv tool install --force git+https://github.com/Longhuiberkeley/specflow"
)
_FORMAT_WARNED: set[str] = set()


def default_config(project_name: str = "") -> dict:
    """Return a default config dict with timestamps."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "format_version": FORMAT_VERSION,
        "project": {"name": project_name, "created": now, "domain": "", "domain_tags": []},
        "impact_analysis": {},
        "learning": {
            "learnable_techniques": [],
            "max_patterns_per_session": 3,
        },
        "lint": {
            "compliance_evidence_strict": False,
            "bp_evidence_strict": False,
            "autoresearch_logging_strict": False,
            "role_target_strict": False,
        },
        "artifact_types": [
            "requirement",
            "architecture",
            "detailed-design",
            "unit-test",
            "integration-test",
            "qualification-test",
            "story",
            "spike",
            "decision",
            "defect",
        ],
        "active_packs": [],
        # What counts as "source" for coverage / orphan / drift scans. Empty =
        # respect .gitignore (git repos) + the built-in extension heuristic.
        #   include:    glob allowlist; if set, ONLY these count and they bypass
        #               the extension heuristic (e.g. ["src/**/*.py", "tests/**/*.py"]).
        #   exclude:    glob denylist, subtracted last (e.g. ["data/**"]).
        #   extensions: extra suffixes treated as code (e.g. [".ipynb"]).
        "source_scope": {"include": [], "exclude": [], "extensions": []},
        # The recognized documentation surface — prose docs that SpecFlow indexes
        # and surfaces but does NOT treat as lifecycle artifacts. Markdown sitting
        # directly at the project root is always recognized (README, AGENTS,
        # CHANGELOG, ROADMAP, …). Docs cite artifacts with inline @ID markers;
        # audit warns (never blocks) when a doc cites a superseded artifact.
        # Editing a doc is git-history-only. See lib/docs.py and
        # lib/files.py:docs_surface_paths.
        #   roots:       dirs/files treated as docs (default docs/).
        #   extra_files: loose files outside roots + root (e.g. examples/guide.md).
        #   exclude:     glob denylist subtracted from the surface.
        "docs": {
            "roots": ["docs/"],
            "extra_files": [],
            "exclude": [],
        },
        "team": {
            "roles": {
                "reviewer": [],
                "approver": [],
                "maintainer": [],
            },
            "policy": {
                "transitions": {},
                "verification_statuses": ["verified"],
                "directory_ownership": {},
            },
        },
        "ci": {
        },
    }


def default_state() -> dict:
    """Return a default state dict."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {"current": "idle", "history": [], "created": now}


def write_config(root: Path, config: dict) -> None:
    """Write config.yaml to .specflow/."""
    path = root / ".specflow" / CONFIG_FILENAME
    path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))


def write_state(root: Path, state: dict) -> None:
    """Write state.yaml to .specflow/."""
    from specflow.lib import locks as locks_lib

    path = root / ".specflow" / STATE_FILENAME
    locks_lib.locked_write(root, path, yaml.dump(state, default_flow_style=False, sort_keys=False))


def read_config(root: Path) -> dict:
    """Read config.yaml from .specflow/."""
    path = root / ".specflow" / CONFIG_FILENAME
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def read_state(root: Path) -> dict:
    """Read state.yaml from .specflow/."""
    path = root / ".specflow" / STATE_FILENAME
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def get_domain(root: Path) -> tuple[str, list[str]]:
    """Return (domain, tags) from config.yaml, or ('', []) if unset."""
    cfg = read_config(root)
    project = cfg.get("project") or {}
    domain = project.get("domain") or ""
    tags = project.get("domain_tags") or []
    if not isinstance(tags, list):
        tags = []
    return domain, tags


def set_domain(root: Path, domain: str, tags: list[str] | None = None) -> None:
    """Persist domain (and optional tags) under project.domain in config.yaml.

    Creates the project section if missing. Existing keys outside project.domain
    and project.domain_tags are preserved.
    """
    cfg = read_config(root)
    project = cfg.get("project")
    if not isinstance(project, dict):
        project = {}
    project["domain"] = domain
    project["domain_tags"] = list(tags or [])
    cfg["project"] = project
    write_config(root, cfg)


def merge_config(existing: dict, defaults: dict) -> dict:
    """Deep merge existing user config with new framework defaults.

    User values always win. New default keys are added. Lists are merged
    and deduplicated. The framework version is always stamped.
    """
    merged = copy.deepcopy(defaults)

    def _deep_merge(base: dict, overlay: dict) -> dict:
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                _deep_merge(base[key], value)
            elif key in base and isinstance(base[key], list) and isinstance(value, list):
                combined = base[key] + [v for v in value if v not in base[key]]
                base[key] = combined
            else:
                base[key] = value
        return base

    _deep_merge(merged, existing)
    # The legacy release ``version`` key had no reader and went stale on every
    # upgrade; format_version is the compatibility signal (REQ-057).
    merged.pop("version", None)
    existing_fv = existing.get("format_version")
    if not isinstance(existing_fv, int) or isinstance(existing_fv, bool) or existing_fv < FORMAT_VERSION:
        merged["format_version"] = FORMAT_VERSION
    return merged


def _read_format_version(cfg: dict) -> int | None:
    value = cfg.get("format_version")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def stamp_format_version(root: Path, *, dry_run: bool = False) -> bool:
    """Ensure config.yaml carries ``format_version: FORMAT_VERSION``.

    A minimal text edit (comments and key order survive). A higher
    format_version is never downgraded.
    Returns True when the file was (or, with ``dry_run``, would be) changed.
    """
    path = root / ".specflow" / CONFIG_FILENAME
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    cfg = yaml.safe_load(text) or {}
    if not isinstance(cfg, dict):
        return False
    current = _read_format_version(cfg)
    if current is not None and current >= FORMAT_VERSION:
        return False
    if dry_run:
        return True
    line = f"format_version: {FORMAT_VERSION}"
    if re.search(r"^format_version:.*$", text, flags=re.M):
        text = re.sub(r"^format_version:.*$", line, text, count=1, flags=re.M)
    elif re.search(r"^version:.*$", text, flags=re.M):
        text = re.sub(r"^(version:.*)$", lambda m: f"{m.group(1)}\n{line}", text, count=1, flags=re.M)
    else:
        text = f"{line}\n{text}"
    path.write_text(text, encoding="utf-8")
    return True


_LEGACY_VERSION_LINE = re.compile(r"^version:.*\n?", flags=re.M)


def strip_legacy_version(root: Path, *, dry_run: bool = False) -> str | None:
    """Remove the stale top-level ``version:`` key from config.yaml.

    Returns the removed value (or, with ``dry_run``, the value that would be
    removed); None when there is nothing to strip. Only a top-level line
    matches, so nested ``version`` keys are never touched.
    """
    path = root / ".specflow" / CONFIG_FILENAME
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    cfg = yaml.safe_load(text) or {}
    if not isinstance(cfg, dict) or "version" not in cfg:
        return None
    if not _LEGACY_VERSION_LINE.search(text):
        return None
    if not dry_run:
        path.write_text(_LEGACY_VERSION_LINE.sub("", text, count=1), encoding="utf-8")
    return str(cfg["version"])


def format_version_mismatch(root: Path) -> str | None:
    """Return the upgrade message when the repo is newer than this engine."""
    try:
        cfg = read_config(root)
    except Exception:
        return None
    if not isinstance(cfg, dict):
        return None
    repo_fv = _read_format_version(cfg)
    if repo_fv is None or repo_fv <= SUPPORTED_FORMAT_VERSION:
        return None
    return (
        f"This project's format_version is {repo_fv}, but this SpecFlow "
        f"(v{specflow.__version__}) supports format_version "
        f"{SUPPORTED_FORMAT_VERSION}. Upgrade SpecFlow: {UPGRADE_INSTRUCTION}"
    )


def warn_format_version_once(root: Path) -> None:
    """Print the format_version mismatch to stderr at most once per process."""
    key = str(root.resolve())
    if key in _FORMAT_WARNED:
        return
    msg = format_version_mismatch(root)
    if msg is None:
        return
    _FORMAT_WARNED.add(key)
    print(f"! specflow: {msg}", file=sys.stderr)


def backup_specflow_internals(root: Path, backup_dir: Path) -> list[str]:
    """Backup .specflow/ internals to backup_dir before ``init --force`` resets.

    config.yaml, state.yaml and schema/ are what the reset rewrites; the
    findings baseline, checklists/ and source fingerprints are accepted debt,
    user edits and drift state that would be expensive to reconstruct, so
    they ride along even though the reset itself keeps them (F-117). The
    literal names stay inline: tests/test_single_index_writer.py exempts
    this copy by matching them here.

    Returns list of backed-up file paths relative to root.
    """
    import shutil

    backed_up: list[str] = []
    specflow_dir = root / ".specflow"
    backup_dir.mkdir(parents=True, exist_ok=True)

    for name in ("config.yaml", "state.yaml", "findings-baseline.yaml", "source-fingerprints.yaml"):
        src = specflow_dir / name
        if src.exists():
            shutil.copy2(str(src), str(backup_dir / name))
            backed_up.append(f".specflow/{name}")

    for name in ("schema", "checklists"):
        tree_src = specflow_dir / name
        tree_dst = backup_dir / name
        if tree_src.is_dir():
            if tree_dst.exists():
                shutil.rmtree(str(tree_dst))
            shutil.copytree(str(tree_src), str(tree_dst))
            backed_up.append(f".specflow/{name}/")

    return backed_up

