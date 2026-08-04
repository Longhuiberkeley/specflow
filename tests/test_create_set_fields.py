"""Regression tests for `specflow create --set` field handling.

Covers the --set links=... collision bug: art_lib.create_artifact() takes an
explicit `links` keyword, so a raw --set links=... entry used to raise
`TypeError: got multiple values for keyword argument 'links'`. It also covers
the broader reserved-key collision guard (title, status, priority, ...).
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import create as create_cmd
from specflow.lib import artifacts as art_lib

_SCHEMA_TYPES = [("requirement", "REQ"), ("story", "STORY")]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"],
}


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    for art_type, prefix in _SCHEMA_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_STATUS_FLOW),
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "artifact_types": [t for t, _ in _SCHEMA_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
    )

    for subdir in ["_specflow/specs/requirements", "_specflow/work/stories"]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    return root


def _base_args(**overrides) -> dict:
    args = {
        "type": "requirement",
        "title": "A requirement",
        "status": "draft",
        "priority": None,
        "rationale": None,
        "tags": None,
        "links": None,
        "body": "The system shall do X.",
        "from_standard": None,
        "force": False,
        "skip_dedup_check": True,
        "nfr_category": None,
        "set_fields": None,
    }
    args.update(overrides)
    return args


def _created_requirement(root: Path) -> art_lib.Artifact:
    artifacts = art_lib.discover_artifacts(root, artifact_type="requirement")
    assert len(artifacts) == 1
    return artifacts[0]


class TestSetLinksAlone:
    def test_set_links_without_dashdash_links(self, project_root: Path):
        rc = create_cmd.run(project_root, _base_args(
            set_fields=['links=[{"target":"REQ-001","role":"derives_from"}]'],
        ))
        assert rc == 0
        art = _created_requirement(project_root)
        assert any(l.target == "REQ-001" and l.role == "derives_from" for l in art.links)


class TestSetLinksMergedWithDashdashLinks:
    def test_set_links_merges_with_dashdash_links(self, project_root: Path):
        rc = create_cmd.run(project_root, _base_args(
            links='[{"target":"REQ-002","role":"relates_to"}]',
            set_fields=['links=[{"target":"REQ-001","role":"derives_from"}]'],
        ))
        assert rc == 0
        art = _created_requirement(project_root)
        targets = {(l.target, l.role) for l in art.links}
        assert ("REQ-002", "relates_to") in targets
        assert ("REQ-001", "derives_from") in targets


class TestReservedKeyCollisions:
    def test_set_status_returns_error(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _base_args(
            set_fields=["status=approved"],
        ))
        assert rc == 1
        out = capsys.readouterr().out
        assert "--status" in out
        req_dir = project_root / "_specflow" / "specs" / "requirements"
        assert list(req_dir.glob("REQ-*.md")) == []

    def test_set_title_returns_error(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _base_args(
            set_fields=["title=Something else"],
        ))
        assert rc == 1
        assert "--title" in capsys.readouterr().out

    def test_set_root_returns_error_no_flag_named(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _base_args(
            set_fields=["root=/tmp/somewhere"],
        ))
        assert rc == 1
        out = capsys.readouterr().out
        assert "reserved" in out.lower()


class TestPromoteRecipeShape:
    def test_promote_recipe_from_autoresearch_skill(self, project_root: Path):
        # Pre-existing REQ-001 target of the derives_from link. Created through
        # the real command path so the artifact-id counter advances correctly.
        rc0 = create_cmd.run(project_root, _base_args(title="Existing req"))
        assert rc0 == 0

        rc = create_cmd.run(project_root, _base_args(
            type="requirement",
            title="Promoted finding",
            set_fields=['links=[{"target":"REQ-001","role":"derives_from"}]'],
        ))
        assert rc == 0
        artifacts = art_lib.discover_artifacts(project_root, artifact_type="requirement")
        promoted = [a for a in artifacts if a.title == "Promoted finding"]
        assert len(promoted) == 1
        assert any(l.target == "REQ-001" and l.role == "derives_from" for l in promoted[0].links)


class TestMalformedSetLinks:
    def test_set_links_not_a_list_returns_error(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _base_args(
            set_fields=['links={"target":"x"}'],
        ))
        assert rc == 1
        out = capsys.readouterr().out
        assert "✗" in out
        req_dir = project_root / "_specflow" / "specs" / "requirements"
        assert list(req_dir.glob("REQ-*.md")) == []

    def test_set_links_entry_missing_role_returns_error(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _base_args(
            set_fields=['links=[{"target":"x"}]'],
        ))
        assert rc == 1
        out = capsys.readouterr().out
        assert "✗" in out


class TestParseSetFieldsDottedKeys:
    """W1.3 — dotted ``--set key.subkey=`` targets nested-map fields.

    Direct unit tests of ``parse_set_fields`` (no project needed): a dotted key
    merges into the head map, an unknown head or a non-map existing value fails
    loudly, a flat typo suggests the nearest known key, and an unknown-but-not-
    close flat key still passes through as a custom-field escape hatch.
    """

    def test_dotted_merges_into_existing_map(self):
        result = art_lib.parse_set_fields(
            ["risk_profile.confidence=high"],
            known_keys=["risk_profile"],
            existing={"risk_profile": {"tier": 2}},
        )
        assert result == {"risk_profile": {"tier": 2, "confidence": "high"}}

    def test_dotted_starts_fresh_when_absent(self):
        result = art_lib.parse_set_fields(
            ["risk_profile.confidence=high"], known_keys=["risk_profile"]
        )
        assert result == {"risk_profile": {"confidence": "high"}}

    def test_multiple_dotted_same_head_merge(self):
        result = art_lib.parse_set_fields(
            ["risk_profile.a=1", "risk_profile.b=2"], known_keys=["risk_profile"]
        )
        assert result == {"risk_profile": {"a": 1, "b": 2}}

    def test_dotted_unknown_head_raises(self):
        with pytest.raises(ValueError, match="not a known nested-map field"):
            art_lib.parse_set_fields(["bogus.x=1"], known_keys=["risk_profile"])

    def test_dotted_non_dict_existing_raises(self):
        with pytest.raises(ValueError, match="not a map"):
            art_lib.parse_set_fields(
                ["tags.x=1"], known_keys=["tags"], existing={"tags": ["a"]}
            )

    def test_flat_typo_suggests_closest(self):
        with pytest.raises(ValueError, match="Did you mean"):
            art_lib.parse_set_fields(["rationalee=x"], known_keys=["rationale"])

    def test_flat_unknown_not_close_passes_through(self):
        # "1" parses as JSON int 1; the key passes through as a custom field.
        result = art_lib.parse_set_fields(["totally_custom=1"], known_keys=["rationale"])
        assert result == {"totally_custom": 1}

    def test_no_known_keys_dotted_still_merges(self):
        # Without a schema (known_keys=None) there is no allowlist to validate
        # against, so dotted keys merge into a nested map instead of erroring.
        result = art_lib.parse_set_fields(["a.b=1", "plain=2"])
        assert result == {"a": {"b": 1}, "plain": 2}


class TestCreateSetNestedMapField:
    """W1.3 end-to-end through the create command with a nested-map schema."""

    def test_create_set_dotted_into_declared_map(self, project_root: Path):
        # Extend the requirement schema with a nested-map optional field.
        schema_path = project_root / ".specflow" / "schema" / "requirement.yaml"
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        schema["optional_fields"] = ["risk_profile"]
        schema_path.write_text(yaml.dump(schema), encoding="utf-8")

        rc = create_cmd.run(project_root, _base_args(
            set_fields=["risk_profile.confidence=high"],
        ))
        assert rc == 0
        art = art_lib.discover_artifacts(project_root, artifact_type="requirement")[0]
        assert art.frontmatter.get("risk_profile") == {"confidence": "high"}

    def test_create_set_dotted_unknown_head_errors(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _base_args(
            set_fields=["not_a_map.x=1"],
        ))
        assert rc == 1
        out = capsys.readouterr().out
        assert "not a known nested-map field" in out
