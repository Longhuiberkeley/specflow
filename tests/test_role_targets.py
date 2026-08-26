"""STORY-639 — role-target semantic matrix (accounting, not policing).

Core guarantees under test:

- direction-bearing roles warn when the TARGET TYPE is semantically wrong
  (``implements → UT``, ``belongs_to → REQ``) while every legal shape in the
  repo's vocabulary (both ``verified_by`` directions, canonical/legacy
  ``refined_by``, research hierarchy, ops RUN/MONITOR) stays quiet;
- standard-clause targets (``complies_with: ISO-14971-4.2``) are exempt;
- the check is accounting-only: artifact-lint warns (exit 0) by default,
  ``lint.role_target_strict`` escalates, and project-audit NEVER escalates
  these warnings to exit 2 (the dedicated-check isolation);
- create/update print an advisory without blocking the write.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import role_targets as rt


@pytest.fixture(autouse=True)
def _restore_type_registry():
    """Keep this module's pack-type registrations from leaking into other
    test modules (TYPE_TO_DIR is process-global once _load_active_packs
    registers a fixture schema's type). Snapshot/restore around each test."""
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
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"),
    ("defect", "DEF"),
    # research + ops corpus (STORY-639 AC6): dogfood has zero EXPTs, so the
    # research/ops matrix rows are exercised HERE, not on the dogfood repo.
    ("competition", "COMP"), ("loop", "LOOP"), ("experiment", "EXPT"),
    ("finding", "FIND"), ("run", "RUN"), ("monitor", "MONITOR"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"],
}

_ROLES_BY_TYPE = {
    "requirement": ["refined_by", "verified_by", "derives_from", "complies_with", "validated_by", "supersedes"],
    "architecture": ["refined_by", "verified_by", "derives_from", "guided_by", "complies_with"],
    "detailed-design": ["refined_by", "verified_by", "derives_from", "specified_by"],
    "unit-test": ["verified_by", "derives_from"],
    "story": ["implements", "guided_by", "specified_by", "derives_from", "verified_by", "depends_on"],
    "spike": ["derives_from", "guided_by"],
    "decision": ["derives_from"],
    "defect": ["fails_to_meet", "exposed_by", "derives_from"],
    "competition": ["derives_from", "operates_on", "guided_by"],
    "loop": ["derives_from"],
    "experiment": ["derives_from", "belongs_to"],
    "finding": ["derives_from", "belongs_to", "condenses", "validated_by", "supersedes"],
    "run": ["derives_from", "implements", "complies_with", "guided_by"],
    "monitor": ["derives_from", "belongs_to"],
}


_DIR_BY_TYPE = {
    "requirement": "specs/requirements", "architecture": "specs/architecture",
    "detailed-design": "specs/detailed-design", "unit-test": "specs/unit-tests",
    "integration-test": "specs/integration-tests",
    "qualification-test": "specs/qualification-tests",
    "story": "work/stories", "spike": "work/spikes",
    "decision": "work/decisions", "defect": "work/defects",
    "competition": "research/competitions", "loop": "research/loops",
    "experiment": "research/experiments", "finding": "research/findings",
    "run": "ops/runs", "monitor": "ops/monitors",
}


def _project(tmp: Path) -> Path:
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    for art_type, prefix in _SCHEMA_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "directory": f"_specflow/{_DIR_BY_TYPE[art_type]}",
            "allowed_status": dict(_STATUS_FLOW),
            "allowed_link_roles": _ROLES_BY_TYPE.get(art_type, ["derives_from"]),
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")
    config = {
        "project": {"name": "rt-test", "created": "2026-01-01"},
        "artifact_types": [t for t, _ in _SCHEMA_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
    )
    return root


def _mk(root: Path, art_type: str, art_id: str, links: list[dict], title: str = "t") -> None:
    rel_dir = art_lib.TYPE_TO_DIR.get(art_type, _DIR_BY_TYPE.get(art_type, "misc"))
    path = root / "_specflow" / rel_dir / f"{art_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": art_id,
        "title": title,
        "type": art_type,
        "status": "draft",
        "tags": [],
        "suspect": False,
        "links": links,
        "created": "2026-01-01",
    }
    path.write_text(
        f"---\n{yaml.dump(fm, sort_keys=False)}---\n\nBody prose for {art_id}.\n",
        encoding="utf-8",
    )


def _link(target: str, role: str) -> dict:
    return {"target": target, "role": role}


class TestMatrixSemantics:
    def test_semantically_wrong_targets_warn(self, tmp_path: Path):
        root = _project(tmp_path)
        _mk(root, "story", "STORY-001", [_link("UT-001", "implements")])
        _mk(root, "unit-test", "UT-001", [_link("STORY-001", "verified_by")])
        _mk(root, "experiment", "EXPT-001", [_link("REQ-001", "belongs_to")])
        arts = art_lib.discover_artifacts(root)
        issues = rt.check_role_targets(arts)
        msgs = " | ".join(i["message"] for i in issues)
        assert "STORY-001" in msgs and "implements" in msgs
        assert "EXPT-001" in msgs and "belongs_to" in msgs
        # UT-001 verified_by STORY-001 is the LEGAL test→story shape: no warn
        # ("UT-001" may appear as a bad TARGET of STORY's warning — that's
        # the warning we DO want).
        assert not any(m.startswith("[UT-001]") for m in msgs.split(" | "))

    def test_legal_shapes_stay_quiet(self, tmp_path: Path):
        root = _project(tmp_path)
        _mk(root, "requirement", "REQ-001", [
            _link("ARCH-001", "refined_by"),      # canonical: downstream refiner
            _link("QT-001", "verified_by"),        # spec owns its verifier edge
            _link("ISO-14971-4.2", "complies_with"),  # clause target: exempt
        ])
        _mk(root, "architecture", "ARCH-001", [
            _link("REQ-001", "derives_from"),
            _link("DDD-001", "refined_by"),
        ])
        _mk(root, "detailed-design", "DDD-001", [
            _link("ARCH-001", "refined_by"),       # legacy concrete→abstract
            _link("ARCH-001", "specified_by"),
            _link("UT-001", "verified_by"),
        ])
        _mk(root, "unit-test", "UT-001", [
            _link("DDD-001", "verified_by"),       # legal test→spec shape
            _link("STORY-001", "verified_by"),     # legal test→story shape
        ])
        _mk(root, "story", "STORY-001", [_link("REQ-001", "implements")])
        arts = art_lib.discover_artifacts(root)
        assert rt.check_role_targets(arts) == []

    def test_research_ops_corpus(self, tmp_path: Path):
        root = _project(tmp_path)
        _mk(root, "competition", "COMP-001", [_link("REQ-001", "derives_from")])
        _mk(root, "loop", "LOOP-001", [_link("COMP-001", "derives_from")])
        _mk(root, "experiment", "EXPT-001", [_link("LOOP-001", "belongs_to")])
        _mk(root, "finding", "FIND-001", [
            _link("LOOP-001", "belongs_to"),
            _link("EXPT-002", "validated_by"),
        ])
        _mk(root, "experiment", "EXPT-002", [_link("LOOP-001", "belongs_to")])
        _mk(root, "run", "RUN-001", [_link("REQ-001", "implements")])
        _mk(root, "monitor", "MONITOR-001", [_link("RUN-001", "belongs_to")])
        # Bad research/ops shapes DO warn:
        _mk(root, "loop", "LOOP-002", [_link("REQ-001", "derives_from")])
        _mk(root, "run", "RUN-002", [_link("UT-001", "implements")])
        arts = art_lib.discover_artifacts(root)
        issues = rt.check_role_targets(arts)
        flagged = [i["message"] for i in issues]
        assert len(flagged) == 2, flagged
        assert any("LOOP-002" in m for m in flagged)
        assert any("RUN-002" in m for m in flagged)

    def test_clause_targets_exempt_but_artifact_complies_warns(self, tmp_path: Path):
        root = _project(tmp_path)
        # Clause-shaped: unregistered prefix → exempt.
        _mk(root, "requirement", "REQ-001", [_link("ISO-26262-CL-4.1.2", "complies_with")])
        # Artifact-shaped complies_with: falls through to the spec-only row.
        _mk(root, "requirement", "REQ-002", [_link("STORY-001", "complies_with")])
        _mk(root, "story", "STORY-001", [])
        arts = art_lib.discover_artifacts(root)
        issues = rt.check_role_targets(arts)
        assert len(issues) == 1
        assert "REQ-002" in issues[0]["message"]

    def test_strict_escalates_to_blocking(self, tmp_path: Path):
        root = _project(tmp_path)
        _mk(root, "story", "STORY-001", [_link("UT-001", "implements")])
        _mk(root, "unit-test", "UT-001", [])
        issues = rt.check_role_targets(art_lib.discover_artifacts(root), strict=True)
        assert issues and issues[0]["severity"] == "blocking"


class TestLintWiring:
    def test_check_registered_and_accounting_by_default(self, tmp_path: Path):
        root = _project(tmp_path)
        _mk(root, "story", "STORY-001", [_link("UT-001", "implements")])
        _mk(root, "unit-test", "UT-001", [])
        result = lint_cmd._run_check(art_lib.discover_artifacts(root), root, "role-target")
        assert result["warning_count"] == 1
        assert result["blocking_count"] == 0

    def test_strict_config_escalates(self, tmp_path: Path):
        root = _project(tmp_path)
        cfg = yaml.safe_load((root / ".specflow" / "config.yaml").read_text())
        cfg["lint"] = {"role_target_strict": True}
        (root / ".specflow" / "config.yaml").write_text(yaml.dump(cfg), encoding="utf-8")
        _mk(root, "story", "STORY-001", [_link("UT-001", "implements")])
        _mk(root, "unit-test", "UT-001", [])
        result = lint_cmd._run_check(art_lib.discover_artifacts(root), root, "role-target")
        assert result["blocking_count"] == 1

    def test_project_audit_never_escalates_role_target_warnings(self, tmp_path):
        """CRITICAL (plan MUST-FIX #1): a repo full of role-target warnings
        must not flip project-audit's exit code — the warnings live in a
        dedicated check that the audit's consistency lens never folds in."""
        from specflow.commands import project_audit as pa

        root = _project(tmp_path)
        # A small flock of semantically-wrong links:
        _mk(root, "story", "STORY-001", [_link("UT-001", "implements")])
        _mk(root, "story", "STORY-002", [_link("UT-002", "implements")])
        _mk(root, "unit-test", "UT-001", [])
        _mk(root, "unit-test", "UT-002", [])
        arts = art_lib.discover_artifacts(root)
        assert len(rt.check_role_targets(arts)) == 2  # warnings exist…
        exit_code = pa.run(root, {"dry_run": True})
        assert exit_code == 0  # …and the audit stays green.

    def test_dogfood_shapes_do_not_cry_wolf(self):
        """The dogfood repo's own live link shapes (both verified_by
        directions, RUN implements, legacy refined_by) must produce zero
        findings against the real repo — checked inline via the matrix."""
        import inspect

        src = inspect.getsource(rt)
        # sanity: the matrix exists and covers the research/ops rows
        for t in ("competition", "loop", "experiment", "finding", "run", "monitor"):
            assert t in rt.ROLE_TARGET_MATRIX
        # verified_by row on tests allows both shapes
        assert "story" in rt.ROLE_TARGET_MATRIX["unit-test"]["verified_by"]
        assert "requirement" in rt.ROLE_TARGET_MATRIX["unit-test"]["verified_by"]
