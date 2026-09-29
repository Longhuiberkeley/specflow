"""Shared fixture helpers for the cascade-status tests (STORY-697).

Projects are scaffolded from the repo's REAL schemas in ``.specflow/schema``
so the tests pin the transition maps SpecFlow actually enforces.
"""

from __future__ import annotations

import contextlib
import io
import shutil
from pathlib import Path

import yaml

from specflow import cli
from specflow.lib import artifacts as art_lib

REPO = Path(__file__).resolve().parents[1]
REAL_SCHEMAS = REPO / ".specflow" / "schema"

PREFIX_TYPE = {"REQ": "requirement", "ARCH": "architecture", "DDD": "detailed-design",
               "STORY": "story"}


def project(tmp_path: Path, name: str = "p") -> Path:
    root = tmp_path / name
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True)
    for f in REAL_SCHEMAS.glob("*.yaml"):
        shutil.copy(f, schema_dir / f.name)
    for t in PREFIX_TYPE.values():
        (root / "_specflow" / art_lib.TYPE_TO_DIR[t]).mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "t"}, "active_packs": []}), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "executing", "history": []}), encoding="utf-8")
    return root


def put(root: Path, art_id: str, status: str, links: list[tuple[str, str]] | None = None) -> None:
    """Write an artifact file directly in ``status`` (fixture seeding only)."""
    art_type = PREFIX_TYPE[art_lib.get_prefix_from_id(art_id)]
    fm = {
        "id": art_id, "title": f"{art_id} title", "type": art_type, "status": status,
        "links": [{"target": t, "role": r} for t, r in (links or [])],
        "created": "2026-09-30",
    }
    path = root / "_specflow" / art_lib.TYPE_TO_DIR[art_type] / f"{art_id}.md"
    path.write_text("---\n" + yaml.dump(fm, sort_keys=False) + "---\n\n# body\n",
                    encoding="utf-8")


def status_of(root: Path, art_id: str) -> str:
    art = art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))
    return art.status


def allowed(root: Path, art_type: str) -> dict[str, list[str]]:
    schema = yaml.safe_load((root / ".specflow" / "schema" / f"{art_type}.yaml").read_text())
    return schema.get("allowed_status") or {}


def run_cli(root: Path, monkeypatch, *argv: str) -> tuple[int, str]:
    monkeypatch.chdir(root)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue()


def spy_updates(monkeypatch) -> list[tuple[str, str, str, str]]:
    """Record every status write as (id, type, from, to) and pass it through."""
    calls: list[tuple[str, str, str, str]] = []
    real = art_lib.update_artifact

    def spy(root, artifact_id, **kw):
        if "status" in kw:
            art = art_lib.parse_artifact(art_lib.resolve_link_target(root, artifact_id))
            calls.append((artifact_id, art.type, art.status, kw["status"]))
        return real(root, artifact_id, **kw)

    monkeypatch.setattr(art_lib, "update_artifact", spy)
    return calls
