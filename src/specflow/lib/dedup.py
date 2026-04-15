"""Three-tier duplicate detection for SpecFlow artifacts.

Tier 1: tag overlap (Jaccard over the `tags` set).
Tier 2: TF-IDF cosine similarity over title + normative body tokens.
Tier 3: LLM confirmation — handled by the check skill, which reads the
candidates file produced here. This module produces pure-Python (zero-token)
candidates for the agent to confirm.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from specflow.lib.artifacts import Artifact, discover_artifacts

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{1,}")

# Minimal stopword list. Keeping it small avoids over-aggressive filtering
# on short spec artifacts.
_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "of", "in", "to", "for", "on",
    "at", "by", "with", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "should", "could", "may", "might", "must", "can", "this",
    "that", "these", "those", "it", "its", "if", "then", "else", "when",
    "where", "which", "who", "what", "how", "any", "all", "some", "no",
    "not", "so", "than", "such",
})


@dataclass
class DedupCandidate:
    """A pair of artifacts flagged as potential duplicates."""

    pair: tuple[str, str]
    tag_jaccard: float
    tfidf_cosine: float
    confidence: str
    tier_reached: int


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _tokenize(text: str) -> list[str]:
    return [
        tok.lower()
        for tok in _TOKEN_RE.findall(text)
        if tok.lower() not in _STOPWORDS
    ]


def _build_idf(docs: list[list[str]]) -> dict[str, float]:
    n = len(docs)
    if n == 0:
        return {}
    df: Counter[str] = Counter()
    for doc in docs:
        for tok in set(doc):
            df[tok] += 1
    return {tok: math.log(n / count) for tok, count in df.items() if count > 0}


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}
    tf = Counter(tokens)
    return {tok: count * idf.get(tok, 0.0) for tok, count in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = a.keys() & b.keys()
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _classify_confidence(tag_jaccard: float, tfidf_cosine: float) -> str:
    if tfidf_cosine >= 0.8 and tag_jaccard >= 0.7:
        return "high"
    if tfidf_cosine >= 0.7 or (tfidf_cosine >= 0.6 and tag_jaccard >= 0.5):
        return "medium"
    return "low"


def _artifact_text(artifact: Artifact) -> str:
    return f"{artifact.title}\n{artifact.body}"


def find_duplicates(
    artifacts: list[Artifact],
    tag_threshold: float = 0.5,
    tfidf_threshold: float = 0.7,
) -> list[DedupCandidate]:
    """Run tier 1 + tier 2 across all artifact pairs.

    Artifacts of different types are never compared against each other — a
    REQ and a STORY describing the same feature are not duplicates, they are
    traceability pairs.
    """
    # Group by type so only same-type pairs are compared.
    by_type: dict[str, list[Artifact]] = {}
    for art in artifacts:
        by_type.setdefault(art.type, []).append(art)

    candidates: list[DedupCandidate] = []
    for typed_list in by_type.values():
        if len(typed_list) < 2:
            continue

        # Tier 1: tag Jaccard pre-filter.
        tag_sets = [set(art.tags) for art in typed_list]
        survivors: list[tuple[int, int, float]] = []
        for i in range(len(typed_list)):
            for j in range(i + 1, len(typed_list)):
                jac = _jaccard(tag_sets[i], tag_sets[j])
                if jac >= tag_threshold:
                    survivors.append((i, j, jac))

        if not survivors:
            continue

        # Tier 2: TF-IDF cosine on survivors.
        docs = [_tokenize(_artifact_text(art)) for art in typed_list]
        idf = _build_idf(docs)
        vectors = [_tfidf_vector(doc, idf) for doc in docs]

        for i, j, jac in survivors:
            cos = _cosine(vectors[i], vectors[j])
            if cos < tfidf_threshold:
                continue
            pair = tuple(sorted((typed_list[i].id, typed_list[j].id)))
            candidates.append(
                DedupCandidate(
                    pair=pair,  # type: ignore[arg-type]
                    tag_jaccard=round(jac, 3),
                    tfidf_cosine=round(cos, 3),
                    confidence=_classify_confidence(jac, cos),
                    tier_reached=2,
                )
            )

    candidates.sort(key=lambda c: (-c.tfidf_cosine, -c.tag_jaccard, c.pair))
    return candidates


def find_similar_to(
    artifacts: list[Artifact],
    artifact_type: str,
    title: str,
    tags: list[str],
    tag_threshold: float = 0.3,
    tfidf_threshold: float = 0.5,
) -> list[DedupCandidate]:
    """Search-before-create: check a proposed {type, title, tags} against
    existing same-type artifacts.

    Lower thresholds than `find_duplicates` because we only have the title
    (no body yet), so keyword signal is weaker. The new artifact is labelled
    with id "<NEW>" in the returned pair.
    """
    same_type = [a for a in artifacts if a.type == artifact_type]
    if not same_type:
        return []

    proposed_tags = set(tags)
    proposed_tokens = _tokenize(title)

    # Compare title-to-title on both sides. The proposed artifact has no body
    # yet, so including existing bodies in the TF-IDF corpus creates a length
    # asymmetry that drops cosine scores below threshold even for identical
    # titles. Title-only keeps the comparison symmetric.
    title_docs = [_tokenize(a.title) for a in same_type]
    idf = _build_idf(title_docs)
    existing_vectors = [_tfidf_vector(doc, idf) for doc in title_docs]
    proposed_vector = _tfidf_vector(proposed_tokens, idf)

    candidates: list[DedupCandidate] = []
    for i, art in enumerate(same_type):
        jac = _jaccard(proposed_tags, set(art.tags))
        if jac < tag_threshold:
            continue
        cos = _cosine(proposed_vector, existing_vectors[i])
        if cos < tfidf_threshold:
            continue
        candidates.append(
            DedupCandidate(
                pair=("<NEW>", art.id),
                tag_jaccard=round(jac, 3),
                tfidf_cosine=round(cos, 3),
                confidence=_classify_confidence(jac, cos),
                tier_reached=2,
            )
        )

    candidates.sort(key=lambda c: (-c.tfidf_cosine, -c.tag_jaccard))
    return candidates


def candidates_file_path(root: Path) -> Path:
    return root / ".specflow" / "dedup-candidates.yaml"


def write_candidates_file(root: Path, candidates: list[DedupCandidate]) -> Path:
    path = candidates_file_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidates": [
            {
                "pair": list(c.pair),
                "tag_jaccard": c.tag_jaccard,
                "tfidf_cosine": c.tfidf_cosine,
                "confidence": c.confidence,
                "tier_reached": c.tier_reached,
            }
            for c in candidates
        ],
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


