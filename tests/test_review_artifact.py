"""Tests for the REVIEW artifact type and review-pass emission."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import artifact_review as review_cmd
from specflow.commands import status as status_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib.techniques import TechniqueFinding


def _bootstrap_project(tmp_path: Path) -> Path:
    """Set up a minimal project layout that supports CHL + REVIEW emission."""
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


class TestEmitReviewPass:
    def test_no_actionable_findings_skips_emission(self, project_root: Path):
        target = _make_target_req(project_root)
        info_only = [TechniqueFinding(
            title="Just an FYI",
            rationale="info-level",
            severity="info",
            technique="checklist-run",
            target_id=target.id,
        )]
        outcome = review_cmd.emit_review_pass(project_root, target, info_only, depth="normal")
        assert outcome["ok"] is False
        assert outcome["review_id"] == ""

    def test_review_emitted_with_chl_backlinks(self, project_root: Path):
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
        outcome = review_cmd.emit_review_pass(project_root, target, findings, depth="deep")
        assert outcome["ok"] is True
        review_id = outcome["review_id"]
        assert review_id.startswith("REVIEW-")
        assert len(outcome["chl_ids"]) == 2

        all_arts = art_lib.discover_artifacts(project_root)
        review = next((a for a in all_arts if a.id == review_id), None)
        assert review is not None, "REVIEW artifact not discoverable"
        assert review.type == "review"
        assert review.status == "open"

        review_link_targets = {(link.target, link.role) for link in review.links}
        assert (target.id, "review_of") in review_link_targets

        for chl_id in outcome["chl_ids"]:
            chl = next((a for a in all_arts if a.id == chl_id), None)
            assert chl is not None
            chl_pairs = {(link.target, link.role) for link in chl.links}
            assert (review_id, "refers_to") in chl_pairs, (
                f"CHL {chl_id} missing refers_to backlink to {review_id}"
            )
            assert (target.id, "challenges") in chl_pairs

        findings_summary = review.frontmatter.get("findings", [])
        assert isinstance(findings_summary, list) and len(findings_summary) == 2
        chl_refs = {f["chl_ref"] for f in findings_summary}
        assert chl_refs == set(outcome["chl_ids"])


class TestStatusCountsReview:
    def test_review_counted_in_status(self, project_root: Path):
        target = _make_target_req(project_root)
        review_cmd.emit_review_pass(
            project_root,
            target,
            [TechniqueFinding(
                title="A finding",
                rationale="why",
                severity="warn",
                technique="checklist-run",
                target_id=target.id,
            )],
            depth="normal",
        )
        rc = status_cmd.run(project_root, {})
        assert rc == 0

        artifacts = art_lib.discover_artifacts(project_root)
        counts = status_cmd._count_by_type(artifacts)
        assert counts.get("REVIEW", 0) == 1
        assert counts.get("CHL", 0) == 1


class TestReviewSchemaRegistered:
    def test_review_type_in_type_to_dir(self):
        assert art_lib.TYPE_TO_DIR.get("review") == "specs/reviews"
        assert art_lib.PREFIX_TO_TYPE.get("REVIEW") == "review"
        assert art_lib.TYPE_TO_PREFIX.get("review") == "REVIEW"
