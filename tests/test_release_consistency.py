"""Release consistency (STORY-718, AGENTS.md release steps 1-2).

The release version lives in three places that must agree: ``pyproject.toml``
``[project].version``, ``specflow.__version__`` (what ``config.py`` and the
CI pin read), and the newest ``## [x.y.z] - YYYY-MM-DD`` heading of
``CHANGELOG.md``. A tag cut while any one lags is a broken release, so the
check runs with every test run instead of living only in the maintainer's head.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import specflow

REPO_ROOT = Path(__file__).resolve().parents[1]

_HEADING_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)


def _pyproject_version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def _changelog_entries() -> list[tuple[str, str, str]]:
    """Return ``[(version, date, entry_text), ...]`` newest first."""
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    matches = list(_HEADING_RE.finditer(text))
    entries: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entries.append((match.group(1), match.group(2), text[match.start():end]))
    return entries


def test_pyproject_version_matches_package_version():
    assert _pyproject_version() == specflow.__version__, (
        "pyproject.toml [project].version and specflow.__version__ must be bumped together"
    )


def test_changelog_newest_entry_is_the_package_version():
    entries = _changelog_entries()
    assert entries, "CHANGELOG.md has no '## [x.y.z] - YYYY-MM-DD' heading"
    newest_version, newest_date, _ = entries[0]
    assert newest_version == specflow.__version__, (
        f"CHANGELOG.md newest entry is [{newest_version}] - {newest_date} but the package "
        f"is {specflow.__version__}; add the entry or bump the version"
    )


def test_changelog_newest_entry_is_the_highest_version():
    """A new entry added below the top (or a duplicated heading) is caught here.

    Only the newest entry is checked: older history has a few out-of-order
    patch entries that are not worth rewriting.
    """
    versions = [tuple(int(part) for part in v.split(".")) for v, _, _ in _changelog_entries()]
    assert versions[0] == max(versions), "the newest CHANGELOG entry must be the highest version"
    assert len(versions) == len(set(versions)), "CHANGELOG has a duplicated version heading"


def test_changelog_newest_entry_reports_test_total():
    """Every entry closes with the Keep-a-Changelog ``Total: N tests passing`` line."""
    _, _, entry = _changelog_entries()[0]
    assert re.search(r"Total: \d+ tests passing", entry), (
        "the newest CHANGELOG entry lacks its 'Total: N tests passing' line"
    )
