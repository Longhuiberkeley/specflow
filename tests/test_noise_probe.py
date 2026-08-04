"""AC2 of STORY-SMALLFIX-621b: noise variance probe tests.

The autoresearch loop must verify that metric variance is below a configurable
threshold before trusting single-run EXPT results. These tests pin the
deterministic behavior of ``specflow.lib.noise_probe``:

* low-variance samples pass (trustworthy),
* high-variance samples are flagged (noisy),
* the threshold is configurable (tightening/loosening flips a borderline case),
* edge cases (empty, single sample, zero-mean stable, zero-mean volatile) and
  the reported statistics (min/max/mean/stdev/CV) are exact.
"""

from __future__ import annotations

import statistics

import pytest

from specflow.lib.noise_probe import (
    DEFAULT_RELATIVE_THRESHOLD,
    NoiseProbeResult,
    run_noise_probe,
)


class TestNoiseProbePassFail:
    """AC2 core: variance below threshold passes; above threshold flags."""

    def test_low_variance_passes(self) -> None:
        # mean=1.0, sample stdev=0.01 → CV=0.01, well under the 5% default.
        result = run_noise_probe([1.00, 1.01, 0.99])
        assert result.passed is True
        assert result.noisy is False

    def test_high_variance_flags_as_noisy(self) -> None:
        # mean=1.0, sample stdev=0.2 → CV=0.2, far above the 5% default.
        result = run_noise_probe([1.0, 1.2, 0.8])
        assert result.passed is False
        assert result.noisy is True
        assert "too noisy" in result.reason

    def test_default_threshold_is_five_percent(self) -> None:
        assert DEFAULT_RELATIVE_THRESHOLD == 0.05

    def test_passing_result_is_not_noisy_and_vice_versa(self) -> None:
        ok = run_noise_probe([1.0, 1.0, 1.0])
        bad = run_noise_probe([1.0, 2.0, 0.0])
        # The two terminal "enough samples" states are mutually exclusive.
        assert ok.passed and not ok.noisy
        assert (not bad.passed) and bad.noisy


class TestConfigurableThreshold:
    """The threshold is configurable; the verdict flips with it."""

    def test_tighter_threshold_flags_previously_passing_metric(self) -> None:
        # CV ≈ 0.01: passes at 5%, fails at a 0.001 (0.1%) threshold.
        samples = [1.00, 1.01, 0.99]
        assert run_noise_probe(samples).passed is True
        strict = run_noise_probe(samples, threshold=0.001)
        assert strict.passed is False
        assert strict.noisy is True

    def test_looser_threshold_passes_previously_noisy_metric(self) -> None:
        # CV = 0.2: noisy at 5%, passes at a 0.3 (30%) threshold.
        samples = [1.0, 1.2, 0.8]
        assert run_noise_probe(samples).noisy is True
        loose = run_noise_probe(samples, threshold=0.3)
        assert loose.passed is True
        assert loose.noisy is False

    def test_threshold_recorded_on_result(self) -> None:
        result = run_noise_probe([1.0, 1.0], threshold=0.02)
        assert result.threshold == 0.02

    def test_borderline_cv_equal_to_threshold_passes(self) -> None:
        # CV exactly equal to threshold is treated as within-bounds (<=).
        # samples with mean=1.0, stdev=0.05 → CV=0.05 == default threshold.
        # Construct via [1.0 - 0.05, 1.0, 1.0 + 0.05]: mean=1.0,
        # sample stdev = sqrt((0.0025+0+0.0025)/2) = sqrt(0.0025) = 0.05.
        result = run_noise_probe([0.95, 1.0, 1.05], threshold=0.05)
        assert result.passed is True
        assert result.noisy is False


class TestStatisticsExactness:
    """min/max/mean/stdev/CV reported for rendering the protocol's summary."""

    def test_statistics_match_manual_calculation(self) -> None:
        samples = [1.0, 1.2, 0.8]
        result = run_noise_probe(samples)
        assert result.min_value == 0.8
        assert result.max_value == 1.2
        assert result.mean == pytest.approx(1.0)
        assert result.stdev == pytest.approx(statistics.stdev(samples))
        assert result.coefficient_of_variation == pytest.approx(0.2)
        assert result.samples == (1.0, 1.2, 0.8)

    def test_samples_coerced_to_float(self) -> None:
        # Int input should be normalized to float in the stored tuple.
        result = run_noise_probe([1, 1, 1])
        assert all(isinstance(s, float) for s in result.samples)


class TestEdgeCases:
    """Insufficient samples and degenerate metrics are handled deterministically."""

    def test_empty_samples_not_passed_not_noisy(self) -> None:
        result = run_noise_probe([])
        assert result.passed is False
        assert result.noisy is False
        assert "no samples" in result.reason

    def test_single_sample_is_insufficient_by_default(self) -> None:
        result = run_noise_probe([1.0])
        assert result.passed is False
        assert result.noisy is False
        assert "need >=" in result.reason

    def test_single_sample_passes_when_min_samples_lowered(self) -> None:
        # min_samples=1 lets a lone sample through; a single point has no
        # variance, so it is treated as trustworthy under the relative rule.
        result = run_noise_probe([1.0], min_samples=1)
        assert result.passed is True
        assert result.noisy is False

    def test_two_samples_is_the_default_floor(self) -> None:
        result = run_noise_probe([1.0, 1.0])
        assert result.passed is True
        assert result.noisy is False

    def test_zero_mean_stable_passes(self) -> None:
        # mean=0, stdev=0 → perfectly stable at zero; CV undefined but stable.
        result = run_noise_probe([0.0, 0.0, 0.0])
        assert result.passed is True
        assert result.noisy is False

    def test_zero_mean_with_variance_is_noisy(self) -> None:
        # mean=0, non-zero variance → relative noise is unbounded → flag it.
        result = run_noise_probe([0.0, 0.1, -0.1])
        assert result.passed is False
        assert result.noisy is True


class TestDeterminism:
    """The probe is pure arithmetic: identical inputs → identical outputs."""

    def test_repeated_calls_identical(self) -> None:
        samples = [1.0, 1.2, 0.8, 0.9, 1.1]
        first = run_noise_probe(samples)
        second = run_noise_probe(samples)
        assert first == second

    def test_result_is_frozen(self) -> None:
        result = run_noise_probe([1.0, 1.0])
        with pytest.raises(Exception):
            result.passed = False  # type: ignore[misc]

    def test_result_is_hashable_dataclass(self) -> None:
        result = run_noise_probe([1.0, 1.0])
        # Frozen dataclass should be usable as a dict key / set member.
        assert isinstance(result, NoiseProbeResult)
        assert hash(result) == hash(run_noise_probe([1.0, 1.0]))
