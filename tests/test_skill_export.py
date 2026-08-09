"""Tests for cross-platform skill export and the live-vs-shipped byte-equality guard.

Covers:
1. Every ``references/**/*.md`` is inlined deterministically into every
   single-file format (cursor-rules, gemini-toml, codex-agents, markdown).
2. Nested reference files (``references/domain-checklists/...``) are inlined too.
3. Skills with no references export without an ``Inlined references`` section.
4. Exports are byte-identical across runs (deterministic output).
5. ``skills_dirs_identical()`` detects drift (content change / one-sided files).
6. ``.claude/skills`` and ``src/specflow/templates/skills/shared`` are
   byte-identical — the guard that keeps live and shipped skills in sync.
"""

from __future__ import annotations

from pathlib import Path

from specflow.lib.skill_export import (
    FORMAT_HANDLERS,
    _collect_references,
    _inline_references,
    export_skills,
    skills_dirs_identical,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
LIVE_SKILLS = REPO_ROOT / ".claude" / "skills"
SHIPPED_SKILLS = REPO_ROOT / "src" / "specflow" / "templates" / "skills" / "shared"

# Format -> (output subdir, filename suffix) for locating a single exported skill file.
_FORMAT_LAYOUT = {
    "cursor-rules": (".cursor", "rules", ".mdc"),
    "gemini-toml": (".gemini", "commands", ".toml"),
    "codex-agents": (".codex", "agents", ".toml"),
    "markdown": (".rules", "rules", ".md"),
}


def _exported_path(out_dir: Path, fmt: str, name: str) -> Path:
    sub, rules, suffix = _FORMAT_LAYOUT[fmt]
    return out_dir / sub / rules / f"{name}{suffix}"


# ── 1. reference inlining into every single-file format ──────────────────────

class TestReferenceInlining:

    def test_every_format_inlines_own_references(self, tmp_path: Path):
        """Each format's exported specflow-discover file carries the inlined
        reference heading and the verbatim content of a reference file."""
        refs = _collect_references(SHIPPED_SKILLS / "specflow-discover")
        assert refs, "specflow-discover must have references for this test"
        rel, expected_snippet = refs[0]
        assert rel.startswith("references/")

        for fmt in FORMAT_HANDLERS:
            out = tmp_path / fmt.replace("-", "_")
            result = export_skills(out, fmt)
            assert result["ok"], f"{fmt}: {result}"
            text = _exported_path(out, fmt, "specflow-discover").read_text(encoding="utf-8")
            assert "## Inlined references" in text, f"{fmt} lacks inlined section"
            assert f"### {rel}" in text, f"{fmt} lacks heading for {rel}"
            # Plain-text formats carry the reference verbatim; TOML formats escape
            # quotes/backslashes, so only assert verbatim content on the markdown export.
            if fmt == "markdown":
                assert expected_snippet in text, f"{fmt} lacks verbatim content of {rel}"

    def test_nested_reference_inlined(self, tmp_path: Path):
        """references/domain-checklists/web-app.md (nested one level) is inlined."""
        out = tmp_path / "md"
        export_skills(out, "markdown")
        text = _exported_path(out, "markdown", "specflow-discover").read_text(encoding="utf-8")
        assert "### references/domain-checklists/web-app.md" in text
        assert "Questions for browser-based web applications." in text

    def test_skill_without_references_has_no_inlined_section(self, tmp_path: Path):
        """specflow-start has no references/ dir → body exported unchanged."""
        out = tmp_path / "md"
        export_skills(out, "markdown")
        text = _exported_path(out, "markdown", "specflow-start").read_text(encoding="utf-8")
        assert "## Inlined references" not in text

    def test_inline_references_empty_is_noop(self):
        assert _inline_references("body", []) == "body"

    def test_inline_references_sorted_deterministically(self, tmp_path: Path):
        """_collect_references is sorted by relative path, not filesystem order."""
        skill = tmp_path / "sk"
        refs = skill / "references"
        (refs / "b").mkdir(parents=True)
        (refs / "a.md").write_text("A", encoding="utf-8")
        (refs / "b" / "z.md").write_text("Z", encoding="utf-8")
        (refs / "c.md").write_text("C", encoding="utf-8")
        got = [rel for rel, _ in _collect_references(skill)]
        assert got == ["references/a.md", "references/b/z.md", "references/c.md"]


# ── 2. deterministic exports ─────────────────────────────────────────────────

class TestDeterministicExport:

    def test_same_format_byte_identical_across_runs(self, tmp_path: Path):
        out1 = tmp_path / "one"
        out2 = tmp_path / "two"
        export_skills(out1, "markdown")
        export_skills(out2, "markdown")

        for f1 in sorted((out1 / ".rules" / "rules").glob("*.md")):
            f2 = out2 / ".rules" / "rules" / f1.name
            assert f2.exists(), f"missing {f2.name}"
            assert f1.read_bytes() == f2.read_bytes(), f"{f1.name} not deterministic"

    def test_all_formats_export_count_matches_skill_dirs(self, tmp_path: Path):
        # specflow-references is a references-only shared catalog (no SKILL.md),
        # so it is not exported as a standalone skill.
        expected = len([d for d in SHIPPED_SKILLS.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])
        for fmt in FORMAT_HANDLERS:
            out = tmp_path / fmt.replace("-", "_")
            result = export_skills(out, fmt)
            assert result["ok"]
            assert result["count"] == expected

    def test_toml_exports_parse_as_valid_toml(self, tmp_path: Path):
        """gemini-toml and codex-agents must emit parseable TOML even when
        inlined reference content carries backslashes (regex) or triple-quotes."""
        import tomllib

        for fmt in ("gemini-toml", "codex-agents"):
            out = tmp_path / fmt.replace("-", "_")
            assert export_skills(out, fmt)["ok"]
            sub = "commands" if fmt == "gemini-toml" else "agents"
            for f in sorted((out / ("." + fmt.split("-")[0]) / sub).glob("*.toml")):
                tomllib.loads(f.read_text(encoding="utf-8"))  # raises if invalid


# ── 3. byte-equality guard ───────────────────────────────────────────────────

class TestByteEqualityGuard:

    def test_identical_dirs(self, tmp_path: Path):
        a, b = tmp_path / "a", tmp_path / "b"
        (a / "nested").mkdir(parents=True)
        (b / "nested").mkdir(parents=True)
        (a / "SKILL.md").write_bytes(b"hello")
        (a / "nested" / "ref.md").write_bytes(b"ref")
        (b / "SKILL.md").write_bytes(b"hello")
        (b / "nested" / "ref.md").write_bytes(b"ref")
        identical, diffs = skills_dirs_identical(a, b)
        assert identical is True
        assert diffs == []

    def test_content_drift_detected(self, tmp_path: Path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        (a / "SKILL.md").write_bytes(b"v1")
        (b / "SKILL.md").write_bytes(b"v2")
        identical, diffs = skills_dirs_identical(a, b)
        assert identical is False
        assert "SKILL.md" in diffs

    def test_one_sided_file_detected(self, tmp_path: Path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        (a / "references").mkdir()
        (a / "references" / "only-here.md").write_bytes(b"x")
        identical, diffs = skills_dirs_identical(a, b)
        assert identical is False
        assert "references/only-here.md" in diffs

    def test_missing_source_dir_is_drift(self, tmp_path: Path):
        a, b = tmp_path / "a", tmp_path / "b"
        b.mkdir()
        (b / "SKILL.md").write_bytes(b"x")
        identical, diffs = skills_dirs_identical(a, b)
        assert identical is False
        assert "SKILL.md" in diffs

    def test_live_and_shipped_skills_byte_identical(self):
        """The guard this whole feature exists for: live dogfood skills and
        shipped skill templates must never drift. If this fails, edit both
        trees in the same change."""
        identical, diffs = skills_dirs_identical(LIVE_SKILLS, SHIPPED_SKILLS)
        assert identical, f"live vs shipped skills drifted: {diffs[:10]}"
