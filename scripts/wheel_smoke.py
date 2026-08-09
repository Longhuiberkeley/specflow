#!/usr/bin/env python3
"""Wheel smoke test — release verification for a locally built SpecFlow wheel.

Verifies that a ``specflow`` wheel (built from this source tree, never fetched
from PyPI — the public ``specflow`` package on PyPI is an unrelated library)
contains every packaged asset and that the installed entry point can scaffold
and drive a fresh project:

  1. Build the wheel (or accept one via ``--wheel``).
  2. Compare wheel contents against the source tree: schemas, skills including
     their ``references/`` trees, checklists, packs, agent-context, adapters,
     platforms, and all Python modules must all be present.
  3. Install the wheel into an isolated virtualenv created by ``uv``.
  4. ``specflow init`` a throwaway project with the *installed* entry point and
     confirm ``specflow status`` and ``specflow brief`` succeed.
  5. Confirm the initialized project actually received schemas, skills (with
     references), checklists, agent-context, and — via a pack preset — pack
     assets from the wheel.

Requires ``uv`` on PATH. Dependencies (pyyaml) are resolved by uv the normal
way; the specflow package itself is always installed from the built wheel.

Usage:
    uv run python scripts/wheel_smoke.py
    uv run python scripts/wheel_smoke.py --wheel dist/specflow-1.13.7-py3-none-any.whl
    uv run python scripts/wheel_smoke.py --python 3.13 --keep
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "specflow"

PACK_PRESET = "ops"
PACK_SKILL = "specflow-ops"
PACK_SCHEMAS = ("run.yaml", "monitor.yaml")
PACK_CONTEXT_MARK = "Ops Pack"
AGENT_CONTEXT_SENTINEL = "<!-- SpecFlow section (auto-generated, do not edit manually) -->"

_BIN = "Scripts" if os.name == "nt" else "bin"
_EXE = ".exe" if os.name == "nt" else ""


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run ``cmd`` in ``cwd``, print it, and return the CompletedProcess."""
    print(f"  $ {subprocess.list2cmdline(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed (rc={result.returncode}): {subprocess.list2cmdline(cmd)}"
        )
    return result


# ── Wheel content verification ────────────────────────────────────

def _iter_source_files(src_dir: Path):
    for path in sorted(src_dir.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path


def verify_wheel_contents(wheel_path: Path, src_dir: Path) -> list[str]:
    """Return wheel entries missing relative to the source tree.

    Every file under ``src/specflow/`` must ship as ``specflow/<relpath>`` in
    the wheel. This covers Python modules, schemas, skills (including their
    ``references/`` trees), checklists, packs, agent-context, adapters, and
    platforms in one authoritative pass.
    """
    with zipfile.ZipFile(wheel_path) as zf:
        wheel_names = set(zf.namelist())
    missing: list[str] = []
    for src in _iter_source_files(src_dir):
        rel = src.relative_to(src_dir).as_posix()
        expected = f"specflow/{rel}"
        if expected not in wheel_names:
            missing.append(f"{expected} (source: {src})")
    return missing


def verify_asset_signals(wheel_path: Path) -> list[str]:
    """Curated presence checks with human-readable messages."""
    with zipfile.ZipFile(wheel_path) as zf:
        names = set(zf.namelist())
    signals: list[str] = []

    for label, path in (
        ("agent-context", "specflow/templates/agent-context.md"),
        ("platforms.yaml", "specflow/templates/platforms.yaml"),
        ("adapters.yaml", "specflow/templates/adapters.yaml"),
        ("py.typed", "specflow/py.typed"),
    ):
        if path not in names:
            signals.append(f"wheel is missing {label}: {path}")

    schema_count = sum(
        1 for n in names if n.startswith("specflow/templates/schemas/") and n.endswith(".yaml")
    )
    if schema_count < 10:
        signals.append(f"expected >=10 base schema yamls, found {schema_count}")
    checklist_count = sum(
        1 for n in names if n.startswith("specflow/templates/checklists/") and n.endswith(".yaml")
    )
    if checklist_count < 20:
        signals.append(f"expected >=20 checklist yamls, found {checklist_count}")
    ref_count = sum(1 for n in names if "/references/" in n and n.endswith(".md"))
    if ref_count < 20:
        signals.append(f"expected >=20 skill reference markdown files, found {ref_count}")
    pack_count = sum(1 for n in names if n.startswith("specflow/packs/") and n.endswith("/pack.yaml"))
    if pack_count < 4:
        signals.append(f"expected >=4 pack manifests, found {pack_count}")
    skill_count = sum(1 for n in names if n.endswith("/SKILL.md"))
    if skill_count < 10:
        signals.append(f"expected >=10 skill SKILL.md files, found {skill_count}")

    return signals


# ── Isolated install + init smoke ─────────────────────────────────

def build_wheel(out_dir: Path, repo_root: Path = REPO_ROOT) -> Path:
    """Build the wheel with uv and return its path."""
    _run(["uv", "build", "--wheel", "--out-dir", str(out_dir)], cwd=repo_root)
    wheels = sorted(out_dir.glob("*.whl"))
    if not wheels:
        raise RuntimeError(f"uv build produced no wheel in {out_dir}")
    return wheels[0]


def create_venv(venv_dir: Path, python: str) -> Path:
    """Create an isolated venv with uv and return the venv python path."""
    _run(["uv", "venv", str(venv_dir), "--python", python], cwd=REPO_ROOT)
    return venv_dir / _BIN / f"python{_EXE}"


def install_wheel(venv_python: Path, wheel: Path) -> None:
    _run(
        ["uv", "pip", "install", "--python", str(venv_python), str(wheel)],
        cwd=REPO_ROOT,
    )


def _specflow_bin(venv_python: Path) -> Path:
    return venv_python.parent / f"specflow{_EXE}"


def run_cli(
    venv_python: Path,
    cwd: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return _run([str(_specflow_bin(venv_python)), *args], cwd=cwd, check=check)


def init_project(venv_python: Path, proj_dir: Path, *extra_args: str) -> None:
    """Scaffold a throwaway project with the installed entry point."""
    proj_dir.mkdir(parents=True, exist_ok=True)
    # Real projects are git repos; best-effort so `init` also exercises the
    # pre-commit hook path. brief/status tolerate a missing repo.
    _run(["git", "init", "-q"], cwd=proj_dir, check=False)
    run_cli(venv_python, proj_dir, "init", "--platform", "claude-code", *extra_args)


# ── Post-init asset checks ─────────────────────────────────────────

def verify_initialized_assets(proj_dir: Path) -> list[str]:
    problems: list[str] = []

    schema = proj_dir / ".specflow" / "schema"
    for name in ("requirement.yaml", "architecture.yaml", "story.yaml"):
        if not (schema / name).exists():
            problems.append(f"base schema not installed: {schema / name}")

    skills = proj_dir / ".claude" / "skills"
    for skill in ("specflow-start", "specflow-discover"):
        if not (skills / skill / "SKILL.md").exists():
            problems.append(f"skill not installed: {skills / skill / 'SKILL.md'}")
    if not list(skills.rglob("references/*.md")):
        problems.append("no skill reference markdown files installed")

    if not list((proj_dir / ".specflow" / "checklists").glob("**/*.yaml")):
        problems.append("no checklists installed under .specflow/checklists/")

    agents = proj_dir / "AGENTS.md"
    if not agents.exists() or AGENT_CONTEXT_SENTINEL not in agents.read_text(encoding="utf-8", errors="ignore"):
        problems.append("agent-context not injected into AGENTS.md")

    for rel in (".specflow/config.yaml", ".specflow/state.yaml", ".specflow/adapters.yaml"):
        if not (proj_dir / rel).exists():
            problems.append(f"missing {rel}")

    return problems


def verify_pack_assets(proj_dir: Path, *, require_skill: bool) -> list[str]:
    """Verify pack (preset) assets landed after init and after refresh."""
    problems: list[str] = []
    schema = proj_dir / ".specflow" / "schema"
    for name in PACK_SCHEMAS:
        if not (schema / name).exists():
            problems.append(f"pack schema not installed: {schema / name}")
    agents = proj_dir / "AGENTS.md"
    if not agents.exists() or PACK_CONTEXT_MARK not in agents.read_text(encoding="utf-8", errors="ignore"):
        problems.append("pack context snippet not injected into AGENTS.md")
    if require_skill:
        skill = proj_dir / ".claude" / "skills" / PACK_SKILL / "SKILL.md"
        if not skill.exists():
            problems.append(f"pack skill not installed: {skill}")
    return problems


# ── Entry point ───────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel", help="Path to an already-built wheel (default: build one with uv)"
    )
    parser.add_argument(
        "--python", default="3.11", help="Python version for the isolated venv (default: 3.11)"
    )
    parser.add_argument(
        "--keep", action="store_true", help="Keep the temp dir on failure for inspection"
    )
    args = parser.parse_args(argv)

    if shutil.which("uv") is None:
        print("error: `uv` not found on PATH", file=sys.stderr)
        return 1

    failures: list[str] = []
    tmp = tempfile.mkdtemp(prefix="specflow-wheel-smoke-")
    keep = False
    try:
        tmp_path = Path(tmp)

        if args.wheel:
            wheel = Path(args.wheel).resolve()
            if not wheel.exists():
                print(f"error: wheel not found: {wheel}", file=sys.stderr)
                return 1
            print(f"[1/7] Using existing wheel: {wheel}")
        else:
            print("[1/7] Building wheel (uv build --wheel)...")
            wheel = build_wheel(tmp_path / "dist")
            print(f"       -> {wheel.name}")

        print("[2/7] Verifying wheel contents...")
        missing = verify_wheel_contents(wheel, SRC_DIR)
        signals = verify_asset_signals(wheel)
        failures.extend(f"wheel missing packaged asset: {m}" for m in missing)
        failures.extend(signals)
        if not (missing or signals):
            print("       -> packaged assets complete: schemas, skills + references, "
                  "checklists, packs, agent-context, adapters, platforms")

        print("[3/7] Creating isolated venv...")
        venv_python = create_venv(tmp_path / "venv", args.python)

        print("[4/7] Installing wheel into isolated venv...")
        install_wheel(venv_python, wheel)

        print("[5/7] Initializing a throwaway project...")
        proj = tmp_path / "proj"
        init_project(venv_python, proj)
        failures.extend(verify_initialized_assets(proj))

        print("[6/7] Running installed entry points (--version / status / brief)...")
        result = run_cli(venv_python, proj, "--version", check=False)
        if result.returncode != 0 or not result.stdout.strip():
            failures.append(f"`specflow --version` failed (rc={result.returncode})")
            print(f"       specflow --version: rc={result.returncode} (FAIL)")
        else:
            version_line = result.stdout.strip().splitlines()[0]
            print(f"       specflow --version: rc=0 (ok) — {version_line}")

        for cmd in (("status",), ("brief",)):
            result = run_cli(venv_python, proj, *cmd, check=False)
            ok = result.returncode == 0 and bool(result.stdout.strip())
            print(f"       specflow {cmd[0]}: rc={result.returncode} "
                  f"({'ok' if ok else 'FAIL'})")
            if not ok:
                failures.append(f"`specflow {cmd[0]}` failed (rc={result.returncode})")
                if result.stdout:
                    sys.stdout.write(result.stdout)

        print("[7/7] Verifying pack assets from the wheel (--preset ops)...")
        proj_ops = tmp_path / "proj-ops"
        init_project(venv_python, proj_ops, "--preset", PACK_PRESET)
        # With an explicit --platform, pack skills must install during init —
        # no follow-up `refresh --packs` required.
        failures.extend(verify_pack_assets(proj_ops, require_skill=True))

        if failures:
            print("\nWHEEL SMOKE FAILED:")
            for f in failures:
                print(f"  - {f}")
            keep = args.keep
            return 1

        print("\nWHEEL SMOKE PASSED")
        print(f"  wheel: {wheel}")
        print(f"  python: {args.python}")
        return 0
    finally:
        if keep:
            print(f"(keeping temp dir for inspection: {tmp})")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
