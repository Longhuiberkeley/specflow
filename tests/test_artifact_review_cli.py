"""End-to-end `specflow artifact-review` at quick / normal / deep (STORY-707).

Before this file nothing drove ``artifact_review.run()`` through the CLI, so
three regressions went unobserved: the deep pass auto-stamped
``thinking_techniques`` before any lens was applied (silencing the
``unchallenged`` lint), every call ran ~1 s of dead-code/similarity scans whose
results were discarded, and an id-less call rewrote every artifact file via an
implicit ``--all`` checklist sweep.

The second half covers the two artifact writers outside artifacts.py that the
sweep reaches (STORY-707, DDD-034 I5): ``update_artifact_checklists_applied``
(checklist-run) and ``retro_link`` (detect / adopt) used plain
``Path.write_text`` and re-serialised the whole frontmatter, so a
``checklist-run --all`` reformatted flow lists and quoting on every artifact.
Now each patches only its own block under the mutation lock, an unchanged
record is a no-op, and ``checklist-run --proactive`` prints the per-item
``Hint:`` lines it used to build and drop.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
from pathlib import Path

import pytest
import yaml

from specflow import cli
from specflow.commands import artifact_review
from specflow.commands import init as init_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import locks as locks_lib
from specflow.lib import orphans
from specflow.lib.checklists import update_artifact_checklists_applied
from specflow.lib.frontmatter_patch import patch_block, split_frontmatter
from specflow.lib.techniques import (
    TechniquePrompt,
    build_technique_prompt,
    generate_technique_prompts,
)

TARGET = "REQ-001"
PKG_SCHEMAS = Path(art_lib.__file__).resolve().parent.parent / "templates" / "schemas"


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    monkeypatch.chdir(root)
    assert cli.main(["create", "--type", "requirement", "--title", "Login",
                     "--body", "## Acceptance Criteria\n1. The system shall log in.\n"]) == 0
    # Approved + never challenged: the ``unchallenged`` lint must keep firing
    # after a deep review until the host agent records the lenses itself.
    assert cli.main(["update", TARGET, "--status", "approved"]) == 0
    assert cli.main(["create", "--type", "requirement", "--title", "Logout",
                     "--body", "## Acceptance Criteria\n1. The system shall log out.\n"]) == 0
    return root


def _tree(root: Path) -> dict[str, str]:
    """rel path -> sha256 for every file under ``_specflow/`` (artifact store)."""
    out: dict[str, str] = {}
    for p in sorted((root / "_specflow").rglob("*")):
        if p.is_file():
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _changed(before: dict[str, str], after: dict[str, str]) -> set[str]:
    return {k for k in set(before) | set(after) if before.get(k) != after.get(k)}


def _techniques(root: Path, art_id: str) -> list[str]:
    art = art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))
    return art.thinking_techniques


def _target_rel(root: Path) -> str:
    return art_lib.resolve_link_target(root, TARGET).relative_to(root).as_posix()


# ---------------------------------------------------------------------------
# F-139: the three depths through the real CLI


def test_quick_runs_lint_and_checklist_for_the_target_only(project: Path, capsys):
    before = _tree(project)
    rc = cli.main(["artifact-review", TARGET])
    out = capsys.readouterr().out
    assert rc in (0, 2)
    assert "SpecFlow Checklist Run" in out
    assert "— Login" in out and "reviewing 1 artifact(s)" in out
    assert "Agent-judged checks for" not in out  # normal-depth section
    assert "SYSTEM:" not in out                  # deep-depth section
    # Only the reviewed artifact may change (its checklists_applied record).
    assert _changed(before, _tree(project)) <= {_target_rel(project)}


def test_normal_prints_the_agent_judged_prompt(project: Path, capsys):
    before = _tree(project)
    rc = cli.main(["artifact-review", TARGET, "--depth", "normal"])
    out = capsys.readouterr().out
    assert rc in (0, 2)
    assert "SpecFlow Artifact Review — Depth: normal" in out
    assert f"Agent-judged checks for {TARGET}" in out
    assert f"Artifact ID: {TARGET}" in out and "Checks to judge:" in out
    assert "SYSTEM:" not in out
    assert _changed(before, _tree(project)) <= {_target_rel(project)}


def test_deep_prints_lens_prompts_and_the_recording_command(project: Path, capsys):
    before = _tree(project)
    assert _techniques(project, TARGET) == []
    rc = cli.main(["artifact-review", TARGET, "--depth", "deep", "--techniques", "premortem"])
    out = capsys.readouterr().out
    assert rc in (0, 2)
    assert f"┌─ premortem → {TARGET}" in out
    assert "SYSTEM:" in out and "USER:" in out
    assert TARGET in out.split("USER:", 1)[1]
    # F-131: the CLI never records a lens it did not apply; it hands the agent
    # the exact recording command instead.
    assert f"specflow update {TARGET} --thinking-techniques premortem" in out
    assert _techniques(project, TARGET) == []
    assert _changed(before, _tree(project)) <= {_target_rel(project)}


def test_deep_leaves_the_unchallenged_lint_firing(project: Path, capsys):
    assert cli.main(["artifact-review", TARGET, "--depth", "deep",
                     "--techniques", "premortem,devils_advocate"]) in (0, 2)
    capsys.readouterr()
    cli.main(["artifact-lint"])
    out = capsys.readouterr().out
    line = next((ln for ln in out.splitlines() if f"⚠ {TARGET} [approved] has no thinking_techniques" in ln), None)
    assert line is not None and "never challenged" in line, out
    # ...and the printed command is what clears it.
    assert cli.main(["update", TARGET, "--thinking-techniques", "premortem,devils_advocate"]) == 0
    assert _techniques(project, TARGET) == ["premortem", "devils_advocate"]
    capsys.readouterr()
    cli.main(["artifact-lint"])
    assert f"⚠ {TARGET} [approved] has no thinking_techniques" not in capsys.readouterr().out


def test_deep_with_all_prints_one_recording_line_per_target(project: Path, capsys):
    assert cli.main(["artifact-review", "--all", "--depth", "deep",
                     "--techniques", "premortem"]) in (0, 2)
    out = capsys.readouterr().out
    assert "specflow update REQ-001 --thinking-techniques premortem" in out
    assert "specflow update REQ-002 --thinking-techniques premortem" in out
    assert _techniques(project, "REQ-001") == [] and _techniques(project, "REQ-002") == []


def test_recording_command_quotes_shell_metacharacters():
    arts = [art_lib.Artifact(path=Path("x.md"), frontmatter={"id": "REQ-007", "type": "requirement",
                                                               "title": "t"}, body="")]
    assert artifact_review._recording_command(arts, ["premortem", "steelman"]) == [
        "specflow update REQ-007 --thinking-techniques premortem,steelman"]
    # The spelling this repo's own frontmatter already uses.
    (line,) = artifact_review._recording_command(arts, ["devil's-advocate", "premortem"])
    import shlex
    assert shlex.split(line) == ["specflow", "update", "REQ-007", "--thinking-techniques",
                                 "devil's-advocate,premortem"]


# ---------------------------------------------------------------------------
# F-019: no id and no --all never sweeps (and so never writes) the whole store


@pytest.mark.parametrize("depth", ["quick", "normal", "deep"])
def test_idless_review_without_all_is_lint_only(project: Path, capsys, depth: str):
    before = _tree(project)
    rc = cli.main(["artifact-review", "--depth", depth, "--techniques", "premortem"])
    out = capsys.readouterr().out
    assert rc in (0, 2)
    assert "ran lint only" in out and "--all" in out
    assert "SpecFlow Checklist Run" not in out
    assert "SYSTEM:" not in out
    assert _changed(before, _tree(project)) == set()
    assert not list((project / ".specflow" / "checklist-log").glob("*.yaml"))


def test_explicit_all_still_sweeps(project: Path, capsys):
    before = _tree(project)
    rc = cli.main(["artifact-review", "--all"])
    out = capsys.readouterr().out
    assert rc in (0, 2)
    assert "reviewing 2 artifact(s)" in out
    changed = _changed(before, _tree(project))
    assert changed == {
        art_lib.resolve_link_target(project, "REQ-001").relative_to(project).as_posix(),
        art_lib.resolve_link_target(project, "REQ-002").relative_to(project).as_posix(),
    }


# ---------------------------------------------------------------------------
# F-132: no silent hygiene scans


def test_review_runs_no_hygiene_scan(project: Path, monkeypatch, capsys):
    from specflow.lib import analysis

    def boom(*_a, **_k):  # pragma: no cover - must never be reached
        raise AssertionError("artifact-review must not run detect scans")

    monkeypatch.setattr(analysis, "find_dead_code", boom)
    monkeypatch.setattr(analysis, "find_similar_functions", boom)
    assert not hasattr(artifact_review, "_run_hygiene_silently")
    assert cli.main(["artifact-review", TARGET, "--depth", "deep", "--techniques", "premortem"]) in (0, 2)
    assert "Dead Code Detected" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# F-138: schema bootstrap resolves the template from the package, not the cwd


def _bare_root(tmp_path: Path) -> Path:
    root = tmp_path / "consumer"
    (root / ".specflow" / "schema").mkdir(parents=True)
    (root / ".specflow" / "schema" / "requirement.yaml").write_text(
        (PKG_SCHEMAS / "requirement.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    return root


def test_bootstrap_schemas_from_package_without_src_tree(tmp_path: Path, monkeypatch):
    root = _bare_root(tmp_path)
    monkeypatch.chdir(tmp_path)  # cwd is not the SpecFlow checkout
    assert not (root / "src").exists()

    artifact_review._bootstrap_challenge_schema(root)
    artifact_review._bootstrap_review_schema(root)

    for name in ("challenge", "review"):
        dst = root / ".specflow" / "schema" / f"{name}.yaml"
        assert dst.exists(), name
        assert dst.read_bytes() == (PKG_SCHEMAS / f"{name}.yaml").read_bytes()
    index = root / "_specflow" / "specs" / "reviews" / "_index.yaml"
    assert yaml.safe_load(index.read_text(encoding="utf-8")) == {"artifacts": {}, "next_id": 1}


def test_bootstrap_schema_never_overwrites_an_existing_schema(tmp_path: Path):
    root = _bare_root(tmp_path)
    custom = root / ".specflow" / "schema" / "challenge.yaml"
    custom.write_text("type: challenge\nstatuses: [open]\n", encoding="utf-8")
    artifact_review._bootstrap_challenge_schema(root)
    assert custom.read_text(encoding="utf-8") == "type: challenge\nstatuses: [open]\n"


def test_bootstrap_schema_is_a_noop_without_schema_dir(tmp_path: Path):
    root = tmp_path / "nothing"
    root.mkdir()
    artifact_review._bootstrap_challenge_schema(root)
    artifact_review._bootstrap_review_schema(root)
    assert list(root.rglob("*")) == []


# ---------------------------------------------------------------------------
# F-139: technique prompt builders (shape only, no snapshots)


def _art() -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path("x.md"),
        frontmatter={"id": "REQ-042", "type": "requirement", "title": "Answer"},
        body="The system shall answer.",
    )


@pytest.mark.parametrize("name", ["premortem", "devils_advocate", "red_blue_team", "assumption_surfacing"])
def test_dedicated_builders_produce_a_prompt_naming_the_artifact(name: str):
    p = build_technique_prompt(name, _art(), "- some checklist item")
    assert isinstance(p, TechniquePrompt)
    assert p.technique == name and p.artifact_id == "REQ-042"
    assert p.system_prompt.strip() and p.user_prompt.strip() and p.diversity_hint.strip()
    assert "REQ-042" in p.user_prompt


def test_catalog_lens_falls_back_to_generic_prompt_and_unknown_is_none():
    p = build_technique_prompt("temporal_drift", _art(), "ctx")
    assert p is not None and p.artifact_id == "REQ-042" and "REQ-042" in p.user_prompt
    assert build_technique_prompt("not_a_lens", _art(), "ctx") is None


def test_generate_technique_prompts_expands_techniques_times_artifacts():
    arts = [_art(), art_lib.Artifact(path=Path("y.md"),
                                     frontmatter={"id": "REQ-043", "type": "requirement", "title": "B"},
                                     body="b")]
    prompts = generate_technique_prompts(["premortem", "not_a_lens", "devils_advocate"], arts, "ctx")
    assert [(p.technique, p.artifact_id) for p in prompts] == [
        ("premortem", "REQ-042"), ("premortem", "REQ-043"),
        ("devils_advocate", "REQ-042"), ("devils_advocate", "REQ-043"),
    ]


# ===========================================================================
# F-019: the writers the sweep reaches (checklist-run record, retro-link)

_BLOCK = re.compile(r"^checklists_applied:[^\n]*\n(?:(?:[ \t-]|#)[^\n]*\n)*", re.MULTILINE)


@pytest.fixture
def story_project(project: Path) -> Path:
    assert cli.main(["create", "--type", "story", "--title", "Log in", "--links", "REQ-001:implements",
                     "--body", "## Acceptance Criteria\n1. Works.\n"]) == 0
    return project


def _path(root: Path, art_id: str) -> Path:
    return art_lib.resolve_link_target(root, art_id)


def _without_block(text: str) -> str:
    """The file with its ``checklists_applied`` frontmatter block removed."""
    prefix, fm, rest = split_frontmatter(text)
    return prefix + _BLOCK.sub("", fm) + rest


def _applied(text: str) -> list[dict]:
    return yaml.safe_load(split_frontmatter(text)[1]).get("checklists_applied", [])


HAND_WRITTEN = """---
id: REQ-001
title: "Login: the 'quoted' title"
type: requirement
status: draft
tags: [auth, login]   # flow list stays a flow list
suspect: false
links: []
created: '2026-01-01'
fingerprint: sha256:0000000000000000
version: 1
---

# Login

Body with --- a dash run that is not a fence.
"""


@pytest.fixture
def no_raw_artifact_writes(monkeypatch):
    """Fail if any ``.md`` under ``_specflow/`` is written with ``Path.write_text``
    directly (the atomic path writes a temp file and ``os.replace``s it)."""
    orig = pathlib.Path.write_text

    def guarded(self, data, *a, **kw):
        if self.suffix == ".md" and "_specflow" in self.parts:
            raise AssertionError(f"raw write_text on artifact {self}")
        return orig(self, data, *a, **kw)

    monkeypatch.setattr(pathlib.Path, "write_text", guarded)


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# --- update_artifact_checklists_applied


def test_only_the_checklists_applied_block_changes(project: Path, no_raw_artifact_writes):
    path = _path(project, TARGET)
    _write(path, HAND_WRITTEN)  # the style a YAML round-trip used to destroy

    update_artifact_checklists_applied(project, TARGET, "check-REQ-001", "2026-02-02T00:00:00Z")
    after = path.read_text(encoding="utf-8")
    assert _without_block(after) == HAND_WRITTEN
    assert _applied(after) == [{"checklist": "check-REQ-001", "timestamp": "2026-02-02T00:00:00Z"}]
    assert "tags: [auth, login]   # flow list stays a flow list" in after
    assert "Body with --- a dash run" in after

    # Upsert: same record, new timestamp -> block replaced in place, nothing else.
    update_artifact_checklists_applied(project, TARGET, "check-REQ-001", "2026-03-03T00:00:00Z")
    again = path.read_text(encoding="utf-8")
    assert _without_block(again) == HAND_WRITTEN
    assert _applied(again) == [{"checklist": "check-REQ-001", "timestamp": "2026-03-03T00:00:00Z"}]

    # A second checklist appends to the block; the first entry survives.
    update_artifact_checklists_applied(project, TARGET, "gate-x", "2026-03-03T00:00:00Z")
    assert [e["checklist"] for e in _applied(path.read_text(encoding="utf-8"))] == ["check-REQ-001", "gate-x"]


def test_leading_blank_lines_are_tolerated_and_kept(project: Path):
    """parse_artifact strips before looking for the fence; the writer must
    accept the same files, and give the blank lines back untouched."""
    path = _path(project, TARGET)
    _write(path, "\n\n" + HAND_WRITTEN)
    assert art_lib.parse_artifact(path) is not None
    update_artifact_checklists_applied(project, TARGET, "check-REQ-001", "2026-02-02T00:00:00Z")
    after = path.read_text(encoding="utf-8")
    assert after.startswith("\n\n---\nid: REQ-001\n")
    assert _without_block(after) == "\n\n" + HAND_WRITTEN
    assert [e["checklist"] for e in _applied(after)] == ["check-REQ-001"]


def test_malformed_entries_and_in_block_comments_are_dropped_with_the_block(project: Path):
    """Non-mapping entries are not records (nothing to upsert) and a comment
    inside the block belongs to the record; both go when the block is
    rewritten. A comment after the block belongs to the next key and stays."""
    path = _path(project, TARGET)
    _write(path, HAND_WRITTEN.replace("version: 1\n", (
        "checklists_applied:\n"
        "- not-a-record\n"
        "# inside the block\n"
        "- checklist: gate-x\n"
        "  timestamp: '2026-01-01T00:00:00Z'\n"
        "# belongs to version\n"
        "version: 1\n")))
    update_artifact_checklists_applied(project, TARGET, "check-REQ-001", "2026-02-02T00:00:00Z")
    after = path.read_text(encoding="utf-8")
    assert _applied(after) == [
        {"checklist": "gate-x", "timestamp": "2026-01-01T00:00:00Z"},
        {"checklist": "check-REQ-001", "timestamp": "2026-02-02T00:00:00Z"},
    ]
    assert "not-a-record" not in after and "# inside the block" not in after
    assert "# belongs to version\nversion: 1\n" in after
    assert after.count("checklists_applied:") == 1
    assert art_lib.parse_artifact(path).frontmatter["version"] == 1


def test_unchanged_record_is_a_no_op(project: Path):
    path = _path(project, TARGET)
    update_artifact_checklists_applied(project, TARGET, "check-REQ-001", "2026-02-02T00:00:00Z")
    before = path.read_bytes()
    stat = path.stat()
    update_artifact_checklists_applied(project, TARGET, "check-REQ-001", "2026-02-02T00:00:00Z")
    assert path.read_bytes() == before
    assert path.stat().st_ino == stat.st_ino  # no os.replace happened either


def test_update_goes_through_the_atomic_locked_writer(project: Path, monkeypatch):
    seen: list[Path] = []
    real = art_lib.write_artifact_text

    def spy(root, path, text):
        seen.append(Path(path))
        real(root, path, text)

    monkeypatch.setattr(art_lib, "write_artifact_text", spy)
    update_artifact_checklists_applied(project, TARGET, "check-REQ-001", "2026-02-02T00:00:00Z")
    assert seen == [_path(project, TARGET)]


@pytest.mark.parametrize("writer", ["checklist", "retro_link"])
def test_writers_read_the_artifact_under_the_mutation_lock(story_project: Path, monkeypatch, writer):
    """The write alone being locked is not enough: a read outside the lock
    lets a concurrent `specflow update` land between read and write and be
    overwritten by the stale copy (DEF-008 shape, DDD-034 I4)."""
    held: list[bool] = []
    real = pathlib.Path.read_text

    def spy(self, *a, **kw):
        if self.suffix == ".md" and "_specflow" in self.parts:
            held.append(locks_lib.lock_held(story_project))
        return real(self, *a, **kw)

    monkeypatch.setattr(pathlib.Path, "read_text", spy)
    if writer == "checklist":
        update_artifact_checklists_applied(story_project, TARGET, "check-REQ-001", "2026-02-02T00:00:00Z")
    else:
        (story_project / "src").mkdir()
        (story_project / "src" / "login.py").write_text("x = 1\n", encoding="utf-8")
        assert orphans.retro_link(story_project, "src/login.py", "STORY-001") is True
    assert held and all(held), f"{writer} read the artifact outside the mutation lock"


def test_checklist_run_all_rewrites_nothing_but_the_record(story_project: Path, capsys, no_raw_artifact_writes):
    store = story_project / "_specflow"
    before = {p: p.read_text(encoding="utf-8") for p in store.rglob("*.md") if not p.name.startswith("_")}
    indexes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in store.rglob("_index.yaml")}

    rc = cli.main(["checklist-run", "--all"])
    capsys.readouterr()
    assert rc in (0, 1)

    for p, text in before.items():
        after = p.read_text(encoding="utf-8")
        assert _without_block(after) == _without_block(text), p
        art_id = yaml.safe_load(split_frontmatter(text)[1])["id"]
        assert [e["checklist"] for e in _applied(after)] == [f"check-{art_id}"]
    for p, digest in indexes.items():
        assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, p


# --- retro_link


def test_retro_link_is_atomic_and_idempotent(story_project: Path, no_raw_artifact_writes):
    (story_project / "src").mkdir()
    (story_project / "src" / "login.py").write_text("x = 1\n", encoding="utf-8")
    path = _path(story_project, "STORY-001")

    assert orphans.retro_link(story_project, "src/login.py", "STORY-001") is True
    first = path.read_bytes()
    assert art_lib.parse_artifact(path).output_files == ["src/login.py"]

    stat = path.stat()
    assert orphans.retro_link(story_project, "src/login.py", "STORY-001") is True
    assert path.read_bytes() == first
    assert path.stat().st_ino == stat.st_ino  # already linked: file untouched


def test_retro_link_patches_only_the_output_files_block(story_project: Path, no_raw_artifact_writes):
    (story_project / "src").mkdir()
    for name in ("a.py", "b.py"):
        (story_project / "src" / name).write_text("", encoding="utf-8")
    path = _path(story_project, "STORY-001")
    hand = HAND_WRITTEN.replace("id: REQ-001", "id: STORY-001").replace("type: requirement", "type: story")
    _write(path, hand)

    assert orphans.retro_link(story_project, "src/a.py", "STORY-001") is True
    after = path.read_text(encoding="utf-8")
    assert after == hand.replace("version: 1\n", "version: 1\noutput_files:\n- src/a.py\n")
    assert "tags: [auth, login]   # flow list stays a flow list" in after

    assert orphans.retro_link(story_project, "src/b.py", "STORY-001") is True
    after = path.read_text(encoding="utf-8")
    assert after == hand.replace("version: 1\n", "version: 1\noutput_files:\n- src/a.py\n- src/b.py\n")
    assert art_lib.parse_artifact(path).output_files == ["src/a.py", "src/b.py"]


def test_retro_link_rejects_unknown_target_and_missing_file(story_project: Path):
    (story_project / "src").mkdir()
    (story_project / "src" / "a.py").write_text("", encoding="utf-8")
    assert orphans.retro_link(story_project, "src/a.py", "STORY-999") is False
    assert orphans.retro_link(story_project, "src/missing.py", "STORY-001") is False


# --- frontmatter_patch helpers


def test_split_frontmatter_round_trips_and_ignores_body_dashes():
    text = "\n---\nid: X\nnote: 'a --- b'\n---\n\n# T\n\n---\n\nrule above\n"
    prefix, fm, rest = split_frontmatter(text)
    assert prefix == "\n---\n" and fm == "id: X\nnote: 'a --- b'\n" and prefix + fm + rest == text
    assert rest.startswith("---\n\n# T")
    assert split_frontmatter("no frontmatter\n") is None
    assert split_frontmatter("---\nid: X\n") is None  # unclosed
    assert split_frontmatter("  ---\nid: X\n---\n") is None  # indented fence is not a fence


def test_patch_block_touches_only_its_key():
    fm = "id: X\ntags: [a, b]  # keep\noutput_files:\n- old.py\n# next key's note\nversion: 2\n"
    out = patch_block(fm, "output_files", ["old.py", "new.py"])
    assert out == "id: X\ntags: [a, b]  # keep\noutput_files:\n- old.py\n- new.py\n# next key's note\nversion: 2\n"
    assert patch_block("id: X\nversion: 2", "output_files", ["n.py"]) == "id: X\nversion: 2\noutput_files:\n- n.py\n"
    assert patch_block("id: X\noutput_files: []\nversion: 2\n", "output_files", []) == "id: X\noutput_files: []\nversion: 2\n"


# ===========================================================================
# F-137: checklist-run --proactive prints the hints

PROACTIVE_CHECKLIST = """id: edge-cases
applies_to:
  tags: [auth]
  types: [requirement]
items:
  - id: EDGE-01
    check: Every external call has a timeout path
    mode: proactive
    severity: warning
    llm_prompt: Enumerate each external dependency and name its timeout handling.
  - id: EDGE-02
    check: Empty input is specified
    mode: proactive
    severity: info
  - id: STD-01
    check: Rationale names the stakeholder
    severity: warning
    llm_prompt: Look for a named stakeholder in the rationale.
"""


@pytest.fixture
def proactive_project(project: Path) -> Path:
    shared = project / ".specflow" / "checklists" / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "edge-cases.yaml").write_text(PROACTIVE_CHECKLIST, encoding="utf-8")
    assert cli.main(["update", TARGET, "--tags", "auth"]) == 0
    return project


def test_proactive_prints_hint_lines_once(proactive_project: Path, capsys):
    capsys.readouterr()
    rc = cli.main(["checklist-run", TARGET, "--proactive"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Proactive challenges (" in out
    assert "⚡ [warning] Every external call has a timeout path" in out
    assert "Hint: Enumerate each external dependency and name its timeout handling." in out
    assert "⚡ [info] Empty input is specified" in out
    # Listed once: not again under the agent-judged section.
    assert out.count("Every external call has a timeout path") == 1
    assert out.count("Empty input is specified") == 1
    # Standard agent-judged items keep their section and carry no hint.
    assert "• [warning] Rationale names the stakeholder" in out
    assert "Hint: Look for a named stakeholder" not in out


def test_without_proactive_flag_items_stay_in_the_agent_judged_list(proactive_project: Path, capsys):
    capsys.readouterr()
    assert cli.main(["checklist-run", TARGET]) == 0
    out = capsys.readouterr().out
    assert "Proactive challenges" not in out
    assert "• [warning] [proactive] Every external call has a timeout path" in out
    assert "Hint:" not in out
