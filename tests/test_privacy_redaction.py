"""Privacy redaction primitives + generator choke points (STORY-649, REQ-038).

The v1.14.6 pre-release review found the audit *generator* re-leaking
REQ-038's denylist into every new report (reports quote spec ACs, and
REQ-038's AC enumerates the denylist). These tests pin the fix:

  1. lib/privacy.redact_text — token replacement, idempotence, non-matches.
  2. The write-time choke points: cached findings and (via the shared
     function) every generated report file are redacted at write.
  3. The gate script imports the SAME pattern object (single source of
     truth — divergence fails here).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from specflow.commands.project_audit import _save_cached_findings
from specflow.lib.privacy import PATTERN, REDACTION_MARKER, redact_text

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "denylist_gate.py"
_spec = importlib.util.spec_from_file_location("denylist_gate", _SCRIPT)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def test_redact_replaces_every_token_class():
    text = (
        "grep for cs2 and HKJC via quant_trade; arbitrage on run_comp002; "
        "track_a plus Track A; a trailing stop at 0.020 and 0.021; "
        "Sharpe > 2 with 6.62 and 8.45; Kalman BTC ADA ETH; "
        "/Volumes/ExternalDrive and /Users/longhui"
    )
    out = redact_text(text)
    for token in (
        "cs2", "HKJC", "quant_trade", "run_comp002", "track_a", "Track A",
        "trailing stop", "0.020", "0.021", "6.62", "8.45", "Kalman",
        "BTC", "ADA", "ETH", "ExternalDrive", "longhui",
    ):
        assert token not in out, f"token survived redaction: {token}"
    assert out.count(REDACTION_MARKER) >= 15


def test_redact_is_idempotent_and_leaves_prose_alone():
    prose = "Ordinary report text: whether to use eth lowercase, 0.0207 and 10.0219 numbers."
    assert redact_text(prose) == prose
    once = redact_text("leak: cs2 end")
    assert redact_text(once) == once


def test_cached_findings_redacted_at_write(tmp_path: Path):
    """_save_cached_findings is the cache choke point: findings quoting the
    denylist (e.g. REQ-038's own AC) must land on disk redacted."""
    findings = [
        {"severity": "info", "message": "Denylist grep (cs2/HKJC/quant_trade) returned zero hits"},
    ]
    _save_cached_findings(tmp_path, "deadbeef", findings)
    cached = list(tmp_path.glob("*.md"))
    assert len(cached) == 1
    content = cached[0].read_text(encoding="utf-8")
    for token in ("cs2", "HKJC", "quant_trade"):
        assert token not in content
    assert REDACTION_MARKER in content


def test_gate_script_shares_the_pattern_object_source():
    """Single source of truth: the standalone gate script must import the
    package pattern, not embed a drifting copy."""
    src = _SCRIPT.read_text(encoding="utf-8")
    assert "from specflow.lib.privacy import PATTERN" in src
    assert "PATTERN = re.compile" not in src  # no embedded duplicate
    assert gate.PATTERN.pattern == PATTERN.pattern
