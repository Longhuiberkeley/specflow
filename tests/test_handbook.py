"""Tests for 'specflow handbook generate' — QT-027 AC3.

Verifies that the command provides bundled generic best practices as a
deterministic fallback, without any external LLM API key or call.
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import handbook as handbook_cmd
from specflow.lib import handbook as handbook_lib


_SCHEMA_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"),
    ("defect", "DEF"), ("best-practice", "BP"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"],
}


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    for art_type, prefix in _SCHEMA_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_STATUS_FLOW),
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config = {
        "project": {
            "name": "test-project",
            "created": "2026-01-01",
            "domain": "",
            "domain_tags": [],
        },
        "artifact_types": [t for t, _ in _SCHEMA_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/best-practices", "_specflow/work/stories",
        "_specflow/work/decisions",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    return root


class TestHandbookLibrary:
    """Unit tests for lib/handbook.py."""

    def test_generic_practices_exist(self):
        assert len(handbook_lib.GENERIC_PRACTICES) >= 5

    def test_generic_practice_has_required_fields(self):
        for p in handbook_lib.GENERIC_PRACTICES:
            assert p.title
            assert p.practice
            assert p.rationale
            assert p.verification
            assert p.domain == "generic"

    def test_domain_practices_have_correct_domain(self):
        for domain, practices in handbook_lib.DOMAIN_PRACTICES.items():
            for p in practices:
                assert p.domain == domain

    def test_get_practices_generic_only(self):
        practices = handbook_lib.get_practices("")
        # No domain -> generic only
        assert all(p.domain == "generic" for p in practices)

    def test_get_practices_unknown_domain(self):
        practices = handbook_lib.get_practices("nonexistent-domain")
        # Unknown domain -> generic only
        assert all(p.domain == "generic" for p in practices)

    def test_get_practices_known_domain_includes_domain_specific(self):
        practices = handbook_lib.get_practices("web-app")
        domain_specific = [p for p in practices if p.domain == "web-app"]
        assert len(domain_specific) >= 3
        # Generic practices are still included
        generic = [p for p in practices if p.domain == "generic"]
        assert len(generic) >= 5

    def test_get_practices_domain_first(self):
        """Domain-specific practices come before generic ones."""
        practices = handbook_lib.get_practices("cli-tool")
        first_domain = practices[0].domain
        assert first_domain == "cli-tool"

    def test_practice_to_body_has_sections(self):
        p = handbook_lib.GENERIC_PRACTICES[0]
        body = p.to_body()
        assert "## Practice" in body
        assert "## Rationale" in body
        assert "## Verification" in body

    def test_generate_handbook_no_domain(self, project_root: Path):
        hb = handbook_lib.generate_handbook(project_root)
        assert hb["domain"] == "generic"
        assert hb["source"] == "bundled"
        assert len(hb["practices"]) >= 5

    def test_generate_handbook_with_domain(self, project_root: Path):
        from specflow.lib.config import set_domain
        set_domain(project_root, "web-app", ["security"])
        hb = handbook_lib.generate_handbook(project_root)
        assert hb["domain"] == "web-app"
        assert hb["tags"] == ["security"]
        domain_practices = [p for p in hb["practices"] if p.domain == "web-app"]
        assert len(domain_practices) >= 3

    def test_format_handbook_text_has_header(self, project_root: Path):
        hb = handbook_lib.generate_handbook(project_root)
        text = handbook_lib.format_handbook_text(hb)
        assert "SpecFlow Best-Practice Handbook" in text
        assert "bundled" in text.lower()
        assert "## Generic Best Practices" in text

    def test_format_handbook_text_domain_section(self, project_root: Path):
        from specflow.lib.config import set_domain
        set_domain(project_root, "web-app")
        hb = handbook_lib.generate_handbook(project_root)
        text = handbook_lib.format_handbook_text(hb)
        assert "Domain-Specific Practices" in text
        assert "web-app" in text

    def test_all_known_domains_have_practices(self):
        """Every domain in the discover skill's checklist list has BPs."""
        known_domains = [
            "web-app", "cli-tool", "api-service", "data-pipeline",
            "embedded", "ml", "quant", "library",
        ]
        for d in known_domains:
            practices = handbook_lib.get_practices(d)
            domain_specific = [p for p in practices if p.domain == d]
            assert len(domain_specific) >= 3, f"Domain '{d}' has fewer than 3 practices"


class TestHandbookCommand:
    """CLI command tests for 'specflow handbook generate'."""

    def test_generate_prints_to_stdout(self, project_root: Path, capsys):
        rc = handbook_cmd.run(project_root, {"create": False})
        assert rc == 0
        out = capsys.readouterr().out
        assert "Best-Practice Handbook" in out
        assert "Generic Best Practices" in out

    def test_generate_no_domain_shows_generic(self, project_root: Path, capsys):
        rc = handbook_cmd.run(project_root, {"create": False})
        assert rc == 0
        out = capsys.readouterr().out
        assert "Domain:** generic" in out

    def test_generate_with_domain(self, project_root: Path, capsys):
        from specflow.lib.config import set_domain
        set_domain(project_root, "ml")
        rc = handbook_cmd.run(project_root, {"create": False})
        assert rc == 0
        out = capsys.readouterr().out
        assert "ml" in out
        assert "Data Leakage" in out

    def test_generate_create_writes_bp_artifacts(self, project_root: Path):
        rc = handbook_cmd.run(project_root, {"create": True})
        assert rc == 0
        bp_dir = project_root / "_specflow" / "specs" / "best-practices"
        files = list(bp_dir.glob("BP-*.md"))
        assert len(files) >= 5  # at least the generic set

    def test_generate_create_with_domain(self, project_root: Path):
        from specflow.lib.config import set_domain
        set_domain(project_root, "web-app")
        rc = handbook_cmd.run(project_root, {"create": True})
        assert rc == 0
        bp_dir = project_root / "_specflow" / "specs" / "best-practices"
        files = list(bp_dir.glob("BP-*.md"))
        # 3 domain + 6 generic = 9
        assert len(files) >= 8

    def test_generate_create_artifact_has_correct_body(self, project_root: Path):
        rc = handbook_cmd.run(project_root, {"create": True})
        assert rc == 0
        bp_dir = project_root / "_specflow" / "specs" / "best-practices"
        files = list(bp_dir.glob("BP-*.md"))
        content = files[0].read_text()
        assert "## Practice" in content
        assert "## Rationale" in content
        assert "## Verification" in content

    def test_generate_create_artifact_status_approved(self, project_root: Path):
        rc = handbook_cmd.run(project_root, {"create": True})
        assert rc == 0
        bp_dir = project_root / "_specflow" / "specs" / "best-practices"
        files = list(bp_dir.glob("BP-*.md"))
        content = files[0].read_text()
        assert "status: approved" in content

    def test_generate_does_not_require_api_key(self, project_root: Path):
        """QT-027 AC3: the command works without any API key env var."""
        import os
        # Ensure no API key is set
        old_keys = {}
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SPECFLOW_API_KEY"):
            if key in os.environ:
                old_keys[key] = os.environ.pop(key)
        try:
            rc = handbook_cmd.run(project_root, {"create": False})
            assert rc == 0
        finally:
            os.environ.update(old_keys)


class TestHandbookCLIRegistration:
    """Verify the command is registered in the argparse parser and dispatch map."""

    def test_handbook_in_parser(self):
        from specflow.cli import build_parser
        parser = build_parser()
        # Parse with handbook generate
        args = parser.parse_args(["handbook", "generate"])
        assert args.command == "handbook"
        assert args.handbook_subcommand == "generate"

    def test_handbook_generate_create_flag(self):
        from specflow.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["handbook", "generate", "--create"])
        assert args.create is True

    def test_handbook_in_dispatch_map(self):
        from specflow.cli import cmd_handbook
        assert callable(cmd_handbook)

    def test_handbook_in_help_epilog(self):
        from specflow.cli import _HELP_EPILOG
        assert "handbook" in _HELP_EPILOG
