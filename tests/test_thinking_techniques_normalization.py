"""Bracket-wrapped list scalars split into items, not ``"[a"``/``"b]"`` tokens."""

from __future__ import annotations

from specflow.lib import artifacts as art_lib


def test_bracket_wrapped_scalar_is_unwrapped_before_split():
    assert art_lib._normalize_str_list("[premortem, dependency_shock]") == [
        "premortem", "dependency_shock",
    ]
    assert art_lib._normalize_str_list(" [ premortem ] ") == ["premortem"]
    assert art_lib._normalize_str_list("[]") == []


def test_plain_scalars_and_lists_are_unchanged():
    assert art_lib._normalize_str_list("a,b") == ["a", "b"]
    assert art_lib._normalize_str_list("[a, b") == ["[a", "b"], "only a full outer pair is stripped"
    assert art_lib._normalize_str_list(["x", "y"]) == ["x", "y"]


def test_set_thinking_techniques_with_unquoted_bracket_list_round_trips():
    fields = art_lib.parse_set_fields(["thinking_techniques=[premortem, dependency_shock]"])
    assert fields["thinking_techniques"] == ["premortem", "dependency_shock"]


def test_dogfood_corpus_has_no_non_catalog_thinking_techniques():
    """Pin the F-135 sweep: every lens name in this repo's ledger is a catalog key.

    Until the ``thinking-techniques/unknown-name`` lint rule lands (v1.18),
    nothing else stops hyphenated (``devil's-advocate``) or bracket-split
    (``[premortem``) names from creeping back into ``_specflow/``. The sweep
    took the corpus from 147 non-catalog names to 0; this keeps it there.
    """
    from pathlib import Path

    from specflow.lib.techniques import ALL_LENS_NAMES

    repo_root = Path(__file__).resolve().parents[1]
    allowed = ALL_LENS_NAMES | {"lean_assessment"}  # update.py _SENTINEL_NAMES
    offenders: dict[str, list[str]] = {}
    for art in art_lib.discover_artifacts(repo_root):
        bad = [t for t in art.thinking_techniques if t not in allowed]
        if bad:
            offenders[art.id] = bad
    assert not offenders, (
        "non-catalog thinking_techniques names in the dogfood ledger "
        "(fix via `specflow update <ID> --set thinking_techniques='[...]'`): "
        + ", ".join(f"{aid}: {names}" for aid, names in sorted(offenders.items()))
    )
