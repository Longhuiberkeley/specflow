"""artifact-lint rendering (STORY-716 AC3, F-005/F-026/F-085): with a
baseline the default view prints `N known (baselined), M new` per check and
lists only the new lines; surveys collapse to one line; `--verbose` restores
every line; exit codes never depend on the view."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import findings_baseline
from specflow.commands import init as init_cmd

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI.sub("", text)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    return root


def _story(root: Path, sid: str, links: list[dict] | None = None, status: str = "draft") -> None:
    fm = {"id": sid, "title": sid, "type": "story", "status": status,
          "created": "2026-10-01", "links": links or []}
    path = root / "_specflow" / "work" / "stories" / f"{sid}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "## Acceptance Criteria\n\n1. Given a\n2. Then b"
    path.write_text(f"---\n{yaml.safe_dump(fm, sort_keys=False)}---\n\n{body}\n", encoding="utf-8")


def _update_baseline(root: Path, **args) -> int:
    return findings_baseline.run(root, {"findings_baseline_subcommand": "update", **args})


def _line(out: str, label: str) -> str:
    """The rendered line (plus continuation lines) for one check label."""
    lines = _plain(out).splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"  {label}"):
            block = [line]
            for nxt in lines[i + 1:]:
                if re.match(r"  [A-Z][a-z-]+:", nxt) or nxt.startswith("Findings baseline"):
                    break
                block.append(nxt)
            return "\n".join(block)
    raise AssertionError(f"no {label} line in:\n{out}")


class TestKnownNewSplit:
    def test_lists_only_new_lines_and_counts_known(self, project: Path, capsys):
        _story(project, "STORY-001")  # orphan + draft linkage: both escalating
        assert _update_baseline(project, accept_new=True) == 0
        _story(project, "STORY-002")
        capsys.readouterr()
        rc = lint_cmd.run(project, {})
        out = capsys.readouterr().out
        assert rc == 1
        linkage = _line(out, "Story-linkage:")
        assert "1 known (baselined), 1 new" in linkage
        assert "[STORY-002] has no spec linkage" in linkage
        assert "[STORY-001]" not in linkage, "known lines are counted, not re-printed"
        assert "condensed view" in _plain(out)

    def test_verbose_restores_every_line_same_exit(self, project: Path, capsys):
        _story(project, "STORY-001")
        assert _update_baseline(project, accept_new=True) == 0
        _story(project, "STORY-002")
        capsys.readouterr()
        rc_default = lint_cmd.run(project, {})
        default_out = capsys.readouterr().out
        rc_verbose = lint_cmd.run(project, {"verbose": True})
        verbose_out = capsys.readouterr().out
        assert rc_default == rc_verbose == 1
        linkage = _line(verbose_out, "Story-linkage:")
        assert "[STORY-001] has no spec linkage" in linkage
        assert "[STORY-002] has no spec linkage" in linkage
        assert "known (baselined)" not in linkage
        assert "condensed view" not in _plain(verbose_out)
        # The ratchet section is identical in both views.
        assert "[links/orphan] STORY-002" in default_out and "[links/orphan] STORY-002" in verbose_out

    def test_accounting_rows_are_counted_not_listed(self, project: Path, capsys):
        _story(project, "STORY-001", status="approved",
               links=[{"target": "REQ-001", "role": "implements"}])
        req = project / "_specflow" / "specs" / "requirements" / "REQ-001.md"
        req.parent.mkdir(parents=True, exist_ok=True)
        req.write_text(
            "---\nid: REQ-001\ntitle: R\ntype: requirement\nstatus: approved\n"
            "created: '2026-10-01'\nthinking_techniques: [premortem]\n"
            "non_functional_category: functional\nlinks: []\n---\n\n# R\n\n"
            "The system **shall** do it.\n\n## Acceptance Criteria\n\n"
            "- [ ] AC1: Given x, when y, then z.\n- [ ] AC2: Given a, when b, then c.\n",
            encoding="utf-8",
        )
        capsys.readouterr()
        assert lint_cmd.run(project, {}) == 0
        coverage = _line(capsys.readouterr().out, "Coverage:")
        assert "0 known (baselined), 0 new" in coverage and "accounting" in coverage
        assert "no UT linked" not in coverage
        assert lint_cmd.run(project, {"verbose": True}) == 0
        assert "no UT linked" in _line(capsys.readouterr().out, "Coverage:")

    def test_no_baseline_prints_full_detail(self, project: Path, capsys):
        (project / ".specflow" / "findings-baseline.yaml").unlink()
        _story(project, "STORY-001")
        capsys.readouterr()
        assert lint_cmd.run(project, {}) == 0
        linkage = _line(capsys.readouterr().out, "Story-linkage:")
        assert "[STORY-001] has no spec linkage" in linkage
        assert "known (baselined)" not in linkage


class TestIconsAndSurveys:
    def test_warning_icon_when_only_warnings(self, project: Path, capsys):
        _story(project, "STORY-001")
        capsys.readouterr()
        lint_cmd.run(project, {})
        links = _line(capsys.readouterr().out, "Links:")
        assert "⚠" in links and "✓" not in links

    def test_wave_survey_collapses_unless_verbose(self, project: Path, capsys):
        _story(project, "STORY-001")
        _story(project, "STORY-002", links=[{"target": "STORY-001", "role": "depends_on"}])
        capsys.readouterr()
        lint_cmd.run(project, {})
        waves = _line(capsys.readouterr().out, "Wave-cycles:")
        assert "2 stories in 2 wave(s) (--verbose lists each wave)" in waves
        assert "wave 1:" not in waves
        lint_cmd.run(project, {"verbose": True})
        waves = _line(capsys.readouterr().out, "Wave-cycles:")
        assert "wave 1: STORY-001" in waves and "wave 2: STORY-002" in waves

    def test_chain_report_is_one_line_unless_verbose(self, project: Path, capsys):
        req = project / "_specflow" / "specs" / "requirements" / "REQ-001.md"
        req.parent.mkdir(parents=True, exist_ok=True)
        req.write_text(
            "---\nid: REQ-001\ntitle: R\ntype: requirement\nstatus: approved\n"
            "created: '2026-10-01'\nlinks: []\n---\n\n# R\n", encoding="utf-8",
        )
        capsys.readouterr()
        lint_cmd.run(project, {})
        chain = _line(capsys.readouterr().out, "Chain-report:")
        assert "chain survey: 1 approved spec(s)" in chain
        assert "Chain depth distribution" not in chain
        lint_cmd.run(project, {"verbose": True})
        assert "Chain depth distribution" in _line(capsys.readouterr().out, "Chain-report:")

    def test_single_type_run_is_always_verbose(self, project: Path, capsys):
        _story(project, "STORY-001")
        _story(project, "STORY-002", links=[{"target": "STORY-001", "role": "depends_on"}])
        capsys.readouterr()
        lint_cmd.run(project, {"type": "wave-cycles"})
        out = _plain(capsys.readouterr().out)
        assert "wave 1: STORY-001" in out and "condensed view" not in out

    def test_bp_advisory_collapses_to_count(self):
        result = {
            "detail": "  ℹ requirement: 1/1 in-scope BP binding(s) bound; 0 unbound\n"
                      "  ℹ [BP-001] advisory inspection item (not compiled): read it\n"
                      "  ℹ [BP-002] advisory inspection item (not compiled): read it too",
            "findings": [], "warning_count": 0, "blocking_count": 0,
        }
        from specflow.core.policy import Verdict

        condensed = lint_cmd._condense_detail("bp-application", result, Verdict(exit_code=0))
        assert "1/1 in-scope BP binding(s) bound" in condensed
        assert "2 advisory inspection item(s)" in condensed and "[BP-001]" not in condensed

    def test_legacy_link_info_carries_fix_command(self, tmp_path: Path):
        from specflow.lib import artifacts as art_lib

        def _art(aid, atype, status="approved", links=()):
            return art_lib.Artifact(
                path=Path(f"{aid}.md"),
                frontmatter={"id": aid, "title": aid, "type": atype, "status": status},
                body="", links=[art_lib.Link(target=t, role=r) for t, r in links],
            )

        arts = [
            _art("REQ-001", "requirement"),
            _art("ARCH-001", "architecture", links=[("REQ-001", "derives_from")]),
            _art("STORY-001", "story", links=[("REQ-001", "implements")]),
        ]
        result = lint_cmd.check_coverage(arts)
        assert "refined only via legacy" in result["accounting_detail"]
        assert "specflow update <REQ> --add-link <ARCH>:refined_by" in result["accounting_detail"]


class TestEntryHints:
    def test_ids_print_repo_wide_hint_and_proceed(self, project: Path, capsys):
        _story(project, "STORY-001")
        capsys.readouterr()
        rc_plain = lint_cmd.run(project, {})
        capsys.readouterr()
        rc_ids = lint_cmd.run(project, {"ids": ["STORY-001", "REQ-009"]})
        out = _plain(capsys.readouterr().out)
        assert rc_ids == rc_plain
        assert "artifact-lint is repo-wide; ignoring STORY-001, REQ-009" in out
        assert "Result:" in out, "the full run still happens"

    def test_method_flag_is_accepted_and_ignored(self, project: Path, capsys):
        _story(project, "STORY-001")
        capsys.readouterr()
        rc_bare = lint_cmd.run(project, {})
        bare = _plain(capsys.readouterr().out)
        rc_llm = lint_cmd.run(project, {"method": "llm"})
        llm = _plain(capsys.readouterr().out)
        assert rc_bare == rc_llm and bare == llm


def test_split_detail_handles_both_join_styles():
    joined = "  ⚠ [A-1] one;   ⚠ [A-2] two; keep; this\n  ℹ three"
    assert lint_cmd._split_detail(joined) == [
        "  ⚠ [A-1] one", "  ⚠ [A-2] two; keep; this", "  ℹ three",
    ]


class TestSharedSubjectAttribution:
    def test_accounting_line_sharing_subject_with_new_finding_is_not_listed(self, project: Path, capsys):
        # Approved REQ-001 with no links: links/orphan is NEW (escalating) and
        # links/missing-v-pair is ACCOUNTING (approved spec) — both name REQ-001.
        req = project / "_specflow" / "specs" / "requirements" / "REQ-001.md"
        req.parent.mkdir(parents=True, exist_ok=True)
        req.write_text(
            "---\nid: REQ-001\ntitle: R\ntype: requirement\nstatus: approved\n"
            "created: '2026-10-01'\nthinking_techniques: [premortem]\n"
            "non_functional_category: functional\nlinks: []\n---\n\n# R\n\n"
            "The system **shall** do it.\n\n## Acceptance Criteria\n\n"
            "- [ ] AC1: Given x, when y, then z.\n",
            encoding="utf-8",
        )
        # From planning on an orphan approved REQ is debt (before planning it
        # is the expected discovery state — DEC-095 pre-planning staging).
        from specflow.lib import learning

        assert learning.set_phase(project, "planning", "test")["ok"]
        capsys.readouterr()
        rc = lint_cmd.run(project, {})
        out = capsys.readouterr().out
        assert rc == 1
        links = _line(out, "Links:")
        assert "0 known (baselined), 1 new, 1 accounting" in links
        assert "orphan(s) with no links: REQ-001" in links
        assert "missing verification pair" not in links, "accounting rows are counted, never listed"
        # The status icon carries ⚠; the header text does not repeat it, so the
        # only other ⚠ is the listed orphan line itself.
        assert re.search(r"Links:\s+⚠\s+0 known", links), links
        assert links.count("⚠") == 2

    def test_subject_match_is_whole_token(self):
        assert lint_cmd._subject_in_line("REQ-001", "⚠ 1 orphan(s): REQ-001")
        assert not lint_cmd._subject_in_line("REQ-001", "⚠ 1 orphan(s): REQ-0011")
        assert not lint_cmd._subject_in_line("REQ-001", "⚠ XREQ-001 something")
        assert lint_cmd._subject_in_line("IT", "REQ-001 (no IT verification)")
        assert not lint_cmd._subject_in_line("IT", "orphan(s) with no links")
