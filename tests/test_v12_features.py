"""Tests for v1.2.0 features: spec-body, output-files, coverage-arch, story-min-ac, init upgrade."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml
import pytest

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import init as init_cmd
from specflow.commands import create as create_cmd
from specflow.commands import update as update_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import config as config_lib
from specflow.lib import scaffold as scaffold_lib

_SCHEMA_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"),
    ("defect", "DEF"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"],
}


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "cache" / "backups").mkdir(parents=True, exist_ok=True)

    for art_type, prefix in _SCHEMA_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_STATUS_FLOW),
            "optional_fields": ["output_files"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump(schema), encoding="utf-8"
        )

    config = config_lib.default_config("test-project")
    config_lib.write_config(root, config)

    state = config_lib.default_state()
    config_lib.write_state(root, state)

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/detailed-design", "_specflow/specs/unit-tests",
        "_specflow/specs/integration-tests", "_specflow/specs/qualification-tests",
        "_specflow/work/stories", "_specflow/work/spikes",
        "_specflow/work/decisions", "_specflow/work/defects",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    return root


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


ARCH_BODY_GOOD = """## Interface

The system exposes a REST API.

## Component

The lint engine validates artifacts.

## Data Flow

Artifacts flow from discovery through lint checks.

## Dependencies

Depends on the schema validation library.
""" * 2

ARCH_BODY_SHORT = "This is too short."

ARCH_BODY_NO_HEADERS = "This artifact has enough words to pass the word count threshold but it does not contain any structural headers that would be expected in an architecture document. It is just a long paragraph of text without meaningful structure."

DDD_BODY_GOOD = """## Function

The merge function combines two dictionaries recursively. It takes an existing configuration dictionary and a defaults dictionary, producing a merged result where user values take precedence over defaults for all matching keys.

## Algorithm

Deep copy defaults first, then overlay user values on top. Recurse into nested dictionaries to preserve deeply nested user customizations. Lists are merged and deduplicated to avoid duplicate entries. The framework version is always stamped last to ensure accuracy.

## Data Structure

VersionDelta holds current and framework version strings along with a boolean flag indicating whether an upgrade is needed and a list of newly added field names that were not present in the previous configuration version.

## Error Handling

Corrupted config triggers a fresh initialization instead of crashing. Unparseable version strings are treated as unknown versions, which safely triggers a full upgrade path with all new fields added.

## Implementation

Uses copy.deepcopy for safe merging to avoid mutating the original defaults dictionary. The version field is always overwritten with the current framework version regardless of what was in the existing configuration.
"""

DDD_BODY_SHORT = "Too brief for a design doc."

DDD_BODY_NO_HEADERS = "This detailed design document has enough words to pass the one hundred word minimum threshold but it does not contain any of the expected design headers like Function, Algorithm, Data Structure, Error Handling, Invariant, Precondition, Signature, or Implementation sections that would normally be present in a well-structured design document."


class TestCheckSpecBody:
    def test_arch_with_headers_and_words_passes(self):
        arts = [_make_art("ARCH-001", "architecture", body=ARCH_BODY_GOOD)]
        result = lint_cmd._check_spec_body(arts)
        assert result["warning_count"] == 0
        assert result["blocking_count"] == 0

    def test_arch_under_fifty_words_warns(self):
        arts = [_make_art("ARCH-001", "architecture", body=ARCH_BODY_SHORT)]
        result = lint_cmd._check_spec_body(arts)
        assert result["warning_count"] >= 1
        assert "minimum 50" in result["detail"]

    def test_arch_without_structural_headers_warns(self):
        arts = [_make_art("ARCH-001", "architecture", body=ARCH_BODY_NO_HEADERS)]
        result = lint_cmd._check_spec_body(arts)
        assert result["warning_count"] >= 1
        assert "structural headers" in result["detail"]

    def test_ddd_with_headers_and_words_passes(self):
        arts = [_make_art("DDD-001", "detailed-design", body=DDD_BODY_GOOD)]
        result = lint_cmd._check_spec_body(arts)
        assert result["warning_count"] == 0
        assert result["blocking_count"] == 0

    def test_ddd_under_hundred_words_warns(self):
        arts = [_make_art("DDD-001", "detailed-design", body=DDD_BODY_SHORT)]
        result = lint_cmd._check_spec_body(arts)
        assert result["warning_count"] >= 1
        assert "minimum 100" in result["detail"]

    def test_ddd_without_design_headers_warns(self):
        arts = [_make_art("DDD-001", "detailed-design", body=DDD_BODY_NO_HEADERS)]
        result = lint_cmd._check_spec_body(arts)
        assert result["warning_count"] >= 1
        assert "design headers" in result["detail"]

    def test_non_spec_artifacts_not_checked(self):
        arts = [_make_art("REQ-001", "requirement", body="Short.")]
        result = lint_cmd._check_spec_body(arts)
        assert result["warning_count"] == 0

    def test_story_not_checked(self):
        arts = [_make_art("STORY-001", "story", body="Short.")]
        result = lint_cmd._check_spec_body(arts)
        assert result["warning_count"] == 0


class TestCheckCoverageArch:
    def test_approved_req_with_arch_derives_from_passes(self):
        arts = [
            _make_art("REQ-001", "requirement", status="approved"),
            _make_art(
                "ARCH-001", "architecture", status="draft",
                links=[art_lib.Link(target="REQ-001", role="derives_from")],
            ),
        ]
        result = lint_cmd.check_coverage(arts)
        assert "no ARCH derives_from" not in result["detail"]

    def test_approved_req_without_arch_derives_from_warns(self):
        arts = [
            _make_art("REQ-001", "requirement", status="approved"),
        ]
        result = lint_cmd.check_coverage(arts)
        assert result["warning_count"] >= 1
        assert "no ARCH derives_from" in result["detail"]

    def test_draft_req_no_arch_warning(self):
        arts = [
            _make_art("REQ-001", "requirement", status="draft"),
        ]
        result = lint_cmd.check_coverage(arts)
        assert "no ARCH derives_from" not in result["detail"]


class TestCheckStoryMinAC:
    def test_story_with_two_acs_passes(self):
        body = "## Acceptance Criteria\n\n1. First criterion.\n2. Second criterion."
        arts = [_make_art("STORY-001", "story", body=body)]
        result = lint_cmd._check_story_size(arts)
        ac_warnings = [d for d in result["detail"].split("\n") if "minimum 2" in d or "no Acceptance Criteria" in d]
        assert len(ac_warnings) == 0

    def test_story_with_one_ac_warns(self):
        body = "## Acceptance Criteria\n\n1. Only one criterion."
        arts = [_make_art("STORY-001", "story", body=body)]
        result = lint_cmd._check_story_size(arts)
        assert result["warning_count"] >= 1
        assert "minimum 2" in result["detail"]

    def test_story_with_no_ac_section_warns(self):
        arts = [_make_art("STORY-001", "story", body="Just some body text.")]
        result = lint_cmd._check_story_size(arts)
        assert result["warning_count"] >= 1
        assert "no Acceptance Criteria section" in result["detail"]

    def test_story_with_three_acs_passes(self):
        body = "## Acceptance Criteria\n\n1. First.\n2. Second.\n3. Third."
        arts = [_make_art("STORY-001", "story", body=body)]
        result = lint_cmd._check_story_size(arts)
        ac_warnings = [d for d in result["detail"].split("\n") if "minimum 2" in d or "no Acceptance Criteria" in d]
        assert len(ac_warnings) == 0


class TestCheckOutputFiles:
    def test_existing_file_passes(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        (project_root / "src" / "foo.py").write_text("pass", encoding="utf-8")
        arts = [_make_art("ARCH-001", "architecture", extra_fm={"output_files": ["src/foo.py"]})]
        result = lint_cmd._check_output_files(arts, project_root)
        assert result["warning_count"] == 0

    def test_nonexistent_file_warns(self, project_root: Path):
        arts = [_make_art("ARCH-001", "architecture", extra_fm={"output_files": ["src/nonexistent.py"]})]
        result = lint_cmd._check_output_files(arts, project_root)
        assert result["warning_count"] >= 1
        assert "not found" in result["detail"]

    def test_glob_pattern_matching_nothing_warns(self, project_root: Path):
        # A glob that matches nothing is surfaced as ambiguous (the package may
        # be deleted, or the pattern may be a typo). Previously globs were
        # silently skipped — that hid broken/stale output_files globs.
        arts = [_make_art("ARCH-001", "architecture", extra_fm={"output_files": ["output/YY_MM_DD_*.json"]})]
        result = lint_cmd._check_output_files(arts, project_root)
        assert result["warning_count"] == 1
        assert "matched nothing" in result["detail"]

    def test_glob_pattern_matching_files_passes(self, project_root: Path):
        # A glob that resolves to real files is credited — no warning. This is
        # the core adoption use case: one ARCH covering a package via a glob.
        pkg = project_root / "src" / "payments"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "charge.py").write_text("pass", encoding="utf-8")
        (pkg / "refund.py").write_text("pass", encoding="utf-8")
        arts = [_make_art("ARCH-001", "architecture",
                          extra_fm={"output_files": ["src/payments/**/*.py"]})]
        result = lint_cmd._check_output_files(arts, project_root)
        assert result["warning_count"] == 0

    def test_no_output_files_field_no_warnings(self, project_root: Path):
        arts = [_make_art("ARCH-001", "architecture")]
        result = lint_cmd._check_output_files(arts, project_root)
        assert result["warning_count"] == 0

    def test_multiple_files_mixed(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        (project_root / "src" / "exists.py").write_text("pass", encoding="utf-8")
        arts = [_make_art("ARCH-001", "architecture", extra_fm={
            "output_files": ["src/exists.py", "src/missing.py", "output/*.json"]
        })]
        result = lint_cmd._check_output_files(arts, project_root)
        # Two warnings: the literal miss (src/missing.py) + the glob that
        # matched nothing (output/*.json).
        assert result["warning_count"] == 2
        assert "src/missing.py" in result["detail"]
        assert "matched nothing" in result["detail"]


class TestUpdateOutputFiles:
    def test_update_sets_output_files(self, project_root: Path):
        _write_artifact(project_root, "ARCH-001", "architecture", "Test ARCH")
        rc = update_cmd.run(project_root, {
            "artifact_id": "ARCH-001",
            "status": None, "priority": None, "rationale": None,
            "tags": None, "title": None, "output_files": "src/foo.py,src/bar.py",
        })
        assert rc == 0
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-001.md"
        )
        assert art is not None
        assert art.frontmatter.get("output_files") == ["src/foo.py", "src/bar.py"]

    def test_update_replaces_output_files(self, project_root: Path):
        _write_artifact(project_root, "ARCH-001", "architecture", "Test ARCH",
                        extra_fm={"output_files": ["old.py"]})
        rc = update_cmd.run(project_root, {
            "artifact_id": "ARCH-001",
            "status": None, "priority": None, "rationale": None,
            "tags": None, "title": None, "output_files": "new.py",
        })
        assert rc == 0
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-001.md"
        )
        assert art is not None
        assert art.frontmatter.get("output_files") == ["new.py"]

    def test_update_removes_output_files_with_empty(self, project_root: Path):
        _write_artifact(project_root, "ARCH-001", "architecture", "Test ARCH",
                        extra_fm={"output_files": ["old.py"]})
        rc = update_cmd.run(project_root, {
            "artifact_id": "ARCH-001",
            "status": None, "priority": None, "rationale": None,
            "tags": None, "title": None, "output_files": "",
        })
        assert rc == 0
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-001.md"
        )
        assert art is not None
        assert "output_files" not in art.frontmatter

    def test_update_nonexistent_artifact_returns_error(self, project_root: Path):
        rc = update_cmd.run(project_root, {
            "artifact_id": "ARCH-999",
            "status": None, "priority": None, "rationale": None,
            "tags": None, "title": None, "output_files": "foo.py",
        })
        assert rc == 1


class TestConfigMerge:
    def test_merge_preserves_user_values(self):
        defaults = config_lib.default_config("test")
        existing = {
            "project": {"name": "my-project", "domain": "embedded"},
            "impact_analysis": {"auto_flag": False, "auto_resolve": True, "remind_after": "14d"},
        }
        merged = config_lib.merge_config(existing, defaults)
        assert merged["project"]["domain"] == "embedded"
        assert merged["impact_analysis"]["auto_flag"] is False
        assert merged["version"] is not None

    def test_merge_adds_new_default_keys(self):
        defaults = {"a": 1, "b": 2, "new_key": "new_value"}
        existing = {"a": 1, "b": 2}
        merged = config_lib.merge_config(existing, defaults)
        assert merged["new_key"] == "new_value"

    def test_version_always_stamped(self):
        import specflow
        defaults = config_lib.default_config("test")
        existing = {"version": "0.1.0"}
        merged = config_lib.merge_config(existing, defaults)
        assert merged["version"] == specflow.__version__


class TestDetectVersionDelta:
    def test_detects_upgrade(self, project_root: Path):
        config = config_lib.read_config(project_root)
        config["version"] = "0.1.0"
        config_lib.write_config(project_root, config)

        delta = config_lib.detect_version_delta(project_root)
        assert delta["is_upgrade"] is True
        assert delta["current_version"] == "0.1.0"
        assert delta["framework_version"] is not None

    def test_no_version_not_upgrade(self, project_root: Path):
        config = config_lib.read_config(project_root)
        config.pop("version", None)
        config_lib.write_config(project_root, config)

        delta = config_lib.detect_version_delta(project_root)
        assert delta["is_upgrade"] is False
        assert delta["current_version"] is None


class TestInitUpgrade:
    def test_reinit_preserves_config(self, project_root: Path):
        config = config_lib.read_config(project_root)
        config["project"]["domain"] = "aerospace"
        config["project"]["domain_tags"] = ["safety-critical", "real-time"]
        config_lib.write_config(project_root, config)

        rc = init_cmd.run(project_root, {"platform": "claude-code", "no_ci": True})
        assert rc == 0

        updated_config = config_lib.read_config(project_root)
        assert updated_config["project"]["domain"] == "aerospace"
        assert updated_config["project"]["domain_tags"] == ["safety-critical", "real-time"]

    def test_reinit_preserves_state(self, project_root: Path):
        state = config_lib.read_state(project_root)
        state["current"] = "executing"
        state["history"] = [{"phase": "discover", "completed": "2026-05-04"}]
        config_lib.write_state(project_root, state)

        rc = init_cmd.run(project_root, {"platform": "claude-code", "no_ci": True})
        assert rc == 0

        updated_state = config_lib.read_state(project_root)
        assert updated_state["current"] == "executing"
        assert len(updated_state["history"]) == 1

    def test_reinit_adds_version(self, project_root: Path):
        config = config_lib.read_config(project_root)
        config.pop("version", None)
        config_lib.write_config(project_root, config)

        rc = init_cmd.run(project_root, {"platform": "claude-code", "no_ci": True})
        assert rc == 0

        updated_config = config_lib.read_config(project_root)
        assert "version" in updated_config
        assert updated_config["version"] is not None

    def test_fresh_init_has_version(self, tmp_path: Path):
        root = tmp_path / "fresh_project"
        root.mkdir()
        template_dir = Path(__file__).parent.parent / "src" / "specflow" / "templates"
        scaffold_lib.create_internal_dirs(root, template_dir)
        scaffold_lib.create_spec_dirs(root)
        config = config_lib.default_config("fresh")
        config_lib.write_config(root, config)
        state = config_lib.default_state()
        config_lib.write_state(root, state)

        assert config_lib.read_config(root).get("version") is not None


class TestInitForce:
    def test_force_creates_backup(self, project_root: Path):
        config = config_lib.read_config(project_root)
        config["project"]["domain"] = "embedded"
        config_lib.write_config(project_root, config)

        rc = init_cmd.run(project_root, {"platform": "claude-code", "no_ci": True, "force": True})
        assert rc == 0

        backups_dir = project_root / ".specflow" / "cache" / "backups"
        assert backups_dir.exists()
        backup_dirs = list(backups_dir.iterdir())
        assert len(backup_dirs) >= 1

    def test_force_fresh_state(self, project_root: Path):
        state = config_lib.read_state(project_root)
        state["current"] = "executing"
        config_lib.write_state(project_root, state)

        rc = init_cmd.run(project_root, {"platform": "claude-code", "no_ci": True, "force": True})
        assert rc == 0

    def test_without_force_uses_merge(self, project_root: Path):
        config = config_lib.read_config(project_root)
        config["project"]["domain"] = "automotive"
        config_lib.write_config(project_root, config)

        rc = init_cmd.run(project_root, {"platform": "claude-code", "no_ci": True})
        assert rc == 0

        updated_config = config_lib.read_config(project_root)
        assert updated_config["project"]["domain"] == "automotive"
