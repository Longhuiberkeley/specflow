"""Tests for the docs knowledge surface (D-22) — lib/docs.py + the orphan fix.

Covers:
  - @ID citation extraction, including code-strip false-positive guards
    (single/double backticks, fenced & indented blocks, email/url/no-@)
  - the docs surface enumeration (root markdown, roots recursion, extra_files,
    exclude, `_`-prefixed skip) and the orphan-code regression guard
    (markdown is never counted as source)
  - discovery (frontmatter split, specflow-doc metadata, H1 title fallback,
    unreadable files skipped), reverse index, and staleness checks
  - config robustness when the `docs:` key is absent (older projects)
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import docs as docs_lib
from specflow.lib import files as files_lib


def _write(root: Path, rel: str, content: str = "") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _write_config(root: Path, cfg: dict) -> None:
    cfg_dir = root / ".specflow"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.yaml").write_text(yaml.dump(cfg), encoding="utf-8")


def _art(art_id: str, status: str) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"_specflow/work/decisions/{art_id}.md"),
        frontmatter={"id": art_id, "status": status},
        body="",
    )


# ---------------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------------

class TestExtractCitations:
    def test_plain_prose_is_cited(self, tmp_path: Path):
        assert docs_lib.extract_citations(tmp_path, "See @DEC-018 here.") == ["DEC-018"]

    def test_single_backtick_is_not_cited(self, tmp_path: Path):
        assert docs_lib.extract_citations(tmp_path, "Use `@ARCH-007` like so.") == []

    def test_double_backtick_is_not_cited(self, tmp_path: Path):
        # Idiomatic literal span; previously leaked a phantom citation.
        assert docs_lib.extract_citations(tmp_path, "Literal: ``@ARCH-007`` shown.") == []

    def test_fenced_block_is_not_cited(self, tmp_path: Path):
        text = "```\n@REQ-001\n```\nprose @REQ-002"
        assert docs_lib.extract_citations(tmp_path, text) == ["REQ-002"]

    def test_indented_block_is_not_cited(self, tmp_path: Path):
        text = "prose @REQ-002\n\n    @ARCH-007 in an indented block\n"
        assert docs_lib.extract_citations(tmp_path, text) == ["REQ-002"]

    def test_email_and_identifier_not_cited(self, tmp_path: Path):
        assert docs_lib.extract_citations(tmp_path, "mail user@host.com or x@REQ-003") == []

    def test_url_with_marker_is_cited(self, tmp_path: Path):
        # A bare @DEC after a slash still satisfies the lookbehind (not \w/@).
        assert docs_lib.extract_citations(tmp_path, "https://x/@DEC-018 here") == ["DEC-018"]

    def test_subid_is_cited(self, tmp_path: Path):
        assert docs_lib.extract_citations(tmp_path, "(@DEC-018.2) and @REQ-001.10") == [
            "DEC-018.2",
            "REQ-001.10",
        ]

    def test_no_at_is_not_cited(self, tmp_path: Path):
        assert docs_lib.extract_citations(tmp_path, "DEC-019 unmarked") == []

    def test_pack_prefix_via_fallback(self, tmp_path: Path):
        # No .specflow/schema present → fallback prefixes apply (includes RUN).
        assert docs_lib.extract_citations(tmp_path, "deployed as @RUN-001") == ["RUN-001"]

    def test_result_is_sorted_and_deduped(self, tmp_path: Path):
        out = docs_lib.extract_citations(tmp_path, "@REQ-002 then @REQ-001 then @REQ-002")
        assert out == ["REQ-001", "REQ-002"]


# ---------------------------------------------------------------------------
# Surface enumeration + orphan-code regression guard
# ---------------------------------------------------------------------------

class TestDocsSurfacePaths:
    def _rel(self, root: Path, paths) -> set[str]:
        return {str(p.resolve().relative_to(root.resolve())) for p in paths}

    def test_root_markdown_always_recognized(self, tmp_path: Path):
        _write(tmp_path, "README.md", "# r")
        _write(tmp_path, "CHANGELOG.md", "# c")
        found = self._rel(tmp_path, files_lib.docs_surface_paths(tmp_path))
        assert {"README.md", "CHANGELOG.md"} <= found

    def test_default_root_recurses(self, tmp_path: Path):
        _write(tmp_path, "docs/guide.md")
        _write(tmp_path, "docs/sub/deep.md")
        found = self._rel(tmp_path, files_lib.docs_surface_paths(tmp_path))
        assert {"docs/guide.md", "docs/sub/deep.md"} <= found

    def test_underscore_prefixed_skipped(self, tmp_path: Path):
        _write(tmp_path, "docs/_generated.md")
        found = self._rel(tmp_path, files_lib.docs_surface_paths(tmp_path))
        assert "docs/_generated.md" not in found

    def test_extra_files_and_custom_roots(self, tmp_path: Path):
        _write_config(tmp_path, {"docs": {"roots": ["wiki/"], "extra_files": ["notes/x.md"]}})
        _write(tmp_path, "wiki/a.md")
        _write(tmp_path, "notes/x.md")
        _write(tmp_path, "docs/ignored.md")  # docs/ no longer a root
        found = self._rel(tmp_path, files_lib.docs_surface_paths(tmp_path))
        assert {"wiki/a.md", "notes/x.md"} <= found
        assert "docs/ignored.md" not in found

    def test_exclude_denylist(self, tmp_path: Path):
        _write_config(tmp_path, {"docs": {"exclude": ["docs/archive/**"]}})
        _write(tmp_path, "docs/keep.md")
        _write(tmp_path, "docs/archive/old.md")
        found = self._rel(tmp_path, files_lib.docs_surface_paths(tmp_path))
        assert "docs/keep.md" in found
        assert "docs/archive/old.md" not in found

    def test_missing_docs_config_key_defaults(self, tmp_path: Path):
        # Older project: config exists but has no `docs:` block — must not crash.
        _write_config(tmp_path, {"source_scope": {"include": []}})
        _write(tmp_path, "docs/g.md")
        found = self._rel(tmp_path, files_lib.docs_surface_paths(tmp_path))
        assert "docs/g.md" in found


class TestOrphanRegressionGuard:
    def test_markdown_is_never_source(self, tmp_path: Path):
        # The headline D-22 bug: markdown anywhere must not be scanned as code,
        # including nested files outside the configured docs surface.
        _write(tmp_path, "src/app.py", "x = 1")
        _write(tmp_path, "README.md", "# r")
        _write(tmp_path, "docs/guide.md", "# g")
        _write(tmp_path, "src/payments/README.md", "# nested")
        names = {
            str(p.resolve().relative_to(tmp_path.resolve()))
            for p in files_lib.scan_source_files(tmp_path)
        }
        assert "src/app.py" in names
        assert not any(n.endswith(".md") for n in names)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

class TestDiscoverDocs:
    def test_title_from_first_h1(self, tmp_path: Path):
        _write(tmp_path, "docs/a.md", "intro\n# Real Title\nbody")
        d = {x.path.name: x for x in docs_lib.discover_docs(tmp_path)}["a.md"]
        assert d.title == "Real Title"

    def test_frontmatter_metadata_and_citation(self, tmp_path: Path):
        body = (
            "---\n"
            "specflow-doc:\n"
            "  title: Storage\n"
            "  audience: backend\n"
            "  last_reviewed: 2026-06-30\n"
            "---\n"
            "# H1 Ignored\n"
            "Governed by @ARCH-007.\n"
        )
        _write(tmp_path, "docs/s.md", body)
        d = {x.path.name: x for x in docs_lib.discover_docs(tmp_path)}["s.md"]
        assert d.title == "Storage"
        assert d.audience == "backend"
        assert d.cites == ["ARCH-007"]

    def test_other_frontmatter_tolerated(self, tmp_path: Path):
        _write(tmp_path, "docs/h.md", "---\ntitle: Hugo\nweight: 3\n---\n# B\ncites @REQ-001")
        d = {x.path.name: x for x in docs_lib.discover_docs(tmp_path)}["h.md"]
        assert d.cites == ["REQ-001"]


# ---------------------------------------------------------------------------
# Reverse index + staleness
# ---------------------------------------------------------------------------

class TestReverseIndex:
    def test_maps_artifact_to_sorted_unique_docs(self, tmp_path: Path):
        docs = [
            docs_lib.Doc(path=tmp_path / "docs/b.md", cites=["DEC-018"]),
            docs_lib.Doc(path=tmp_path / "docs/a.md", cites=["DEC-018", "REQ-001"]),
        ]
        rev = docs_lib.build_reverse_index(docs, tmp_path)
        assert rev["DEC-018"] == ["docs/a.md", "docs/b.md"]
        assert rev["REQ-001"] == ["docs/a.md"]


class TestCheckStale:
    def test_superseded_is_flagged(self, tmp_path: Path):
        docs = [docs_lib.Doc(path=tmp_path / "docs/a.md", cites=["DEC-018"])]
        out = docs_lib.check_stale(tmp_path, docs, [_art("DEC-018", "superseded")])
        assert len(out) == 1
        assert out[0]["artifact_status"] == "superseded"
        assert out[0]["doc"] == "docs/a.md"

    def test_current_is_not_flagged(self, tmp_path: Path):
        docs = [docs_lib.Doc(path=tmp_path / "docs/a.md", cites=["DEC-018"])]
        assert docs_lib.check_stale(tmp_path, docs, [_art("DEC-018", "approved")]) == []

    def test_missing_artifact_not_flagged(self, tmp_path: Path):
        docs = [docs_lib.Doc(path=tmp_path / "docs/a.md", cites=["DEC-999"])]
        assert docs_lib.check_stale(tmp_path, docs, []) == []

    def test_subid_falls_back_to_parent_and_shows_cited_token(self, tmp_path: Path):
        docs = [docs_lib.Doc(path=tmp_path / "docs/a.md", cites=["DEC-018.2"])]
        out = docs_lib.check_stale(tmp_path, docs, [_art("DEC-018", "deprecated")])
        assert len(out) == 1
        assert out[0]["cited_id"] == "DEC-018.2"
        assert out[0]["artifact_id"] == "DEC-018"
        # The author's token is preserved in the message.
        assert "DEC-018.2" in out[0]["message"]


# ---------------------------------------------------------------------------
# Derived cache
# ---------------------------------------------------------------------------

class TestDocsIndex:
    def test_write_index_payload(self, tmp_path: Path):
        _write(tmp_path, "docs/a.md", "# A\ncites @ARCH-007")
        payload = docs_lib.write_docs_index(tmp_path)
        assert (tmp_path / docs_lib.DOCS_INDEX_FILE).is_file()
        assert "docs/a.md" in payload["docs"]
        assert payload["docs"]["docs/a.md"]["cites"] == ["ARCH-007"]
        assert "audience" in payload["docs"]["docs/a.md"]
        assert payload["reverse"]["ARCH-007"] == ["docs/a.md"]
