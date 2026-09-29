"""STORY-689 / STORY-690: core skill text, always-on context, and docs match the CLI.

Deterministic text/structure guards over the shipped skills, the always-on
agent-context block, the autoresearch snippet, and docs/. They pin the
behaviour fixes (ship ordering, output_files recording, catalog lens keys,
five-section BP body, ...) so the prose cannot drift from the CLI again.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specflow.lib import practices as practices_lib
from specflow.lib.techniques import ALL_LENS_NAMES

_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _ROOT / "src/specflow/templates/skills/shared"
_LIVE = _ROOT / ".claude/skills"
_CONTEXT = _ROOT / "src/specflow/templates/agent-context.md"


def _read(rel: str) -> str:
    return (_SKILLS / rel).read_text(encoding="utf-8")


def _all_skill_text() -> dict[str, str]:
    return {
        str(p.relative_to(_SKILLS)): p.read_text(encoding="utf-8")
        for p in sorted(_SKILLS.rglob("*.md"))
    }


class TestShip:
    def test_gate_and_verification_precede_baseline(self):
        text = _read("specflow-ship/SKILL.md")
        baseline = text.index("baseline create")
        for marker in (
            "project-audit --quick",
            "document-changes",
            "risk-tier",
            "temporal_drift",
        ):
            assert text.index(marker) < baseline, f"{marker} must precede baseline create"

    def test_phase_complete_and_handoff_follow_baseline(self):
        text = _read("specflow-ship/SKILL.md")
        assert text.index('phase-set complete --reason "released <tag>"') > text.index(
            "baseline create"
        )
        assert "Handoff" in text

    def test_router_style_and_guardrails_kept(self):
        text = _read("specflow-ship/SKILL.md")
        assert len(text.splitlines()) < 50
        assert "No self-approval" in text
        assert re.search(r"only the direct user'?s explicit go-ahead", text)
        assert "`blocking` → stop" in text


class TestExecuteAndReview:
    def test_execute_records_output_files_after_implemented(self):
        text = _read("specflow-execute/SKILL.md")
        assert text.index("--status implemented") < text.index("--output-files")

    def test_artifact_review_uses_composite_and_trace(self):
        text = _read("specflow-artifact-review/SKILL.md")
        assert "specflow artifact-review <ARTIFACT_ID>" in text
        assert "specflow trace <ARTIFACT_ID>" in text
        assert "`specflow status`" not in text
        assert "Blocking issues → report and stop" not in text
        assert "name the artifact under review" in text
        # the learned-pattern rule is stated once
        assert text.count("learned prevention patterns") == 1


class TestLensKeys:
    _FILES = (
        "specflow-change-impact-review/SKILL.md",
        "specflow-references/references/adversarial-lenses.md",
        "specflow-execute/SKILL.md",
    )

    @pytest.mark.parametrize("rel", _FILES)
    def test_no_hyphenated_lens_keys_in_code_spans(self, rel):
        hyphenated = {n.replace("_", "-") for n in ALL_LENS_NAMES if "_" in n}
        for span in re.findall(r"`([^`]+)`", _read(rel)):
            assert span not in hyphenated, f"{rel}: `{span}` is not a catalog key"

    def test_every_backticked_lens_key_is_in_catalog(self):
        text = _read("specflow-change-impact-review/SKILL.md")
        step4 = text[text.index("4. **Pick 2-3 lenses**") : text.index("5. **File findings")]
        keys = set(re.findall(r"`([a-z_]+)`", step4))
        assert keys and keys <= ALL_LENS_NAMES

    def test_no_dollar_spend_example(self):
        text = _read("specflow-references/references/adversarial-lenses.md")
        assert "spend" not in text.lower()
        assert not re.search(r"\$\d", text)
        assert "Subagents: 3" in text


class TestBestPractices:
    def test_deprecated_handbook_alias_gone_from_skills(self):
        for rel, text in _all_skill_text().items():
            assert "handbook generate" not in text, rel

    @pytest.mark.parametrize(
        "rel",
        ["specflow-discover/SKILL.md", "specflow-plan/SKILL.md"],
    )
    def test_discover_and_plan_seed_validate_and_link(self, rel):
        text = _read(rel)
        assert "practices seed" in text
        assert "practices validate" in text
        assert ":guided_by" in text and "BP-ID" in text

    def test_init_uses_practices_seed(self):
        assert "practices seed" in _read("specflow-init/SKILL.md")

    def test_bp_authoring_matches_five_section_anatomy(self):
        text = _read("specflow-references/references/bp-authoring.md")
        headings = re.findall(r"^## (.+)$", text.split("## Creation Command")[0], re.M)
        body_sections = [h for h in headings if h in practices_lib.PRACTICE_SECTIONS]
        assert tuple(body_sections) == practices_lib.PRACTICE_SECTIONS

    def test_bp_authoring_draft_provenance_and_spec_side_guided_by(self):
        text = _read("specflow-references/references/bp-authoring.md")
        assert "--status approved" not in text.split("specflow update <BP-ID>")[0]
        assert "--set provenance=" in text
        assert "--add-link BP-004:guided_by" in text
        assert "Step 3F.5" not in text and "Step 2.5" not in text

    def test_bp_authoring_is_reachable(self):
        assert "bp-authoring.md" in _read("specflow-discover/SKILL.md")
        assert "bp-authoring.md" in _read("specflow-plan/SKILL.md")

    def test_link_roles_has_bp_row(self):
        text = _read("specflow-plan/references/link-roles.md")
        assert "REQ/ARCH/STORY → BP" in text


class TestAlwaysOnContext:
    def test_hand_edit_rule_is_narrowed(self):
        text = _CONTEXT.read_text(encoding="utf-8")
        assert "Never hand-edit `.specflow/` (config, state" not in text
        assert re.search(r"Never hand-edit `\.specflow/` state, schemas, or indexes", text)
        assert "adapter, doc, or pack-author skill" in text

    def test_bare_cascade_status_clause_dropped(self):
        assert "cascade-status" not in _CONTEXT.read_text(encoding="utf-8")

    def test_no_self_approval_context_rule_kept(self):
        text = _CONTEXT.read_text(encoding="utf-8")
        assert "not consent" in text and "go-ahead" in text

    def test_autoresearch_exit_3_says_proceed(self):
        text = (_ROOT / "src/specflow/packs/autoresearch/pack.yaml").read_text(encoding="utf-8")
        assert re.search(r"exit 3 is warnings only, so proceed", text)


class TestInit:
    def test_no_truncated_sections(self):
        text = _read("specflow-init/SKILL.md")
        for line in text.splitlines():
            assert not line.rstrip().endswith("marker:"), line
        section = text[text.index("#### 4a."):text.index("### 5.")]
        assert "<!-- SpecFlow section" in section
        assert "AGENTS.md" in section and "GEMINI.md" in section

    def test_domain_labels_match_loader_stems(self):
        text = _read("specflow-init/SKILL.md")
        line = next(l for l in text.splitlines() if "What type of project is this" in l)
        labels = set(re.findall(r"`([a-z][a-z-]*)`", line))
        stems = {p.stem for p in (_ROOT / "src/specflow/templates/checklists/domain").glob("*.yaml")}
        stems |= {p.stem for p in (_SKILLS / "specflow-discover/references/domain-checklists").glob("*.md")}
        assert labels and labels <= stems

    def test_ci_default_consistent_and_pack_author_route(self):
        text = _read("specflow-init/SKILL.md")
        assert "`--no-ci` only if the user chose None" in text
        assert 'default to "None" unless the user mentions "GitHub"' not in text
        assert "/specflow-pack-author" in text
        line = next(l for l in text.splitlines() if "optional preset" in l)
        assert "iso26262-demo" in line and "never offer it" in line


class TestSetupSkills:
    def test_pack_author_install_message_names_working_path(self):
        text = _read("specflow-pack-author/SKILL.md")
        assert ".specflow/packs/{name}/" in text
        assert "src/specflow" not in text
        assert "STORY-" not in text

    def test_pack_author_never_teaches_hand_copy_into_specflow(self):
        # STORY-681/690 fix pass: init --preset (merge mode) installs on an
        # initialised project; refresh --packs --force syncs later edits.
        skill = _read("specflow-pack-author/SKILL.md")
        structure = _read("specflow-pack-author/references/pack-structure.md")
        for text in (skill, structure):
            assert "`specflow init --preset {name}`" in text
            assert "specflow refresh --packs --force" in text
        assert "copy `standards/*.yaml`" not in skill
        assert "by hand." not in structure

    def test_init_tldr_preset_line_matches_pack(self):
        # STORY-695 AC1: the pack is a two-clause delta, not a longer reply.
        line = next(
            l for l in _read("specflow-init/SKILL.md").splitlines()
            if "optional preset" in l
        )
        assert "tldr-communication" in line
        assert "10-line" not in line and "longer" not in line
        assert "ELI5" in line

    def test_init_validates_seeded_practices(self):
        # STORY-689 AC4: init seeds AND validates BPs, like discover/plan.
        text = _read("specflow-init/SKILL.md")
        assert "practices seed" in text and "practices validate" in text

    def test_large_documents_moved_to_reference(self):
        skill = _read("specflow-pack-author/SKILL.md")
        assert "Phase 2: Section-by-Section" not in skill
        assert "Section-by-Section Extraction" in _read(
            "specflow-pack-author/references/large-documents.md"
        )
        assert "references/large-documents.md" in skill

    def test_pack_docs_cover_manifest_and_schema_fields(self):
        structure = _read("specflow-pack-author/references/pack-structure.md")
        for token in ("adds_skills", "context_snippet", "375", "`category`"):
            assert token in structure, token
        schema = _read("specflow-pack-author/references/schema-template.md")
        for token in ("category", "allowed_review_status", "specflow schema <type>"):
            assert token in schema, token
        assert "can transition to nothing" not in schema
        assert "can go back to draft" not in schema

    def test_adapter_drops_repo_only_paths_and_states_advisory_vs_blocking(self):
        skill = _read("specflow-adapter/SKILL.md")
        ref = _read("specflow-adapter/references/adapter-framework.md")
        for text in (skill, ref):
            assert "docs/authoring" not in text
            assert "ADAPTER_REGISTRY" not in text
            assert "src/specflow" not in text
        assert "Standards Setup" not in skill and "### 2E. Status" not in skill
        assert "**advisory**" in skill and "**blocking**" in skill
        adapters = (_ROOT / "src/specflow/templates/adapters.yaml").read_text(encoding="utf-8")
        assert "docs/authoring" not in adapters and "standards:" not in adapters

    def test_doc_and_start_routing(self):
        doc = _read("specflow-doc/SKILL.md")
        assert "README" in doc.split("---")[1] and "stale" in doc.split("---")[1]
        assert "DEC-082" not in doc
        start = _read("specflow-start/SKILL.md")
        assert "/specflow-init" in start
        assert "V-model tests" not in start
        assert "/specflow-change-impact-review" in start

    def test_approval_presentation_contract_line(self):
        text = _read("specflow-references/references/approval-presentation.md")
        assert "On approve I will run: specflow update <ID> --status <next>. Impact:" in text
        assert "specflow-audit" in text.split("## Why This Exists")[0]
        assert "**read-only**" in text


class TestNoRepoInternals:
    def test_no_repo_internal_ids_or_paths_in_shipped_skills(self):
        pat = re.compile(r"\b(?:STORY-6\d\d|REQ-0[4-9]\d|DEC-08\d|DEC-09\d|D-\d{2})\b|src/specflow/")
        for rel, text in _all_skill_text().items():
            assert not pat.search(text), f"{rel}: {pat.search(text).group(0)}"


class TestDocs:
    def test_no_uv_run_teaching_outside_decisions(self):
        offenders = []
        for p in list((_ROOT / "docs").rglob("*.md")) + [_ROOT / "README.md"]:
            if p.name == "decisions.md":
                continue
            if "uv run" in p.read_text(encoding="utf-8"):
                offenders.append(str(p.relative_to(_ROOT)))
        assert not offenders, offenders

    def test_ci_example_bootstraps_via_uvx_from_git(self):
        text = (_ROOT / "docs/authoring-an-adapter.md").read_text(encoding="utf-8")
        assert "uvx --from git+https://github.com/Longhuiberkeley/specflow@v" in text


class TestMirror:
    def test_live_skills_are_byte_identical(self):
        for p in _SKILLS.rglob("*"):
            if p.is_file():
                live = _LIVE / p.relative_to(_SKILLS)
                assert live.is_file(), live
                assert live.read_bytes() == p.read_bytes(), live
