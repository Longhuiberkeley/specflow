"""Regression: list-valued frontmatter fields must normalize scalar strings.

YAML parses ``tags: a,b`` (no brackets/quotes) as the scalar string ``"a,b"``,
not a list. Before normalization ``Artifact.tags`` returned that string raw, and
``list(artifact.tags)`` (used by ``learning.extract_prevention_pattern``)
char-split it into individual characters — silently corrupting PREV
``applies_to.tags``. The same scalar hazard crashes the
``thinking_techniques`` consumers (``existing + techniques`` -> ``str + list``
``TypeError``) and silently zero-credits ``output_files``.

See ``_normalize_str_list`` in :mod:`specflow.lib.artifacts`.
"""
from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import learning as learn_lib


def _artifact(tags):
    return art_lib.Artifact(
        path=Path("artifact.md"),
        frontmatter={
            "id": "DEF-1",
            "title": "T",
            "type": "defect",
            "status": "closed",
            "tags": tags,
        },
        body="",
    )


def _scaffold(tmp: Path) -> Path:
    """Minimal project: requirement + story schemas, config, spec/story dirs."""
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    for art_type, prefix in [("requirement", "REQ"), ("story", "STORY")]:
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump(
                {
                    "type": art_type,
                    "prefix": prefix,
                    "allowed_status": {"draft": [], "approved": [], "open": [], "closed": []},
                    "allowed_link_roles": ["implements", "verifies"],
                }
            ),
            encoding="utf-8",
        )
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "t", "created": "2026-01-01"}, "artifact_types": ["requirement", "story"], "active_packs": []}),
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "executing", "history": []}), encoding="utf-8"
    )
    for sub in ["_specflow/specs/requirements", "_specflow/work/stories"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


class TestTagsNormalization:
    def test_scalar_string_splits_into_list(self):
        assert _artifact("dota2,spine,launchd").tags == ["dota2", "spine", "launchd"]

    def test_list_passes_through_stripped(self):
        assert _artifact(["a", " b ", ""]).tags == ["a", "b"]

    def test_none_yields_empty(self):
        assert _artifact(None).tags == []

    def test_missing_key_yields_empty(self):
        a = art_lib.Artifact(
            path=Path("x.md"),
            frontmatter={"id": "D", "type": "defect", "status": "closed"},
            body="",
        )
        assert a.tags == []

    def test_extract_prevention_pattern_does_not_char_split(self):
        """The actual reported bug: a defect with scalar tags fed to PREV
        extraction must not produce per-character tags."""
        defect = _artifact("dota2,spine,launchd,binding,incident")
        pattern = learn_lib.extract_prevention_pattern(defect, "Prevent X", "Verify X")
        tags = pattern["applies_to"]["tags"]
        # Real tags, not char-split ('d','o','t','a','2',',',...).
        assert tags == ["dota2", "spine", "launchd", "binding", "incident"]
        assert "," not in tags  # the char-split tell
        assert all(len(t) > 1 for t in tags)  # no single-char fragments


class TestParseSetFieldsTags:
    def test_set_tags_scalar_string_normalizes(self):
        out = art_lib.parse_set_fields(["tags=dota2,spine"])
        assert out["tags"] == ["dota2", "spine"]

    def test_set_tags_json_list_preserved(self):
        out = art_lib.parse_set_fields(['tags=["a","b"]'])
        assert out["tags"] == ["a", "b"]

    def test_set_tags_empty_string_yields_empty_list(self):
        out = art_lib.parse_set_fields(["tags="])
        assert out["tags"] == []

    def test_set_thinking_techniques_scalar_normalizes(self):
        """Same-class write hazard: --set thinking_techniques=a,b must persist a
        list, not the scalar string that later TypeErrors on str+list concat."""
        out = art_lib.parse_set_fields(["thinking_techniques=premortem,devils_advocate"])
        assert out["thinking_techniques"] == ["premortem", "devils_advocate"]
        assert isinstance(out["thinking_techniques"], list)

    def test_set_output_files_scalar_normalizes(self):
        out = art_lib.parse_set_fields(["output_files=src/x.py,src/y.py"])
        assert out["output_files"] == ["src/x.py", "src/y.py"]

    def test_dotted_list_key_not_normalized(self):
        """Dotted keys target nested-map fields and are left to the merge logic;
        the list-normalization only applies to the flat key form."""
        out = art_lib.parse_set_fields(["tags.x=a"])
        assert out == {"tags": {"x": "a"}}


class TestNormalizeStrListEdgeCases:
    def test_empty_and_whitespace_strings(self):
        assert art_lib._normalize_str_list("") == []
        assert art_lib._normalize_str_list("   ") == []

    def test_tags_with_internal_spaces_kept_as_one(self):
        assert art_lib._normalize_str_list("a b, c") == ["a b", "c"]

    def test_tuple_input(self):
        assert art_lib._normalize_str_list(("a", "b")) == ["a", "b"]

    def test_none_element_dropped_not_stringified(self):
        """str(None) is the truthy 'None', so a null list element must be
        dropped explicitly rather than promoted to a phantom 'None' tag."""
        assert art_lib._normalize_str_list(["a", None, "b"]) == ["a", "b"]

    def test_unexpected_type_yields_empty(self):
        assert art_lib._normalize_str_list(42) == []
        assert art_lib._normalize_str_list({"a": 1}) == []

    def test_property_does_not_mutate_frontmatter(self):
        a = _artifact("a,b")
        _ = a.tags
        # The raw scalar must remain untouched on disk/in-memory.
        assert a.frontmatter["tags"] == "a,b"


class TestChecklistTagMatchingWithScalar:
    """WARNING-2: a checklist/PREV whose YAML tags parsed as a scalar string
    must still match an artifact via the normalized path."""

    def test_match_tags_with_normalized_scalar(self):
        from specflow.lib.checklists import match_tags

        artifact_tags = ["dota2", "spine"]
        scalar_checklist_tags = "dota2,spine"  # what YAML hands us for `tags: dota2,spine`
        # Without normalization, set("dota2,spine") char-splits and never matches.
        assert match_tags(artifact_tags, art_lib._normalize_str_list(scalar_checklist_tags)) is True


class TestWarning2ChecklistBoundaryRegression:
    """Pin the WARNING-2 fix sites (checklists.py _load_shared_checklists /
    _load_learned_patterns normalize applies_to.tags) at their real boundary.
    Reverting either normalization flips a scalar-tagged checklist/PREV from
    matching to silently not loading."""

    def test_shared_checklist_with_scalar_applies_to_tags_loads(self, tmp_path: Path):
        from specflow.lib.checklists import _load_shared_checklists

        root = _scaffold(tmp_path)
        shared_dir = root / ".specflow" / "checklists" / "shared"
        shared_dir.mkdir(parents=True, exist_ok=True)
        (shared_dir / "domain.yaml").write_text(
            yaml.dump(
                {
                    "id": "CKL-SHARED-1",
                    "name": "domain doctrine",
                    "applies_to": {"tags": "dota2,spine", "types": ["story"]},  # SCALAR tags
                    "items": [{"id": "CKL-SHARED-1-01", "check": "domain check", "severity": "warning"}],
                }
            ),
            encoding="utf-8",
        )
        artifact = art_lib.Artifact(
            path=Path("story.md"),
            frontmatter={"id": "STORY-1", "type": "story", "status": "draft", "tags": ["dota2"]},
            body="",
        )
        items = _load_shared_checklists(root, artifact)
        assert len(items) == 1  # would be 0 if the scalar char-splits (no match)

    def test_learned_pattern_with_scalar_applies_to_tags_loads(self, tmp_path: Path):
        from specflow.lib.checklists import _load_learned_patterns

        root = _scaffold(tmp_path)
        learned_dir = root / ".specflow" / "checklists" / "learned"
        learned_dir.mkdir(parents=True, exist_ok=True)
        (learned_dir / "PREV-001.yaml").write_text(
            yaml.dump(
                {
                    "id": "PREV-001",
                    "name": "learned prev",
                    "applies_to": {"tags": "dota2,spine"},  # SCALAR tags
                    "items": [{"id": "PREV-001-01", "check": "prev check", "severity": "warning"}],
                }
            ),
            encoding="utf-8",
        )
        artifact = art_lib.Artifact(
            path=Path("story.md"),
            frontmatter={"id": "STORY-1", "type": "story", "status": "draft", "tags": ["dota2"]},
            body="",
        )
        items = _load_learned_patterns(root, artifact)
        assert len(items) == 1  # would be 0 if the scalar char-splits


class TestWarning1IndexConsistencyRegression:
    """Pin the WARNING-1 fix sites: update_artifact (artifacts.py index write)
    and create_artifact must persist NORMALIZED tags to _index.yaml, matching
    rebuild_index (which writes via the normalized .tags property)."""

    def test_update_artifact_normalizes_scalar_tags_in_index(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        created = art_lib.create_artifact(root, "requirement", title="T", body="b", status="draft")
        assert created["ok"]
        art_id = created["id"]

        # Plant a scalar tags value via the programmatic update path (fm[key]=value
        # writes it raw); the index write at update_artifact must normalize it.
        res = art_lib.update_artifact(root=root, artifact_id=art_id, tags="alpha,beta")
        assert res["ok"]

        index_path = root / "_specflow" / "specs" / "requirements" / "_index.yaml"
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        assert index["artifacts"][art_id]["tags"] == ["alpha", "beta"]  # list, not "alpha,beta"

        art = art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))
        assert art.tags == ["alpha", "beta"]  # round-trip parity

    def test_create_artifact_normalizes_scalar_tags_in_index(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        # Programmatic caller passing a scalar string — create must normalize at
        # both the frontmatter write and the index write.
        created = art_lib.create_artifact(
            root, "requirement", title="T", body="b", status="draft", tags="alpha,beta"
        )
        assert created["ok"]
        art_id = created["id"]

        index_path = root / "_specflow" / "specs" / "requirements" / "_index.yaml"
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        assert index["artifacts"][art_id]["tags"] == ["alpha", "beta"]

        art = art_lib.parse_artifact(Path(created["path"]))
        assert art.tags == ["alpha", "beta"]
        # Frontmatter itself is normalized too (create write site).
        assert art.frontmatter["tags"] == ["alpha", "beta"]


class TestThinkingTechniquesNoCrash:
    """The centerpiece regression: a scalar thinking_techniques value (from
    --set thinking_techniques=a,b persisted raw, or a hand-edit) must NOT crash
    the review/update merge paths with str+list TypeError."""

    def test_property_normalizes_scalar(self):
        a = art_lib.Artifact(
            path=Path("x.md"),
            frontmatter={"id": "S", "type": "story", "thinking_techniques": "premortem,devils_advocate"},
            body="",
        )
        assert a.thinking_techniques == ["premortem", "devils_advocate"]

    def test_record_techniques_does_not_crash_on_scalar(self, tmp_path: Path):
        from specflow.commands.artifact_review import _record_techniques_on_artifacts

        root = _scaffold(tmp_path)
        created = art_lib.create_artifact(root, "story", title="T", body="b", status="draft")
        assert created["ok"]
        art_id = created["id"]
        # Persist a scalar (the hazard form) via the programmatic update path.
        art_lib.update_artifact(root=root, artifact_id=art_id, thinking_techniques="premortem,devils_advocate")

        art = art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))
        # Before the fix this raised: "premortem,devils_advocate" + [...] -> TypeError.
        _record_techniques_on_artifacts(root, [art], ["red_blue_team"])

        after = art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))
        assert after.thinking_techniques == ["premortem", "devils_advocate", "red_blue_team"]


class TestOutputFilesScalarCredit:
    """output_files carries the same scalar hazard; it must credit a file given
    a scalar rather than silently zero-counting."""

    def test_property_normalizes_scalar(self):
        a = art_lib.Artifact(
            path=Path("x.md"),
            frontmatter={"id": "S", "type": "story", "output_files": "src/x.py,src/y.py"},
            body="",
        )
        assert a.output_files == ["src/x.py", "src/y.py"]

    def test_expand_output_files_credits_scalar(self, tmp_path: Path):
        from specflow.lib.files import expand_output_files

        root = tmp_path / "proj"
        (root / "src").mkdir(parents=True)
        (root / "src" / "x.py").write_text("x = 1", encoding="utf-8")
        # A hand-edited scalar `output_files: src/x.py` must credit the file.
        credited = expand_output_files(root, "src/x.py")
        assert (root / "src" / "x.py").resolve() in credited
