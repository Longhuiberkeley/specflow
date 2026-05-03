"""Configuration reading and writing for SpecFlow."""

from datetime import datetime, timezone
from pathlib import Path

import yaml


CONFIG_FILENAME = "config.yaml"
STATE_FILENAME = "state.yaml"


def default_config(project_name: str = "") -> dict:
    """Return a default config dict with timestamps."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "project": {"name": project_name, "created": now, "domain": "", "domain_tags": []},
        "impact_analysis": {
            "auto_flag": True,
            "auto_resolve": False,
            "remind_after": "7d",
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
            "llm": {
                "provider": "openrouter",
                "model": "google/gemma-4-26b-a4b-it:free",
                "api_key_env": "OPENROUTER_API_KEY",
                "base_url": "https://openrouter.ai/api/v1",
            },
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


