"""Tests for spec supersession on requirement/architecture/detailed-design.

Context: the frozen D-18 link vocabulary already includes ``supersedes`` and the
``superseded`` status for decision (DEC) and best-practice (BP) schemas. This
extends the *same* additive pairing to requirement (REQ), architecture (ARCH),
and detailed-design (DDD): a new artifact links ``supersedes`` -> the old one,
then the old one's status moves to ``superseded``. The link vocabulary itself is
unchanged — no new role was added, only new schemas were granted access to the
existing ``supersedes`` role and ``superseded`` status.

The fixture below copies the REAL shipped schema YAMLs (the same files a fresh
``specflow init`` would install) into a tmp project's ``.specflow/schema/`` dir,
so these tests exercise the actual edited schemas rather than a hand-rolled
duplicate that could silently drift from the shipped ones.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from specflow.commands import create as create_cmd
from specflow.commands import update as update_cmd
from specflow.lib import artifacts as art_lib

_SHIPPED_SCHEMA_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "specflow"
    / "templates"
    / "schemas"
)

_SCHEMA_TYPES = ["requirement", "architecture", "detailed-design"]


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    for art_type in _SCHEMA_TYPES:
        shutil.copy(
            _SHIPPED_SCHEMA_DIR / f"{art_type}.yaml",
            schema_dir / f"{art_type}.yaml",
        )

    for rel_dir in [
        "_specflow/specs/requirements",
        "_specflow/specs/architecture",
        "_specflow/specs/detailed-design",
    ]:
        (root / rel_dir).mkdir(parents=True, exist_ok=True)

    return root


def _create_args(**overrides) -> dict:
    args = {
        "type": "requirement",
        "title": "A requirement",
        "status": "draft",
        "priority": None,
        "rationale": None,
        "tags": None,
        "links": None,
        "body": "The system shall do X.",
        "from_standard": None,
        "force": False,
        "skip_dedup_check": True,
        "nfr_category": None,
        "set_fields": None,
    }
    args.update(overrides)
    return args


def _update_args(artifact_id: str, status: str) -> dict:
    return {
        "artifact_id": artifact_id,
        "status": status,
        "set_fields": None,
        "priority": None,
        "rationale": None,
        "tags": None,
        "title": None,
        "output_files": None,
        "thinking_techniques": None,
    }


def _artifact(root: Path, artifact_type: str, artifact_id: str) -> art_lib.Artifact:
    artifacts = art_lib.discover_artifacts(root, artifact_type=artifact_type)
    match = [a for a in artifacts if a.id == artifact_id]
    assert len(match) == 1, f"{artifact_id} not found among {[a.id for a in artifacts]}"
    return match[0]


class TestRequirementSupersession:
    def test_approved_to_superseded_succeeds(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(status="draft"))
        assert rc == 0
        rc = update_cmd.run(project_root, _update_args("REQ-001", "approved"))
        assert rc == 0

        rc = update_cmd.run(project_root, _update_args("REQ-001", "superseded"))
        assert rc == 0
        art = _artifact(project_root, "requirement", "REQ-001")
        assert art.status == "superseded"

    def test_draft_to_superseded_rejected(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _create_args(status="draft"))
        assert rc == 0

        rc = update_cmd.run(project_root, _update_args("REQ-001", "superseded"))
        assert rc == 1
        out = capsys.readouterr().out
        assert "Cannot transition" in out

        art = _artifact(project_root, "requirement", "REQ-001")
        assert art.status == "draft"

    def test_new_requirement_supersedes_link_survives(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(status="draft"))
        assert rc == 0
        rc = update_cmd.run(project_root, _update_args("REQ-001", "approved"))
        assert rc == 0

        rc = create_cmd.run(project_root, _create_args(
            title="Replacement requirement",
            links='[{"target":"REQ-001","role":"supersedes"}]',
        ))
        assert rc == 0

        successor = _artifact(project_root, "requirement", "REQ-002")
        assert any(l.target == "REQ-001" and l.role == "supersedes" for l in successor.links)

        rc = update_cmd.run(project_root, _update_args("REQ-001", "superseded"))
        assert rc == 0
        predecessor = _artifact(project_root, "requirement", "REQ-001")
        assert predecessor.status == "superseded"


class TestArchitectureSupersession:
    def test_supersedes_link_and_status_transition(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(
            type="architecture", title="Old architecture", status="draft",
        ))
        assert rc == 0
        rc = update_cmd.run(project_root, _update_args("ARCH-001", "approved"))
        assert rc == 0

        rc = create_cmd.run(project_root, _create_args(
            type="architecture",
            title="New architecture",
            links='[{"target":"ARCH-001","role":"supersedes"}]',
        ))
        assert rc == 0
        successor = _artifact(project_root, "architecture", "ARCH-002")
        assert any(l.target == "ARCH-001" and l.role == "supersedes" for l in successor.links)

        rc = update_cmd.run(project_root, _update_args("ARCH-001", "superseded"))
        assert rc == 0
        predecessor = _artifact(project_root, "architecture", "ARCH-001")
        assert predecessor.status == "superseded"

    def test_draft_to_superseded_rejected(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(
            type="architecture", title="Draft architecture", status="draft",
        ))
        assert rc == 0
        rc = update_cmd.run(project_root, _update_args("ARCH-001", "superseded"))
        assert rc == 1
        art = _artifact(project_root, "architecture", "ARCH-001")
        assert art.status == "draft"


class TestDetailedDesignSupersession:
    def test_supersedes_link_and_status_transition(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(
            type="detailed-design", title="Old design", status="draft",
        ))
        assert rc == 0
        rc = update_cmd.run(project_root, _update_args("DDD-001", "approved"))
        assert rc == 0

        rc = create_cmd.run(project_root, _create_args(
            type="detailed-design",
            title="New design",
            links='[{"target":"DDD-001","role":"supersedes"}]',
        ))
        assert rc == 0
        successor = _artifact(project_root, "detailed-design", "DDD-002")
        assert any(l.target == "DDD-001" and l.role == "supersedes" for l in successor.links)

        rc = update_cmd.run(project_root, _update_args("DDD-001", "superseded"))
        assert rc == 0
        predecessor = _artifact(project_root, "detailed-design", "DDD-001")
        assert predecessor.status == "superseded"

    def test_draft_to_superseded_rejected(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(
            type="detailed-design", title="Draft design", status="draft",
        ))
        assert rc == 0
        rc = update_cmd.run(project_root, _update_args("DDD-001", "superseded"))
        assert rc == 1
        art = _artifact(project_root, "detailed-design", "DDD-001")
        assert art.status == "draft"


class TestOtherTransitionsIntoSupersededStillWork:
    """Sanity: implemented/verified predecessors can also be superseded (not just approved)."""

    def test_implemented_to_superseded_succeeds(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(status="draft"))
        assert rc == 0
        rc = update_cmd.run(project_root, _update_args("REQ-001", "approved"))
        assert rc == 0
        rc = update_cmd.run(project_root, _update_args("REQ-001", "implemented"))
        assert rc == 0

        rc = update_cmd.run(project_root, _update_args("REQ-001", "superseded"))
        assert rc == 0
        art = _artifact(project_root, "requirement", "REQ-001")
        assert art.status == "superseded"
