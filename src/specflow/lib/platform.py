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
    detected = detect_platforms(root)
    if detected:
        return detected[0]
    return None, None


def detect_platforms(root: Path) -> list[tuple[str, dict]]:
    """Detect ALL AI code platforms in use, in registry order.

    Returns a list of (platform_code, platform_config) for every platform
    whose detection marker(s) exist under `root`. Empty list if none detected.
    """
    platforms = _load_registry()
    detected: list[tuple[str, dict]] = []
    for code, cfg in platforms.items():
        markers = cfg.get("detection", [])
        for marker in markers:
            if (root / marker).exists():
                detected.append((code, cfg))
                break
    return detected


# Hosts that already read project `.claude/skills` (OpenCode V2 compatibility
# source). Installing a second SpecFlow tree into their own skills_dir would
# collapse to the same IDs — `.opencode/skills` wins, silently forking the
# playbook. `.opencode/skills` stays reserved for *different* IDs only.
_SKILLS_CONSUME_CLAUDE = frozenset({"opencode"})


def get_skills_install_code(platform_code: str) -> str:
    """Platform whose ``skills_dir`` should receive SpecFlow + pack skills."""
    if platform_code in _SKILLS_CONSUME_CLAUDE:
        return "claude-code"
    return platform_code


def unique_skill_install_codes(platform_codes: list[str]) -> list[str]:
    """Dedup platform codes that share one SpecFlow skill tree."""
    seen: list[str] = []
    for code in platform_codes:
        install = get_skills_install_code(code)
        if install not in seen:
            seen.append(install)
    return seen


def get_skills_dir(root: Path, platform_code: str) -> Path:
    """Return the absolute skills directory listed in the platform registry.

    This is the host's *own* skills dir (e.g. ``.opencode/skills``). Use
    :func:`get_skills_install_dir` when copying SpecFlow or pack skills.
    """
    cfg = get_platform(platform_code)
    if cfg is None:
        cfg = get_platform("claude-code")
    rel = cfg["skills_dir"]
    return root / rel


def get_skills_install_dir(root: Path, platform_code: str) -> Path:
    """Directory that should receive SpecFlow + pack skill copies."""
    return get_skills_dir(root, get_skills_install_code(platform_code))


def leftover_specflow_skills(root: Path, platform_code: str) -> list[str]:
    """SpecFlow skill dirs sitting in a host tree we no longer install to.

    Same-ID leftovers in ``.opencode/skills`` silently override ``.claude/skills``
    on OpenCode. Callers should warn; we do not delete them.
    """
    if get_skills_install_code(platform_code) == platform_code:
        return []
    own = get_skills_dir(root, platform_code)
    if not own.is_dir():
        return []
    return sorted(
        p.name for p in own.iterdir()
        if p.is_dir() and p.name.startswith("specflow-")
    )


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
        "specflow-doc",
        "specflow-start",
    ]
