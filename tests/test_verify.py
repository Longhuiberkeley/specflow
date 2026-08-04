"""Tests for ``specflow verify`` — the verification contract runner.

Covers the keystone accounting-not-policing invariant: a non-zero
verify_command is RECORDED and the CLI still exits 0; non-zero CLI exit is
reserved for runner failures (unknown ID, timeout) only. Also covers
deterministic hashing, fingerprint-exempt writes, and evidence-file capture.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from specflow.commands import verify as verify_cmd
from specflow.lib import verification as verify_lib


# ── Fixture helpers ───────────────────────────────────────────────


def _scaffold(tmp: Path) -> Path:
    """Create a bare SpecFlow project under tmp with the test/spec directories."""
    root = tmp / "project"
    for rel in [
        "_specflow/specs/unit-tests",
        "_specflow/specs/integration-tests",
        "_specflow/specs/qualification-tests",
        "_specflow/work/stories",
        ".specflow/schema",
    ]:
        (root / rel).mkdir(parents=True, exist_ok=True)
    return root


def _write_artifact(
    root: Path,
    rel_path: str,
    frontmatter: dict,
    body: str = "Some body text.",
) -> Path:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "---\n" + yaml.dump(frontmatter, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def _read_fm(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    end = text.find("---", 3)
    return yaml.safe_load(text[3:end])


def _run(root: Path, **kwargs) -> tuple[int, str]:
    """Invoke the verify command, return (exit_code, captured_stdout)."""
    args = {"ids": [], "all": False, "type": None, "dry_run": False,
            "evidence_file": False, "timeout": 600, "seed_prev": False}
    args.update(kwargs)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = verify_cmd.run(root, args)
    return code, buf.getvalue()


# ── dry-run ───────────────────────────────────────────────────────


class TestDryRun:
    def test_dry_run_executes_nothing_and_writes_nothing(self, tmp_path, capsys):
        root = _scaffold(tmp_path)
        path = _write_artifact(
            root, "_specflow/specs/unit-tests/UT-001.md",
            {"id": "UT-001", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "exit 1"},
        )
        before = path.read_text(encoding="utf-8")

        code, out = _run(root, ids=["UT-001"], dry_run=True)

        assert code == 0
        assert "exit 1" in out  # the command is printed
        assert "UT-001" in out
        # File byte-identical: nothing written.
        assert path.read_text(encoding="utf-8") == before
        assert "verify_run_" not in before


# ── successful command ────────────────────────────────────────────


class TestSuccess:
    def test_records_all_pinned_fields(self, tmp_path):
        root = _scaffold(tmp_path)
        path = _write_artifact(
            root, "_specflow/specs/unit-tests/UT-001.md",
            {"id": "UT-001", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "echo hello"},
        )

        code, out = _run(root, ids=["UT-001"])

        assert code == 0
        assert "exit=0" in out
        fm = _read_fm(path)
        # All five always-written pinned result fields present.
        assert fm["verify_run_exit_code"] == 0
        assert fm["verify_run_out_hash"].startswith("sha256:")
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", fm["verify_run_at"])
        assert isinstance(fm["verify_run_git_ref"], str)
        assert fm["verify_run_command_hash"] == verify_lib.hash_text("echo hello")
        # out_hash must equal hash of stdout+stderr of the command.
        assert fm["verify_run_out_hash"] == verify_lib.hash_text("hello\n")

    def test_out_hash_is_deterministic(self, tmp_path):
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-001.md",
            {"id": "UT-001", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "echo hello"},
        )

        _run(root, ids=["UT-001"])
        path = root / "_specflow/specs/unit-tests/UT-001.md"
        h1 = _read_fm(path)["verify_run_out_hash"]

        _run(root, ids=["UT-001"])
        h2 = _read_fm(path)["verify_run_out_hash"]

        assert h1 == h2  # same command output → same hash


# ── keystone: failing command recorded, CLI exit 0 ────────────────


class TestFailingCommandKeystone:
    def test_failing_command_recorded_with_cli_exit_zero(self, tmp_path):
        """THE KEYSTONE INVARIANT TEST.

        A verify_command that exits non-zero is RECORDED (verify_run_exit_code
        = that code) and the CLI STILL exits 0. Recording, not blocking.
        """
        root = _scaffold(tmp_path)
        path = _write_artifact(
            root, "_specflow/specs/unit-tests/UT-002.md",
            {"id": "UT-002", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "echo fail; exit 3"},
        )

        code, out = _run(root, ids=["UT-002"])

        assert code == 0  # keystone: CLI still succeeds
        assert "exit=3" in out
        assert "recorded" in out
        fm = _read_fm(path)
        assert fm["verify_run_exit_code"] == 3  # actual code recorded, not 0


# ── runner failures (non-zero CLI exit) ───────────────────────────


class TestRunnerFailures:
    def test_timeout_exits_nonzero_with_clear_message(self, tmp_path):
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-003.md",
            {"id": "UT-003", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "sleep 5"},
        )

        code, out = _run(root, ids=["UT-003"], timeout=1)

        assert code == 1
        assert "timed out" in out
        assert "UT-003" in out

    def test_unknown_id_exits_nonzero(self, tmp_path):
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-004.md",
            {"id": "UT-004", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "echo ok"},
        )

        code, out = _run(root, ids=["UT-999"])

        assert code == 1
        assert "unknown artifact ID" in out
        assert "UT-999" in out


# ── no contract → skipped, exit 0 ─────────────────────────────────


class TestNoContract:
    def test_no_verify_command_is_skipped_exit_zero(self, tmp_path):
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-005.md",
            {"id": "UT-005", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02"},
        )

        code, out = _run(root, ids=["UT-005"])

        assert code == 0
        assert "no verification contract declared" in out
        assert "skipped" in out


# ── batching ──────────────────────────────────────────────────────


class TestBatching:
    def test_all_batches_across_every_artifact(self, tmp_path):
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-010.md",
            {"id": "UT-010", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "echo a"},
        )
        _write_artifact(
            root, "_specflow/work/stories/STORY-010.md",
            {"id": "STORY-010", "title": "T", "type": "story", "status": "verified",
             "created": "2026-08-02", "verify_command": "echo b"},
        )

        code, out = _run(root, all=True)

        assert code == 0
        assert "UT-010" in out
        assert "STORY-010" in out

    def test_type_filter_batches_one_type(self, tmp_path):
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-011.md",
            {"id": "UT-011", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "echo a"},
        )
        _write_artifact(
            root, "_specflow/specs/integration-tests/IT-011.md",
            {"id": "IT-011", "title": "T", "type": "integration-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "echo b"},
        )

        code, out = _run(root, type="UT")

        assert code == 0
        assert "UT-011" in out
        assert "IT-011" not in out


# ── fingerprint-exempt write ──────────────────────────────────────


class TestFingerprintExempt:
    def test_fingerprint_byte_identical_and_no_suspect(self, tmp_path):
        from specflow.lib import artifacts as art_lib

        root = _scaffold(tmp_path)
        body = "Invariant body content."
        path = _write_artifact(
            root, "_specflow/specs/unit-tests/UT-020.md",
            {"id": "UT-020", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "echo ok"},
            body=body,
        )

        # The fingerprint must always equal compute_fingerprint(body), and
        # recording verify_run_* fields (which lands in frontmatter only) must
        # NOT alter it or set suspect.
        expected_fp = art_lib.compute_fingerprint(body)

        code, _ = _run(root, ids=["UT-020"])
        assert code == 0
        fm_after = _read_fm(path)
        assert fm_after["fingerprint"] == expected_fp  # body-only hash preserved
        assert fm_after.get("suspect", False) is False  # never flagged
        assert fm_after["verify_run_exit_code"] == 0  # result recorded

        # Idempotent: a second recording keeps the same fingerprint.
        _run(root, ids=["UT-020"])
        assert _read_fm(path)["fingerprint"] == expected_fp


# ── evidence-file capture ─────────────────────────────────────────


class TestEvidenceFile:
    def test_evidence_hash_and_mtime_captured(self, tmp_path):
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-030.md",
            {"id": "UT-030", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "true",
             "verify_evidence": ["evidence/*.log"]},
        )
        ev = root / "evidence" / "out.log"
        ev.parent.mkdir(parents=True, exist_ok=True)
        ev.write_text("metric=0.99\n", encoding="utf-8")

        code, out = _run(root, ids=["UT-030"], evidence_file=True)

        assert code == 0
        fm = _read_fm(root / "_specflow/specs/unit-tests/UT-030.md")
        assert fm["verify_run_evidence_hash"] == verify_lib.hash_file(ev)
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
                        fm["verify_run_evidence_mtime"])
        assert "no evidence file matched" not in out

    def test_missing_evidence_match_handled(self, tmp_path):
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-031.md",
            {"id": "UT-031", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-02", "verify_command": "true",
             "verify_evidence": ["nonexistent/*.txt"]},
        )

        code, out = _run(root, ids=["UT-031"], evidence_file=True)

        assert code == 0  # missing match is a warning, not a runner failure
        assert "no evidence file matched" in out
        fm = _read_fm(root / "_specflow/specs/unit-tests/UT-031.md")
        assert fm["verify_run_evidence_hash"] == ""
        assert fm["verify_run_evidence_mtime"] == ""


# ── STORY-624: outcome feedback loop (divergent verify → PREV) ──────


class TestSeedPrevFeedback:
    """STORY-624 Part 2: a divergent verify_command can seed a PREV prevention
    pattern via the existing learnings path. Opt-in (--seed-prev), never blocks."""

    def test_divergent_with_seed_prev_creates_prev(self, tmp_path):
        """A non-zero (divergent) exit code + --seed-prev seeds a PREV pattern;
        verify STILL exits 0 (opt-in, never blocking)."""
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-040.md",
            {"id": "UT-040", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-04", "verify_command": "echo fail; exit 2"},
        )

        code, out = _run(root, ids=["UT-040"], seed_prev=True)

        assert code == 0  # never blocking
        assert "exit=2" in out
        assert "recorded" in out
        assert "seeded PREV-" in out
        # The PREV file exists on disk under the learned-checklists surface.
        learned_dir = root / ".specflow" / "checklists" / "learned"
        prevs = sorted(learned_dir.glob("PREV-*.yaml"))
        assert len(prevs) == 1
        data = yaml.safe_load(prevs[0].read_text(encoding="utf-8"))
        assert data["source"] == "verify-divergence"
        assert data["discovered_from"] == "UT-040"
        assert data["mode"] == "reactive"
        # The recorded divergence is captured in the check text.
        check_text = data["items"][0]["check"]
        assert "exit=2" in check_text and "expected=0" in check_text

    def test_divergent_without_seed_prev_creates_no_prev(self, tmp_path):
        """Without --seed-prev, a divergent contract records evidence but seeds
        NO PREV — only the Tip (the offer) is printed."""
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-041.md",
            {"id": "UT-041", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-04", "verify_command": "exit 1"},
        )

        code, out = _run(root, ids=["UT-041"])  # seed_prev defaults to False

        assert code == 0
        assert "seeded PREV-" not in out
        assert "--seed-prev" in out  # the Tip offers the opt-in
        learned_dir = root / ".specflow" / "checklists" / "learned"
        assert not learned_dir.exists()

    def test_passing_contract_seeds_no_prev_even_with_seed_prev(self, tmp_path):
        """A non-divergent (passing) contract never seeds a PREV, even with
        --seed-prev: the loop fires on divergence only."""
        root = _scaffold(tmp_path)
        _write_artifact(
            root, "_specflow/specs/unit-tests/UT-042.md",
            {"id": "UT-042", "title": "T", "type": "unit-test", "status": "verified",
             "created": "2026-08-04", "verify_command": "true"},
        )

        code, out = _run(root, ids=["UT-042"], seed_prev=True)

        assert code == 0
        assert "exit=0" in out
        assert "seeded PREV-" not in out
        learned_dir = root / ".specflow" / "checklists" / "learned"
        assert not learned_dir.exists()

    def test_seed_prev_respects_session_cap(self, tmp_path):
        """Multiple divergent contracts seed at most max_patterns_per_session
        PREVs in one verify run (mirrors the review/done learnable budget)."""
        root = _scaffold(tmp_path)
        for i, aid in enumerate(("UT-050", "UT-051", "UT-052", "UT-053"), start=50):
            _write_artifact(
                root, f"_specflow/specs/unit-tests/{aid}.md",
                {"id": aid, "title": "T", "type": "unit-test", "status": "verified",
                 "created": "2026-08-04", "verify_command": "exit 1"},
            )
        # Force a small cap via config (default is 3; set to 2 to prove the cap).
        (root / ".specflow").mkdir(parents=True, exist_ok=True)
        (root / ".specflow" / "config.yaml").write_text(
            yaml.dump({"learning": {"max_patterns_per_session": 2}}),
            encoding="utf-8",
        )

        code, out = _run(root, all=True, seed_prev=True)

        assert code == 0
        # Exactly 2 PREVs created; the remaining divergences hit the cap message.
        learned_dir = root / ".specflow" / "checklists" / "learned"
        prevs = sorted(learned_dir.glob("PREV-*.yaml"))
        assert len(prevs) == 2
        assert "PREV cap" in out
