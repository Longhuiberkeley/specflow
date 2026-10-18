"""STORY-746 (SPIKE-008 D3): every baseline name in shipped prose is creatable.

`specflow baseline create` rejects names that are not semver-shaped
(lib/baselines.py `_validate_name`, CHL-351). Prose that tells an agent to run
`baseline create adoption-v0` therefore fails on the first try. This guard
scans the same roots as tests/test_prose_cli_surface.py plus all of docs/
(the frozen docs/.archive excepted), extracts every `baseline create <name>`,
substitutes placeholders with "1", and asserts the real validator accepts the
name. It also pins the corrected adoption/autoresearch/ops pack sentences.
"""

from __future__ import annotations

import re
from pathlib import Path

from specflow.lib.baselines import _validate_name
from test_prose_cli_surface import EXCLUDED_DIRS, REPO_ROOT, SUFFIXES, _iter_files

DOCS = REPO_ROOT / "docs"
PACKS = REPO_ROOT / "src" / "specflow" / "packs"
ADOPT = PACKS / "adoption"
ADOPT_SKILL = ADOPT / "skills" / "specflow-adopt"
AUTORESEARCH = PACKS / "autoresearch" / "skills" / "specflow-autoresearch"

_CREATE = re.compile(r"(?<![\w-])baseline create\s+([^\s`\"'|)]+)")
# <tag>, <n>, ${VAR}, $VAR and ALL-CAPS argparse metavars (TAG) are placeholders.
_PLACEHOLDERS = [
    re.compile(r"<[^<>\s]*>"),
    re.compile(r"\$\{[^}]*\}|\$\w+"),
    re.compile(r"^[A-Z][A-Z_]+$"),
]


def _scan_files() -> list[Path]:
    seen: dict[Path, None] = dict.fromkeys(_iter_files())
    for path in sorted(DOCS.rglob("*")):
        if not path.is_file() or path.suffix not in SUFFIXES:
            continue
        if any(parent in EXCLUDED_DIRS for parent in path.parents):
            continue
        seen.setdefault(path, None)
    return list(seen)


def baseline_names(text: str) -> list[tuple[int, str]]:
    """(line number, placeholder-substituted name) for each `baseline create`."""
    out: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in _CREATE.finditer(line):
            name = m.group(1).rstrip(".,;:")
            if name.startswith("-"):
                continue  # `baseline create --help` and the like
            for pattern in _PLACEHOLDERS:
                name = pattern.sub("1", name)
            out.append((lineno, name))
    return out


def violations(paths: list[Path]) -> list[str]:
    bad: list[str] = []
    for path in paths:
        for lineno, name in baseline_names(path.read_text(encoding="utf-8")):
            error = _validate_name(name)
            if error is not None:
                bad.append(f"{path}:{lineno}: `baseline create {name}` — {error}")
    return bad


def test_scanner_sees_the_known_sites():
    found = {
        (p.relative_to(REPO_ROOT).as_posix(), name)
        for p in _scan_files()
        for _, name in baseline_names(p.read_text(encoding="utf-8"))
    }
    assert ("src/specflow/packs/adoption/README.md", "v0.0.0-adoption.1") in found
    assert ("src/specflow/packs/adoption/skills/specflow-adopt/SKILL.md", "v0.0.0-adoption.1") in found
    assert len(found) >= 5, found


def test_shipped_baseline_names_are_valid():
    bad = violations(_scan_files())
    assert not bad, "invalid baseline name(s) in prose:\n" + "\n".join(bad)


def test_seeded_violation_fails(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text(
        "Run `specflow baseline create adoption-v0 --evidence`.\n"
        "Then `specflow baseline create v0.0.0-adoption.<n> --evidence`.\n"
        "And `specflow baseline create TAG`.\n",
        encoding="utf-8",
    )
    bad = violations([doc])
    assert len(bad) == 1 and "adoption-v0" in bad[0], bad


def test_legacy_names_are_not_semver():
    # The reason for D3: the old names are rejected; the new one is accepted.
    assert _validate_name("adoption-v0") is not None
    assert _validate_name("adoption-auth-v0") is not None
    assert _validate_name("v0.0.0-adoption.1") is None
    assert _validate_name("v0.0.0-adoption.12") is None


# ── text pins for the corrected pack prose ─────────────────────────────────

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_merge_recipe_uses_specflow_merge():
    # SPIKE-008 R2-001
    text = _read(ADOPT_SKILL / "references" / "incremental-adoption-protocol.md")
    assert "`specflow merge <loser-ID> <survivor-ID>` retargets every inbound link" in text
    assert "`specflow update <survivor-ID> --output-files '<existing>,<loser paths>'`" in text
    assert "Never repoint links with `update --links`" in text
    assert "Never move or delete artifact files by hand" in text
    assert "_specflow/archive/" not in text


def test_phase4_seeds_source_fingerprints_and_drops_rationale_registration():
    # SPIKE-008 R2-007, R2-008
    skill = _read(ADOPT_SKILL / "SKILL.md")
    assert "`specflow baseline create v0.0.0-adoption.<n> --evidence`" in skill
    assert "Then run `specflow fingerprint-refresh --source`" in skill
    assert "anchors audits with `specflow project-audit --baseline adoption-v0`" in skill
    assert "docs surface registered" not in skill
    protocol = _read(ADOPT_SKILL / "references" / "as-built-baseline-protocol.md")
    assert "in the baseline `--rationale`" not in protocol
    assert "it reads no baseline" in protocol


def test_lint_expectations_name_the_ratchet():
    # SPIKE-008 R2-009
    text = _read(ADOPT_SKILL / "references" / "as-built-baseline-protocol.md")
    assert "none block" not in text
    assert "`specflow findings-baseline update --accept-new`" in text
    assert "escalating at `implemented`/`verified`" in text


def test_adopt_status_depth_vocabulary():
    # SPIKE-008 R2-010: one depth rule shared by adopt status and brief
    text = _read(ADOPT_SKILL / "references" / "incremental-adoption-protocol.md")
    assert "`skeleton` = anything less, including the bare skeleton-sweep ARCH" in text
    assert "`specflow brief` counts its skeleton/full split by the same rule." in text
    assert "isolated" not in text


def test_autoresearch_recipes():
    # SPIKE-008 R2-011, R2-012, R2-022, R2-023
    links = '{"target":"COMP-001","role":"belongs_to"},{"target":"LOOP-001","role":"condenses"}'
    assert links in _read(AUTORESEARCH / "SKILL.md")
    assert links in _read(AUTORESEARCH / "references" / "finding-generation-protocol.md")
    rolling = _read(AUTORESEARCH / "references" / "rolling-evaluation.md")
    assert "specflow create --type loop" not in rolling
    assert "Phase 2e" not in rolling
    loop = _read(AUTORESEARCH / "references" / "autonomous-loop-protocol.md")
    assert '--set condensation_briefs.10="..."' in loop
    assert "`features`, `model`, `params`, `validation`, `analysis`" in loop
    assert "auto-detect the only COMP" in _read(AUTORESEARCH / "SKILL.md")


def test_ops_flagged_monitor_nags_until_resolved():
    # SPIKE-008 R2-024
    readme = _read(PACKS / "ops" / "README.md")
    assert "a `flagged` MONITOR keeps nagging until it is resolved" in readme
    assert "resolved (or credited) MONITOR stops nagging" not in readme
    skill = _read(PACKS / "ops" / "skills" / "specflow-ops" / "SKILL.md")
    assert "(status `flagged` until resolved, credited or not; or `health: breached`, not yet `resolved` and not credited)" in skill


def test_autoresearch_completed_comp_frozen_is_agent_rule():
    # SPIKE-008 R2-023
    skill = _read(AUTORESEARCH / "SKILL.md")
    assert "The CLI does not refuse a LOOP or EXPT on a completed or paused COMP, so keeping it frozen is your rule." in skill


def test_adopt_skill_sentences():
    skill = _read(ADOPT_SKILL / "SKILL.md")
    # SPIKE-008 R2-007: widened globs are re-seeded for drift
    assert "then `specflow fingerprint-refresh --source ARCH-NNN` so the newly covered files are tracked for drift" in skill
    # SPIKE-008 R2-009: skeleton warnings escalate under the findings ratchet
    assert "Once a findings baseline exists, these warnings escalate and a full lint exits 1" in skill
    assert "record the skeleton debt with `specflow findings-baseline update --accept-new` (approval-gated)" in skill
    # SPIKE-008 R2-010: adopt status depth vocabulary
    assert "`skeleton` = anything less, including the bare skeleton-sweep ARCH" in skill
    assert "`specflow brief` counts skeleton/full ARCHs by the same rule." in skill
    assert "isolated" not in skill
    # SPIKE-008 R2-007: resume reads the semver-named (or legacy) baseline
    assert "Read the highest `v0.0.0-adoption.<n>` baseline under `.specflow/baselines/` (or a legacy `adoption-v0`)" in skill
    assert "`adoption-*` baseline" not in skill
    # SPIKE-008 R2-008: docs surface needs no registration
    assert "recognized automatically — there is nothing to register" in skill
