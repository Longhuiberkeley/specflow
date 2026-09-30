"""Exit-code policy and baseline format (STORY-705, REQ-053 AC1/AC7) — unit level."""

from __future__ import annotations

from pathlib import Path

from specflow.core import findings_baseline as fb
from specflow.core.findings import make
from specflow.core.policy import decide

ORPHAN = make("links/orphan", ("STORY-1",), "warning")
QUALITY = make("quality/text", ("REQ-1", "ambiguity word"), "warning")
BROKEN = make("links/broken", ("STORY-1", "REQ-9"), "blocking")


def test_blocking_always_fails():
    assert decide([BROKEN], None, full_run=False).exit_code == 1
    assert decide([BROKEN], frozenset(), full_run=True).exit_code == 1


def test_no_baseline_ratchet_off():
    v = decide([ORPHAN], None, full_run=True)
    assert v.exit_code == 0 and not v.ratchet_on


def test_new_escalating_warning_fails_known_passes():
    assert decide([ORPHAN], frozenset(), full_run=True).exit_code == 1
    v = decide([ORPHAN], frozenset({ORPHAN.key}), full_run=True)
    assert v.exit_code == 0 and v.known == [ORPHAN]


def test_accounting_never_escalates():
    assert decide([QUALITY], frozenset(), full_run=True).exit_code == 0


def test_filtered_runs_never_escalate():
    assert decide([ORPHAN], frozenset(), full_run=False).exit_code == 0


def test_resolved_keys_reported():
    stale = ("links/orphan", ("STORY-GONE",))
    v = decide([], frozenset({stale}), full_run=True)
    assert v.resolved == [stale] and v.exit_code == 0


def test_same_inputs_same_verdict():
    """AC1 at the policy level: order of findings does not matter."""
    a = decide([ORPHAN, QUALITY, BROKEN], frozenset(), full_run=True)
    b = decide([BROKEN, QUALITY, ORPHAN], frozenset(), full_run=True)
    assert (a.exit_code, a.new, a.blocking) == (b.exit_code, b.new, b.blocking)


def test_dumps_sorted_and_idempotent(tmp_path: Path):
    keys = {("b/x", ("B",)), ("a/y", ("A", "z"))}
    text = fb.dumps(keys)
    assert text.index("a/y") < text.index("b/x")
    assert fb.dumps(frozenset(keys)) == text
    (tmp_path / ".specflow").mkdir()
    fb.baseline_path(tmp_path).write_text(text, encoding="utf-8")
    loaded, err = fb.load(tmp_path)
    assert err is None and loaded == frozenset(keys)


def test_absent_and_malformed_baseline(tmp_path: Path):
    assert fb.load(tmp_path) == (None, None)
    (tmp_path / ".specflow").mkdir()
    fb.baseline_path(tmp_path).write_text("format: 99\n", encoding="utf-8")
    keys, err = fb.load(tmp_path)
    assert keys is None and err.severity == "blocking"
    assert err.rule_id == "findings-baseline/schema-error"
