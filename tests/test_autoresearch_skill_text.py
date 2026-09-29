"""STORY-693: shipped pack text names only commands and flags the CLI accepts.

Scans every shipped markdown/YAML under the pack directories for `specflow ...`
invocations (inline backtick spans and fenced blocks) and checks the
subcommand path and every `--flag` against the real argparse tree. Fenced
commands are additionally parsed in full, so a documented example that omits a
required flag (e.g. `autoresearch log`) fails here.
"""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path

import pytest
import yaml

from specflow.cli import build_parser

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"
AR = PACKS_DIR / "autoresearch"
SKILL_PATH = AR / "skills" / "specflow-autoresearch" / "SKILL.md"
REFS = AR / "skills" / "specflow-autoresearch" / "references"

PACKS = ["autoresearch", "adoption", "ops", "tldr-communication", "iso26262-demo"]

_PLACEHOLDER = re.compile(r"<[^>]+>")


def _subparsers(parser: argparse.ArgumentParser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    return None


def _walk(command: str):
    words = command.split()
    parser = build_parser()
    path: list[str] = []
    i = 1
    while i < len(words):
        choices = _subparsers(parser)
        if choices and words[i] in choices:
            parser = choices[words[i]]
            path.append(words[i])
            i += 1
        else:
            break
    return parser, path, words[i:]


def _problems(command: str) -> list[str]:
    parser, path, rest = _walk(command)
    out: list[str] = []
    if _subparsers(parser) and rest and not rest[0].startswith(("-", "<", "[", "{", "|", "\"", "'")):
        out.append(f"unknown subcommand {rest[0]!r} after `specflow {' '.join(path)}`")
    unquoted = re.sub(r"\"[^\"]*\"|'[^']*'", "", command)  # flags inside values are data
    for m in re.finditer(r"(?<![\w-])(--[a-z][a-z0-9-]*)", unquoted):
        if m.group(1) not in parser._option_string_actions:
            out.append(f"unknown flag {m.group(1)} for `specflow {' '.join(path)}`")
    return out


def _inline_and_fenced(text: str):
    """Yield (line_no, command, is_fenced_start) for specflow invocations."""
    lines = text.splitlines()
    in_fence = False
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            if s.startswith("specflow "):
                parts = []
                cur = raw.rstrip()
                start = i
                while cur.endswith("\\") and i + 1 < len(lines):
                    parts.append(cur[:-1].strip())
                    i += 1
                    cur = lines[i].rstrip()
                parts.append(cur.strip())
                yield start + 1, " ".join(p for p in parts if p), True
        else:
            for m in re.finditer(r"`(specflow [^`]+)`", raw):
                yield i + 1, m.group(1), False
        i += 1


def _shipped_text_files():
    for pack in PACKS:
        for p in sorted((PACKS_DIR / pack).rglob("*")):
            if p.is_file() and p.suffix in {".md", ".yaml"}:
                yield p


_FILES = list(_shipped_text_files())


@pytest.mark.parametrize("path", _FILES, ids=[str(p.relative_to(PACKS_DIR)) for p in _FILES])
def test_shipped_commands_and_flags_exist(path: Path):
    failures = []
    for line_no, command, _fenced in _inline_and_fenced(path.read_text(encoding="utf-8")):
        for problem in _problems(command):
            failures.append(f"{path.name}:{line_no}: {problem}: {command[:90]}")
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize("path", _FILES, ids=[str(p.relative_to(PACKS_DIR)) for p in _FILES])
def test_fenced_commands_parse_in_full(path: Path):
    """A documented fenced command must satisfy argparse, required flags included."""
    parser = build_parser()
    failures = []
    for line_no, command, fenced in _inline_and_fenced(path.read_text(encoding="utf-8")):
        if not fenced or "$(" in command or "<<" in command:
            continue
        command = re.sub(r"\s+#.*$", "", command)
        try:
            argv = shlex.split(_PLACEHOLDER.sub("X", command))
        except ValueError:
            continue
        argv = argv[1:]  # drop leading `specflow`
        # Skip pseudo-syntax: optional [..] groups and a|b alternatives.
        if any(re.match(r"^\[--|^[\w-]+\]$|^\w+\|\w+", t) for t in argv):
            continue
        try:
            parser.parse_args(argv)
        except SystemExit:
            failures.append(f"{path.name}:{line_no}: `{command[:110]}`")
    assert not failures, "Documented commands failed to parse:\n" + "\n".join(failures)


class TestAutoresearchSkillText:
    skill = SKILL_PATH.read_text(encoding="utf-8")

    def test_no_phantom_flags_or_claims(self):
        assert "--no-profile" not in self.skill
        assert "practices list --scope" not in (REFS / "landscape-resurvey.md").read_text()
        assert "practices list --scope" not in self.skill
        assert "all commands accept" not in self.skill.lower()
        assert "specflow list --type best-practice" in (REFS / "landscape-resurvey.md").read_text()

    def test_log_example_carries_required_flags(self):
        text = (REFS / "rolling-evaluation.md").read_text(encoding="utf-8")
        cmds = [c for _n, c, f in _inline_and_fenced(text) if f and c.startswith("specflow autoresearch log")]
        assert cmds, "rolling-evaluation should keep its log example"
        for c in cmds:
            for flag in ("--loop", "--status", "--change-category", "--summary"):
                assert flag in c, c

    def test_frontier_row_and_alias(self):
        assert "specflow autoresearch frontier" in self.skill
        parser, path, _ = _walk("specflow autoresearch frontier --competition COMP-001")
        assert path == ["autoresearch", "frontier"]
        assert "--competition" in parser._option_string_actions, "frontier must accept --competition"

    def test_competition_flag_claim_is_accurate(self):
        line = next(ln for ln in self.skill.splitlines() if "COMP-NNN" in ln and "multi-competition" in ln.lower())
        # log / suggest-finds take --loop, not --competition.
        assert "log" in line and "--loop" in line

    def test_no_backendless_delegate_review_row(self):
        table = [ln for ln in self.skill.splitlines() if ln.startswith("|")]
        assert not any("delegate-review" in ln for ln in table)
        assert "delegate-review" not in self.skill

    def test_review_pass_rule_stated_once(self):
        low = self.skill.lower()
        assert low.count("consequential boundar") == 1
        assert "One investigator" in self.skill  # the kept, test-pinned statement
        assert "never required" in low
        assert "## Optional Review Passes" not in self.skill

    def test_step3_leads_with_plan(self):
        start = self.skill.index("### Step 3:")
        end = self.skill.index("### Step 4:")
        section = self.skill[start:end]
        first_cmd = re.search(r"specflow (autoresearch plan|create --type loop)", section)
        assert first_cmd and first_cmd.group(1) == "autoresearch plan"
        head = section[: section.index("Walk the research ladder")]
        for flag in ("--mode", "--budget", "--knowledge-input", "--inherit"):
            assert flag in head, flag

    def test_noise_protocol_records_three_samples_via_update(self):
        for text in (self.skill, (REFS / "noise-handling-protocol.md").read_text(encoding="utf-8")):
            assert "update COMP-NNN --set 'noise_characterization=" in text
        assert "three" in self.skill.lower()

    def test_no_stale_step_annotations_or_internal_ids(self):
        assert "referenced from Step" not in self.skill
        assert "referenced from Phase" not in self.skill
        offenders = []
        for p in (AR).rglob("*"):
            if p.is_file() and p.suffix in {".md", ".yaml"}:
                for n, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                    if re.search(r"\b(REQ|STORY|DEC)-\d+\b", ln):
                        offenders.append(f"{p.relative_to(AR)}:{n}")
        assert offenders == []

    def test_skill_is_lean(self):
        assert len(self.skill.splitlines()) < 500


class TestNoiseCharacterizationShape:
    """competition.yaml documents the real shape once; the code reads exactly that."""

    schema_text = (AR / "schemas" / "competition.yaml").read_text(encoding="utf-8")

    def test_shape_documented_once_in_schema(self):
        for token in ("samples", "strategy", "jump_k", "guard_k", "guard_sigmas", "sigma"):
            assert token in self.schema_text, token
        assert self.schema_text.count("noise_characterization:") == 1

    def test_strategy_is_a_key_not_the_whole_value(self):
        for name in ("protocol-integrations.md", "noise-handling-protocol.md"):
            text = (REFS / name).read_text(encoding="utf-8")
            assert "noise_characterization → noise strategy" not in text
            assert "Record the chosen strategy in `COMP.noise_characterization`" not in text

    def test_documented_shape_is_what_status_reads(self):
        from specflow.commands import autoresearch as ar

        comp = type("C", (), {"frontmatter": {"noise_characterization": {
            "samples": [0.80, 0.82, 0.81], "strategy": "multi-run median",
            "jump_k": 2.5, "guard_k": 1.5, "guard_sigmas": {"drawdown": 0.01},
        }}})()
        sigma, source = ar._comp_noise_sigma(comp)
        assert sigma and sigma > 0 and "samples" in source
        assert ar._noise_multiple(comp, "jump_k", 3.0) == 2.5
        assert ar._noise_multiple(comp, "guard_k", 1.0) == 1.5
        assert ar._guard_noise_sigma(comp, "drawdown", 0.5) == 0.01

    def test_schema_still_parses(self):
        assert yaml.safe_load(self.schema_text)["type"] == "competition"
