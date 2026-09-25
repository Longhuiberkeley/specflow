"""Coverage for guided_by practice bindings and bp-application evidence."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import trace as trace_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import role_targets


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_TYPES = (
    "requirement", "architecture", "story", "best-practice", "decision",
    "unit-test", "integration-test", "qualification-test",
)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True)
    for art_type in _SCHEMA_TYPES:
        source = _REPO_ROOT / "src/specflow/templates/schemas" / f"{art_type}.yaml"
        (schema_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (root / ".specflow/config.yaml").write_text(
        yaml.safe_dump({"project": {"name": "bp-test"}, "active_packs": []}),
        encoding="utf-8",
    )
    for art_type in _SCHEMA_TYPES:
        (root / "_specflow" / art_lib.TYPE_TO_DIR[art_type]).mkdir(
            parents=True, exist_ok=True
        )
    return root


def _write_artifact(
    root: Path,
    artifact_id: str,
    art_type: str,
    *,
    status: str = "approved",
    links: list[dict[str, str]] | None = None,
    extra: dict | None = None,
    body: str = "Artifact body.",
) -> Path:
    path = root / "_specflow" / art_lib.TYPE_TO_DIR[art_type] / f"{artifact_id}.md"
    frontmatter = {
        "id": artifact_id,
        "title": artifact_id,
        "type": art_type,
        "status": status,
        "created": "2026-01-01",
        "links": links or [],
    }
    frontmatter.update(extra or {})
    path.write_text(
        f"---\n{yaml.safe_dump(frontmatter, sort_keys=False)}---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


def _bp(root: Path, bp_id: str = "BP-001", **extra) -> Path:
    fields = {
        "provenance": "learned",
        "applicability": {"always": True},
        "strength": "recommended",
        "verification_method": "inspection",
    }
    fields.update(extra)
    return _write_artifact(
        root,
        bp_id,
        "best-practice",
        extra=fields,
        body=(
            "## Practice\nDo the thing.\n\n"
            "## Applies when\nAlways.\n\n"
            "## Work products\nThe artifact.\n\n"
            "## Verification\nInspect the result.\n\n"
            "## Rationale\nIt helps."
        ),
    )


@pytest.mark.parametrize("art_type,artifact_id", [
    ("requirement", "REQ-001"),
    ("architecture", "ARCH-001"),
    ("story", "STORY-001"),
])
def test_guided_by_bp_is_schema_and_role_target_legal(
    project_root: Path, art_type: str, artifact_id: str
):
    _bp(project_root)
    source = _write_artifact(
        project_root,
        artifact_id,
        art_type,
        links=[{"target": "BP-001", "role": "guided_by"}],
    )
    artifacts = [art_lib.parse_artifact(source)]
    bp = art_lib.parse_artifact(
        project_root / "_specflow/specs/best-practices/BP-001.md"
    )
    artifacts.append(bp)

    schema_result = lint_cmd.check_schema(
        artifacts, project_root / ".specflow/schema"
    )
    assert schema_result["blocking_count"] == 0
    assert not role_targets.check_role_targets(artifacts)


def test_trace_renders_guided_by_bp_edge(project_root: Path, capsys):
    _bp(project_root)
    _write_artifact(
        project_root,
        "REQ-001",
        "requirement",
        links=[{"target": "BP-001", "role": "guided_by"}],
    )
    assert trace_cmd.run(project_root, {"artifact_id": "REQ-001"}) == 0
    output = capsys.readouterr().out
    assert "BP-001" in output
    assert "(guided_by)" in output


def test_guided_by_does_not_inflate_chain_depth():
    bp = art_lib.Artifact(
        path=Path("BP-001.md"),
        frontmatter={"id": "BP-001", "type": "best-practice", "status": "approved"},
        body="",
    )
    req = art_lib.Artifact(
        path=Path("REQ-001.md"),
        frontmatter={"id": "REQ-001", "type": "requirement", "status": "approved"},
        body="",
        links=[art_lib.Link(target="BP-001", role="guided_by")],
    )
    index = art_lib.build_id_index([bp, req])
    assert art_lib.compute_chain_depth("BP-001", index) == ["BP-001"]


def test_dangling_guided_by_bp_edge_is_reported_by_links_check(project_root: Path):
    source = _write_artifact(
        project_root,
        "REQ-001",
        "requirement",
        links=[{"target": "BP-999", "role": "guided_by"}],
    )
    result = lint_cmd._check_links([art_lib.parse_artifact(source)], project_root)
    assert result["blocking_count"] == 1
    assert "BP-999 (not found)" in result["detail"]


def _bp_application(root: Path) -> dict[str, str | int]:
    artifacts = art_lib.discover_artifacts(root)
    return lint_cmd._run_check(artifacts, root, "bp-application")


def test_bp_application_warns_by_default_with_coverage_arithmetic(project_root: Path):
    _bp(project_root)
    _write_artifact(project_root, "REQ-001", "requirement")

    result = _bp_application(project_root)

    assert result["warning_count"] == 1
    assert result["blocking_count"] == 0
    assert "REQ-001" in result["detail"]
    assert "0/1 in-scope BP binding(s) bound; 1 unbound" in result["detail"]


def test_bp_application_blocks_only_with_strict_opt_in(project_root: Path):
    _bp(project_root)
    _write_artifact(project_root, "REQ-001", "requirement")
    config_path = project_root / ".specflow/config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["lint"] = {"bp_evidence_strict": True}
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    result = _bp_application(project_root)

    assert result["blocking_count"] == 1
    assert result["warning_count"] == 0


def test_bp_application_warning_is_not_persistently_escalated(
    project_root: Path, monkeypatch, capsys
):
    _bp(project_root)
    _write_artifact(project_root, "REQ-001", "requirement")
    original_check = lint_cmd._run_check
    escalated_checks: list[str] = []

    def check(artifacts, root, name):
        if name == "bp-application":
            return original_check(artifacts, root, name)
        return {
            "status_icon": "✓",
            "detail": "fixture check",
            "blocking_count": 0,
            "warning_count": 0,
        }

    def record(_root, results):
        escalated_checks.extend(name for name, _result in results)
        return []

    monkeypatch.setattr(lint_cmd, "_run_check", check)
    monkeypatch.setattr(lint_cmd, "_record_warning_runs", record)

    assert lint_cmd.run(project_root, {}) == 0
    assert "bp-application" not in escalated_checks
    assert "Result:" in capsys.readouterr().out


def test_bp_application_skips_unstamped_legacy_practice(project_root: Path):
    _bp(project_root, provenance=None)
    _write_artifact(project_root, "REQ-001", "requirement")

    result = _bp_application(project_root)

    assert result["blocking_count"] == 0
    assert result["warning_count"] == 0
    assert "BP-001" not in result["detail"]


def test_bp_application_backfill_grace_skips_unchanged_artifact(project_root: Path):
    bp_path = _bp(project_root)
    req_path = _write_artifact(project_root, "REQ-001", "requirement")
    approval_ns = bp_path.stat().st_mtime_ns
    grace_mtime = approval_ns - 1_000_000
    os.utime(req_path, ns=(grace_mtime, grace_mtime))

    result = _bp_application(project_root)

    assert result["blocking_count"] == 0
    assert result["warning_count"] == 0
    assert "REQ-001" not in result["detail"]


def test_bp_application_checks_test_verification_status(project_root: Path):
    _bp(project_root, verification_method="test")
    _write_artifact(
        project_root,
        "REQ-001",
        "requirement",
        links=[
            {"target": "BP-001", "role": "guided_by"},
            {"target": "UT-001", "role": "verified_by"},
        ],
    )
    _write_artifact(project_root, "UT-001", "unit-test", status="implemented")

    result = _bp_application(project_root)

    assert result["warning_count"] == 1
    assert "UT-001" in result["detail"]
    assert "not verified" in result["detail"]

    _write_artifact(project_root, "UT-001", "unit-test", status="verified")
    passed = _bp_application(project_root)
    assert passed["warning_count"] == 0
    assert passed["blocking_count"] == 0


@pytest.mark.parametrize(
    "dec_status,create_dec,expected_warnings",
    [("draft", True, 1), ("approved", True, 0), (None, False, 1)],
)
def test_dropped_practice_requires_an_approved_dec(
    project_root: Path,
    dec_status: str | None,
    create_dec: bool,
    expected_warnings: int,
):
    _bp(
        project_root,
        tailoring={"status": "dropped", "rationale": "Out of scope", "dec": "DEC-001"},
    )
    if create_dec:
        _write_artifact(
            project_root, "DEC-001", "decision", status=dec_status or "draft"
        )

    result = _bp_application(project_root)

    assert result["warning_count"] == expected_warnings
    assert result["blocking_count"] == 0
    if expected_warnings:
        assert "tailoring DEC" in result["detail"] or "missing DEC" in result["detail"]


def test_verification_prose_is_advisory_not_a_compiled_predicate(project_root: Path):
    bp_path = _bp(project_root)
    bp = art_lib.parse_artifact(bp_path)
    bp.body = bp.body.replace(
        "Inspect the result.", "If GALAXY is absent, reject the artifact."
    )
    bp_path.write_text(
        f"---\n{yaml.safe_dump(bp.frontmatter, sort_keys=False)}---\n\n{bp.body}\n",
        encoding="utf-8",
    )
    _write_artifact(
        project_root,
        "REQ-001",
        "requirement",
        links=[{"target": "BP-001", "role": "guided_by"}],
    )

    result = _bp_application(project_root)

    assert result["warning_count"] == 0
    assert result["blocking_count"] == 0
    assert "advisory inspection item (not compiled)" in result["detail"]
    assert "If GALAXY is absent, reject the artifact." in result["detail"]
