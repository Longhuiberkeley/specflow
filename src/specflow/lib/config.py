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
        "project": {"name": project_name, "created": now},
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


def update_execution_state(root: Path, execution_data: dict) -> None:
    """Merge execution state into state.yaml."""
    state = read_state(root)
    state["execution"] = execution_data
    write_state(root, state)


def read_execution_state(root: Path) -> dict | None:
    """Read the execution block from state.yaml."""
    state = read_state(root)
    return state.get("execution")
