"""Evaluator fingerprint for the autoresearch pack (STORY-676, REQ-047 AC1).

A COMP is a frozen exam. Its ``evaluator_fingerprint`` — recorded at setup —
is the identity of the evaluation harness: the ``verify_command`` string plus
the content hashes of the evaluation scripts it runs. Pure filesystem hashing:
no LLM inference, no network calls, no timestamps (content only, so a touch
never reads as drift).

Why it exists: when the harness changes under an open COMP, every prior
EXPT's ``metric_value`` was scored by a different evaluator than the current
one — silently re-benchmarking the leaderboard. ``autoresearch log`` stamps
each EXPT with the fingerprint it was logged under; ``artifact-lint``'s
``fingerprint-drift`` check compares stamps against the setup fingerprint and
routes once to the successor-COMP path (rolling-evaluation.md § COMP churn
rule). This module is only the deterministic hash; the routing lives in lint.

The public entry point is :func:`compute_evaluator_fingerprint`.
"""

from __future__ import annotations

import hashlib
import shlex
from pathlib import Path


def _tokenize(verify_command: str) -> list[str]:
    """Split a shell-ish command into tokens; fall back to whitespace split."""
    try:
        return shlex.split(verify_command, comments=False, posix=True)
    except ValueError:
        return verify_command.split()


def evaluation_script_paths(root: Path, verify_command: str) -> list[str]:
    """Repo-relative paths of the evaluation scripts named by the command.

    A token names an evaluation script when it resolves to a regular file
    inside the project (``scripts/eval.py``, ``./eval.sh``, ...). Flags,
    brace placeholders like ``{strategy}``, and anything outside the project
    are never scripts. Sorted and deduplicated by resolved path so the hash
    is order- and spelling-stable.
    """
    root = root.resolve()
    found: dict[str, str] = {}
    for token in _tokenize(verify_command):
        if not token or token.startswith("-"):
            continue
        candidate = Path(token)
        if candidate.is_absolute():
            continue
        full = root / candidate
        try:
            if not full.is_file():
                continue
            resolved = full.resolve()
            rel = resolved.relative_to(root).as_posix()
        except (OSError, ValueError):
            continue
        found[rel] = rel
    return sorted(found.values())


def compute_evaluator_fingerprint(root: Path, verify_command: str) -> str:
    """`sha256:<12>` over the verify command plus evaluation-script hashes.

    Same compact shape as ``artifacts.compute_fingerprint``. Sensitive to the
    command string itself and to the *content* of every script it runs: a
    changed script hash changes the fingerprint (REQ-047 AC1).
    """
    root = root.resolve()
    command = (verify_command or "").strip()
    payload = [f"verify_command:{command}"]
    for rel in evaluation_script_paths(root, command):
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        payload.append(f"script:{rel}={digest}")
    blob = "\n".join(payload).encode("utf-8")
    return f"sha256:{hashlib.sha256(blob).hexdigest()[:12]}"
