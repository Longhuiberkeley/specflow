"""Privacy redaction primitives (REQ-038) — single source of truth for the
denylist pattern.

Shared by:
  - scripts/denylist_gate.py   (the CI/pytest gate; imports this via a
    src/-path bootstrap so the CI job needs no package install)
  - specflow.commands.project_audit (generated audit reports must never carry
    personal fingerprints, even when quoting REQ-038's own AC — the generator
    re-leak was found in the v1.14.6 pre-release review)

The pattern is case-sensitive (a case-insensitive ETH/ADA would false-positive
on ordinary prose) and word-bounded; numeric tokens are anchored so e.g.
0.0207 does not trip 0.020. Frozen by DDD-029.
"""

from __future__ import annotations

import re

PATTERN = re.compile(
    r"\b(?:cs2|HKJC|quant_trade|arbitrage|run_comp002|track_a|Kalman|BTC|ADA|ETH)\b"
    r"|\bTrack\s+[AB]\b"
    r"|\btrailing\s+stop\b"
    r"|/Volumes/ExternalDrive"
    r"|/Users/longhui"
    r"|Sharpe\s*>\s*2"
    r"|\b0\.020\b"
    r"|\b0\.021\b"
    r"|\b6\.62\b"
    r"|\b8\.45\b"
)

REDACTION_MARKER = "[REDACTED — enumerated in REQ-038 AC]"


def redact_text(text: str) -> str:
    """Replace every denylist match with the redaction marker.

    Idempotent: the marker itself contains no pattern tokens, so re-applying
    is a no-op. Used as a write-time choke point for all generated state
    (audit reports, caches) so quoting a spec that *defines* the denylist can
    never re-leak it.
    """
    return PATTERN.sub(REDACTION_MARKER, text)
