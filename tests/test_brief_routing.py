"""Router honesty for `specflow brief --next` (STORY-715, F-002 / F-007 / F-038
and the discover lean path).

Pure tests of ``brief._next_skill_recommendation`` + the shared story-progress
helper that ``status`` reuses, so the two dashboards cannot drift apart again.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from specflow.commands import brief as brief_cmd
from specflow.commands import status as status_cmd


class _Link:
    def __init__(self, target: str, role: str) -> None:
        self.target = target
        self.role = role


def _art(
    artifact_id: str,
    status: str,
    title: str | None = None,
    links: list[_Link] | None = None,
    frontmatter: dict | None = None,
    tags: list[str] | None = None,
) -> SimpleNamespace:
    ns = SimpleNamespace(
        id=artifact_id, status=status, suspect=False,
        links=links or [], frontmatter=frontmatter or {}, tags=tags or [],
        path=Path(f"/fake/{artifact_id}.md"), body="",
    )
    if title is not None:
        ns.title = title
    return ns


def _next(phase: str, artifacts: list, next_wave: list[str] | None = None, **kw) -> str:
    return brief_cmd._next_skill_recommendation(phase, artifacts, [], next_wave or [], **kw)


# ── F-002: "Continue /specflow-execute" with zero approved stories ──────────

def _dogfood_mix() -> list[SimpleNamespace]:
    """This repo on 2026-10-08 before STORY-707..719 were approved: 102
    verified / 70 implemented / 4 deprecated / 0 approved — scaled down."""
    return (
        [_art(f"STORY-{i:03d}", "verified") for i in range(1, 11)]
        + [_art(f"STORY-{i:03d}", "implemented") for i in range(11, 18)]
        + [_art(f"STORY-{i:03d}", "deprecated") for i in range(18, 20)]
        + [_art("UT-001", "verified")]
    )


def test_story_progress_counts_done_and_non_terminal():
    p = brief_cmd.story_progress(_dogfood_mix())
    assert p == {"total": 19, "approved": 0, "done": 17, "non_terminal": 17}
    assert brief_cmd.stories_complete(p)


def test_story_progress_not_complete_with_an_approved_story():
    p = brief_cmd.story_progress(_dogfood_mix() + [_art("STORY-099", "approved")])
    assert p["approved"] == 1
    assert not brief_cmd.stories_complete(p)


def test_story_progress_empty_backlog_is_not_complete():
    assert not brief_cmd.stories_complete(brief_cmd.story_progress([]))


def test_executing_verified_implemented_deprecated_mix_routes_to_ship_not_execute():
    """The F-002 reproduction: verified stories were not counted as done and
    deprecated ones stayed in the denominator, so the router fell through to
    'Continue /specflow-execute' with nothing executable."""
    out = _next("executing", _dogfood_mix())
    assert "Continue /specflow-execute" not in out
    assert "/specflow-execute" not in out.split("\n")[0]
    assert "/specflow-ship" in out


def test_executing_fallback_never_says_continue_execute():
    """Approved-plus stories exist, no wave, backlog not complete (one story
    is still approved but blocked — e.g. a dependency cycle) → the router
    names the blockage instead of a bare 'continue'."""
    arts = [_art("STORY-001", "implemented"), _art("STORY-002", "approved")]
    out = _next("executing", arts, next_wave=[])
    assert "Continue /specflow-execute" not in out
    assert "no executable wave" in out
    assert "/specflow-plan" in out


def test_executing_no_approved_no_done_backlog_routes_to_plan_reconcile():
    """Nothing approved, nothing executable, backlog not complete (a mix of
    implemented and cancelled-but-not-terminal statuses cannot happen; model
    it with an unknown status) → reconcile via plan."""
    arts = [_art("STORY-001", "implemented"), _art("STORY-002", "blocked")]
    out = _next("executing", arts)
    assert "Continue /specflow-execute" not in out
    assert "No approved stories ready to execute" in out
    assert "/specflow-plan" in out


def test_planning_complete_backlog_ignores_deprecated_stories():
    arts = [_art("REQ-001", "approved"), _art("ARCH-001", "approved")] + _dogfood_mix()
    out = _next("planning", arts)
    assert "existing stories are complete" in out
    assert "/specflow-artifact-review" in out


def test_status_suggest_action_shares_the_helper():
    """status._suggest_action with zero executable stories must not say
    execute either: review/ship when done, plan-reconcile otherwise."""
    done = status_cmd._suggest_action(
        Path("."), "executing", {"REQ": 1, "STORY": 19},
        approved_stories=17, executable_stories=0, stories_done=True,
    )
    assert "/specflow-execute" not in done
    assert "/specflow-artifact-review" in done and "/specflow-ship" in done
    pending = status_cmd._suggest_action(
        Path("."), "executing", {"REQ": 1, "STORY": 3},
        approved_stories=2, executable_stories=0, stories_done=False,
    )
    assert "/specflow-execute" not in pending
    assert "/specflow-plan" in pending
    ready = status_cmd._suggest_action(
        Path("."), "executing", {"REQ": 1, "STORY": 3},
        approved_stories=2, executable_stories=1, stories_done=False,
    )
    assert "/specflow-execute" in ready


# ── Lean path: approved REQ + approved STORY implementing it, no ARCH ──────

def _lean_project(story_status: str = "approved") -> list[SimpleNamespace]:
    return [
        _art("REQ-001", "approved", title="Dark mode"),
        _art("STORY-001", story_status, title="Add dark mode",
             links=[_Link("REQ-001", "implements")]),
    ]


def test_lean_path_routes_discovering_to_execute():
    out = _next("discovering", _lean_project())
    assert "/specflow-execute" in out
    assert "/specflow-plan" not in out
    assert "Lean path" in out


def test_lean_path_routes_specifying_to_execute():
    out = _next("specifying", _lean_project())
    assert "/specflow-execute" in out
    assert "/specflow-plan" not in out


def test_lean_path_implemented_only_routes_to_review_not_execute():
    """Every covering STORY already implemented → zero executable stories, so
    the lean path must not say execute (F-002); review then ship instead."""
    out = _next("discovering", _lean_project("implemented"))
    assert "/specflow-execute" not in out
    assert "/specflow-artifact-review" in out and "/specflow-ship" in out
    assert "/specflow-plan" not in out
    assert brief_cmd._lean_path_state(_lean_project("implemented")) == "done"


def test_lean_path_verified_story_counts_as_covered():
    out = _next("specifying", _lean_project("verified"))
    assert "/specflow-artifact-review" in out
    assert "/specflow-plan" not in out and "/specflow-execute" not in out


def test_lean_path_mixed_approved_and_implemented_routes_to_execute():
    arts = _lean_project("implemented") + [
        _art("REQ-002", "approved"),
        _art("STORY-002", "approved", links=[_Link("REQ-002", "implements")]),
    ]
    assert brief_cmd._lean_path_state(arts) == "execute"
    assert "/specflow-execute" in _next("discovering", arts)


def test_approved_req_without_story_still_routes_to_plan():
    out = _next("discovering", [_art("REQ-001", "approved")])
    assert "/specflow-plan" in out
    assert "/specflow-execute" not in out


def test_lean_path_needs_every_lean_req_covered():
    arts = _lean_project() + [_art("REQ-002", "approved", title="Uncovered")]
    out = _next("discovering", arts)
    assert "/specflow-plan" in out
    assert "/specflow-execute" not in out


def test_lean_path_ignores_draft_story():
    out = _next("discovering", _lean_project("draft"))
    assert "/specflow-plan" in out


def test_lean_path_not_taken_when_an_arch_exists():
    """A REQ realized by an ARCH is on the full path: plan, not execute."""
    arts = _lean_project() + [
        _art("ARCH-001", "approved", links=[_Link("REQ-001", "derives_from")]),
    ]
    out = _next("discovering", arts)
    assert "/specflow-plan" in out
    assert "Lean path" not in out


def test_lean_path_req_refined_by_arch_is_not_lean():
    arts = [
        _art("REQ-001", "approved", links=[_Link("ARCH-001", "refined_by")]),
        _art("STORY-001", "approved", links=[_Link("REQ-001", "implements")]),
        _art("ARCH-001", "approved"),
    ]
    assert not brief_cmd._lean_path_ready(arts)


# ── F-007: open DEFs, draft DECs, unexecuted work in verifying/complete ─────

def test_open_defects_note_lists_ids_and_caps():
    arts = [_art("STORY-001", "approved")] + [
        _art(f"DEF-00{i}", s) for i, s in enumerate(("open", "fixing", "investigating", "open"), 1)
    ] + [_art("DEF-009", "closed"), _art("DEF-010", "wontfix")]
    out = _next("executing", arts, next_wave=["STORY-001"])
    assert "4 open DEF(s)" in out
    assert "DEF-001, DEF-002, DEF-003, +1 more" in out
    assert "DEF-009" not in out and "DEF-010" not in out


def test_draft_dec_note_carries_exact_consent_command():
    arts = [
        _art("STORY-001", "approved"),
        _art("DEC-084", "draft", title="Deferred enhancements"),
        _art("DEC-085", "approved", title="In force"),
    ]
    out = _next("executing", arts, next_wave=["STORY-001"])
    assert "1 draft DEC(s) await approval" in out
    assert "DEC-084 — Deferred enhancements → `specflow update DEC-084 --status approved`" in out
    assert "DEC-085" not in out
    assert "--yes" not in out


def test_draft_dec_note_skips_auto_generated_records():
    arts = [_art("DEC-001", "draft", tags=["change-record", "auto-generated"])]
    out = _next("executing", arts)
    assert "draft DEC" not in out


def test_draft_unreviewed_dec_is_listed_once(tmp_path: Path):
    """A fresh DEC is draft AND review_status: unreviewed — review precedes
    approval, so the unreviewed/blast-radius note owns it and the draft-DEC
    consent note does not repeat it."""
    arts = [
        _art("DEC-001", "draft", title="New call",
             frontmatter={"id": "DEC-001", "review_status": "unreviewed"}),
    ]
    out = _next("executing", arts, root=tmp_path)
    assert "1 unreviewed DEC(s) (DEC-001)" in out
    assert "draft DEC(s) await approval" not in out
    assert out.count("DEC-001") == 1


def test_verifying_phase_surfaces_unexecuted_approved_work():
    arts = [
        _art("STORY-001", "verified"), _art("STORY-002", "approved"),
        _art("SPIKE-005", "approved"), _art("SPIKE-001", "completed"),
    ]
    out = _next("verifying", arts)
    assert out.startswith("Ready to release")
    assert "2 approved STORY/SPIKE(s) unexecuted (STORY-002, SPIKE-005)" in out
    assert "/specflow-execute" in out


def test_complete_phase_same_note():
    out = _next("complete", [_art("STORY-002", "approved")])
    assert "1 approved STORY/SPIKE(s) unexecuted" in out


def test_executing_phase_does_not_add_unexecuted_note():
    out = _next("executing", [_art("STORY-002", "approved")], next_wave=["STORY-002"])
    assert "unexecuted" not in out


def test_quiet_project_adds_no_notes(tmp_path: Path):
    """A healthy project (closed DEFs, approved DECs, nothing left behind)
    prints the core line and nothing else — no cry-wolf."""
    arts = [
        _art("REQ-001", "approved"), _art("ARCH-001", "approved"),
        _art("STORY-001", "approved"), _art("DEF-001", "closed"),
        _art("DEC-001", "approved", frontmatter={"review_status": "reviewed"}),
    ]
    out = _next("executing", arts, next_wave=["STORY-001"], root=tmp_path)
    assert out == "Next wave ready (1 stories) → /specflow-execute (or `specflow go`)."
    verifying = _next("verifying", [_art("STORY-001", "verified")], root=tmp_path)
    assert "\n" not in verifying


# ── F-038: the router names the skill, not the raw CLI ─────────────────────

def test_suspects_route_to_change_impact_review_skill():
    suspect = _art("REQ-001", "approved")
    suspect.suspect = True
    out = brief_cmd._next_skill_recommendation("executing", [suspect], [suspect], [])
    assert out.startswith("1 suspect(s) open → /specflow-change-impact-review")
    assert "specflow defect-from-suspect <ID> --req <REQ>" in out


def test_unreviewed_decs_route_to_change_impact_review_skill(tmp_path: Path):
    dec = _art("DEC-002", "approved", frontmatter={"review_status": "unreviewed"})
    out = _next("executing", [dec], root=tmp_path)
    assert "unreviewed DEC(s) (DEC-002)" in out
    assert "→ /specflow-change-impact-review" in out
    assert "`specflow change-impact`" in out


# ── F-035: draft ARCH/DDD consent lines only where they gate (planning) ─────

def test_planning_lists_draft_arch_and_ddd_consent_lines():
    arts = [
        _art("REQ-001", "approved"), _art("ARCH-001", "approved"),
        _art("ARCH-039", "draft", title="Findings engine"),
        _art("DDD-033", "draft", title="Ratchet internals"),
        _art("STORY-001", "approved"),
    ]
    out = _next("planning", arts)
    assert "specflow approve --type ARCH" in out
    assert "ARCH-039 — Findings engine" in out
    assert "specflow approve --type DDD" in out
    assert "DDD-033 — Ratchet internals" in out


def test_executing_does_not_list_draft_arch_consent_lines():
    arts = [
        _art("ARCH-039", "draft", title="Findings engine"),
        _art("STORY-001", "approved"),
    ]
    out = _next("executing", arts, next_wave=["STORY-001"])
    assert "ARCH-039" not in out
    assert "approve --type ARCH" not in out


# ── F-068: draft tests carrying passing verify evidence ─────────────────────

def _test_art(test_id: str, status: str, exit_code: int | None, run_at: str | None = "2026-09-13T06:05:26Z"):
    fm = {"id": test_id, "verify_command": "pytest -q"}
    if run_at:
        fm["verify_run_at"] = run_at
    if exit_code is not None:
        fm["verify_run_exit_code"] = exit_code
    return _art(test_id, status, frontmatter=fm)


def test_draft_tests_with_passing_evidence_are_surfaced_capped_at_five():
    arts = [_test_art(f"UT-{i:03d}", "draft", 0) for i in range(80, 87)]
    out = _next("executing", arts)
    assert "7 draft test(s) carry passing verify evidence" in out
    assert "UT-080, UT-081, UT-082, UT-083, UT-084, +2 more" in out
    # Per-ID consent: the batch `approve --type UT` would also sweep drafts
    # that carry no evidence, so it is named only as the thing to avoid.
    assert "`specflow update <ID> --status approved`" in out
    assert "would also sweep drafts without evidence" in out


def test_draft_tests_with_failing_or_no_evidence_stay_silent():
    arts = [
        _test_art("UT-001", "draft", 1),
        _test_art("UT-002", "draft", None, run_at=None),
        _test_art("STORY-001", "draft", 0),
    ]
    out = _next("executing", arts)
    assert "passing verify evidence" not in out
    # and the existing needs-verify line does not fire for drafts either
    assert "verify_run evidence" not in out


def test_implemented_test_with_evidence_is_not_a_draft_line():
    out = _next("executing", [_test_art("UT-001", "implemented", 0)])
    assert "draft test" not in out
    assert "verify_run evidence" not in out
