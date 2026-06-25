"""Lightweight, extensible domain detection from repo dependency signals.

Suggests a project domain by scanning dependency manifests. Quant/ML are seeded
first; the signal table is extensible — add rows to extend detection to new
domains without changing the scanning logic. Never silently sets a domain: it
always returns a suggestion for the caller (CLI/skill) to confirm with the user.
"""

from __future__ import annotations

import re
from pathlib import Path

# Signal substring (lowercase) -> domain. Add rows here to extend detection.
# Order within a domain is irrelevant; per-domain hit count decides ties.
SIGNALS: list[tuple[str, str]] = [
    # quant / algo-trading / prediction markets
    ("backtrader", "quant"), ("zipline", "quant"), ("vectorbt", "quant"),
    ("ccxt", "quant"), ("pandas-ta", "quant"), ("quantconnect", "quant"),
    ("pyfolio", "quant"), ("empyrical", "quant"), ("betfair", "quant"),
    # ml / data-science
    ("scikit-learn", "ml"), ("sklearn", "ml"), ("torch", "ml"),
    ("tensorflow", "ml"), ("xgboost", "ml"), ("lightgbm", "ml"),
    ("catboost", "ml"), ("transformers", "ml"), ("pytorch-lightning", "ml"),
]

_MANIFESTS = [
    "pyproject.toml", "requirements.txt", "requirements-dev.txt",
    "setup.py", "package.json", "go.mod", "Gemfile", "Cargo.toml",
]


def _read_manifests(root: Path) -> str:
    """Concatenate likely dependency manifests into one lowercase blob."""
    chunks: list[str] = []
    for name in _MANIFESTS:
        path = root / name
        try:
            if path.exists():
                chunks.append(path.read_text(encoding="utf-8", errors="ignore").lower())
        except Exception:
            continue
    return "\n".join(chunks)


def suggest_domain(root: Path) -> tuple[str | None, str]:
    """Return ``(domain, reason)`` or ``(None, reason)``.

    Pure read of dependency manifests — never writes. The caller confirms before
    setting anything.
    """
    blob = _read_manifests(root)
    if not blob.strip():
        return None, "no dependency manifests found to scan"
    hits: dict[str, set[str]] = {}
    for signal, domain in SIGNALS:
        if re.search(rf"(^|[^a-z0-9]){re.escape(signal)}([^a-z0-9]|$)", blob):
            hits.setdefault(domain, set()).add(signal)
    if not hits:
        return None, "no matching dependency signals; set manually via `specflow domain set`"
    # Most signals wins; ties broken by first appearance (quant before ml in SIGNALS).
    best = max(hits, key=lambda d: len(hits[d]))
    return best, f"matched {', '.join(sorted(hits[best]))} in dependency manifests"
