"""Tests for the shared CHL creation module (specflow.lib.challenges)."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.lib import artifacts as art_lib
from specflow.lib import challenges as chl_lib
from specflow.lib.techniques import TechniqueFinding


def _bootstrap_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    pkg_schemas = Path(__file__).parent.parent / "src" / "specflow" / "templates" / "schemas"
    for name in ("requirement.yaml", "challenge.yaml", "review.yaml"):
        src = pkg_schemas / name
        assert src.exists(), f"missing template schema: {src}"
        (schema_dir / name).write_text(src.read_text(), encoding="utf-8")

    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({
            "project": {"name": "test", "created": "2026-01-01"},
            "artifact_types": ["requirement", "challenge", "review"],
        }),
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "verifying", "history": []}),
        encoding="utf-8",
    )

    for sub in ("requirements", "challenges", "reviews"):
        d = root / "_specflow" / "specs" / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / "_index.yaml").write_text("artifacts: {}\nnext_id: 1\n", encoding="utf-8")

    return root


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return _bootstrap_project(tmp_path)


def _make_target_req(root: Path) -> art_lib.Artifact:
    target = art_lib.create_artifact(
        root,
        artifact_type="requirement",
        title="Sample REQ",
        body="Some body content for review.",
    )
    assert target.get("ok"), target
    arts = art_lib.discover_artifacts(root)
    return next(a for a in arts if a.id == target["id"])


class TestCreateChlArtifacts:
    def test_creates_chl_for_warn_and_error(self, project_root: Path):
        target = _make_target_req(project_root)
        findings = [
            TechniqueFinding(
                title="Acceptance criteria missing measurability",
                rationale="No measurable threshold provided.",
                severity="warn",
                technique="checklist-run",
                target_id=target.id,
            ),
            TechniqueFinding(
                title="Premortem: silent data corruption",
                rationale="Premortem flagged silent data corruption path.",
                severity="error",
                technique="premortem",
                target_id=target.id,
            ),
        ]
        created = chl_lib.create_chl_artifacts(project_root, findings, target.id)
        assert len(created) == 2
        assert {c["severity"] for c in created} == {"warn", "error"}

    def test_body_table_written_to_chl(self, project_root: Path):
        # The audit batches grouped findings into one CHL whose body is a
        # markdown table (was previously an empty body with a truncated title).
        target = _make_target_req(project_root)
        table = (
            "| Scope | Severity | Finding |\n|---|---|---|\n"
            "| story | warn | no acceptance criteria |\n"
        )
        findings = [
            TechniqueFinding(
                title="3 horizontal/story audit finding(s)",
                rationale="3 warn finding(s) under horizontal/story",
                severity="warn",
                technique="audit-horizontal",
                target_id=target.id,
                body=table,
            ),
        ]
        created = chl_lib.create_chl_artifacts(project_root, findings, target.id)
        assert len(created) == 1
        chl = next(
            a for a in art_lib.discover_artifacts(project_root, artifact_type="challenge")
            if a.id == created[0]["id"]
        )
        assert "| Scope |" in chl.body
        assert "no acceptance criteria" in chl.body

    def test_skips_info_findings(self, project_root: Path):
        target = _make_target_req(project_root)
        findings = [
            TechniqueFinding(
                title="Just an FYI",
                rationale="info-level",
                severity="info",
                technique="checklist-run",
                target_id=target.id,
            ),
        ]
        created = chl_lib.create_chl_artifacts(project_root, findings, target.id)
        assert len(created) == 0

    def test_dedup_skips_existing_title(self, project_root: Path):
        target = _make_target_req(project_root)
        findings = [
            TechniqueFinding(
                title="Duplicate finding",
                rationale="first",
                severity="warn",
                technique="checklist-run",
                target_id=target.id,
            ),
        ]
        chl_lib.create_chl_artifacts(project_root, findings, target.id, dedup=True)
        second = chl_lib.create_chl_artifacts(project_root, findings, target.id, dedup=True)
        assert len(second) == 0

    def test_link_role_refers_to(self, project_root: Path):
        target = _make_target_req(project_root)
        findings = [
            TechniqueFinding(
                title="Audit finding",
                rationale="rationale",
                severity="warn",
                technique="project-audit",
                target_id=target.id,
            ),
        ]
        created = chl_lib.create_chl_artifacts(
            project_root, findings, target.id, link_role="refers_to",
        )
        assert len(created) == 1
        chl = art_lib.discover_artifacts(project_root, artifact_type="challenge")
        assert len(chl) == 1
        roles = {link.role for link in chl[0].links}
        assert "refers_to" in roles

    def test_technique_override(self, project_root: Path):
        target = _make_target_req(project_root)
        findings = [
            TechniqueFinding(
                title="Some finding",
                rationale="reason",
                severity="warn",
                technique="checklist-run",
                target_id=target.id,
            ),
        ]
        created = chl_lib.create_chl_artifacts(
            project_root, findings, target.id,
            technique_override="project-audit",
        )
        assert created[0]["technique"] == "project-audit"

    def test_review_backlink(self, project_root: Path):
        target = _make_target_req(project_root)
        review = art_lib.create_artifact(
            root=project_root,
            artifact_type="review",
            title="Test review",
            status="open",
            links=[{"target": target.id, "role": "review_of"}],
        )
        assert review.get("ok")
        findings = [
            TechniqueFinding(
                title="Finding with review",
                rationale="reason",
                severity="warn",
                technique="checklist-run",
                target_id=target.id,
            ),
        ]
        created = chl_lib.create_chl_artifacts(
            project_root, findings, target.id, review_id=review["id"],
        )
        assert len(created) == 1
        chl = art_lib.discover_artifacts(project_root, artifact_type="challenge")
        link_targets = {(link.target, link.role) for link in chl[0].links}
        assert (review["id"], "refers_to") in link_targets
