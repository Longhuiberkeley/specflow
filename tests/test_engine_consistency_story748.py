"""STORY-748 (W-3 engine): small engine fixes from the SPIKE-008 review.

Covers the patterns empty state, the role-target matrix vs schema roles, the
audit severity ranker, and two CLI help texts. The ci, brief, status and rbac
items have tests next to their existing suites.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pytest
import yaml

from specflow import cli
from specflow.commands import project_audit as audit_cmd
from specflow.lib.role_targets import ROLE_TARGET_MATRIX

_SRC = Path(__file__).resolve().parents[1] / "src" / "specflow"


# ── patterns list empty state (R2-006) ──────────────────────────────────────

@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / ".specflow").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _empty_state(capsys) -> str:
    assert cli.main(["patterns", "list"]) == 0
    return capsys.readouterr().out


def test_patterns_empty_state_names_the_real_sources(project: Path, capsys):
    out = _empty_state(capsys)
    assert "artifact review" not in out
    assert "seeded when a DEF closes" in out
    assert "specflow done --auto" in out
    assert "specflow verify --seed-prev" in out
    assert "retired patterns are hidden" in out


def test_patterns_empty_state_when_every_pattern_is_retired(project: Path, capsys):
    learned = project / ".specflow" / "checklists" / "learned"
    learned.mkdir(parents=True)
    (learned / "PREV-001.yaml").write_text(
        yaml.dump({"id": "PREV-001", "name": "old", "retired": True,
                   "items": [{"check": "x", "severity": "warning"}]}),
        encoding="utf-8",
    )
    assert "retired patterns are hidden" in _empty_state(capsys)


# ── role-target matrix tracks schema allowed_link_roles (AC5) ───────────────

def _schema_roles() -> dict[str, set[str]]:
    files = glob.glob(str(_SRC / "templates" / "schemas" / "**" / "*.yaml"), recursive=True)
    files += glob.glob(str(_SRC / "packs" / "*" / "schemas" / "*.yaml"))
    out: dict[str, set[str]] = {}
    for f in files:
        data = yaml.safe_load(Path(f).read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("type"):
            out[data["type"]] = set(data.get("allowed_link_roles") or [])
    return out


def test_every_matrix_pair_is_allowed_by_its_schema():
    roles = _schema_roles()
    bad = [
        (art_type, role)
        for art_type, rows in ROLE_TARGET_MATRIX.items()
        for role in rows
        if role not in roles.get(art_type, set())
    ]
    assert bad == []
    # Every matrix source type has a shipped schema.
    assert set(ROLE_TARGET_MATRIX) <= set(roles)


def test_detailed_design_has_no_guided_by_row():
    assert "guided_by" not in ROLE_TARGET_MATRIX["detailed-design"]


# ── project-audit severity ranking (D5) ─────────────────────────────────────

@pytest.mark.parametrize("hi,lo", [
    ("warning", "info"), ("warn", "info"), ("error", "warning"), ("blocking", "warning"),
])
def test_severity_rank_orders_both_vocabularies(hi, lo):
    assert audit_cmd._severity_rank(hi) > audit_cmd._severity_rank(lo)
    assert audit_cmd._severity_rank("warning") == audit_cmd._severity_rank("warn")
    assert audit_cmd._severity_rank("blocking") == audit_cmd._severity_rank("error")


def test_grouped_chl_takes_warning_over_info():
    findings = [
        {"axis": "horizontal", "severity": "info", "message": "a", "type": "story"},
        {"axis": "horizontal", "severity": "warning", "message": "b", "type": "story"},
    ]
    (g,) = audit_cmd._group_findings_to_chls(findings)
    assert g.severity == "warning"


# ── help texts (R1-077, export --output) ────────────────────────────────────

def _help(*argv: str) -> None:
    """Print argparse help for *argv* (read back through capsys)."""
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([*argv, "--help"])


def test_orphan_code_retro_link_help_is_not_a_closed_list(capsys):
    _help("detect", "orphan-code")
    out = " ".join(capsys.readouterr().out.split())
    assert "owns output_files" in out
    assert "Artifact ID (STORY/ARCH/DDD/REQ)" not in out


def test_export_output_help_says_required_with_adapter(capsys):
    _help("export")
    out = " ".join(capsys.readouterr().out.split())
    assert "required with --adapter" in out
