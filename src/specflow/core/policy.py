"""Exit-code policy over typed findings (REQ-053 AC1/AC7, DEC-FINDINGS-79d8).

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
ACCOUNTING_RULES: frozenset[str] = frozenset({
    "fingerprint-drift",
    "bp-application",
    "dead-oracle",
    "conflicts",
    "quality",
    "ac-observable",
    "dec-risk-profile",
    "spike-lifecycle/stale",
})


def klass_for(rule_id: str) -> str:
    """``accounting`` or ``escalating`` for a rule id (default escalating).

    ``audit/<concern>`` rules defer to project-audit's documented
    ``_ACCOUNTING_CONCERNS`` table, so lint and audit share one decision.
    """
    if rule_id in ACCOUNTING_RULES:
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
