"""Tests for the adoption code-linking model (D-20):

- output_files glob expansion (lib.files)
- orphan meter credits ARCH/DDD output_files (not just STORY/REQ)
- retro_link targets any artifact type (ARCH/DDD/STORY)
- coverage % + biggest-cluster in detect output
- reconcile counts glob-expanded output_files as evidence
- source-drift checks glob-expanded files
- specflow adopt status (project + artifact completeness views)
- brief Adoption section (derived from graph, no state file)
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import adopt as adopt_cmd
from specflow.commands import brief as brief_cmd
from specflow.commands import detect as detect_cmd
from specflow.commands import reconcile as reconcile_cmd
from specflow.commands import artifact_lint as lint_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import config as config_lib
from specflow.lib import files as files_lib
from specflow.lib import orphans as orphans_lib


_SCHEMA_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"),
    ("defect", "DEF"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"], "cancelled": ["draft", "approved", "implemented", "verified"],
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
            "optional_fields": ["output_files", "rationale", "tags", "links"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config_lib.write_config(root, config_lib.default_config("test-project"))
    config_lib.write_state(root, config_lib.default_state())

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
    title: str = "t",
    status: str = "draft",
    output_files: list[str] | None = None,
    tags: list[str] | None = None,
    rationale: str | None = None,
    body: str = "",
    extra_fm: dict | None = None,
) -> Path:
    rel_dir = art_lib.TYPE_TO_DIR.get(art_type, "")
    target_dir = root / "_specflow" / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{artifact_id}.md"
    fm: dict = {"id": artifact_id, "title": title, "type": art_type,
                "status": status, "created": "2026-06-14"}
    if output_files is not None:
        fm["output_files"] = output_files
    if tags is not None:
        fm["tags"] = tags
    if rationale is not None:
        fm["rationale"] = rationale
    if extra_fm:
        fm.update(extra_fm)
    path.write_text(f"---\n{yaml.dump(fm, sort_keys=False)}---\n{body}", encoding="utf-8")
    return path


# ────────────────────────────────────────────────────────────────────
# lib.files.expand_output_files
# ────────────────────────────────────────────────────────────────────

class TestExpandOutputFiles:
    def test_literal_path_resolves(self, project_root: Path):
        (project_root / "src" / "auth").mkdir(parents=True, exist_ok=True)
        f = project_root / "src" / "auth" / "login.py"
        f.write_text("pass", encoding="utf-8")
        result = files_lib.expand_output_files(project_root, ["src/auth/login.py"])
        assert f.resolve() in result

    def test_literal_missing_resolves_to_nothing(self, project_root: Path):
        result = files_lib.expand_output_files(project_root, ["src/nonexistent.py"])
        assert result == set()

    def test_glob_double_star_expands(self, project_root: Path):
        pkg = project_root / "src" / "main" / "java" / "com" / "acme" / "payments"
        pkg.mkdir(parents=True, exist_ok=True)
        a = pkg / "Charge.java"
        b = pkg / "Refund.java"
        a.write_text("x", encoding="utf-8")
        b.write_text("y", encoding="utf-8")
        result = files_lib.expand_output_files(
            project_root, ["src/main/java/com/acme/payments/**/*.java"]
        )
        assert a.resolve() in result
        assert b.resolve() in result
        assert len(result) == 2

    def test_glob_matching_nothing_returns_empty(self, project_root: Path):
        result = files_lib.expand_output_files(project_root, ["src/ghost/**/*.py"])
        assert result == set()

    def test_glob_excludes_non_source_files(self, project_root: Path):
        # A glob should NOT credit generated artifacts (.min.js) even if they
        # sit inside the globbed package.
        pkg = project_root / "src" / "pkg"
        pkg.mkdir(parents=True, exist_ok=True)
        good = pkg / "service.py"
        junk = pkg / "bundle.min.js"
        good.write_text("pass", encoding="utf-8")
        junk.write_text("minified", encoding="utf-8")
        result = files_lib.expand_output_files(project_root, ["src/pkg/**/*"])
        assert good.resolve() in result
        assert junk.resolve() not in result

    def test_literal_non_source_file_is_honored(self, project_root: Path):
        # A literal entry is credited even if it fails the source-file filter —
        # explicit user intent. Globs are filtered; literals are honored.
        cfg = project_root / "config.json"
        cfg.write_text("{}", encoding="utf-8")
        # config.json IS a source extension (.json is in SOURCE_EXTENSIONS) and
        # is not in the generated-name skip list, so it'd pass anyway. Use a
        # generated name to prove the literal-honor point:
        mini = project_root / "app.min.js"
        mini.write_text("x", encoding="utf-8")
        result = files_lib.expand_output_files(project_root, ["app.min.js"])
        assert mini.resolve() in result

    def test_glob_excludes_specflow_dirs(self, project_root: Path):
        # .specflow/ and _specflow/ must never be credited even if a glob
        # sweeps across the whole repo.
        (project_root / "_specflow" / "specs").mkdir(parents=True, exist_ok=True)
        leaked = project_root / "_specflow" / "leaked.py"
        leaked.write_text("x", encoding="utf-8")
        result = files_lib.expand_output_files(project_root, ["**/*.py"])
        assert leaked.resolve() not in result

    def test_none_and_non_list_entries_safe(self, project_root: Path):
        assert files_lib.expand_output_files(project_root, None) == set()
        assert files_lib.expand_output_files(project_root, []) == set()
        # Non-string entries ignored, others still resolve.
        (project_root / "ok.py").write_text("x", encoding="utf-8")
        result = files_lib.expand_output_files(project_root, ["ok.py", 42, None])
        assert (project_root / "ok.py").resolve() in result


class TestLiteralMissingAndGlobEntries:
    def test_literal_missing_reports(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        (project_root / "src" / "ok.py").write_text("x", encoding="utf-8")
        missing = files_lib.literal_missing(project_root, ["src/gone.py", "src/ok.py"])
        assert missing == ["src/gone.py"]

    def test_literal_missing_skips_globs(self, project_root: Path):
        # Globs are ambiguous-miss; literal_missing only reports hard misses.
        missing = files_lib.literal_missing(project_root, ["src/*.py"])
        assert missing == []

    def test_glob_entries_isolate_globs(self, project_root: Path):
        entries = ["src/a.py", "src/**/*.java", "README.md", "pkg/*"]
        assert files_lib.glob_entries(entries) == ["src/**/*.java", "pkg/*"]


# ────────────────────────────────────────────────────────────────────
# Orphan meter credits ARCH / DDD (not just STORY/REQ)
# ────────────────────────────────────────────────────────────────────

class TestOrphanMeterArtifactTypes:
    def test_arch_output_files_credit_files(self, project_root: Path):
        pkg = project_root / "src" / "payments"
        pkg.mkdir(parents=True, exist_ok=True)
        for n in ("charge.py", "refund.py"):
            (pkg / n).write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "ARCH-001", "architecture",
                        output_files=["src/payments/**/*.py"])
        result = orphans_lib.find_orphan_code(project_root)
        # Both payments files are referenced → not orphan.
        payments_files = {f.resolve() for f in pkg.glob("*.py")}
        orphan_set = {f.resolve() for f in result["orphan_files"]}
        assert all(pf not in orphan_set for pf in payments_files)
        assert result["referenced_count"] >= 2

    def test_ddd_output_files_credit_files(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        f = project_root / "src" / "engine.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "DDD-001", "detailed-design",
                        output_files=["src/engine.py"])
        result = orphans_lib.find_orphan_code(project_root)
        assert f.resolve() not in {o.resolve() for o in result["orphan_files"]}

    def test_req_output_files_still_credited_backward_compat(self, project_root: Path):
        # REQ schema doesn't bless output_files, but the meter still reads it
        # so existing projects don't suddenly orphan on upgrade.
        (project_root / "src").mkdir(exist_ok=True)
        f = project_root / "src" / "legacy.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "REQ-001", "requirement",
                        output_files=["src/legacy.py"])
        result = orphans_lib.find_orphan_code(project_root)
        assert f.resolve() not in {o.resolve() for o in result["orphan_files"]}

    def test_story_output_files_still_credited(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        f = project_root / "src" / "feature.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "STORY-001", "story",
                        output_files=["src/feature.py"])
        result = orphans_lib.find_orphan_code(project_root)
        assert f.resolve() not in {o.resolve() for o in result["orphan_files"]}


# ────────────────────────────────────────────────────────────────────
# retro_link targets any artifact type
# ────────────────────────────────────────────────────────────────────

class TestRetroLinkTargets:
    def test_retro_link_to_arch(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        f = project_root / "src" / "orphan1.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "ARCH-007", "architecture")
        assert orphans_lib.retro_link(project_root, "src/orphan1.py", "ARCH-007") is True
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-007.md")
        assert "src/orphan1.py" in (art.frontmatter.get("output_files") or [])

    def test_retro_link_to_ddd(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        f = project_root / "src" / "orphan2.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "DDD-003", "detailed-design")
        assert orphans_lib.retro_link(project_root, "src/orphan2.py", "DDD-003") is True

    def test_retro_link_to_story(self, project_root: Path):
        # Backward compat: STORY still works as a target.
        (project_root / "src").mkdir(exist_ok=True)
        f = project_root / "src" / "orphan3.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "STORY-042", "story")
        assert orphans_lib.retro_link(project_root, "src/orphan3.py", "STORY-042") is True

    def test_retro_link_unknown_target_fails(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        f = project_root / "src" / "ok.py"
        f.write_text("pass", encoding="utf-8")
        assert orphans_lib.retro_link(project_root, "src/ok.py", "ARCH-999") is False

    def test_retro_link_idempotent(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        f = project_root / "src" / "once.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "ARCH-001", "architecture")
        assert orphans_lib.retro_link(project_root, "src/once.py", "ARCH-001") is True
        assert orphans_lib.retro_link(project_root, "src/once.py", "ARCH-001") is True  # no dup
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-001.md")
        assert (art.frontmatter.get("output_files") or []).count("src/once.py") == 1


# ────────────────────────────────────────────────────────────────────
# Coverage % + biggest cluster in detect output
# ────────────────────────────────────────────────────────────────────

class TestDetectOrphanCodeReporting:
    def test_coverage_pct_displayed(self, project_root: Path, capsys):
        # 2 source files, 1 referenced via ARCH glob → ~50% coverage.
        (project_root / "src" / "pkg").mkdir(parents=True, exist_ok=True)
        (project_root / "src" / "pkg" / "a.py").write_text("x", encoding="utf-8")
        (project_root / "src" / "pkg" / "b.py").write_text("y", encoding="utf-8")
        _write_artifact(project_root, "ARCH-001", "architecture",
                        output_files=["src/pkg/a.py"])
        detect_cmd._run_orphan_code(project_root, {})
        out = capsys.readouterr().out
        assert "coverage" in out
        assert "50.0%" in out

    def test_biggest_cluster_reported(self, project_root: Path, capsys):
        # Two top-level dirs of orphans; the larger should be flagged.
        for d in ("legacy", "experimental"):
            (project_root / d).mkdir(exist_ok=True)
        for n in range(5):
            (project_root / "legacy" / f"f{n}.py").write_text("x", encoding="utf-8")
        for n in range(2):
            (project_root / "experimental" / f"f{n}.py").write_text("y", encoding="utf-8")
        detect_cmd._run_orphan_code(project_root, {})
        out = capsys.readouterr().out
        assert "Biggest un-adopted cluster" in out
        assert "legacy" in out


# ────────────────────────────────────────────────────────────────────
# reconcile: globs count as evidence
# ────────────────────────────────────────────────────────────────────

class TestReconcileGlobEvidence:
    def test_glob_output_files_count_as_evidence(self, project_root: Path, capsys):
        # An approved STORY whose output_files is a package glob + at least one
        # matching file exists → reconcile promotes it to implemented.
        pkg = project_root / "src" / "feature"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "impl.py").write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "STORY-001", "story", status="approved",
                        output_files=["src/feature/**/*.py"])
        rc = reconcile_cmd.run(project_root, {"dry_run": True, "cascade": False})
        out = capsys.readouterr().out
        assert rc == 0
        assert "STORY-001" in out
        assert "implemented" in out.lower()


# ────────────────────────────────────────────────────────────────────
# source-drift: globs expanded and hashed
# ────────────────────────────────────────────────────────────────────

class TestSourceDriftGlobs:
    def test_glob_files_are_hashed(self, project_root: Path):
        # Seed: ARCH with a package glob → first run seeds fingerprints for
        # every matched file (not just zero, which was the old glob-skip bug).
        pkg = project_root / "src" / "svc"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "a.py").write_text("v1", encoding="utf-8")
        (pkg / "b.py").write_text("v1", encoding="utf-8")
        arts = [art_lib.parse_artifact(
            _write_artifact(project_root, "ARCH-001", "architecture",
                            output_files=["src/svc/**/*.py"]))]
        # First run seeds.
        result0 = lint_cmd._check_source_drift(arts, project_root)
        assert result0["warning_count"] == 0
        # The seed file should contain per-file hashes for both a.py and b.py
        # under ARCH-001 (proving the glob was expanded, not skipped).
        fp_path = project_root / ".specflow" / "source-fingerprints.yaml"
        seeded = yaml.safe_load(fp_path.read_text(encoding="utf-8"))
        assert "ARCH-001" in seeded
        assert any("a.py" in k for k in seeded["ARCH-001"])
        assert any("b.py" in k for k in seeded["ARCH-001"])

    def test_glob_file_change_triggers_drift(self, project_root: Path):
        pkg = project_root / "src" / "svc"
        pkg.mkdir(parents=True, exist_ok=True)
        f = pkg / "a.py"
        f.write_text("v1", encoding="utf-8")
        arts = [art_lib.parse_artifact(
            _write_artifact(project_root, "ARCH-001", "architecture",
                            output_files=["src/svc/**/*.py"]))]
        lint_cmd._check_source_drift(arts, project_root)  # seed
        f.write_text("v2 CHANGED", encoding="utf-8")  # drift
        result = lint_cmd._check_source_drift(arts, project_root)
        assert result["warning_count"] >= 1
        assert "ARCH-001" in result["detail"]


# ────────────────────────────────────────────────────────────────────
# specflow adopt status — project + artifact completeness views
# ────────────────────────────────────────────────────────────────────

def _make_backfilled_project(root: Path):
    """Scaffold a mini brownfield project: payments (skeleton) + auth (full V)."""
    for sub in ("payments", "auth", "inventory"):
        pkg = root / "src" / "main" / sub
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "a.py").write_text("pass", encoding="utf-8")
        (pkg / "b.py").write_text("pass", encoding="utf-8")

    # payments: skeleton ARCH only (glob)
    _write_artifact(root, "ARCH-001", "architecture", title="Payments",
                    status="implemented", tags=["backfilled"],
                    output_files=["src/main/payments/**/*.py"])
    # auth: full V-model REQ ← ARCH ← DDD
    _write_artifact(root, "REQ-001", "requirement", title="User auth",
                    status="approved", tags=["backfilled"],
                    rationale="Backfilled from README + framing",
                    body="## Acceptance Criteria\n\n**Given** a user\n**When** they log in\n**Then** they get a token\n")
    _write_artifact(root, "ARCH-002", "architecture", title="Auth component",
                    status="implemented", tags=["backfilled"],
                    output_files=["src/main/auth/**/*.py"],
                    extra_fm={"links": [{"target": "REQ-001", "role": "derives_from"}]})
    _write_artifact(root, "DDD-001", "detailed-design", title="Token internals",
                    status="implemented", tags=["backfilled"],
                    rationale="Inferred from code; not confirmed",
                    output_files=["src/main/auth/a.py"],
                    extra_fm={"links": [{"target": "ARCH-002", "role": "derives_from"}]})


class TestAdoptStatusProjectView:
    def test_project_view_shows_coverage_and_boundaries(self, project_root, capsys):
        _make_backfilled_project(project_root)
        rc = adopt_cmd.run(project_root, {})
        out = capsys.readouterr().out
        assert rc == 0
        assert "Coverage:" in out
        assert "Boundaries (by ARCH)" in out
        assert "ARCH-001" in out and "ARCH-002" in out

    def test_project_view_reports_inference_debt(self, project_root, capsys):
        _make_backfilled_project(project_root)
        adopt_cmd.run(project_root, {})
        out = capsys.readouterr().out
        # DDD-001 rationale says "inferred...not confirmed" → flagged.
        assert "Inference debt" in out

    def test_project_view_no_backfilled_shows_no_adoption_block(self, project_root, capsys):
        # A greenfield project (no backfilled tags) — adopt status still runs
        # but the "Backfilled:" line is absent.
        _write_artifact(project_root, "REQ-001", "requirement", title="x")
        adopt_cmd.run(project_root, {})
        out = capsys.readouterr().out
        assert "Coverage:" in out
        assert "Backfilled:" not in out

    def test_project_view_biggest_cluster_reported(self, project_root, capsys):
        _make_backfilled_project(project_root)
        adopt_cmd.run(project_root, {})
        out = capsys.readouterr().out
        assert "Biggest un-adopted cluster" in out


class TestAdoptStatusArtifactView:
    def test_req_view_shows_realizer_and_criteria(self, project_root, capsys):
        _make_backfilled_project(project_root)
        rc = adopt_cmd.run(project_root, {"target": "REQ-001"})
        out = capsys.readouterr().out
        assert rc == 0
        assert "Realized by:" in out
        assert "ARCH-002" in out
        assert "acceptance criteria" in out
        # The body had 1 Given → 1 criterion.
        assert "1 acceptance criteria" in out

    def test_req_view_depth_is_realized_not_missing_parent(self, project_root, capsys):
        # REQ is the top of the V — depth must NOT say "missing parent spec".
        _make_backfilled_project(project_root)
        adopt_cmd.run(project_root, {"target": "REQ-001"})
        out = capsys.readouterr().out
        assert "missing parent" not in out

    def test_arch_skeleton_shows_gap(self, project_root, capsys):
        _make_backfilled_project(project_root)
        adopt_cmd.run(project_root, {"target": "ARCH-001"})
        out = capsys.readouterr().out
        assert "skeleton" in out or "isolated" in out
        assert "Gap" in out or "no DDD" in out

    def test_arch_full_depth_no_gap(self, project_root, capsys):
        _make_backfilled_project(project_root)
        adopt_cmd.run(project_root, {"target": "ARCH-002"})
        out = capsys.readouterr().out
        assert "full" in out

    def test_unknown_target_returns_error(self, project_root, capsys):
        _make_backfilled_project(project_root)
        rc = adopt_cmd.run(project_root, {"target": "ARCH-999"})
        out = capsys.readouterr().out
        assert rc == 1
        assert "not found" in out.lower()

    def test_provenance_conflict_marker_surfaced(self, project_root, capsys):
        # An artifact whose rationale records a resolved conflict should surface
        # the "conflict resolved" provenance marker.
        _write_artifact(root=project_root, artifact_id="ARCH-001", art_type="architecture",
                        tags=["backfilled"],
                        rationale="README↔code conflict — user confirmed code authoritative")
        adopt_cmd.run(project_root, {"target": "ARCH-001"})
        out = capsys.readouterr().out
        assert "conflict resolved" in out


class TestBriefAdoptionSection:
    def test_brief_shows_adoption_when_backfilled_present(self, project_root, capsys):
        _make_backfilled_project(project_root)
        brief_cmd.run(project_root, {"since": "7 days ago"})
        out = capsys.readouterr().out
        assert "Adoption" in out
        assert "Coverage:" in out
        assert "specflow adopt status" in out

    def test_brief_omits_adoption_when_no_backfilled(self, project_root, capsys):
        # Greenfield: no backfilled tags → no Adoption section, no orphan scan
        # cost (the helper returns None early).
        _write_artifact(project_root, "REQ-001", "requirement", title="x")
        brief_cmd.run(project_root, {"since": "7 days ago"})
        out = capsys.readouterr().out
        assert "Adoption" not in out


# ────────────────────────────────────────────────────────────────────
# Corrupted fingerprint file handling
# ────────────────────────────────────────────────────────────────────

class TestSourceDriftCorruptedFingerprints:
    def test_drift_handles_malformed_yaml(self, project_root: Path, capsys):
        fp_path = project_root / ".specflow" / "source-fingerprints.yaml"
        fp_path.write_text("{{{{invalid yaml", encoding="utf-8")
        _write_artifact(project_root, "ARCH-001", "architecture",
                        output_files=["src/a.py"])
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-001.md")
        result = adopt_cmd._drift_for_artifact(project_root, art)
        assert result == []
        out = capsys.readouterr().out
        assert "Could not read" in out or "malformed" in out

    def test_drift_handles_non_dict_yaml(self, project_root: Path, capsys):
        fp_path = project_root / ".specflow" / "source-fingerprints.yaml"
        fp_path.write_text("- item1\n- item2\n", encoding="utf-8")
        _write_artifact(project_root, "ARCH-001", "architecture",
                        output_files=["src/a.py"])
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-001.md")
        result = adopt_cmd._drift_for_artifact(project_root, art)
        assert result == []
        out = capsys.readouterr().out
        assert "malformed" in out

    def test_drift_handles_non_dict_per_artifact_entry(self, project_root: Path):
        fp_path = project_root / ".specflow" / "source-fingerprints.yaml"
        fp_path.write_text(yaml.dump({"ARCH-001": "not-a-dict"}), encoding="utf-8")
        _write_artifact(project_root, "ARCH-001", "architecture",
                        output_files=["src/a.py"])
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-001.md")
        result = adopt_cmd._drift_for_artifact(project_root, art)
        assert result == []

    def test_check_source_drift_handles_corrupted_file(self, project_root: Path):
        fp_path = project_root / ".specflow" / "source-fingerprints.yaml"
        fp_path.write_text("not: valid: yaml: {{{", encoding="utf-8")
        pkg = project_root / "src" / "svc"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "a.py").write_text("v1", encoding="utf-8")
        arts = [art_lib.parse_artifact(
            _write_artifact(project_root, "ARCH-001", "architecture",
                            output_files=["src/svc/**/*.py"]))]
        result = lint_cmd._check_source_drift(arts, project_root)
        assert result["warning_count"] == 0


# ────────────────────────────────────────────────────────────────────
# retro_link with absolute paths
# ────────────────────────────────────────────────────────────────────

class TestRetroLinkAbsolutePaths:
    def test_retro_link_with_absolute_path(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        f = project_root / "src" / "abs_orphan.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "ARCH-010", "architecture")
        abs_path = str(f.resolve())
        assert orphans_lib.retro_link(project_root, abs_path, "ARCH-010") is True
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-010.md")
        stored = art.frontmatter.get("output_files") or []
        assert "src/abs_orphan.py" in stored
        assert not any(p.startswith("/") for p in stored)

    def test_retro_link_absolute_nonexistent_fails(self, project_root: Path):
        (project_root / "src").mkdir(exist_ok=True)
        _write_artifact(project_root, "ARCH-010", "architecture")
        abs_path = str((project_root / "src" / "ghost.py").resolve())
        assert orphans_lib.retro_link(project_root, abs_path, "ARCH-010") is False

    def test_retro_link_absolute_outside_root_fails(self, project_root: Path):
        _write_artifact(project_root, "ARCH-010", "architecture")
        assert orphans_lib.retro_link(project_root, "/tmp/outside.py", "ARCH-010") is False


# ────────────────────────────────────────────────────────────────────
# Non-referencing type exclusion (SPIKE/DEC don't credit orphan meter)
# ────────────────────────────────────────────────────────────────────

class TestOrphanMeterExcludedTypes:
    def test_spike_output_files_do_not_credit_orphan_meter(self, project_root: Path):
        pkg = project_root / "src" / "spike_code"
        pkg.mkdir(parents=True, exist_ok=True)
        f = pkg / "experimental.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "SPIKE-001", "spike",
                        output_files=["src/spike_code/experimental.py"])
        result = orphans_lib.find_orphan_code(project_root)
        orphan_set = {o.resolve() for o in result["orphan_files"]}
        assert f.resolve() in orphan_set

    def test_dec_output_files_do_not_credit_orphan_meter(self, project_root: Path):
        pkg = project_root / "src" / "dec_code"
        pkg.mkdir(parents=True, exist_ok=True)
        f = pkg / "config_module.py"
        f.write_text("pass", encoding="utf-8")
        _write_artifact(project_root, "DEC-099", "decision",
                        output_files=["src/dec_code/config_module.py"])
        result = orphans_lib.find_orphan_code(project_root)
        orphan_set = {o.resolve() for o in result["orphan_files"]}
        assert f.resolve() in orphan_set

    def test_spike_and_dec_not_in_referencing_types(self):
        assert "spike" not in orphans_lib.REFERENCING_TYPES
        assert "decision" not in orphans_lib.REFERENCING_TYPES


# ────────────────────────────────────────────────────────────────────
# Acceptance criteria counting edge cases
# ────────────────────────────────────────────────────────────────────

class TestAcceptanceCriteriaCount:
    def test_no_body_returns_zero(self, project_root: Path):
        _write_artifact(project_root, "REQ-100", "requirement", body="")
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "requirements" / "REQ-100.md")
        assert adopt_cmd._acceptance_criteria_count(art) == 0

    def test_body_without_ac_section_counts_given_in_body(self, project_root: Path):
        body = "Some prose.\n\n**Given** a user\n**When** they click\n**Then** it works\n"
        _write_artifact(project_root, "REQ-101", "requirement", body=body)
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "requirements" / "REQ-101.md")
        assert adopt_cmd._acceptance_criteria_count(art) == 1

    def test_ac_section_only_counts_given_within_section(self, project_root: Path):
        body = ("Given in intro prose should not count.\n\n"
                "## Acceptance Criteria\n\n"
                "**Given** a valid user\n**When** they login\n**Then** success\n\n"
                "## Notes\n\nMore Given here ignored.\n")
        _write_artifact(project_root, "REQ-102", "requirement", body=body)
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "requirements" / "REQ-102.md")
        assert adopt_cmd._acceptance_criteria_count(art) == 1

    def test_multiple_given_in_ac_section(self, project_root: Path):
        body = ("## Acceptance Criteria\n\n"
                "**Given** user A\n**When** ...\n**Then** ...\n\n"
                "**Given** user B\n**When** ...\n**Then** ...\n")
        _write_artifact(project_root, "REQ-103", "requirement", body=body)
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "requirements" / "REQ-103.md")
        assert adopt_cmd._acceptance_criteria_count(art) == 2

    def test_given_without_bold_still_counts(self, project_root: Path):
        body = "## Acceptance Criteria\n\nGiven a user\nWhen they login\nThen success\n"
        _write_artifact(project_root, "REQ-104", "requirement", body=body)
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "requirements" / "REQ-104.md")
        assert adopt_cmd._acceptance_criteria_count(art) == 1

    def test_case_insensitive_given(self, project_root: Path):
        body = "## Acceptance Criteria\n\ngiven a user\nwhen they login\nthen success\n"
        _write_artifact(project_root, "REQ-105", "requirement", body=body)
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "requirements" / "REQ-105.md")
        assert adopt_cmd._acceptance_criteria_count(art) == 1

    def test_given_in_code_block_still_counted(self, project_root: Path):
        body = ("## Acceptance Criteria\n\n"
                "```\nGiven a code example\n```\n")
        _write_artifact(project_root, "REQ-107", "requirement", body=body)
        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "requirements" / "REQ-107.md")
        # Documents current behavior: counts even in code blocks.
        assert adopt_cmd._acceptance_criteria_count(art) == 1

