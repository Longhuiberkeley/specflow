"""Backward-compatibility shim — delegates to specflow.lib.best_practices.

This module is kept so that any external code importing from
``specflow.lib.handbook`` continues to work.  All new code should use
``specflow.lib.best_practices`` directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib import best_practices as _bp


def cache_dir(root: Path) -> Path:
    return _bp.cache_dir(root)


def cache_path(root: Path, domain: str, phase: str) -> Path:
    return _bp.cache_path(root, domain, "phase", phase)


def read_cached(root: Path, domain: str, phase: str) -> str | None:
    data = _bp.read_cached(root, domain, "phase", phase)
    if data is None:
        return None
    import yaml
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def write_cached(root: Path, domain: str, phase: str, content: str) -> Path:
    import yaml
    try:
        data = yaml.safe_load(content)
    except Exception:
        data = {"level": "phase", "raw_content": content}
    if not isinstance(data, dict):
        data = {"level": "phase", "raw_content": content}
    return _bp.write_cached(root, domain, "phase", phase, data)


def build_synthesis_prompt(domain: str, domain_tags: list[str], phase: str) -> tuple[str, str]:
    return _bp.build_phase_synthesis_prompt(domain, domain_tags, phase)


def synthesize_and_cache(
    root: Path,
    domain: str,
    domain_tags: list[str],
    phase: str,
    *,
    overwrite: bool = False,
) -> dict:
    return _bp.synthesize_and_cache(
        root, domain, domain_tags, "phase", phase, overwrite=overwrite,
    )


def compose_review_prefix(
    root: Path,
    domain: str,
    domain_tags: list[str],
    phase: str,
    complies_with_clause_ids: list[str],
    *,
    existing_techniques: list[str] | None = None,
) -> str:
    return _bp.compose_review_prefix(
        root, domain, domain_tags, phase, complies_with_clause_ids,
        existing_techniques=existing_techniques,
    )
