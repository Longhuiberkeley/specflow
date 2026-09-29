"""STORY-688 AC3: one aggregate budget for the always-on context.

Everything an agent reads on every turn is the base block
(templates/agent-context.md) plus the context_snippet of every pack that could
be installed alongside it. The whole set is bounded to 375 words, and no
sentence may be carried twice (a pack snippet carries only its delta to the
base block). This replaces the old 40-line cap on agent-context.md alone.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src" / "specflow"
WORD_BUDGET = 375
# Sentences shorter than this ("Installed.") are labels, not guidance.
MIN_SENTENCE_WORDS = 4


def always_on_blocks() -> dict[str, str]:
    blocks = {"templates/agent-context.md": (SRC / "templates" / "agent-context.md").read_text(encoding="utf-8")}
    for pack in sorted((SRC / "packs").glob("*/pack.yaml")):
        snippet = (yaml.safe_load(pack.read_text(encoding="utf-8")) or {}).get("context_snippet")
        if snippet:
            blocks[f"packs/{pack.parent.name}/pack.yaml"] = str(snippet)
    return blocks


def word_count(text: str) -> int:
    return len(text.split())


def sentences(text: str) -> set[str]:
    out = set()
    for raw in re.split(r"(?<=[.!?])\s+|\n+", text):
        norm = re.sub(r"[^\w\s/<>-]", "", raw).lower()
        norm = " ".join(norm.split())
        if len(norm.split()) >= MIN_SENTENCE_WORDS and not norm.startswith("#"):
            out.add(norm)
    return out


def shared_sentences(blocks: dict[str, str]) -> list[str]:
    seen: dict[str, str] = {}
    shared = []
    for name, text in blocks.items():
        for sentence in sentences(text):
            if sentence in seen and seen[sentence] != name:
                shared.append(f"{seen[sentence]} and {name}: {sentence!r}")
            seen.setdefault(sentence, name)
    return shared


def test_blocks_cover_base_and_packs():
    blocks = always_on_blocks()
    assert "templates/agent-context.md" in blocks
    assert sum(name.startswith("packs/") for name in blocks) >= 4, list(blocks)


def test_aggregate_always_on_budget():
    blocks = always_on_blocks()
    counts = {name: word_count(text) for name, text in blocks.items()}
    total = sum(counts.values())
    assert total <= WORD_BUDGET, f"always-on context is {total} words > {WORD_BUDGET}: {counts}"


def test_no_sentence_is_carried_twice():
    shared = shared_sentences(always_on_blocks())
    assert not shared, "\n".join(shared)


def test_seeded_violations_fail():
    base = "## SpecFlow\n\nLead with the answer or next action. Every code change traces to a STORY or REQ."
    snippet = "### Pack\nInstalled. Lead with the answer or next action."
    assert shared_sentences({"base": base, "pack": snippet}) == [
        "base and pack: 'lead with the answer or next action'"
    ]
    # Short labels are not guidance and may repeat.
    assert shared_sentences({"a": "Installed. One two three four.", "b": "Installed. Five six seven eight."}) == []
    bloated = {"base": base, "pack": "word " * WORD_BUDGET}
    assert sum(word_count(t) for t in bloated.values()) > WORD_BUDGET
