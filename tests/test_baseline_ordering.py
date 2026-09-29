"""Baseline ordering follows SemVer 2.0 section 11 (STORY-700, DEF-001).

Prerelease identifiers compare per the spec (numeric identifiers as integers,
numeric before alphanumeric, shorter prefix first), build metadata is ignored,
and SpecFlow's post-release suffixes (``-spec-sync``) sort as prereleases.
"""

from __future__ import annotations

import random

import pytest

from specflow.lib.baselines import _semver_sort_key, select_release_pair


def _order(names: list[str]) -> list[str]:
    return sorted(names, key=_semver_sort_key)


def _precedence(name: str):
    """Sort key without the deterministic name tie-break."""
    return _semver_sort_key(name)[:-1]


# SemVer 2.0 section 11 example chain, ascending.
SPEC_CHAIN = [
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-alpha.beta",
    "1.0.0-beta",
    "1.0.0-beta.2",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "1.0.0",
]


@pytest.mark.parametrize("lo,hi", list(zip(SPEC_CHAIN, SPEC_CHAIN[1:])))
def test_spec_section_11_adjacent_pairs(lo: str, hi: str):
    assert _semver_sort_key(lo) < _semver_sort_key(hi)
    assert _order([hi, lo]) == [lo, hi]


@pytest.mark.parametrize("prefix", ["", "v"])
def test_spec_chain_shuffled_sorts_ascending(prefix: str):
    names = [prefix + n for n in SPEC_CHAIN]
    for seed in range(5):
        shuffled = names[:]
        random.Random(seed).shuffle(shuffled)
        assert _order(shuffled) == names


@pytest.mark.parametrize(
    "lo,hi",
    [
        ("v1.0.0-rc.9", "v1.0.0-rc.10"),  # numeric identifiers compare as ints
        ("v1.0.0-rc.2", "v1.0.0-rc.11"),
        ("v1.0.0-1", "v1.0.0-alpha"),  # numeric before alphanumeric
        ("v1.0.0-alpha", "v1.0.0-alpha.1"),  # shorter prefix first
        ("v1.0.0-rc.1", "v1.0.0"),  # prerelease below release
        ("v1.0.0", "v1.0.1-rc.1"),  # numeric core dominates prerelease
        ("v1.9.2", "v1.13.3"),  # multi-digit core segments
    ],
)
def test_prerelease_and_core_ordering(lo: str, hi: str):
    assert _order([hi, lo]) == [lo, hi]
    assert _semver_sort_key(lo) < _semver_sort_key(hi)


@pytest.mark.parametrize(
    "a,b",
    [
        ("v1.0.0+build1", "v1.0.0"),
        ("v1.0.0+build1", "v1.0.0+build2"),
        ("v1.0.0-rc.1+build.5", "v1.0.0-rc.1"),
    ],
)
def test_build_metadata_ignored_for_ordering(a: str, b: str):
    assert _precedence(a) == _precedence(b)


def test_build_metadata_does_not_sort_before_release():
    assert _order(["v1.0.0", "v1.0.0-rc.1+b", "v1.0.0+build1"])[0] == "v1.0.0-rc.1+b"
    assert _precedence("v1.0.0+build1") > _precedence("v1.0.0-rc.1")


def test_equal_precedence_order_is_deterministic():
    a = _order(["v1.0.0+b", "v1.0.0+a", "v1.0.0"])
    b = _order(["v1.0.0", "v1.0.0+a", "v1.0.0+b"])
    assert a == b


def test_post_release_suffix_sorts_as_prerelease():
    # SpecFlow policy: "-spec-sync" is a prerelease of the same core version.
    assert _order(["v0.2.1", "v0.2.1-spec-sync"]) == ["v0.2.1-spec-sync", "v0.2.1"]
    assert _order(["v0.2.2", "v0.2.1", "v0.2.1-spec-sync"]) == [
        "v0.2.1-spec-sync",
        "v0.2.1",
        "v0.2.2",
    ]


def test_release_pair_uses_semver_precedence():
    names = _order(["v1.0.0-rc.10", "v1.0.0-rc.9", "v1.0.0-rc.2"])
    assert select_release_pair(names) == ["v1.0.0-rc.9", "v1.0.0-rc.10"]


def test_unparseable_names_still_sort_last():
    assert _order(["snapshot", "v1.0.0", "v1.0.0-rc.1"]) == [
        "v1.0.0-rc.1",
        "v1.0.0",
        "snapshot",
    ]
