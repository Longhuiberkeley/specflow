"""docs/cli-reference.md covers the real CLI (STORY-712 AC1).

Derived from the argparse parser, not from ``--help`` text: every top-level
subcommand needs a ``### `specflow <cmd>`` heading (a nested form such as
``### `specflow ci generate``` counts for its parent). Deprecated aliases are
exempt by name and must instead be mentioned in the entry of the command they
alias. The init/refresh/artifact-lint flag tables are checked flag-by-flag,
since those were the tables that drifted.

The lifecycle flowchart check lives here too: the mermaid chart, the ASCII
chart, and the Tier-1 table in docs/lifecycle.md must name the same set of
``/specflow-*`` skills.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from specflow.cli import build_parser

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_REFERENCE = REPO_ROOT / "docs" / "cli-reference.md"
LIFECYCLE = REPO_ROOT / "docs" / "lifecycle.md"

# Deprecated aliases: no heading of their own; the aliased command's entry
# must mention them.
ALIASES = {"handbook": "practices"}

# Flag tables regenerated from --help; keep them complete.
FLAG_TABLE_COMMANDS = ("init", "refresh", "artifact-lint", "findings-baseline")


def _subparsers_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _top_level() -> dict[str, argparse.ArgumentParser]:
    action = _subparsers_action(build_parser())
    assert action is not None
    return dict(action.choices)


def _headings(text: str) -> list[str]:
    return re.findall(r"^### `specflow ([^`]+)`", text, flags=re.MULTILINE)


def _section(text: str, command: str) -> str:
    """Return the text under the first heading for `command` up to the next heading."""
    m = re.search(rf"^### `specflow {re.escape(command)}(?: [^`]*)?`\n(.*?)(?=^### |^## |\Z)", text, flags=re.MULTILINE | re.DOTALL)
    assert m, f"no `### `specflow {command}`` heading"
    return m.group(1)


def test_every_subcommand_has_a_heading():
    text = CLI_REFERENCE.read_text(encoding="utf-8")
    documented = {h.split()[0] for h in _headings(text)}
    missing = sorted(name for name in _top_level() if name not in documented and name not in ALIASES)
    assert not missing, f"docs/cli-reference.md lacks a `### `specflow <cmd>`` heading for: {missing}"


def test_headings_name_real_subcommands():
    text = CLI_REFERENCE.read_text(encoding="utf-8")
    real = _top_level()
    unknown = sorted({h.split()[0] for h in _headings(text)} - set(real))
    assert not unknown, f"docs/cli-reference.md documents commands the CLI does not have: {unknown}"


@pytest.mark.parametrize("alias,target", sorted(ALIASES.items()))
def test_deprecated_alias_is_mentioned_in_its_target_entry(alias, target):
    text = CLI_REFERENCE.read_text(encoding="utf-8")
    assert alias in _top_level(), f"{alias} is no longer a subcommand; drop it from ALIASES"
    assert f"`{alias}" in _section(text, target), f"the `{alias}` alias must be mentioned under `specflow {target}`"


def _option_strings(parser: argparse.ArgumentParser) -> set[str]:
    out: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                out |= _option_strings(child)
            continue
        for opt in action.option_strings:
            if opt.startswith("--") and opt != "--help":
                out.add(opt)
    return out


@pytest.mark.parametrize("command", FLAG_TABLE_COMMANDS)
def test_flag_tables_cover_every_flag(command):
    text = CLI_REFERENCE.read_text(encoding="utf-8")
    section = _section(text, command)
    flags = _option_strings(_top_level()[command])
    # Word-boundary match: a documented `--force-x` must not satisfy `--force`.
    missing = sorted(f for f in flags if not re.search(rf"`{re.escape(f)}[` =\[]", section))
    assert not missing, f"`specflow {command}` section does not mention flags {missing} (regenerate from --help)"


def test_parser_builds_fully():
    """Sanity check for the fixtures above: build_parser() yields the full subcommand set."""
    assert len(_top_level()) >= 50


_SKILL_RE = re.compile(r"/specflow-[a-z][a-z-]*[a-z]")
_PACK_SKILLS = {"/specflow-adopt", "/specflow-autoresearch", "/specflow-ops"}


def _skills(text: str) -> set[str]:
    # The ASCII chart wraps one long name across two lines ("/specflow-change-\n    impact-review").
    joined = re.sub(r"-\n\s+", "-", text)
    return {s.rstrip("-") for s in _SKILL_RE.findall(joined)} - _PACK_SKILLS


def test_lifecycle_charts_and_tier1_table_agree():
    text = LIFECYCLE.read_text(encoding="utf-8")
    mermaid = re.search(r"```mermaid\n(.*?)```", text, flags=re.DOTALL).group(1)
    ascii_chart = re.search(r"<summary>Plain-text.*?```\n(.*?)```", text, flags=re.DOTALL).group(1)
    tier1 = re.search(r"## Tier 1.*?\n(\|.*?)\n\n", text, flags=re.DOTALL).group(1)
    m, a, t = _skills(mermaid), _skills(ascii_chart), _skills(tier1)
    assert len(t) == 12, f"Tier-1 table should name the 12 core skills, found {sorted(t)}"
    assert m == t, f"mermaid chart vs Tier-1 table: missing {sorted(t - m)}, extra {sorted(m - t)}"
    assert a == t, f"ASCII chart vs Tier-1 table: missing {sorted(t - a)}, extra {sorted(a - t)}"


def test_lifecycle_ascii_has_no_duplicated_gate_line():
    text = LIFECYCLE.read_text(encoding="utf-8")
    ascii_chart = re.search(r"<summary>Plain-text.*?```\n(.*?)```", text, flags=re.DOTALL).group(1)
    assert ascii_chart.count("(reviewer / CI / operator)") == 1
