"""STORY-740 / REQ-067 OBL-3: the PREV compound loop.

DEF closure seeds a PREV with matchable tags (DEF ∪ fails_to_meet REQ tags,
minus release tags) and names an empty result as inert; `patterns update` /
`patterns retire` repair and retire learned patterns through the CLI;
project-audit reports inert PREVs as `prev/inert` accounting rows; brief shows
"PREV N (M inert)".
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow import cli
from specflow.commands import project_audit as audit_cmd
from specflow.core.findings import from_audit_dict
from specflow.lib import artifacts as art_lib
from specflow.lib import learning as learn_lib
from specflow.lib.checklists import assemble_checklist


@pytest.fixture
def project(tmp_path: Path, monkeypatch, capsys) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.chdir(root)
    assert cli.main(["init", "--platform", "claude-code", "--no-ci"]) == 0
    capsys.readouterr()
    return root


def _close_def(def_id: str) -> None:
    for status in ("fixing", "verified", "closed"):
        assert cli.main(["update", def_id, "--status", status]) == 0


def _learned(root: Path, pattern_id: str) -> dict:
    path = root / ".specflow" / "checklists" / "learned" / f"{pattern_id}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _seed_untagged_prev(root: Path) -> str:
    """An inert PREV through the blessed persistence path (no hand-written YAML)."""
    pattern = {
        "id": "", "name": "legacy", "discovered_from": "DEF-999", "mode": "reactive",
        "pattern": "legacy", "applies_to": {"tags": []},
        "items": [{"id": "", "check": "legacy check", "severity": "warning",
                   "automated": False, "mode": "reactive"}],
    }
    return learn_lib.persist_prevention_pattern(root, pattern).stem


class TestTagInheritanceOnClosure:
    def test_def_and_req_tags_union_without_release_tags(self, project: Path, capsys):
        """AC1: DEF `cli,v1.17.5` fails_to_meet REQ `core` → PREV tags cli+core, no v1.17.5."""
        assert cli.main(["create", "--type", "requirement", "--title", "Core req", "--tags", "core"]) == 0
        assert cli.main(["create", "--type", "defect", "--title", "Bug", "--tags", "cli,v1.17.5",
                         "--add-link", "REQ-001:fails_to_meet"]) == 0
        capsys.readouterr()
        _close_def("DEF-001")
        out = capsys.readouterr().out
        tags = _learned(project, "PREV-001")["applies_to"]["tags"]
        assert tags == ["cli", "core"]
        assert "v1.17.5" not in tags
        assert "inert" not in out

    def test_empty_tags_warns_inert_with_repair_command(self, project: Path, capsys):
        """AC2: no DEF/REQ tags → stdout names the PREV inert + the repair command."""
        assert cli.main(["create", "--type", "defect", "--title", "Untagged bug"]) == 0
        capsys.readouterr()
        _close_def("DEF-001")
        out = capsys.readouterr().out
        assert "PREV-001 is inert" in out
        assert "specflow patterns update PREV-001 --tags <a,b>" in out
        assert _learned(project, "PREV-001")["applies_to"]["tags"] == []

    def test_inherited_tags_dedupes_in_order_and_drops_release_tags(self, project: Path):
        art_lib.create_artifact(project, "requirement", title="R", status="draft", body="b",
                                tags=["core", "v1.13", "cli"])
        created = art_lib.create_artifact(
            project, "defect", title="t", status="open", body="b",
            tags=["cli", "v2", "robustness"],
            links=[{"target": "REQ-001", "role": "fails_to_meet"},
                   {"target": "REQ-001", "role": "exposed_by"}],
        )
        defect = art_lib.parse_artifact(Path(created["path"]))
        assert learn_lib.inherited_tags(project, defect) == ["cli", "robustness", "core"]


class TestPatternsUpdateRetire:
    def test_update_sets_exact_tags_and_checklist_run_assembles_it(self, project: Path, capsys):
        """AC3/AC6: update → YAML carries exactly those tags; checklist-run on a `core`
        artifact assembles learned/PREV-* and the PREV's item."""
        pid = _seed_untagged_prev(project)
        assert cli.main(["create", "--type", "requirement", "--title", "Core req", "--tags", "core"]) == 0
        capsys.readouterr()
        assert cli.main(["patterns", "update", pid, "--tags", "core,review"]) == 0
        assert _learned(project, pid)["applies_to"]["tags"] == ["core", "review"]
        capsys.readouterr()
        cli.main(["checklist-run", "REQ-001"])
        out = capsys.readouterr().out
        assert "learned/PREV-*" in out
        req = art_lib.parse_artifact(art_lib.resolve_link_target(project, "REQ-001"))
        assert f"{pid}-01" in {i.id for i in assemble_checklist(project, req).items}

    def test_retire_removes_from_list_and_assembly(self, project: Path, capsys):
        """AC4: retired → absent from `patterns list` and checklist assembly; show still finds it."""
        pid = _seed_untagged_prev(project)
        assert cli.main(["create", "--type", "requirement", "--title", "Core req", "--tags", "core"]) == 0
        assert cli.main(["patterns", "update", pid, "--tags", "core"]) == 0
        assert cli.main(["patterns", "retire", pid]) == 0
        assert _learned(project, pid)["retired"] is True
        capsys.readouterr()
        assert cli.main(["patterns", "list"]) == 0
        assert pid not in capsys.readouterr().out
        req = art_lib.parse_artifact(art_lib.resolve_link_target(project, "REQ-001"))
        assembled = assemble_checklist(project, req)
        assert f"{pid}-01" not in {i.id for i in assembled.items}
        assert "learned/PREV-*" not in assembled.sources
        assert cli.main(["patterns", "show", pid]) == 0
        # The retired file keeps its number: the next PREV never reuses it.
        assert _seed_untagged_prev(project) != pid

    @pytest.mark.parametrize("argv", [
        ["patterns", "update", "PREV-404", "--tags", "core"],      # unknown id
        ["patterns", "update", "../config", "--tags", "core"],     # not a PREV id
        ["patterns", "retire", "PREV-404"],
    ])
    def test_bad_ids_exit_1(self, project: Path, argv, capsys):
        assert cli.main(argv) == 1
        assert "error:" in capsys.readouterr().err

    def test_empty_tag_list_is_rejected(self, project: Path, capsys):
        pid = _seed_untagged_prev(project)
        assert cli.main(["patterns", "update", pid, "--tags", " , "]) == 1
        assert _learned(project, pid)["applies_to"]["tags"] == []

    def test_list_marks_inert_patterns(self, project: Path, capsys):
        pid = _seed_untagged_prev(project)
        assert cli.main(["patterns", "list"]) == 0
        assert f"inert; repair: specflow patterns update {pid}" in capsys.readouterr().out


class TestPrevInertAuditAndBrief:
    def test_lens_emits_one_accounting_row_per_inert_prev(self, project: Path):
        """AC5: one prev/inert warn, classified accounting, never escalating."""
        pid = _seed_untagged_prev(project)
        tagged = _seed_untagged_prev(project)
        learn_lib.update_pattern_tags(project, tagged, ["core"])
        retired = _seed_untagged_prev(project)
        learn_lib.retire_pattern(project, retired)
        findings = audit_cmd._prev_inert_lens(project)
        assert len(findings) == 1
        assert findings[0]["message"].startswith(f"{pid}:")
        assert "prev/inert" in audit_cmd._ACCOUNTING_CONCERNS
        typed = from_audit_dict(findings[0])
        assert typed.rule_id == "audit/prev/inert" and typed.klass == "accounting"
        assert typed.subjects == (pid,)
        assert audit_cmd._count_warns(findings) == (0, 1)

    def test_project_audit_row_appears_exit_unchanged_and_clears_after_repair(
        self, project: Path, capsys,
    ):
        """AC5 + cache: the row shows, the exit code matches the no-PREV run, and a
        `patterns update` repair clears the row even when a cache was written with it."""
        assert cli.main(["create", "--type", "requirement", "--title", "Core req", "--tags", "core"]) == 0
        capsys.readouterr()
        rc_clean = cli.main(["project-audit", "--dry-run"])
        assert "(prev/inert)" not in capsys.readouterr().out
        pid = _seed_untagged_prev(project)
        rc_inert = cli.main(["project-audit", "--dry-run"])
        out = capsys.readouterr().out
        assert out.count("(prev/inert)") == 1 and f"(prev/inert) {pid}:" in out
        assert rc_inert == rc_clean
        # A full run writes the findings cache WITH the row ...
        assert cli.main(["project-audit"]) == rc_clean
        capsys.readouterr()
        assert cli.main(["project-audit", "--dry-run"]) == rc_clean
        assert "Using cached findings" in capsys.readouterr().out
        # ... and the CLI repair changes the key (learned PREVs are a cache input).
        assert cli.main(["patterns", "update", pid, "--tags", "core"]) == 0
        capsys.readouterr()
        cli.main(["project-audit", "--dry-run"])
        out = capsys.readouterr().out
        assert "Using cached findings" not in out
        assert "(prev/inert)" not in out

    def test_brief_knowledge_line_counts_inert(self, project: Path, capsys):
        """AC7 (brief half): "PREV N (M inert)"."""
        _seed_untagged_prev(project)
        tagged = _seed_untagged_prev(project)
        learn_lib.update_pattern_tags(project, tagged, ["core"])
        capsys.readouterr()
        assert cli.main(["brief"]) == 0
        assert "PREV 2 (1 inert)" in capsys.readouterr().out
