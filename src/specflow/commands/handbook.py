"""`specflow handbook` — manage the domain best-practice cache.

Subcommands:
  - generate [project|<phase>]  Synthesize BPs via LLM and cache.
  - show [project|<phase>]      Print cached BPs.
  - path [project|<phase>]      Print cache file path.
  - list                        List all cached BP files.

Uses the structured YAML best-practices format from lib.best_practices.
"""

from __future__ import annotations

import sys
from pathlib import Path

from specflow.lib import best_practices as bp_lib
from specflow.lib import standards as standards_lib
from specflow.lib.config import get_domain

import yaml


def _resolve_domain(root: Path, override: str | None) -> tuple[str, list[str]]:
    if override:
        return override, []
    domain, tags = get_domain(root)
    return domain, tags


def _parse_key(raw: str) -> tuple[str, str]:
    if raw == "project":
        return "project", "project"
    return "phase", raw


def cmd_generate(root: Path, args: dict) -> int:
    raw_key = args.get("phase") or ""
    if not raw_key:
        print("error: key is required (e.g., project, plan-arc, plan-ddd, execute, verify-unit)", file=sys.stderr)
        return 1
    domain, tags = _resolve_domain(root, args.get("domain"))
    if not domain:
        print(
            "error: no domain set. Run `specflow domain set <name>` first, "
            "or pass --domain <name>.",
            file=sys.stderr,
        )
        return 1
    level, key = _parse_key(raw_key)
    overwrite = bool(args.get("overwrite"))
    result = bp_lib.synthesize_and_cache(root, domain, tags, level, key, overwrite=overwrite)
    if not result["ok"]:
        print(f"error: {result['error']}", file=sys.stderr)
        return 1
    if result["cached"]:
        print(f"✓ already cached at {result['path']} (use --overwrite to regenerate)")
    else:
        data = result.get("data") or {}
        bps = data.get("best_practices") or []
        if level == "project":
            print(f"✓ generated project-level BPs for domain={domain}")
        else:
            process_area = data.get("process_area", standards_lib.process_area_for(key))
            print(f"✓ generated phase-level BPs for domain={domain}, phase={key}")
            print(f"  process area: {process_area}")
        print(f"  practices:    {len(bps)}")
        print(f"  written to:   {result['path']}")
        backup = result.get("backup")
        if backup:
            print(f"  backup:       {backup}")
    return 0


def cmd_show(root: Path, args: dict) -> int:
    raw_key = args.get("phase") or ""
    if not raw_key:
        print("error: key is required (project or phase name)", file=sys.stderr)
        return 1
    domain, _ = _resolve_domain(root, args.get("domain"))
    if not domain:
        print("error: no domain set; pass --domain <name> or run `specflow domain set <name>`", file=sys.stderr)
        return 1
    level, key = _parse_key(raw_key)
    data = bp_lib.read_cached(root, domain, level, key)
    if data is None:
        path = bp_lib.cache_path(root, domain, level, key)
        print(f"(no BPs cached at {path.relative_to(root)} — run `specflow handbook generate {raw_key}`)")
        return 0
    print(yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True))
    return 0


def cmd_path(root: Path, args: dict) -> int:
    raw_key = args.get("phase") or ""
    if not raw_key:
        print("error: key is required", file=sys.stderr)
        return 1
    domain, _ = _resolve_domain(root, args.get("domain"))
    if not domain:
        print("error: no domain set; pass --domain <name> or run `specflow domain set <name>`", file=sys.stderr)
        return 1
    level, key = _parse_key(raw_key)
    print(bp_lib.cache_path(root, domain, level, key))
    return 0


def cmd_list(root: Path, args: dict) -> int:
    bp_dir = bp_lib.cache_dir(root)
    if not bp_dir.exists():
        print("(no cached BPs — run `specflow handbook generate project` or a phase name)")
        return 0
    files = sorted(bp_dir.glob("*.yaml"))
    if not files:
        print("(no cached BPs)")
        return 0
    for f in files:
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        level = data.get("level", "?")
        domain = data.get("domain", "?")
        bps = data.get("best_practices") or []
        phase = data.get("phase", "")
        label = f"{domain} project" if level == "project" else f"{domain} phase={phase}"
        print(f"  {f.name}  ({label}, {len(bps)} practices)")
    return 0


def run(root: Path, args: dict) -> int:
    sub = args.get("handbook_subcommand")
    if sub == "generate":
        return cmd_generate(root, args)
    if sub == "show":
        return cmd_show(root, args)
    if sub == "path":
        return cmd_path(root, args)
    if sub == "list":
        return cmd_list(root, args)
    print("error: subcommand required (generate | show | path | list)", file=sys.stderr)
    return 1
