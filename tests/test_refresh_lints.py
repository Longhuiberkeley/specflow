"""Tests for specflow refresh, spike-lifecycle lint, and source-drift lint.

Three new features covered:
1. specflow refresh — dry-run preview, --no-skills, --schemas dry-run
2. _check_spike_lifecycle — stale, zombie, healthy, repeated-tag
3. _check_source_drift — first-run seed, second-run drift, suspect exemption
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.lib import artifacts as art_lib


# ── Shared fixtures and helpers ──────────────────────────────────────────────

_BASE_SPEC_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"), ("defect", "DEF"),
]

_BASE_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"],
}


def _write_artifact(
    root: Path,
    artifact_id: str,
    art_type: str,
    title: str,
    status: str = "draft",
    body: str = "",
    links: list[dict] | None = None,
    extra_fm: dict | None = None,
) -> Path:
    rel_dir = art_lib.TYPE_TO_DIR.get(art_type, "")
    if not rel_dir:
        raise ValueError(f"Unknown type: {art_type}")
    target_dir = root / "_specflow" / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    fm: dict = {
        "id": artifact_id,
        "title": title,
        "type": art_type,
        "status": status,
        "tags": [],
        "suspect": False,
        "links": links or [],
    }
    if extra_fm:
        fm.update(extra_fm)

    fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    content = f"---\n{fm_yaml}---\n\n# {title}\n\n{body}\n"
    file_path = target_dir / f"{artifact_id}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _make_art(
    art_id: str,
    art_type: str,
    status: str = "draft",
    body: str = "body",
    links: list[art_lib.Link] | None = None,
    extra_fm: dict | None = None,
) -> art_lib.Artifact:
    fm: dict = {
        "id": art_id, "title": f"Test {art_id}",
        "type": art_type, "status": status,
    }
    if extra_fm:
        fm.update(extra_fm)
    return art_lib.Artifact(
        path=Path(f"{art_id}.md"),
        frontmatter=fm,
        body=body,
        links=links or [],
    )


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Temp project with base schemas installed; matches test_autoresearch_pack style."""
    root = tmp_path / "project"
    root.mkdir()
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    for art_type, prefix in _BASE_SPEC_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_BASE_STATUS_FLOW),
        }
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump(schema), encoding="utf-8"
        )

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "impact_analysis": {
            "auto_flag": True, "auto_resolve": False, "remind_after": "7d",
        },
        "artifact_types": [t for t, _ in _BASE_SPEC_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )
    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump(state), encoding="utf-8"
    )
    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/detailed-design", "_specflow/specs/unit-tests",
        "_specflow/specs/integration-tests", "_specflow/specs/qualification-tests",
        "_specflow/work/stories", "_specflow/work/spikes",
        "_specflow/work/decisions", "_specflow/work/defects",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def refresh_project(tmp_path: Path) -> Path:
    """Project with .claude/ marker so refresh detects claude-code platform."""
    root = tmp_path / "refresh-project"
    root.mkdir()
    (root / ".claude").mkdir()
    (root / ".specflow" / "schema").mkdir(parents=True)
    (root / ".specflow" / "standards").mkdir(parents=True)
    config = {
        "project": {"name": "refresh-project", "created": "2026-06-01"},
        "artifact_types": [],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config))
    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(yaml.dump(state))
    return root


# ── 1. specflow refresh command ─────────────────────────────────────────────

class TestRefreshCommand:

    def test_dry_run_does_not_create_skill_files(
        self, refresh_project: Path, capsys
    ):
        """dry-run is a pure preview: no skill files are written, no legacy dirs deleted."""
        legacy_dir = refresh_project / ".claude" / "commands"
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "stale.md").write_text("# stale\n")

        rc = refresh_cmd.run(refresh_project, {"dry_run": True})
        assert rc == 0

        out = capsys.readouterr().out
        assert "[dry-run]" in out
        assert "Run without --dry-run" in out

        assert legacy_dir.exists(), "dry-run must not delete legacy dirs"
        assert (legacy_dir / "stale.md").exists(), "dry-run must not touch legacy files"
        assert not (refresh_project / ".claude" / "skills").exists() or \
            not any((refresh_project / ".claude" / "skills").iterdir()), \
            "dry-run must not write skill files"

    def test_no_skills_skips_skill_install(
        self, refresh_project: Path, capsys
    ):
        rc = refresh_cmd.run(refresh_project, {"no_skills": True})
        assert rc == 0

        out = capsys.readouterr().out
        assert "skills" not in out, \
            "summary should not mention 'skills' when --no-skills is set"

        skills_dir = refresh_project / ".claude" / "skills"
        assert not skills_dir.exists(), \
            "no skill directory should be created under --no-skills"

    def test_schemas_dry_run_reports_without_writing(
        self, refresh_project: Path, capsys
    ):
        rc = refresh_cmd.run(refresh_project, {"schemas": True, "dry_run": True})
        assert rc == 0

        out = capsys.readouterr().out
        assert "schemas" in out, "schemas section should appear in summary"
        # dry-run must not actually copy schema files
        schema_files = list((refresh_project / ".specflow" / "schema").glob("*.yaml"))
        assert len(schema_files) == 0, \
            f"dry-run wrote schema files: {[f.name for f in schema_files]}"


# ── 2. _check_spike_lifecycle ────────────────────────────────────────────────

class TestSpikeLifecycle:

    def test_stale_spike_past_timebox_fires_warning(self, project_root: Path):
        long_ago = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%d")
        spike = _make_art(
            "SPIKE-100", "spike", status="draft",
            extra_fm={"created": long_ago, "timebox": 30},
        )
        result = lint_cmd._check_spike_lifecycle([spike], project_root)
        assert result["warning_count"] >= 1
        assert "stale" in result["detail"]
        assert "SPIKE-100" in result["detail"]

    def test_stale_spike_handles_iso_timestamp(self, project_root: Path):
        """ISO 8601 with time component (e.g., 2024-01-01T00:00:00Z) must parse."""
        long_ago_iso = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
        spike = _make_art(
            "SPIKE-101", "spike", status="approved",
            extra_fm={"created": long_ago_iso, "timebox": 30},
        )
        result = lint_cmd._check_spike_lifecycle([spike], project_root)
        assert result["warning_count"] >= 1
        assert "stale" in result["detail"]

    def test_zombie_spike_fires_warning(self, project_root: Path):
        body = " ".join(["finding"] * 120)  # > _MIN_ZOMBIE_WORD_COUNT (100)
        spike = _make_art(
            "SPIKE-200", "spike", status="completed", body=body,
        )
        result = lint_cmd._check_spike_lifecycle([spike], project_root)
        assert result["warning_count"] >= 1
        assert "zombie" in result["detail"]
        assert "120 words" in result["detail"]

    def test_healthy_spike_with_downstream_produces_no_warning(self, project_root: Path):
        """A completed SPIKE linked via derives_from a non-SPIKE artifact is healthy."""
        body = " ".join(["finding"] * 120)
        spike = _make_art(
            "SPIKE-300", "spike", status="completed", body=body,
        )
        consumer = _make_art(
            "REQ-300", "requirement", status="draft",
            links=[art_lib.Link(target="SPIKE-300", role="derives_from")],
        )
        result = lint_cmd._check_spike_lifecycle([spike, consumer], project_root)
        assert result["warning_count"] == 0

    def test_repeated_tag_triggers_info(self, project_root: Path):
        arts = [
            _make_art("SPIKE-401", "spike", status="completed", body="x", extra_fm={"tags": ["auth-flow"]}),
            _make_art("SPIKE-402", "spike", status="completed", body="x", extra_fm={"tags": ["auth-flow"]}),
            _make_art("SPIKE-403", "spike", status="completed", body="x", extra_fm={"tags": ["auth-flow"]}),
        ]
        result = lint_cmd._check_spike_lifecycle(arts, project_root)
        assert "auth-flow" in result["detail"]
        assert "3 SPIKEs share tag" in result["detail"]


# ── 3. _check_source_drift ───────────────────────────────────────────────────

class TestSourceDrift:

    def test_first_run_seeds_and_reports_clean(self, project_root: Path):
        """No fingerprint file + output_files present → silently seed, 0 warnings."""
        target = project_root / "src" / "module.py"
        target.parent.mkdir(parents=True)
        target.write_text("# initial\n")
        _write_artifact(
            project_root, "REQ-500", "requirement", "Drift test",
            status="draft",
            extra_fm={"output_files": ["src/module.py"]},
        )
        arts = art_lib.discover_artifacts(project_root)
        result = lint_cmd._check_source_drift(arts, project_root)

        assert result["warning_count"] == 0
        assert "Seeded" in result["detail"]
        fp_path = project_root / ".specflow" / "source-fingerprints.yaml"
        assert fp_path.exists(), "first run must write the fingerprint file"
        fp_data = yaml.safe_load(fp_path.read_text())
        assert "REQ-500" in fp_data
        assert "src/module.py" in fp_data["REQ-500"]

    def test_second_run_after_edit_detects_drift(self, project_root: Path):
        """After seeding, editing an output_file should produce a warning."""
        target = project_root / "src" / "module.py"
        target.parent.mkdir(parents=True)
        target.write_text("# initial\n")
        _write_artifact(
            project_root, "REQ-501", "requirement", "Drift test",
            status="draft",
            extra_fm={"output_files": ["src/module.py"]},
        )
        arts = art_lib.discover_artifacts(project_root)

        lint_cmd._check_source_drift(arts, project_root)  # seed

        target.write_text("# changed content\n")  # drift

        result = lint_cmd._check_source_drift(arts, project_root)
        assert result["warning_count"] >= 1
        assert "source file changed" in result["detail"]
        assert "REQ-501" in result["detail"]
        assert "src/module.py" in result["detail"]

    def test_suspect_flagged_artifact_is_exempt(self, project_root: Path):
        """A suspect-flagged artifact should NOT fire a drift warning."""
        target = project_root / "src" / "module.py"
        target.parent.mkdir(parents=True)
        target.write_text("# initial\n")
        _write_artifact(
            project_root, "REQ-502", "requirement", "Drift test",
            status="draft",
            extra_fm={"output_files": ["src/module.py"]},
        )
        arts = art_lib.discover_artifacts(project_root)
        lint_cmd._check_source_drift(arts, project_root)  # seed

        target.write_text("# changed content\n")
        # Edit the artifact to mark it suspect (post-impact-review)
        art_path = project_root / "_specflow" / "specs" / "requirements" / "REQ-502.md"
        text = art_path.read_text()
        text = text.replace("suspect: false", "suspect: true", 1)
        art_path.write_text(text)

        arts = art_lib.discover_artifacts(project_root)
        result = lint_cmd._check_source_drift(arts, project_root)
        assert result["warning_count"] == 0, \
            "suspect-flagged artifact should be exempt from drift warnings"
