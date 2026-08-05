"""Acceptance-criteria observability accounting (v1.13.1).

This module closes the honest gap between "has ACs" and "has ACs a test could
actually fail on". ``artifact-lint --type acceptance`` checks AC *presence*
(via :mod:`specflow.lib.lint`); this module classifies AC *observability* —
the falsifiability character of each criterion.

ACCOUNTING, NOT POLICING (the project's load-bearing doctrine, BP-005/006):
``classify_ac_observability`` never asserts and never blocks. It surfaces, per
AC item, whether the criterion is **observable** (a test could fail on it),
**aspirational** (vague prose with no testable outcome), or **unclassified**
(domain behaviour the lexicon cannot confirm either way — reported at INFO,
never a defect). Surfacing happens in ``brief`` (one aggregate line) and in
``project-audit`` (an ``ac-observability`` cross-cutting block registered in
``_ACCOUNTING_CONCERNS`` so any signal it emits can NEVER drive exit-2).

ANTI-CRY-WOLF DESIGN (non-negotiable). Crying wolf here means smearing a
legitimate engineering AC as "aspirational". The guard is the classification
*conjunction*:

    observable    — the item has >=1 outcome marker (high-precision lexicon).
    aspirational  — the item has NO outcome marker AND it matches an ambiguity
                    word OR a bare vague verb ("works/handles/succeeds/...").
    unclassified  — everything else (no marker, no ambiguity word, no vague
                    verb) — e.g. domain observables such as "the relay
                    energizes" or "the bus arbitrates the channel".

Both conditions of the conjunction are required for ASPIRATIONAL: a bare verb
alone with a real outcome ("writes the log") is observable; a domain verb with
no outcome and no ambiguity ("the relay energizes") is UNCLASSIFIED, never
aspirational. The observable lexicon is deliberately precision-first — a miss
only demotes an item to UNCLASSIFIED (info), which is safe; the aspirational
lexicon is the one that must not over-fire, and the conjunction is what
prevents it.

ZERO external LLM calls: classification is pure regex/lexicon, deterministic.
"""

from __future__ import annotations

import re

from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib

# Reuse lint.py's AC parsers (the section-finding work) — do NOT re-parse the
# marker/heading logic. The private ``_AC_GIVEN_PATTERN`` is the Given-When-Then
# fallback already used by ``count_acceptance_criteria_items``; accessed as an
# attribute (mirrors ``_ac_coverage_lens`` in project_audit.py).
_AC_GIVEN_PATTERN = lint_lib._AC_GIVEN_PATTERN  # noqa: SLF001 — stable reuse


# ---------------------------------------------------------------------------
# Lexicons
# ---------------------------------------------------------------------------
#
# Outcome markers — each pattern is HIGH-PRECISION evidence that an AC item
# carries a testable outcome. Precision over recall: a false negative only
# demotes an item to UNCLASSIFIED (info), never aspirational. Observable is the
# neutral/good bucket, so over-crediting here is not the cry-wolf failure mode.
#
_OUTCOME_PATTERNS: list[re.Pattern[str]] = [
    # Exit code / return value / process exit.
    re.compile(r"\bexit\s+code\b", re.IGNORECASE),
    re.compile(r"\breturn(?:s|ed|ing)?\s+value\b", re.IGNORECASE),
    re.compile(r"\breturns?\s+exit\b", re.IGNORECASE),
    re.compile(r"\bexits?\s+with\b", re.IGNORECASE),
    # HTTP / status / response code (the numeric value is caught by the digit
    # fallback; these anchor it to a transport context).
    re.compile(r"\bhttps?\b", re.IGNORECASE),
    re.compile(r"\bhttp\s+status\b", re.IGNORECASE),
    re.compile(r"\bstatus\s+code\b", re.IGNORECASE),
    re.compile(r"\bresponse\s+code\b", re.IGNORECASE),
    # Transitive action verbs that produce a checkable signal + an object
    # ("returns the value", "emits an event", "writes the file", ...). Covers
    # base / 3rd-person / past / gerund conjugations so gerund AC prose
    # ("by writing the file") is not missed.
    re.compile(
        r"\b(returns?|returned|returning|emits?|emitted|emitting|"
        r"displays?|displayed|displaying|prints?|printed|printing|"
        r"writes?|wrote|written|writing|creates?|created|creating|"
        r"removes?|removed|removing|deletes?|deleted|deleting|"
        r"generates?|generated|generating|outputs?|outputted|outputting|"
        r"produces?|produced|producing|logs?|logged|logging|"
        r"persists?|persisted|persisting|stores?|stored|storing|"
        r"sends?|sent|sending|publishes?|published|publishing|"
        r"renders?|rendered|rendering)\b\s+\S",
        re.IGNORECASE,
    ),
    # Latency / throughput / time budget.
    re.compile(r"\bwithin\s+\d", re.IGNORECASE),
    re.compile(r"\blatenc(?:y|ies)\b", re.IGNORECASE),
    re.compile(r"\bthroughput\b", re.IGNORECASE),
    re.compile(
        r"\b\d+(?:\.\d+)?\s*"
        r"(?:ms|millisecond|s|sec|second|min|minute|hour|hr|fps|qps|rps|hz|"
        r"tps|req/s|op/s|mb/s|gb/s|kb/s)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:at least|no more than|no fewer than)\s+\d", re.IGNORECASE),
    re.compile(r"[≤≥]\s*\d"),
    # Named error / exception (NOT the generic noun "error" — that would smear
    # "handles errors gracefully" as observable). Concrete raise/throw, the
    # word "exception"/"errno", or a CamelCase exception type.
    re.compile(r"\b(?:raises?|throws?|raising|throwing)\b", re.IGNORECASE),
    re.compile(r"\bexception\b", re.IGNORECASE),
    re.compile(r"\berrno\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]\w*(?:Error|Exception)\b"),  # ValueError, ConnError
    # Given-When-Then with a Then-clause (a Then asserts a checkable outcome).
    re.compile(r"\bthen\b", re.IGNORECASE),
]

# References that look numeric but are not measurable thresholds — stripped
# before the digit-presence check so a citation ("see REQ-002") or version tag
# ("v1.13") does not masquerade as a concrete falsifiable value.
_ID_REF_RE = re.compile(r"\b[A-Z]{2,}[-_]?\d+\b")            # REQ-001, ARCH_2
_VERSION_RE = re.compile(r"\bv\d+(?:\.\d+)*\b", re.IGNORECASE)  # v2, v1.13
_DIGIT_RE = re.compile(r"\d")

# Markdown list / numbering markers, stripped from each AC item before
# classification so a list bullet ("1.") is not mistaken for a threshold.
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")

# Inline code spans — stripped ONLY for the aspirational lexicon check (mirrors
# the ``_STRIP_CODE`` convention in artifact_lint._check_quality) so a token
# like `` `work` `` (a category label) is not read as the bare verb "work".
# Kept VISIBLE for the observable check because backticks often carry the very
# outcome signal being detected (`` `exit code 0` ``, `` `returns 0` ``).
_INLINE_CODE_RE = re.compile(r"`[^`]+`")


# Ambiguity lexicon — MIRRORED from
# ``specflow.commands.artifact_lint._AMBIGUITY_WORDS`` (the source of truth for
# the whole codebase). Mirrored rather than imported because that module is a
# command-layer file owned by a different workstream; the lexicon is frozen
# doctrine. If it changes upstream, update this mirror in lockstep.
_AMBIGUITY_WORDS_RE = re.compile(
    r"\b(fast|slow|quickly|efficiently|responsive|performant|real-time"
    r"|user-friendly|robust|flexible|scalable|maintainable|reliable|stable|safe"
    r"|approximately|roughly|several|etc\.?"
    r"|should be able to|it would be nice if|ideally|preferably"
    r"|properly|correctly|appropriately|as expected|as needed|if possible"
    r"|easy|simple|straightforward|intuitive|seamless|effortless"
    r"|frequently|often|rarely|sometimes|occasionally|regularly"
    r"|reasonable|adequate|sufficient|appropriate)\b",
    re.IGNORECASE,
)

# Bare vague verbs — generic process-verbs with NO domain specificity. This is
# the "works/handles/succeeds/proceeds-class" named in the v1.13.1 design.
# Deliberately NARROW: domain verbs ("energizes", "arbitrates", "calibrates")
# are excluded so a real engineering AC is never smeared as aspirational. A
# bare vague verb only triggers ASPIRATIONAL in conjunction with NO outcome
# marker — "handles errors by writing /var/log/x" has an outcome (observable).
_BARE_VAGUE_VERBS_RE = re.compile(
    r"\b(works?|handles?|succeeds?|proceeds?|functions?|operates?|behaves?)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Item extraction (reuses lint.py's section parser — no re-parsing of markers)
# ---------------------------------------------------------------------------

def _ac_items(artifact: art_lib.Artifact) -> list[str]:
    """Return the AC items of an artifact as clean, marker-stripped strings.

    Reuses :func:`lint.acceptance_criteria_text` for the section-finding work
    (the marker + heading-boundary logic is NOT reimplemented). Item splitting
    mirrors :func:`lint.count_acceptance_criteria_items` line-for-line so
    ``len(_ac_items(a)) == count_acceptance_criteria_items(a)``; the only
    addition is stripping the list/numbering marker so a bullet digit ("1.")
    is not later mistaken for a measurable threshold.
    """
    section = lint_lib.acceptance_criteria_text(artifact)
    if section:
        items: list[str] = []
        for line in section.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            stripped = _LIST_MARKER_RE.sub("", stripped).strip()
            if stripped:
                items.append(stripped)
        return items
    # Given-When-Then fallback (mirrors count_acceptance_criteria_items): when
    # no explicit AC header is present, treat numbered "1. given ..." lines as
    # the items. Extract the full line so the Then-clause is classifiable.
    body = artifact.body
    out: list[str] = []
    for m in _AC_GIVEN_PATTERN.finditer(body):
        line_end = body.find("\n", m.start())
        line = body[m.start():line_end if line_end != -1 else len(body)]
        line = _LIST_MARKER_RE.sub("", line).strip()
        if line:
            out.append(line)
    return out


# ---------------------------------------------------------------------------
# Classification primitives
# ---------------------------------------------------------------------------

def _has_outcome_marker(text: str) -> bool:
    """True if ``text`` carries any high-precision testable-outcome signal."""
    for p in _OUTCOME_PATTERNS:
        if p.search(text):
            return True
    # Digit-presence as a concrete-value signal, after stripping ID refs and
    # version tags so a citation does not pose as a threshold.
    cleaned = _VERSION_RE.sub(" ", _ID_REF_RE.sub(" ", text))
    return bool(_DIGIT_RE.search(cleaned))


def _is_aspirational(text: str) -> bool:
    """True if ``text`` matches an ambiguity word OR a bare vague verb.

    Only consulted AFTER ``_has_outcome_marker`` returns False (the
    conjunction guardrail), so an item with a real outcome is never smeared.
    Inline code spans are stripped first (mirrors artifact_lint._check_quality)
    so a code/identifier token like `` `work` `` is not read as the bare verb.
    """
    prose = _INLINE_CODE_RE.sub(" ", text)
    return bool(_AMBIGUITY_WORDS_RE.search(prose) or _BARE_VAGUE_VERBS_RE.search(prose))


def _classify_item(text: str) -> str:
    """Classify one AC item: ``observable`` | ``aspirational`` | ``unclassified``.

    The conjunction is the anti-cry-wolf guardrail — see module docstring.
    """
    if _has_outcome_marker(text):
        return "observable"
    if _is_aspirational(text):
        return "aspirational"
    return "unclassified"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_ac_observability(artifact: art_lib.Artifact) -> dict:
    """Classify each AC item of ``artifact`` by test-observability.

    Returns a per-artifact summary dict::

        {
          "artifact_id": str,
          "is_requirement": bool,
          "total": int,                 # number of AC items found
          "observable": int,
          "aspirational": int,
          "unclassified": int,
          "items": [{"text": str, "classification": str}, ...],
          "observable_texts": [str, ...],
          "aspirational_texts": [str, ...],
          "unclassified_texts": [str, ...],
        }

    Works on any artifact that has an Acceptance Criteria section (ACs are
    surfaced wherever they appear); the cross-REQ aggregate
    (:func:`classify_reqs_observability`) filters to REQs. Pure read — never
    asserts, never blocks.
    """
    items = _ac_items(artifact)
    classified = [{"text": t, "classification": _classify_item(t)} for t in items]
    buckets: dict[str, list[str]] = {"observable": [], "aspirational": [], "unclassified": []}
    for it in classified:
        buckets[it["classification"]].append(it["text"])
    return {
        "artifact_id": artifact.id,
        "is_requirement": art_lib.get_prefix_from_id(artifact.id) == "REQ",
        "total": len(items),
        "observable": len(buckets["observable"]),
        "aspirational": len(buckets["aspirational"]),
        "unclassified": len(buckets["unclassified"]),
        "items": classified,
        "observable_texts": buckets["observable"],
        "aspirational_texts": buckets["aspirational"],
        "unclassified_texts": buckets["unclassified"],
    }


def classify_reqs_observability(artifacts: list[art_lib.Artifact]) -> dict:
    """Aggregate AC observability across all REQ artifacts.

    Returns::

        {
          "reqs_with_acs": int,          # REQs with >=1 AC item
          "aspirational_free_reqs": int, # of those, REQs with 0 aspirational ACs
          "aspirational_reqs": int,      # REQs with >=1 aspirational AC
          "total_items": int,
          "observable": int,
          "aspirational": int,
          "unclassified": int,
          "per_req": [ {id, total, observable, aspirational, unclassified,
                        observable_ratio, items}, ... ],
          "aspirational_texts": [str, ...],
        }

    ``observable_ratio`` is observable/total (0.0 when total==0). Each per-REQ
    entry's ``items`` is the SAME per-AC list
    (:func:`classify_ac_observability` computes — one ``{"text", "classification"}``
    dict per item, in document order) carried out unchanged (A3, CHL-344): it is
    the single parse path for the per-AC report appendix and the cross-cutting
    subagent table, so neither surface re-parses AC text. REQs with no AC items
    are excluded from ``reqs_with_acs`` (a presence gap is the acceptance-check's
    job, not this lens's).
    """
    per_req: list[dict] = []
    asp_texts: list[str] = []
    totals = {"observable": 0, "aspirational": 0, "unclassified": 0, "total": 0}
    aspirational_free = 0
    aspirational_reqs = 0
    reqs_with_acs = 0
    for art in artifacts:
        if art_lib.get_prefix_from_id(art.id) != "REQ":
            continue
        summary = classify_ac_observability(art)
        if summary["total"] == 0:
            continue
        reqs_with_acs += 1
        totals["total"] += summary["total"]
        for k in ("observable", "aspirational", "unclassified"):
            totals[k] += summary[k]
        asp_texts.extend(summary["aspirational_texts"])
        ratio = summary["observable"] / summary["total"] if summary["total"] else 0.0
        per_req.append({
            "id": summary["artifact_id"],
            "total": summary["total"],
            "observable": summary["observable"],
            "aspirational": summary["aspirational"],
            "unclassified": summary["unclassified"],
            "observable_ratio": ratio,
            # A3 (CHL-344): carry the per-AC rows out unchanged so the report
            # appendix / cross-cutting table consume the single parse path.
            "items": summary["items"],
        })
        if summary["aspirational"] == 0:
            aspirational_free += 1
        else:
            aspirational_reqs += 1
    return {
        "reqs_with_acs": reqs_with_acs,
        "aspirational_free_reqs": aspirational_free,
        "aspirational_reqs": aspirational_reqs,
        "total_items": totals["total"],
        "observable": totals["observable"],
        "aspirational": totals["aspirational"],
        "unclassified": totals["unclassified"],
        "per_req": per_req,
        "aspirational_texts": asp_texts,
    }


def lint_ac_observability(artifacts: list[art_lib.Artifact]) -> dict[str, str | int]:
    """Advisory, non-blocking lint check: REQ-level AC observability ratio.

    Returns the standard check-summary shape consumed by
    :func:`artifact_lint._run_check`
    (``status_icon``/``detail``/``blocking_count``/``warning_count``) so it can
    be wired into ``CHECK_NAMES`` and dispatched without modification.

    ACCOUNTING, NOT POLICING: ``blocking_count`` is ALWAYS 0 and this check is
    never part of ``--type gate``. ``warning_count`` is the number of REQs that
    carry >=1 aspirational AC — reported REQ-by-REQ (an aggregate per REQ, not
    per individual AC) so lexicon edge cases cannot cry-wolf at item level.
    Detail text is REQ-level ("REQ-001: 2/5 ACs aspirational").
    """
    from specflow.lib.display import GREEN, YELLOW, NC

    agg = classify_reqs_observability(artifacts)
    flagged = [r for r in agg["per_req"] if r["aspirational"] > 0]
    details: list[str] = []
    for r in sorted(flagged, key=lambda r: r["id"]):
        details.append(
            f"  ⚠ [{r['id']}] {r['aspirational']}/{r['total']} ACs aspirational "
            f"({r['observable']} observable, {r['unclassified']} unclassified)"
        )
    warnings = len(flagged)
    blocking = 0
    if warnings > 0:
        icon = YELLOW + "⚠" + NC
        detail = "; ".join(details)
    else:
        icon = GREEN + "✓" + NC
        n = agg["reqs_with_acs"]
        if n == 0:
            detail = "No REQs with acceptance criteria to classify"
        else:
            detail = (
                f"All {n} REQ(s) with ACs are free of aspirational criteria "
                f"({agg['observable']} observable, {agg['unclassified']} unclassified)"
            )
    return {
        "status_icon": icon,
        "detail": detail,
        "blocking_count": blocking,
        "warning_count": warnings,
    }
