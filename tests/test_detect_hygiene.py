"""`specflow detect dead-code | similarity | stale-docs` behaviour (STORY-718).

Each handler is exercised end to end on a throwaway project with a known
positive AND a false-positive guard, because these scans are the most
signal-sensitive detectors: a scan that fires on a healthy repository is a
cry-wolf regression. Unit tests for ``lib.analysis`` sit alongside.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from conftest import write_artifact

from specflow import cli
from specflow.commands import detect as detect_cmd
from specflow.commands import init as init_cmd
from specflow.lib import analysis


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    monkeypatch.chdir(root)
    return root


def _write_py(root: Path, rel: str, source: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


# ── dead-code ───────────────────────────────────────────────────────────────

_MOD = '''
    __all__ = ["exported"]

    def exported():
        return 1

    def used_directly():
        return 2

    def used_via_attribute():
        return 3

    def never_called():
        return 4

    class NeverUsed:
        pass

    class UsedClass:
        pass

    def main():
        return UsedClass()

    def test_helper():
        return 5

    def __dunder__():
        return 6
'''

_CALLER = '''
    from pkg import mod
    from pkg.mod import used_directly

    def run():
        used_directly()
        return mod.used_via_attribute()

    RESULT = run()
'''


class TestDeadCode:
    def test_flags_only_unreferenced_symbols(self, tmp_path: Path):
        _write_py(tmp_path, "src/pkg/mod.py", _MOD)
        _write_py(tmp_path, "src/pkg/caller.py", _CALLER)
        dead = analysis.find_dead_code(tmp_path)
        assert [(d.name, d.kind) for d in dead] == [("never_called", "function"), ("NeverUsed", "class")]
        assert all(d.file.name == "mod.py" and d.line > 0 for d in dead)

    def test_clean_tree_and_missing_src_dir_report_nothing(self, tmp_path: Path):
        assert analysis.find_dead_code(tmp_path) == []
        _write_py(tmp_path, "src/pkg/a.py", "def f():\n    return 1\n")
        _write_py(tmp_path, "src/pkg/b.py", "from pkg.a import f\nvalue = f()\n")
        assert analysis.find_dead_code(tmp_path) == []

    def test_project_scripts_entry_points_are_not_dead(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0"\n[project.scripts]\nx = "pkg.app:entry"\n',
            encoding="utf-8",
        )
        _write_py(tmp_path, "src/pkg/app.py", "def entry():\n    return 0\n\ndef lonely():\n    return 1\n")
        assert [d.name for d in analysis.find_dead_code(tmp_path)] == ["lonely"]

    def test_handler_lists_findings_and_never_blocks(self, project: Path, capsys):
        _write_py(project, "src/pkg/mod.py", _MOD)
        _write_py(project, "src/pkg/caller.py", _CALLER)
        assert cli.main(["detect", "dead-code"]) == 0
        out = capsys.readouterr().out
        assert "2 unreferenced top-level symbol(s)" in out
        assert "src/pkg/mod.py" in out and "[function] never_called" in out and "[class] NeverUsed" in out
        assert "Informational only" in out

    def test_handler_is_quiet_on_a_clean_tree(self, project: Path, capsys):
        _write_py(project, "lib/pkg/a.py", "def f():\n    return 1\n\nvalue = f()\n")
        assert cli.main(["detect", "dead-code", "--src-dir", "lib"]) == 0
        out = capsys.readouterr().out
        assert "No dead code detected" in out and "(src: lib)" in out


# ── similarity ──────────────────────────────────────────────────────────────

def _long_function(name: str, prefix: str, statements: int = 12) -> str:
    lines = [f"def {name}(items):", f"    {prefix}_total = 0"]
    for index in range(statements - 2):
        lines.append(f"    {prefix}_total += items[{index}] * {index + 1}")
    lines.append(f"    return {prefix}_total")
    return "\n".join(lines) + "\n"


class TestSimilarity:
    def test_identifier_renamed_clone_is_found(self, tmp_path: Path):
        _write_py(tmp_path, "src/pkg/a.py", _long_function("alpha", "a"))
        _write_py(tmp_path, "src/pkg/b.py", _long_function("beta", "b"))
        pairs = analysis.find_similar_functions(tmp_path)
        assert len(pairs) == 1
        pair = pairs[0]
        assert {pair.func_a, pair.func_b} == {"alpha", "beta"}
        assert pair.similarity >= 0.9
        assert pair.lines_a[0] == 1 and pair.lines_a[1] > pair.lines_a[0]

    def test_different_bodies_and_short_functions_are_not_paired(self, tmp_path: Path):
        _write_py(tmp_path, "src/pkg/a.py", _long_function("alpha", "a"))
        _write_py(tmp_path, "src/pkg/c.py", "\n".join(
            ["def gamma(items):"] + [f"    print({i}, len(items), sorted(items)[:{i}])" for i in range(12)]
        ) + "\n")
        _write_py(tmp_path, "src/pkg/d.py", "def short_a(x):\n    return x + 1\n\ndef short_b(y):\n    return y + 1\n")
        assert analysis.find_similar_functions(tmp_path) == []
        assert analysis.find_similar_functions(tmp_path, min_statements=1, threshold=0.5) != [], (
            "lowering the statement floor and threshold pairs the short clones"
        )

    def test_handler_reports_pairs_and_stays_quiet_when_clean(self, project: Path, capsys):
        _write_py(project, "src/pkg/a.py", _long_function("alpha", "a"))
        assert cli.main(["detect", "similarity"]) == 0
        assert "No near-duplicate functions found" in capsys.readouterr().out

        _write_py(project, "src/pkg/b.py", _long_function("beta", "b"))
        assert cli.main(["detect", "similarity", "--threshold", "0.8"]) == 0
        out = capsys.readouterr().out
        assert "1 similar function pair(s)" in out and "alpha" in out and "beta" in out
        assert "threshold: 0.8" in out and "Informational only" in out


# ── stale-docs ──────────────────────────────────────────────────────────────

class TestStaleDocs:
    def test_superseded_citation_is_surfaced_once_per_doc(self, project: Path, capsys):
        write_artifact(project, "DEC-001", "decision", "Old way", status="superseded")
        write_artifact(project, "DEC-002", "decision", "Current way", status="approved")
        docs = project / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text(
            "# Guide\n\nWe follow @DEC-001 and @DEC-002.\nAlso @DEC-001 again.\n", encoding="utf-8"
        )
        assert cli.main(["detect", "stale-docs"]) == 0
        out = capsys.readouterr().out
        assert "Docs scanned: 2" in out, "docs/guide.md plus the root AGENTS.md that init wrote"
        assert "1 stale citation(s)" in out
        assert "docs/guide.md" in out and "DEC-001" in out and "superseded" in out
        assert "Informational only" in out

    def test_no_false_positives_for_current_missing_or_code_span_citations(self, project: Path, capsys):
        write_artifact(project, "DEC-001", "decision", "Old way", status="superseded")
        write_artifact(project, "REQ-001", "requirement", "Live requirement", status="approved")
        docs = project / "docs"
        docs.mkdir()
        (docs / "ok.md").write_text(
            "# Ok\n\nCurrent: @REQ-001. Unknown id: @REQ-999.\n"
            "Example syntax only: `@DEC-001` and\n\n```\n@DEC-001\n```\n",
            encoding="utf-8",
        )
        assert cli.main(["detect", "stale-docs"]) == 0
        out = capsys.readouterr().out
        assert "All doc citations reference current artifacts" in out
        assert "stale citation" not in out

    def test_project_without_docs_is_clean(self, project: Path, capsys):
        assert cli.main(["detect", "stale-docs"]) == 0
        out = capsys.readouterr().out
        assert "Docs scanned: 1" in out, "only the root AGENTS.md that init wrote"
        assert "All doc citations reference current artifacts" in out


def test_detect_without_subcommand_prints_usage_and_exits_one(tmp_path: Path, capsys):
    assert detect_cmd.run(tmp_path, {}) == 1
    assert "Usage: specflow detect" in capsys.readouterr().out
