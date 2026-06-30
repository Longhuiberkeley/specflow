"""Configuration reading and writing for SpecFlow."""

import copy
from datetime import datetime, timezone
from pathlib import Path

import yaml

import specflow


CONFIG_FILENAME = "config.yaml"
STATE_FILENAME = "state.yaml"


def default_config(project_name: str = "") -> dict:
    """Return a default config dict with timestamps."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "version": specflow.__version__,
        "project": {"name": project_name, "created": now, "domain": "", "domain_tags": []},
        "impact_analysis": {},
        "learning": {
            "learnable_techniques": [],
            "max_patterns_per_session": 3,
        },
        "lint": {
            "compliance_evidence_strict": False,
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
    path = root / ".specflow" / STATE_FILENAME
    path.write_text(yaml.dump(state, default_flow_style=False, sort_keys=False))


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
    merged["version"] = specflow.__version__
    return merged


def detect_version_delta(root: Path) -> dict:
    """Detect config version and compare against framework version.

    Returns dict with: current_version, framework_version, is_upgrade, new_fields.
    """
    cfg = read_config(root)
    current_version = cfg.get("version")
    framework_version = specflow.__version__

    defaults = default_config()
    default_keys = set(defaults.keys())
    existing_keys = set(cfg.keys())
    new_fields = sorted(default_keys - existing_keys - {"version"})

    return {
        "current_version": current_version,
        "framework_version": framework_version,
        "is_upgrade": current_version is not None and current_version != framework_version,
        "new_fields": new_fields,
    }


def backup_specflow_internals(root: Path, backup_dir: Path) -> list[str]:
    """Backup .specflow/ internals (config, state, schemas) to backup_dir.

    Returns list of backed-up file paths relative to root.
    """
    import shutil

    backed_up: list[str] = []
    specflow_dir = root / ".specflow"

    for name in ("config.yaml", "state.yaml"):
        src = specflow_dir / name
        if src.exists():
            shutil.copy2(str(src), str(backup_dir / name))
            backed_up.append(f".specflow/{name}")

    schema_src = specflow_dir / "schema"
    schema_dst = backup_dir / "schema"
    if schema_src.exists():
        if schema_dst.exists():
            shutil.rmtree(str(schema_dst))
        shutil.copytree(str(schema_src), str(schema_dst))
        backed_up.append(".specflow/schema/")

    return backed_up


