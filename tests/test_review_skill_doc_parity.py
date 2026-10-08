"""Docs and review-skill text track the engine (STORY-712, v1.17.2 P-6c).

Guards the prose fixes that followed the Round-1 engine changes:

- the artifact-review skill names the real `patterns` subcommand (F-071),
  says that an ID-less run is lint only, and tells the agent to run the
  recording command the CLI prints (the CLI never stamps lenses itself);
- `challenge-engine.md` describes proactive items as `Hint:` lines (there is
  no prompt-builder helper);
- `docs/commands.md` and the skill state the lens-catalog size that the
  engine actually ships (F-134);
- `docs/cli-reference.md` documents `hook install --force` / ownership /
  backups, `ci generate --dry-run`/`--force`, and the artifact-review
  behaviours above;
- the pack-author skill closes with the discover / `--from-standard` handoff;
- ROADMAP names the review→PREV emission path and the `--findings` ingest.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specflow.lib.techniques import ALL_LENS_NAMES

_ROOT = Path(__file__).resolve().parents[1]
_SHIP = _ROOT / "src" / "specflow" / "templates" / "skills" / "shared"
_LIVE = _ROOT / ".claude" / "skills"
_CLI_REF = _ROOT / "docs" / "cli-reference.md"


def _read(rel: str) -> str:
    return (_SHIP / rel).read_text(encoding="utf-8")


def _section(text: str, command: str) -> str:
    m = re.search(
        rf"^### `specflow {re.escape(command)}`\n(.*?)(?=^### |^## |\Z)",
        text, flags=re.MULTILINE | re.DOTALL,
    )
    assert m, f"no `### `specflow {command}`` heading in docs/cli-reference.md"
    return m.group(1)


class TestArtifactReviewSkill:
    def test_patterns_is_never_bare(self):
        text = _read("specflow-artifact-review/SKILL.md")
        assert "`specflow patterns list`" in text
        assert "`specflow patterns`" not in text

    def test_id_less_run_is_lint_only(self):
        text = _read("specflow-artifact-review/SKILL.md")
        assert "With neither an ID nor `--all` it runs lint only" in text

    def test_agent_runs_the_printed_recording_command(self):
        text = _read("specflow-artifact-review/SKILL.md")
        assert "`specflow update <ID> --thinking-techniques <a,b>` line the command prints" in text
        assert "the CLI never records lenses itself" in text

    def test_proactive_items_are_hint_lines(self):
        skill = _read("specflow-artifact-review/SKILL.md")
        ref = _read("specflow-artifact-review/references/challenge-engine.md")
        assert "`Hint:` line" in skill
        assert "`Hint:` line carrying its `llm_prompt`" in ref
        assert "format_proactive_prompt" not in ref

    def test_lens_catalog_size_matches_engine(self):
        n = len(ALL_LENS_NAMES)
        skill = _read("specflow-artifact-review/SKILL.md")
        assert f"full {n}-lens catalog" in skill
        commands = (_ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
        assert "16 lenses" not in commands
        assert f"{n} lenses" in commands

    @pytest.mark.parametrize("rel", [
        "specflow-artifact-review/SKILL.md",
        "specflow-artifact-review/references/challenge-engine.md",
        "specflow-pack-author/SKILL.md",
    ])
    def test_live_mirror_is_byte_identical(self, rel):
        assert (_LIVE / rel).read_bytes() == (_SHIP / rel).read_bytes()


class TestCliReference:
    def test_hook_install_documents_force_ownership_and_backups(self):
        sec = _section(_CLI_REF.read_text(encoding="utf-8"), "hook install")
        assert "`--force`" in sec
        assert "# specflow pre-commit hook — installed by" in sec
        assert ".specflow/cache/backups/<timestamp>/hooks/" in sec
        assert "git rev-parse --git-path hooks" in sec and "core.hooksPath" in sec
        assert "specflow hook pre-commit" in sec

    def test_ci_generate_documents_dry_run_and_force(self):
        sec = _section(_CLI_REF.read_text(encoding="utf-8"), "ci generate")
        assert "`--dry-run`" in sec and "`--force`" in sec
        assert "`unchanged`" in sec
        assert ".specflow/cache/backups/<timestamp>/ci/" in sec

    def test_artifact_review_documents_lint_only_recording_and_hints(self):
        sec = _section(_CLI_REF.read_text(encoding="utf-8"), "artifact-review")
        assert "runs lint only" in sec
        assert "--thinking-techniques" in sec
        assert "never stamps `thinking_techniques`" in sec
        assert "`Hint:` line" in sec
        assert "creates no REVIEW, CHL or PREV" in sec


class TestPackAuthorHandoff:
    def test_closing_line_follows_exit_message(self):
        text = _read("specflow-pack-author/SKILL.md")
        exit_at = text.index("**Exit message:**")
        rules_at = text.index("## Rules")
        closing = text[exit_at:rules_at]
        assert "/specflow-discover" in closing
        assert "`specflow create --from-standard <clause-id>`" in closing
        assert "`specflow standards gaps`" in closing


class TestRoadmap:
    def test_review_to_prev_deferral_is_spelled_out(self):
        text = (_ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        assert "`emit_review_pass`" in text
        assert "`specflow artifact-review --findings <json>`" in text
        assert "`.specflow/checklist-log/`" in text and "not evidence" in text

    def test_patch_versions_follow_their_minor(self):
        heads = re.findall(r"^## (v1\.[34]\.\d)$", (_ROOT / "ROADMAP.md").read_text(encoding="utf-8"), flags=re.MULTILINE)
        assert heads == ["v1.3.0", "v1.3.1", "v1.4.0", "v1.4.1"]
