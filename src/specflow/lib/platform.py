"""Platform detection and registry for SpecFlow."""

from pathlib import Path

import yaml


_REGISTRY: dict | None = None


def _load_registry() -> dict:
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY
    registry_path = Path(__file__).parent.parent / "templates" / "platforms.yaml"
    with open(registry_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _REGISTRY = data.get("platforms", {})
    return _REGISTRY


def reload_registry() -> None:
    global _REGISTRY
    _REGISTRY = None


def get_all_platforms() -> dict:
    return _load_registry()


def get_platform(code: str) -> dict | None:
    platforms = _load_registry()
    return platforms.get(code)


def detect_platform(root: Path) -> tuple[str | None, dict | None]:
    """Detect which AI code platform is in use.

    Returns (platform_code, platform_config) or (None, None) if not detected.
    """
    platforms = _load_registry()
    for code, cfg in platforms.items():
        markers = cfg.get("detection", [])
        for marker in markers:
            if (root / marker).exists():
                return code, cfg
    return None, None


def get_skills_dir(root: Path, platform_code: str) -> Path:
    """Return the absolute skills directory for a platform."""
    cfg = get_platform(platform_code)
    if cfg is None:
        cfg = get_platform("claude-code")
    rel = cfg["skills_dir"]
    return root / rel


def get_preferred_platforms() -> list[tuple[str, dict]]:
    """Return platforms marked as preferred."""
    platforms = _load_registry()
    return [(code, cfg) for code, cfg in platforms.items() if cfg.get("preferred")]


def get_skill_names() -> list[str]:
    return [
        "specflow-init",
        "specflow-discover",
        "specflow-plan",
        "specflow-execute",
        "specflow-artifact-review",
        "specflow-change-impact-review",
        "specflow-audit",
        "specflow-ship",
        "specflow-pack-author",
        "specflow-adapter",
    ]
