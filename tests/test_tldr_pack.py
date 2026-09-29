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

    def test_snippet_carries_only_the_delta(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "tldr-communication", PACKS_DIR)
        snippet = result["context_snippet"]
        # STORY-695: the delta to the base block is the compaction recap plus a
        # plain-language gloss rule. `eli5` must be in the BODY, not only the
        # heading, and nothing the base block already says is restated.
        heading, _, body = snippet.strip().partition("\n")
        assert heading.startswith("###")
        body_l = body.lower()
        for needle in ("compacted", "eli5", "plain"):
            assert needle in body_l, f"snippet body missing '{needle}'"
        base = (PACKS_DIR.parent / "templates" / "agent-context.md").read_text(encoding="utf-8").lower()
        assert "lead with the answer" in base  # the thing the pack must NOT restate
        assert "lead with" not in snippet.lower()
        assert "when they aid scan" not in body_l and "format when it helps" not in body_l

    def test_description_matches_the_snippet(self):
        import yaml

        manifest = yaml.safe_load((PACKS_DIR / "tldr-communication" / "pack.yaml").read_text(encoding="utf-8"))
        desc = manifest["description"].lower()
        assert "10-line" not in desc and "step n of m" not in desc and "list cap" not in desc
        assert "compacted" in desc and "eli5" in desc
        readme = (PACKS_DIR / "tldr-communication" / "README.md").read_text(encoding="utf-8").lower()
        assert "compacted" in readme and "eli5" in readme

    def test_snippet_is_concise(self, fresh_project: Path):
        """context_snippet is injected into every project's AGENTS.md — keep it tight."""
        result = scaffold_lib.apply_pack(fresh_project, "tldr-communication", PACKS_DIR)
        non_empty = [ln for ln in result["context_snippet"].splitlines() if ln.strip()]
        assert len(non_empty) <= 14, (
            f"tldr context_snippet grew to {len(non_empty)} non-empty lines; "
            f"distill, don't copy. (autoresearch was cut 30→6 for the same reason.)"
        )

    def test_snippet_is_two_lines_max_bytes(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "tldr-communication", PACKS_DIR)
        assert len(result["context_snippet"].encode("utf-8")) <= 300


class TestAggregateAlwaysOnBudget:
    """STORY-695 AC4: the base block plus EVERY pack snippet stays inside the same
    budget the base block alone is held to (see test_approval_guardrail)."""

    _MAX_BYTES = 3072
    _MAX_NON_EMPTY_LINES = 36

    def test_base_plus_all_pack_snippets_within_budget(self):
        import yaml

        base = (PACKS_DIR.parent / "templates" / "agent-context.md").read_text(encoding="utf-8")
        total = base
        for manifest_path in sorted(PACKS_DIR.glob("*/pack.yaml")):
            snippet = (yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}).get("context_snippet") or ""
            total += "\n" + snippet
        assert len(total.encode("utf-8")) <= self._MAX_BYTES, len(total.encode("utf-8"))
        non_empty = [ln for ln in total.splitlines() if ln.strip()]
        assert len(non_empty) <= self._MAX_NON_EMPTY_LINES, len(non_empty)
