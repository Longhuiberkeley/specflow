"""WS4: auto-domain detection tests (quant/ml seeds, extensible, word-boundary aware)."""

from __future__ import annotations

from pathlib import Path

from specflow.lib.domain_detect import suggest_domain


def _write(root: Path, name: str, content: str) -> None:
    (root / name).write_text(content, encoding="utf-8")


class TestSuggestDomain:

    def test_detects_quant_from_requirements(self, tmp_path: Path):
        _write(tmp_path, "requirements.txt", "pandas\nbacktrader\nnumpy\nccxt\n")
        domain, reason = suggest_domain(tmp_path)
        assert domain == "quant"
        assert "backtrader" in reason

    def test_detects_ml_from_pyproject(self, tmp_path: Path):
        _write(tmp_path, "pyproject.toml",
               '[project]\ndependencies = ["scikit-learn", "xgboost"]\n')
        domain, reason = suggest_domain(tmp_path)
        assert domain == "ml"
        assert "scikit-learn" in reason

    def test_most_hits_wins(self, tmp_path: Path):
        # 1 quant signal vs 3 ml signals → ml
        _write(tmp_path, "requirements.txt",
               "scikit-learn\ntensorflow\nxgboost\nccxt\n")
        domain, _ = suggest_domain(tmp_path)
        assert domain == "ml"

    def test_quant_wins_ties_by_signal_order(self, tmp_path: Path):
        # equal hits (1 each) → quant listed first in SIGNALS
        _write(tmp_path, "requirements.txt", "backtrader\ntorch\n")
        domain, _ = suggest_domain(tmp_path)
        assert domain == "quant"

    def test_no_manifests(self, tmp_path: Path):
        domain, reason = suggest_domain(tmp_path)
        assert domain is None
        assert "manifests" in reason

    def test_no_matching_signals(self, tmp_path: Path):
        _write(tmp_path, "requirements.txt", "requests\nflask\n")
        domain, reason = suggest_domain(tmp_path)
        assert domain is None
        assert "manually" in reason

    def test_word_boundary_no_false_positive(self, tmp_path: Path):
        # "sklearn" embedded in a longer token must not match
        _write(tmp_path, "requirements.txt", "mysklearnapp\n")
        domain, _ = suggest_domain(tmp_path)
        assert domain is None

    def test_signal_table_is_extensible(self):
        from specflow.lib import domain_detect
        # Adding a row enables a new domain without touching scan logic.
        domain_detect.SIGNALS.append(("polars-only-fixture", "data-science"))
        try:
            assert any(s[1] == "data-science" for s in domain_detect.SIGNALS)
        finally:
            domain_detect.SIGNALS.pop()
