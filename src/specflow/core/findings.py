"""Typed finding records (REQ-053 AC3).

A :class:`Finding` is one lint or audit result: which rule fired, on which
subjects, how severe, and whether it is *escalating* (debt that must not
grow — compared against the committed findings baseline) or *accounting*
(a standing fact that never gates). Rendered text stays the check's own
business (AC4); policy reads only these records.

Identity for the findings baseline is ``(rule_id, subjects)``. Volatile
values (counts, ages, hashes, samples) live in ``args`` so they never churn
the baseline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["blocking", "warning", "info"]
Klass = Literal["escalating", "accounting"]

SEVERITIES: tuple[str, ...] = ("blocking", "warning", "info")


@dataclass(frozen=True, order=True)
class Finding:
    rule_id: str
    subjects: tuple[str, ...]
    severity: str
    klass: str
    args: tuple[tuple[str, Any], ...] = ()
    text: str | None = field(default=None, compare=False)

    @property
    def key(self) -> tuple[str, tuple[str, ...]]:
        """Baseline identity: ``(rule_id, subjects)``, args excluded."""
        return (self.rule_id, self.subjects)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "subjects": list(self.subjects),
            "severity": self.severity,
            "class": self.klass,
            "args": dict(self.args),
        }


def make(
    rule_id: str,
    subjects: tuple[str, ...] | list[str] | str,
    severity: str,
    *,
    text: str | None = None,
    subject_status: str | None = None,
    lean_path: bool = False,
    pre_planning: bool = False,
    **args: Any,
) -> Finding:
    """Build a Finding; its class comes from the one policy table.

    ``subject_status``, ``lean_path`` and ``pre_planning`` are classification inputs only
    (``policy.klass_for``): they are not stored, so they never touch the
    key or the args.
    """
    from specflow.core.policy import klass_for

    if severity not in SEVERITIES:
        raise ValueError(f"unknown severity {severity!r}")
    if isinstance(subjects, str):
        subjects = (subjects,)
    frozen_args = tuple(sorted((k, _freeze(v)) for k, v in args.items()))
    klass = klass_for(rule_id, subject_status=subject_status, lean_path=lean_path,
                      pre_planning=pre_planning)
    return Finding(rule_id, tuple(subjects), severity, klass, frozen_args, text)


def _freeze(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze(v) for v in value))
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    return value


_AUDIT_SEVERITY = {"error": "blocking", "warn": "warning", "info": "info"}
_LEADING_ID = re.compile(r"^\[?([A-Z][A-Z0-9]*-[A-Za-z0-9.-]+)\]?")


def from_audit_dict(d: dict[str, Any]) -> Finding:
    """Typed record for a project-audit finding dict (REQ-053 AC3).

    rule_id is ``audit/<concern>`` (``audit/lens:<category>`` when no
    concern is set — only a concern can be accounting); the subject is the
    leading artifact id of the message when there is one, else the lens name.
    """
    concern = str(d.get("concern") or f"lens:{d.get('category') or 'general'}")
    message = str(d.get("message", ""))
    m = _LEADING_ID.match(message)
    subject = m.group(1) if m else f"lens:{d.get('lens') or d.get('category') or concern}"
    severity = _AUDIT_SEVERITY.get(str(d.get("severity")), "info")
    return make(f"audit/{concern}", (subject,), severity, message=re.sub(r"\d+", "#", message))


def counts(findings: list[Finding]) -> tuple[int, int]:
    """``(blocking, warning)`` counts — must equal the check's own counters."""
    blocking = sum(1 for f in findings if f.severity == "blocking")
    warning = sum(1 for f in findings if f.severity == "warning")
    return blocking, warning
