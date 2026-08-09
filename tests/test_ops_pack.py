"""WS3: ops pack (RUN + MONITOR) tests.

Covers schema lifecycle, pack install, domain-neutrality of the schemas, link-role
allow-lists, and pack-state-aware routing in brief --next.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import brief as brief_cmd
from specflow.commands import init as init_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import scaffold as scaffold_lib

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"

OPS_SCHEMAS = {
    "run": {"prefix": "RUN", "statuses": ["deployed", "live", "paused", "retired"]},
    "monitor": {"prefix": "MON", "statuses": ["logged", "flagged", "resolved"]},
}


def _make_art(
    art_id: str, art_type: str, status: str = "draft", fm_extra: dict | None = None,
) -> art_lib.Artifact:
    fm: dict = {"id": art_id, "title": f"Test {art_id}", "type": art_type, "status": status}
    if fm_extra:
        fm.update(fm_extra)
    return art_lib.Artifact(path=Path(f"{art_id}.md"), frontmatter=fm, body="b", links=[])


@pytest.fixture
def ops_project(tmp_path: Path) -> Path:
    """Temp project with ops schemas installed (for status-lint checks)."""
    root = tmp_path / "ops-project"
    root.mkdir()
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True)
    (root / ".specflow" / "standards").mkdir(parents=True)
    for name in ("run", "monitor"):
        src = PACKS_DIR / "ops" / "schemas" / f"{name}.yaml"
        (schema_dir / f"{name}.yaml").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (root / ".specflow" / "config.yaml").write_text(
        "project: {name: ops, created: '2026-01-01'}\n"
        "artifact_types: [run, monitor]\nactive_packs: [ops]\n",
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text("current: idle\nhistory: []\n", encoding="utf-8")
    for sub in ("_specflow/ops/runs", "_specflow/ops/monitors"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    art_lib._load_active_packs(root)
    yield root
    for t in ("run", "monitor"):
        prefix = art_lib.TYPE_TO_PREFIX.pop(t, None)
        art_lib.TYPE_TO_DIR.pop(t, None)
        if prefix:
            art_lib.PREFIX_TO_TYPE.pop(prefix, None)


@pytest.fixture
def fresh_project(tmp_path: Path) -> Path:
    root = tmp_path / "fresh-project"
    root.mkdir()
    (root / ".claude").mkdir()
    (root / ".specflow" / "schema").mkdir(parents=True)
    (root / ".specflow" / "standards").mkdir(parents=True)
    (root / ".specflow" / "config.yaml").write_text(
        "project: {name: fresh, created: '2026-01-01'}\n"
        "artifact_types: []\nactive_packs: []\n",
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text("current: idle\nhistory: []\n", encoding="utf-8")
    return root


# ── 1. Schema lifecycle ──────────────────────────────────────────────────────

class TestSchemaLifecycle:

    @pytest.mark.parametrize("art_type,info", list(OPS_SCHEMAS.items()))
    def test_valid_statuses_pass(self, ops_project: Path, art_type: str, info: dict):
        for status in info["statuses"]:
            arts = [_make_art(f"{info['prefix']}-001", art_type, status=status)]
            result = lint_cmd._check_status(arts, ops_project / ".specflow" / "schema")
            assert result["blocking_count"] == 0, f"{art_type} '{status}' should be valid"

    @pytest.mark.parametrize("art_type,info", list(OPS_SCHEMAS.items()))
    def test_invalid_status_blocked(self, ops_project: Path, art_type: str, info: dict):
        arts = [_make_art(f"{info['prefix']}-002", art_type, status="nonexistent")]
        result = lint_cmd._check_status(arts, ops_project / ".specflow" / "schema")
        assert result["blocking_count"] >= 1

    def test_run_transition_structure(self, ops_project: Path):
        schema = yaml.safe_load((ops_project / ".specflow" / "schema" / "run.yaml").read_text())
        allowed = schema["allowed_status"]
        assert allowed["deployed"] == [], "deployed is initial"
        assert "deployed" in allowed["live"], "deployed→live allowed"
        assert "live" in allowed["paused"], "live→paused allowed"
        assert "paused" in allowed["retired"], "paused→retired allowed"
        assert "live" in allowed["retired"], "live→retired allowed"
        assert "deployed" not in allowed["retired"], "deployed→retired NOT allowed"

    def test_monitor_transition_structure(self, ops_project: Path):
        schema = yaml.safe_load((ops_project / ".specflow" / "schema" / "monitor.yaml").read_text())
        allowed = schema["allowed_status"]
        assert allowed["logged"] == [], "logged is initial"
        assert "logged" in allowed["flagged"], "logged→flagged allowed"
        assert "flagged" in allowed["resolved"], "flagged→resolved allowed"
        assert "logged" not in allowed["resolved"], "logged→resolved NOT allowed"


# ── 2. Pack install ──────────────────────────────────────────────────────────

class TestPackInstall:

    def test_schemas_copied_and_dirs_created(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "ops", PACKS_DIR)
        assert result["ok"]
        schema_dir = fresh_project / ".specflow" / "schema"
        assert (schema_dir / "run.yaml").exists()
        assert (schema_dir / "monitor.yaml").exists()
        for rel in ("runs", "monitors"):
            d = fresh_project / "_specflow" / "ops" / rel
            assert d.is_dir(), f"_specflow/ops/{rel}/ not created"
            assert (d / "_index.yaml").exists()

    def test_skill_installed_and_types_returned(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "ops", PACKS_DIR)
        assert result["ok"]
        assert "specflow-ops" in result.get("skills_added", [])
        assert (fresh_project / ".claude" / "skills" / "specflow-ops" / "SKILL.md").exists()
        for t in ("run", "monitor"):
            assert t in result["types_added"]

    def test_context_snippet_returned(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "ops", PACKS_DIR)
        snippet = result["context_snippet"]
        assert snippet and "RUN" in snippet and "MONITOR" in snippet

    def test_explicit_platform_installs_skill_without_marker(self, tmp_path: Path):
        """apply_pack with an explicit platform code must install the pack skill
        even when no platform marker dir exists yet (fresh init applies presets
        before the shared skills / .claude/ dir exist)."""
        root = tmp_path / "bare"
        root.mkdir()
        result = scaffold_lib.apply_pack(root, "ops", PACKS_DIR, platform_code="claude-code")
        assert result["ok"]
        assert "specflow-ops" in result.get("skills_added", [])
        skill = root / ".claude" / "skills" / "specflow-ops" / "SKILL.md"
        assert skill.exists(), f"pack skill not installed: {skill}"

    def test_no_platform_skips_skill_without_marker(self, tmp_path: Path):
        """Without an explicit platform and without a detectable marker dir, the
        pack skill must be skipped (with a warning), preserving the pre-fix
        fallback path for callers that do not resolve a platform."""
        root = tmp_path / "bare"
        root.mkdir()
        result = scaffold_lib.apply_pack(root, "ops", PACKS_DIR)
        assert result["ok"]
        assert "specflow-ops" not in result.get("skills_added", [])
        assert not (root / ".claude" / "skills" / "specflow-ops" / "SKILL.md").exists()


# ── Init ordering: pack skills install during init (no follow-up refresh) ────

class TestInitPresetSkillOrdering:

    def test_init_with_explicit_platform_installs_pack_skill(self, tmp_path: Path):
        """`specflow init --platform claude-code --preset ops` must install the
        ops pack skill during init — no follow-up `refresh --packs` required."""
        root = tmp_path / "init-ops"
        root.mkdir()
        rc = init_cmd.run(root, {
            "platform": "claude-code",
            "no_ci": True,
            "preset": "ops",
            "with_types": "",
            "domain": None,
            "domain_tags": "",
            "force": False,
        })
        assert rc == 0

        skill = root / ".claude" / "skills" / "specflow-ops" / "SKILL.md"
        assert skill.exists(), f"ops pack skill missing after init: {skill}"

        # Pack schemas + context snippet land too (unchanged behavior).
        for name in ("run.yaml", "monitor.yaml"):
            assert (root / ".specflow" / "schema" / name).exists(), f"pack schema {name} missing"
        assert "Ops Pack" in (root / "AGENTS.md").read_text(encoding="utf-8")

        # Shared skills still install alongside the pack skill.
        assert (root / ".claude" / "skills" / "specflow-start" / "SKILL.md").exists()

    def test_init_without_preset_installs_no_pack_skill(self, tmp_path: Path):
        """Baseline: init without a preset still installs only shared skills."""
        root = tmp_path / "init-plain"
        root.mkdir()
        rc = init_cmd.run(root, {
            "platform": "claude-code",
            "no_ci": True,
            "preset": None,
            "with_types": "",
            "domain": None,
            "domain_tags": "",
            "force": False,
        })
        assert rc == 0
        assert (root / ".claude" / "skills" / "specflow-start" / "SKILL.md").exists()
        assert not (root / ".claude" / "skills" / "specflow-ops" / "SKILL.md").exists()


# ── 3. Domain-neutrality ─────────────────────────────────────────────────────

class TestDomainNeutrality:
    """The ops core must stay domain-neutral — drift/oos_decay/model belong in
    per-domain maps, never in the schema."""

    @pytest.mark.parametrize("name", ["run", "monitor"])
    def test_category_is_ops(self, name: str):
        schema = yaml.safe_load((PACKS_DIR / "ops" / "schemas" / f"{name}.yaml").read_text())
        assert schema.get("category") == "ops"

    @pytest.mark.parametrize("name", ["run", "monitor"])
    def test_no_ml_specific_fields_leak(self, name: str):
        schema = yaml.safe_load((PACKS_DIR / "ops" / "schemas" / f"{name}.yaml").read_text())
        joined = " ".join(schema.get("optional_fields", []) + schema.get("required_fields", []))
        for forbidden in ("drift", "oos_decay", "model"):
            assert forbidden not in joined, f"{name}.yaml leaks ML-specific field '{forbidden}'"

    def test_link_roles(self):
        run_s = yaml.safe_load((PACKS_DIR / "ops" / "schemas" / "run.yaml").read_text())
        mon_s = yaml.safe_load((PACKS_DIR / "ops" / "schemas" / "monitor.yaml").read_text())
        # RUN reuses derives_from (spec satisfaction / promoted-from lineage).
        assert "derives_from" in run_s["allowed_link_roles"]
        # MONITOR reuses belongs_to (→RUN) and informs (→LOOP/DEC on breach).
        assert "belongs_to" in mon_s["allowed_link_roles"]
        assert "informs" in mon_s["allowed_link_roles"]


# ── 4. Pack-state-aware routing (brief --next) ───────────────────────────────

class TestPackStateRouting:

    def test_no_note_without_pack(self):
        arts = [_make_art("RUN-001", "run", status="live")]
        line = brief_cmd._next_skill_recommendation("executing", arts, [], [], active_packs=[])
        assert "unobserved" not in line

    def test_ops_live_run_unobserved_note(self):
        arts = [_make_art("RUN-001", "run", status="live")]
        line = brief_cmd._next_skill_recommendation(
            "executing", arts, [], [], active_packs=["ops"]
        )
        assert "live RUN(s) unobserved" in line
        assert "MONITOR" in line

    def test_ops_breached_monitor_outranks_unobserved(self):
        arts = [
            _make_art("RUN-001", "run", status="live"),
            _make_art("MON-001", "monitor", status="flagged", fm_extra={"run": "RUN-001"}),
        ]
        line = brief_cmd._next_skill_recommendation(
            "executing", arts, [], [], active_packs=["ops"]
        )
        assert "breached MONITOR" in line
        assert "unobserved" not in line

    def test_ops_health_breached_also_flags(self):
        arts = [
            _make_art("RUN-001", "run", status="live"),
            _make_art("MON-001", "monitor", status="logged",
                      fm_extra={"run": "RUN-001", "health": "breached"}),
        ]
        line = brief_cmd._next_skill_recommendation(
            "executing", arts, [], [], active_packs=["ops"]
        )
        assert "breached MONITOR" in line

    def test_ops_silent_when_monitor_present_and_healthy(self):
        arts = [
            _make_art("RUN-001", "run", status="live"),
            _make_art("MON-001", "monitor", status="logged",
                      fm_extra={"run": "RUN-001", "health": "ok"}),
        ]
        line = brief_cmd._next_skill_recommendation(
            "executing", arts, [], [], active_packs=["ops"]
        )
        assert "ops" not in line.lower()

    def test_autoresearch_running_loop_note(self):
        arts = [_make_art("LOOP-001", "loop", status="running")]
        line = brief_cmd._next_skill_recommendation(
            "executing", arts, [], [], active_packs=["autoresearch"]
        )
        assert "LOOP(s) running" in line
