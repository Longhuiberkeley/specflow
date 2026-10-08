"""Exit-code policy over typed findings (REQ-053 AC1/AC7, DEC-099).

The single classification table lives here: a rule is *accounting* (a
standing fact that never gates) or *escalating* (debt the committed findings
baseline must not let grow). ``decide`` turns findings plus the baseline into
a verdict; it reads nothing else, so the same repository, as-of date and
baseline always give the same exit code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from specflow.core.findings import Finding

# Accounting rules never escalate. Match is by exact rule_id or by the
# check prefix before "/". Former STORY-663 exemptions (fingerprint-drift,
# bp-application, dead-oracle) plus the ARCH-039 heuristics: a regex over
# prose must not decide an exit code. Spike staleness is accounting (it is
# clock-driven); spike zombie / repeated-topic stay escalating (structural).
# Authoring-shape advice (story-size, wave-cycles/fan-in) is accounting: how
# a story is sliced or how many dependencies it declares is a planning
# judgement, never debt the ratchet should hold (amending DEC to
# DEC-099, v1.17.2). A circular dependency stays escalating.
ACCOUNTING_RULES: frozenset[str] = frozenset({
    "fingerprint-drift",
    "bp-application",
    "dead-oracle",
    "conflicts",
    "quality",
    "ac-observable",
    "dec-risk-profile",
    "spike-lifecycle/stale",
    "story-size",
    "wave-cycles/fan-in",
})

# Staged rules: a test-linkage gap is a standing fact while the subject is
# still being authored (draft/approved) and becomes debt only once the
# subject CLAIMS done-ness (implemented/verified). The check passes the
# subject's status; a staged rule emitted without one is accounting, because
# nothing has been claimed yet. Keys never change with the stage, so a row
# that escalates later matches the baseline entry it had before.
STAGED_RULES: frozenset[str] = frozenset({
    "coverage/no-test",
    "links/missing-v-pair",
    "bp-application/no-test",
})
CLAIMED_STATUSES: frozenset[str] = frozenset({"implemented", "verified"})

# Lean-path rules: an approved REQ realised directly by a STORY (via
# ``implements``/``derives_from``) with no ARCH between them is a legitimate
# scale-adaptive shape, not debt. The check passes ``lean_path=True`` when
# such a STORY exists; the warning still prints (accounting). A REQ with no
# STORY at all keeps ``coverage/no-story`` escalating.
LEAN_PATH_RULES: frozenset[str] = frozenset({"coverage/no-arch"})

# Pre-planning rules: before the project has entered the planning phase
# (state ``current`` is ``idle`` or ``discovering``), an approved REQ with
# nothing downstream is the expected state of discovery, not debt — the
# STORY/ARCH arrive in planning. The rows still print (accounting); from
# planning on they escalate as before. The check passes ``pre_planning``
# only for REQ subjects.
PRE_PLANNING_RULES: frozenset[str] = frozenset({
    "coverage/no-arch",
    "coverage/no-story",
    "links/orphan",
})
PRE_PLANNING_PHASES: frozenset[str] = frozenset({"idle", "discovering"})


def klass_for(
    rule_id: str,
    *,
    subject_status: str | None = None,
    lean_path: bool = False,
    pre_planning: bool = False,
) -> str:
    """``accounting`` or ``escalating`` for a rule id (default escalating).

    ``subject_status`` stages the rules in ``STAGED_RULES`` (escalating only
    at ``implemented``/``verified``); ``lean_path`` makes ``LEAN_PATH_RULES``
    accounting; ``pre_planning`` makes ``PRE_PLANNING_RULES`` accounting
    while the project has not entered planning. ``audit/<concern>`` rules defer to project-audit's documented
    ``_ACCOUNTING_CONCERNS`` table, so lint and audit share one decision.
    """
    if rule_id in ACCOUNTING_RULES:
        return "accounting"
    if rule_id in STAGED_RULES:
        return "escalating" if subject_status in CLAIMED_STATUSES else "accounting"
    if rule_id in LEAN_PATH_RULES and lean_path:
        return "accounting"
    if rule_id in PRE_PLANNING_RULES and pre_planning:
        return "accounting"
    prefix, _, rest = rule_id.partition("/")
    if prefix == "audit":
        from specflow.commands.project_audit import _ACCOUNTING_CONCERNS

        return "accounting" if rest in _ACCOUNTING_CONCERNS else "escalating"
    return "accounting" if prefix in ACCOUNTING_RULES else "escalating"


Key = tuple[str, tuple[str, ...]]


@dataclass
class Verdict:
    exit_code: int
    blocking: list[Finding] = field(default_factory=list)
    new: list[Finding] = field(default_factory=list)
    known: list[Finding] = field(default_factory=list)
    resolved: list[Key] = field(default_factory=list)
    ratchet_on: bool = False


def escalating_warnings(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "warning" and f.klass == "escalating"]


def decide(
    findings: list[Finding],
    baseline: frozenset[Key] | None,
    *,
    full_run: bool,
) -> Verdict:
    """Exit 1 on any blocking finding; on a full run with a baseline, also on
    any escalating warning whose key is not in the baseline. ``baseline=None``
    (no file) turns the ratchet off until the v1.18.0 sunset."""
    blocking = sorted(f for f in findings if f.severity == "blocking")
    verdict = Verdict(exit_code=1 if blocking else 0, blocking=blocking)
    if not full_run or baseline is None:
        return verdict
    verdict.ratchet_on = True
    produced: set[Key] = set()
    for f in sorted(escalating_warnings(findings)):
        if f.key in produced:
            continue
        produced.add(f.key)
        (verdict.known if f.key in baseline else verdict.new).append(f)
    verdict.resolved = sorted(baseline - produced)
    if verdict.new:
        verdict.exit_code = 1
    return verdict
