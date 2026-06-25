"""WS1: tldr-communication pack tests.

Asserts the enriched context_snippet:
  - round-trips through apply_pack + inject_pack_context idempotently,
  - carries the action-first levers distilled from the i-have-adhd source,
  - stays concise (regression guard against AGENTS.md bloat).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow.lib import scaffold as scaffold_lib

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"


@pytest.fixture
def fresh_project(tmp_path: Path) -> Path:
    root = tmp_path / "fresh-project"
    root.mkdir()
    (root / ".claude").mkdir()
    (root / ".specflow" / "schema").mkdir(parents=True)
    (root / ".specflow" / "standards").mkdir(parents=True)
    (root / ".specflow" / "config.yaml").write_text(
        "project: {name: fresh, created: '2026-01-01'}\n"
        "artifact_types: []\nactive_packs: []\n",
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text(
        "current: idle\nhistory: []\n", encoding="utf-8"
    )
    return root


class TestTldrPack:

    def test_apply_pack_returns_snippet(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "tldr-communication", PACKS_DIR)
        assert result["ok"]
        assert "context_snippet" in result
        snippet = result["context_snippet"]
        assert snippet and snippet.strip()

    def test_inject_creates_then_is_idempotent(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Project\n", encoding="utf-8")

        result = scaffold_lib.apply_pack(fresh_project, "tldr-communication", PACKS_DIR)
        snippet = result["context_snippet"]

        first = scaffold_lib.inject_pack_context(fresh_project, "tldr-communication", snippet)
        assert first
        second = scaffold_lib.inject_pack_context(fresh_project, "tldr-communication", snippet)
        assert not second, "second injection must be a no-op"

        content = agents_md.read_text(encoding="utf-8")
        assert content.count("<!-- pack:tldr-communication context") == 1

    def test_snippet_carries_action_first_levers(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "tldr-communication", PACKS_DIR)
        snippet = result["context_snippet"].lower()
        # The reader-model lever + the highest-leverage rules + the pre-send check.
        for needle in ("lead", "next action", "preamble", "pre-send check", "eli5"):
            assert needle in snippet, f"snippet missing lever '{needle}'"

    def test_snippet_is_concise(self, fresh_project: Path):
        """context_snippet is injected into every project's AGENTS.md — keep it tight."""
        result = scaffold_lib.apply_pack(fresh_project, "tldr-communication", PACKS_DIR)
        non_empty = [ln for ln in result["context_snippet"].splitlines() if ln.strip()]
        assert len(non_empty) <= 14, (
            f"tldr context_snippet grew to {len(non_empty)} non-empty lines; "
            f"distill, don't copy. (autoresearch was cut 30→6 for the same reason.)"
        )
