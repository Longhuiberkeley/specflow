"""Noise variance probe for the autoresearch pack (AC2 of STORY-SMALLFIX-621b).

Before trusting EXPT ``metric_value`` results, the autoresearch loop runs the
competition's ``verify_command`` several times on the unchanged baseline and
checks that run-to-run metric variance is below a configurable threshold. High
variance means single-run iterations will produce false-positive "keeps" and
false-negative "discards" — the loop must pick a noise strategy (multi-run
median, confirmation run, environment pinning, min-delta — see the pack's
``references/noise-handling-protocol.md``) before committing a long budget.

This module is a deterministic, side-effect-free reference implementation of
that variance check. It does NOT run the ``verify_command`` itself (that is the
host's job, since the command is project-specific and may have side effects);
it takes the already-parsed metric samples and returns the verdict plus the
underlying statistics so a caller can report ``min / max / mean / stdev`` as the
protocol describes.

The public entry point is :func:`run_noise_probe`.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence

# Per noise-handling-protocol.md "Noise Probe at Setup Time": flag the metric as
# noisy when stdev exceeds ~5% of mean. Expressed here as the coefficient of
# variation (stdev / |mean|) so the threshold is scale-free.
DEFAULT_RELATIVE_THRESHOLD = 0.05

# Variance cannot be characterized from fewer than 2 samples. The protocol
# recommends 3+ runs; 2 is the hard floor at which sample stdev is defined.
DEFAULT_MIN_SAMPLES = 2


@dataclass(frozen=True)
class NoiseProbeResult:
    """Outcome of a noise-variance probe.

    Three terminal states, encoded as two booleans:

    * **trustworthy** — ``passed=True``, ``noisy=False``: enough samples and
      variance is within the threshold; single-run results can be trusted.
    * **noisy** — ``passed=False``, ``noisy=True``: enough samples but variance
      exceeds the threshold; pick a noise strategy before trusting results.
    * **insufficient** — ``passed=False``, ``noisy=False``: too few samples to
      characterize variance (see ``reason``); trust is not established.
    """

    samples: tuple[float, ...]
    mean: float
    stdev: float
    min_value: float
    max_value: float
    coefficient_of_variation: float
    threshold: float
    passed: bool
    noisy: bool
    reason: str = ""


def run_noise_probe(
    samples: Sequence[float],
    *,
    threshold: float = DEFAULT_RELATIVE_THRESHOLD,
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> NoiseProbeResult:
    """Check that metric variance is below ``threshold`` before trusting results.

    ``threshold`` is *relative*: it is compared against the coefficient of
    variation ``stdev / |mean|``, matching the pack's documented "stdev > ~5% of
    mean" rule. Passing a larger threshold loosens the gate; a smaller one
    tightens it.

    Parameters
    ----------
    samples:
        Metric values parsed from repeated runs of the unchanged-baseline
        ``verify_command``. They are coerced to ``float``.
    threshold:
        Maximum tolerated coefficient of variation. Defaults to ``0.05`` (5%).
    min_samples:
        Minimum sample count required to characterize variance. Defaults to
        ``2`` (the floor at which sample stdev is defined).

    Returns
    -------
    NoiseProbeResult
        ``passed`` is the primary gate signal — ``True`` means variance is
        within bounds and single-run results may be trusted. ``noisy`` is
        ``True`` only when variance explicitly exceeds the threshold. The
        ``coefficient_of_variation``, ``mean``, ``stdev``, ``min_value`` and
        ``max_value`` fields are populated so a caller can render the
        ``min / max / mean / stdev`` report the protocol prescribes.

    Notes
    -----
    Deterministic: this function performs only arithmetic on its inputs and
    touches no I/O, wall-clock, or randomness, so results are reproducible.

    A zero-mean metric (``|mean|`` below ``1e-12``) makes the relative
    coefficient of variation undefined. Such a metric is treated as trustworthy
    only when it is perfectly stable (``stdev == 0``); any variance at a zero
    mean is flagged as noisy, since the relative noise is unbounded.
    """
    nums = tuple(float(s) for s in samples)
    n = len(nums)
    mean = statistics.fmean(nums) if n else 0.0

    if n == 0:
        return NoiseProbeResult(
            samples=nums,
            mean=0.0,
            stdev=0.0,
            min_value=0.0,
            max_value=0.0,
            coefficient_of_variation=0.0,
            threshold=threshold,
            passed=False,
            noisy=False,
            reason="no samples provided — cannot characterize metric variance",
        )

    if n < min_samples:
        return NoiseProbeResult(
            samples=nums,
            mean=mean,
            stdev=0.0,
            min_value=min(nums),
            max_value=max(nums),
            coefficient_of_variation=0.0,
            threshold=threshold,
            passed=False,
            noisy=False,
            reason=(
                f"only {n} sample(s) — need >= {min_samples} to "
                "characterize metric variance"
            ),
        )

    # n >= min_samples here. Sample stdev is only defined for n >= 2; a single
    # allowed sample (min_samples <= 1) shows no observed run-to-run variance.
    stdev = statistics.stdev(nums) if n >= 2 else 0.0
    min_v = min(nums)
    max_v = max(nums)

    if abs(mean) < 1e-12:
        # Relative CV is undefined at zero mean. Perfectly stable (stdev == 0)
        # is trustworthy; any variance at a zero mean is unbounded relative
        # noise and must be flagged.
        cv = 0.0 if stdev == 0 else float("inf")
    else:
        cv = stdev / abs(mean)

    # Use a tiny tolerance so floating-point noise in the CV computation cannot
    # flip a gate that is effectively at the boundary (e.g. CV of 0.05 computed
    # as 0.05000000001 must still pass a 0.05 threshold).
    if cv <= threshold + 1e-9:
        return NoiseProbeResult(
            samples=nums,
            mean=mean,
            stdev=stdev,
            min_value=min_v,
            max_value=max_v,
            coefficient_of_variation=cv,
            threshold=threshold,
            passed=True,
            noisy=False,
            reason=(
                f"coefficient of variation {cv:.4f} <= threshold {threshold:.4f}"
            ),
        )

    return NoiseProbeResult(
        samples=nums,
        mean=mean,
        stdev=stdev,
        min_value=min_v,
        max_value=max_v,
        coefficient_of_variation=cv,
        threshold=threshold,
        passed=False,
        noisy=True,
        reason=(
            f"coefficient of variation {cv:.4f} > threshold {threshold:.4f} "
            "— metric is too noisy to trust single-run results; "
            "pick a noise strategy (see noise-handling-protocol.md)"
        ),
    )
