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
import re
import shlex
from pathlib import Path


def _tokenize(verify_command: str) -> list[str]:
    """Split a shell-ish command into tokens; fall back to whitespace split."""
    try:
        return shlex.split(verify_command, comments=False, posix=True)
    except ValueError:
        return verify_command.split()


def _path_part(token: str) -> str:
    """Strip a pytest node-id suffix: ``tests/t.py::TestA::test_b`` -> ``tests/t.py``."""
    return token.split("::", 1)[0]


def evaluation_script_paths(root: Path, verify_command: str) -> list[str]:
    """Repo-relative paths of the evaluation scripts named by the command.

    A token names an evaluation script when it resolves to a regular file
    inside the project (``scripts/eval.py``, ``./eval.sh``, ...). A pytest
    node id (``tests/test_x.py::TestA::test_b``) resolves to its file, so the
    fingerprint tracks the test module's content (REQ-058 AC3). Flags,
    brace placeholders like ``{strategy}``, and anything outside the project
    are never scripts. Sorted and deduplicated by resolved path so the hash
    is order- and spelling-stable. Tokens that do not resolve are skipped
    here; :func:`missing_repo_paths` reports the ones that *look like* repo
    paths (the ``dead-oracle`` lint check).
    """
    root = root.resolve()
    found: dict[str, str] = {}
    for token in _tokenize(verify_command):
        if not token or token.startswith("-"):
            continue
        candidate = Path(_path_part(token))
        if not str(candidate) or candidate.is_absolute():
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


# A token "looks like a repository path" only when it is a plain relative
# path: word characters, dots, dashes, plus and slashes -- no whitespace,
# quotes, globs, ``$``, ``=``, redirections, ``{placeholders}`` or ``scheme:``.
_PATHLIKE = re.compile(r"^[A-Za-z0-9_.][A-Za-z0-9_.+/-]*$")
# A bare (slash-less) token is a path only when it carries a source suffix.
_SOURCE_SUFFIXES = frozenset({
    ".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".rb",
    ".pl", ".go", ".rs", ".lean", ".tla", ".cfg", ".toml", ".yaml", ".yml",
    ".json", ".ini",
})


def missing_repo_paths(root: Path, verify_command: str) -> list[str]:
    """Tokens of ``verify_command`` that look like repo paths but do not exist.

    Deterministic heuristic, tuned against cry-wolf:

    - pytest node ids resolve to their file (``a.py::T::t`` -> ``a.py``);
    - flags (``-k``, ``--cov=src``), absolute paths, URLs, quoted
      expressions, globs, ``$VARS``, redirections and ``{placeholders}``
      are never paths;
    - a token containing ``/`` is a repo path only when its first segment
      exists at the project root (``tests/...`` in a repo with ``tests/``),
      so build outputs like ``dist/app.js`` in a fresh checkout stay quiet;
    - a slash-less token is a path only when it has a source suffix
      (``eval.py``), so bare words (``pytest``, ``specflow.cli``) never are.

    Existing files AND directories count as present. Returns sorted,
    de-duplicated repo-relative spellings.
    """
    root = root.resolve()
    missing: set[str] = set()
    for token in _tokenize(verify_command or ""):
        if not token or token.startswith("-"):
            continue
        part = _path_part(token)
        if part.startswith("./"):
            part = part[2:]
        part = part.rstrip("/")
        if not part or part in (".", "..") or not _PATHLIKE.match(part):
            continue
        segments = part.split("/")
        if ".." in segments:
            continue
        if len(segments) > 1:
            if not (root / segments[0]).is_dir():
                continue
        elif Path(part).suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        if not (root / part).exists():
            missing.add(part)
    return sorted(missing)


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
