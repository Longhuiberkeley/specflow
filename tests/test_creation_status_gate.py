"""STORY-640 — creation-status entry gates (CLI level, --sanctioned).

Guarantees:

- an explicit non-entry --status (e.g. `approved`) is rejected without
  --sanctioned and leaves NO partial artifact;
- with --sanctioned the artifact is created and the justification is recorded
  in frontmatter (sanctioned_justification);
- entry statuses (explicit root, or omitted) never hit the gate;
- multi-root types (experiment outcomes) accept any root status explicitly;
- the LIB api stays ungated for trusted internal callers (orphans adopt,
  autoresearch plan, reqif import) — the gate lives at the CLI boundary;
- generated BPs are born draft (handbook no longer asserts approved).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.commands import create as create_cmd
from specflow.lib import artifacts as art_lib


@pytest.fixture(autouse=True)
def _restore_type_registry():
    """Keep this module's pack-type registrations from leaking.

    ``_load_active_packs`` registers fixture schemas' types (experiment, …)
    into the module-global TYPE_TO_DIR/PREFIX maps and they persist for the
    rest of the process; other modules' fixtures use different directories
    for the same type and their creates then land in the wrong place.
    Snapshot/restore keeps the registry local to this module.
    """
    dirs = dict(art_lib.TYPE_TO_DIR)
    prefixes = dict(art_lib.TYPE_TO_PREFIX)
    reverse = dict(art_lib.PREFIX_TO_TYPE)
    aliases = dict(art_lib.TYPE_ALIASES)
    yield
    art_lib.TYPE_TO_DIR.clear()
    art_lib.TYPE_TO_DIR.update(dirs)
    art_lib.TYPE_TO_PREFIX.clear()
    art_lib.TYPE_TO_PREFIX.update(prefixes)
    art_lib.PREFIX_TO_TYPE.clear()
    art_lib.PREFIX_TO_TYPE.update(reverse)
    art_lib.TYPE_ALIASES.clear()
    art_lib.TYPE_ALIASES.update(aliases)


_SCHEMA_TYPES = [
    ("requirement", "REQ", "specs/requirements"),
    ("story", "STORY", "work/stories"),
    ("best-practice", "BP", "specs/best-practices"),
    ("experiment", "EXPT", "research/experiments"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"],
}
# Multi-root outcome statuses (experiment: four outcome-roots, like the
# shipped schema — initial_status returns None and create requires --status).
_EXPT_FLOW = {
    "kept": [],
    "discarded": [],
    "crashed": [],
    "no_op": [],
}


def _project(tmp: Path) -> Path:
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    for art_type, prefix, rel_dir in _SCHEMA_TYPES:
        flow = _EXPT_FLOW if art_type == "experiment" else _STATUS_FLOW
        schema = {
            "type": art_type,
            "prefix": prefix,
            "directory": f"_specflow/{rel_dir}",
            "allowed_status": dict(flow),
            "allowed_link_roles": ["derives_from"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")
    config = {
        "project": {"name": "gate-test", "created": "2026-01-01"},
        "artifact_types": [t for t, _, _ in _SCHEMA_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
    )
    return root


def _args(**over) -> dict:
    base = {
        "type": "story",
        "title": "T",
        "status": None,
        "priority": None,
        "rationale": None,
        "tags": "",
        "links": "",
        "add_link": [],
        "body": "b",
        "from_standard": None,
        "force": True,
        "skip_dedup_check": True,
        "nfr_category": None,
        "sanctioned": None,
        "set_fields": [],
    }
    base.update(over)
    return base


def _created_ids(root: Path) -> set[str]:
    return {a.id for a in art_lib.discover_artifacts(root)}


class TestCreationStatusGate:
    def test_non_entry_status_rejected_without_sanction(self, tmp_path, capsys):
        root = _project(tmp_path)
        rc = create_cmd.run(root, _args(status="approved"))
        out = capsys.readouterr().out
        assert rc == 1
        assert "--sanctioned" in out
        assert _created_ids(root) == set()  # no partial artifact

    def test_non_entry_status_allowed_with_sanction_recorded(self, tmp_path, capsys):
        root = _project(tmp_path)
        rc = create_cmd.run(root, _args(status="approved", sanctioned="User confirmed"))
        assert rc == 0
        assert _created_ids(root) == {"STORY-001"}
        path = art_lib.resolve_link_target(root, "STORY-001")
        fm = yaml.safe_load(path.read_text().split("---")[1])
        assert fm["status"] == "approved"
        assert fm["sanctioned_justification"] == "User confirmed"

    def test_omitted_status_uses_root_no_gate(self, tmp_path):
        root = _project(tmp_path)
        rc = create_cmd.run(root, _args())
        assert rc == 0
        arts = art_lib.discover_artifacts(root)
        assert arts[0].status == "draft"

    def test_explicit_entry_status_no_gate(self, tmp_path):
        root = _project(tmp_path)
        rc = create_cmd.run(root, _args(status="draft"))
        assert rc == 0

    def test_multi_root_type_accepts_any_root(self, tmp_path):
        root = _project(tmp_path)
        rc = create_cmd.run(root, _args(type="experiment", status="kept"))
        assert rc == 0
        arts = art_lib.discover_artifacts(root)
        assert arts[0].status == "kept"

    def test_lib_api_stays_ungated_for_internal_callers(self, tmp_path):
        """Trusted internal paths (orphans adopt, autoresearch plan, reqif
        import) call create_artifact directly — the gate is CLI-only."""
        root = _project(tmp_path)
        result = art_lib.create_artifact(
            root, "story", title="backfill record", status="approved", body="b"
        )
        assert result["ok"] is True
        assert result["id"] == "STORY-001"

    def test_generated_bps_are_born_draft(self, tmp_path):
        """Handbook generation no longer asserts approved on the artifact's
        behalf (STORY-640 handbook fix)."""
        from specflow.commands import handbook as handbook_cmd

        root = _project(tmp_path)
        rc = handbook_cmd.run(root, {"create": True})
        assert rc == 0
        arts = [a for a in art_lib.discover_artifacts(root) if a.type == "best-practice"]
        assert arts
        assert all(a.status == "draft" for a in arts)

    def test_skill_recipes_carry_sanctioned(self):
        """Shipped skill examples that create in non-entry statuses must carry
        --sanctioned so they don't teach a now-rejected command."""
        import re

        skill_root = Path("src/specflow/templates/skills/shared")
        pattern = re.compile(r"--status\s+(\S+)")
        offenders: list[str] = []
        for md in skill_root.rglob("*.md"):
            text = md.read_text(encoding="utf-8")
            for m in pattern.finditer(text):
                status = m.group(1).strip('"')
                if status in ("approved", "implemented", "verified"):
                    # Find the surrounding create block: look backwards for
                    # 'specflow create' within 400 chars.
                    start = max(0, m.start() - 400)
                    ctx = text[start:m.end() + 400]
                    if "specflow create" not in ctx.split("--status")[0]:
                        continue
                    if "--sanctioned" not in ctx:
                        offenders.append(f"{md.relative_to(skill_root)}: --status {status}")
        assert offenders == [], f"create-as-{offenders} without --sanctioned"
