"""Adapter framework — config loading and adapter dispatch.

Usage:
    from specflow.lib.adapters import load_adapters_config, get_adapter

    config = load_adapters_config()
    ci_adapter = get_adapter(config["ci"]["provider"])
    files = ci_adapter.generate_ci_workflow(config["ci"]["operations"])
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from specflow.lib.adapters.base import (
    Adapter,
    ADAPTER_REGISTRY,
    get_adapter,
    register_adapter,
)

# Import concrete adapters so they register themselves.
import specflow.lib.adapters.github_actions  # noqa: F401
import specflow.lib.adapters.reqif  # noqa: F401

# Re-export public names.
__all__ = [
    "Adapter",
    "ADAPTER_REGISTRY",
    "get_adapter",
    "register_adapter",
    "load_adapters_config",
    "DEFAULT_ADAPTERS_CONFIG",
]

# Default config shape when .specflow/adapters.yaml doesn't exist yet.
DEFAULT_ADAPTERS_CONFIG: dict[str, Any] = {
    "ci": {
        "provider": "github-actions",
        "operations": ["artifact-lint", "change-impact", "project-audit"],
        "release_gate": {"severity": "error"},
    },
    "exchange": [
        {"name": "reqif", "provider": "reqif", "direction": "bidirectional"},
    ],
    "standards": [],
}


def load_adapters_config(root: Path | None = None) -> dict[str, Any]:
    """Read .specflow/adapters.yaml and return the parsed config.

    Falls back to DEFAULT_ADAPTERS_CONFIG if the file doesn't exist.
    """
    if root is None:
        root = Path.cwd()
    config_path = root / ".specflow" / "adapters.yaml"
    if not config_path.is_file():
        return dict(DEFAULT_ADAPTERS_CONFIG)

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return dict(DEFAULT_ADAPTERS_CONFIG)

    # Merge with defaults for missing sections.
    merged = dict(DEFAULT_ADAPTERS_CONFIG)
    for key in ("ci", "exchange", "standards"):
        if key in data:
            merged[key] = data[key]
    return merged
