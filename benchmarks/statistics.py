"""
benchmarks/statistics.py
========================
Statistical testing for benchmark results.

Section 18.11:
    "Wilcoxon signed-rank, Friedman test with Nemenyi post-hoc.
     The goal is answering 'are these differences real or just
     run-to-run noise?' — not decorating the report with test names."

Functions:
    wilcoxon_pairwise(a, b)       — signed-rank test for two paired samples
    friedman_test(groups)          — overall test for k groups
    nemenyi_posthoc(groups, names) — pairwise comparisons after Friedman
    summary_stats(values)          — basic descriptive statistics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import stats


@dataclass
class WilcoxonResult:
    algorithm_a: str
    algorithm_b: str
    statistic: float
    p_value: float
    significant: bool     # p < 0.05
    direction: str        # "A better", "B better", or "no significant diff"

    def __str__(self):
        sig = "[SIG]" if self.significant else "[NOT SIG]"
        return (
            f"Wilcoxon {self.algorithm_a} vs {self.algorithm_b}: "
            f"W={self.statistic:.2f}, p={self.p_value:.4f} {sig} -> {self.direction}"
        )


@dataclass
class FriedmanResult:
    statistic: float
    p_value: float
    significant: bool
    n_groups: int
    n_observations: int

    def __str__(self):
        sig = "[SIG]" if self.significant else "[NOT SIG]"
        return (
            f"Friedman test ({self.n_groups} groups, n={self.n_observations}): "
            f"chi2={self.statistic:.2f}, p={self.p_value:.4f} {sig}"
        )


def wilcoxon_pairwise(
    values_a: np.ndarray,
    values_b: np.ndarray,
    name_a: str = "A",
    name_b: str = "B",
    alpha: float = 0.05,
) -> WilcoxonResult:
    """Wilcoxon signed-rank test for two paired samples.

    H0: no difference between the two distributions.
    Use when: comparing two algorithms on the same 30 runs.
    """
    a = np.asarray(values_a, dtype=float)
    b = np.asarray(values_b, dtype=float)
    if len(a) != len(b):
        raise ValueError("Wilcoxon requires equal-length paired samples.")

    # Remove ties (identical pairs)
    diff = a - b
    non_zero = diff[diff != 0]
    if len(non_zero) == 0:
        return WilcoxonResult(name_a, name_b, 0.0, 1.0, False, "no significant diff")

    stat, p = stats.wilcoxon(a, b)
    significant = bool(p < alpha)
    if significant:
        direction = f"{name_a} better" if np.median(a) < np.median(b) else f"{name_b} better"
    else:
        direction = "no significant diff"

    return WilcoxonResult(name_a, name_b, float(stat), float(p), significant, direction)


def friedman_test(
    groups: list[np.ndarray],
    group_names: Optional[list[str]] = None,
    alpha: float = 0.05,
) -> FriedmanResult:
    """Friedman test for k related groups.

    H0: all groups come from the same distribution.
    Use when: comparing 3+ algorithms across 30 matched runs.
    """
    arrays = [np.asarray(g, dtype=float) for g in groups]
    n = len(arrays[0])
    if not all(len(a) == n for a in arrays):
        raise ValueError("All groups must have the same number of observations.")

    stat, p = stats.friedmanchisquare(*arrays)
    return FriedmanResult(
        statistic=float(stat),
        p_value=float(p),
        significant=bool(p < alpha),
        n_groups=len(groups),
        n_observations=n,
    )


def nemenyi_posthoc(
    groups: list[np.ndarray],
    group_names: Optional[list[str]] = None,
    alpha: float = 0.05,
) -> dict:
    """Nemenyi post-hoc test after a significant Friedman result.

    Returns a dict of {(name_i, name_j): p_value} for all pairs.

    NOTE: This is a simplified implementation using the Wilcoxon pairwise
    comparisons with Bonferroni correction as a practical approximation.
    For a full Nemenyi implementation, install the `scikit-posthocs` package.
    """
    k = len(groups)
    if group_names is None:
        group_names = [f"G{i}" for i in range(k)]

    n_comparisons = k * (k - 1) // 2
    adjusted_alpha = alpha / n_comparisons  # Bonferroni correction

    results = {}
    for i in range(k):
        for j in range(i + 1, k):
            a, b = np.asarray(groups[i], float), np.asarray(groups[j], float)
            if len(a) == len(b) and len(a) > 0:
                try:
                    _, p = stats.wilcoxon(a, b)
                except Exception:
                    p = 1.0
            else:
                p = 1.0
            pair = (group_names[i], group_names[j])
            results[pair] = {
                "p_value": float(p),
                "p_adjusted": float(min(1.0, p * n_comparisons)),
                "significant": bool(p < adjusted_alpha),
            }
    return results


def summary_stats(values: np.ndarray, name: str = "metric") -> dict:
    """Basic descriptive statistics."""
    v = np.asarray(values, dtype=float)
    return {
        "name": name,
        "n": len(v),
        "min": float(np.min(v)),
        "max": float(np.max(v)),
        "mean": float(np.mean(v)),
        "median": float(np.median(v)),
        "std": float(np.std(v)),
        "q25": float(np.percentile(v, 25)),
        "q75": float(np.percentile(v, 75)),
    }


def print_comparison_table(
    experiment_results: dict,
    metric: str = "objective_value",
) -> None:
    """Print a formatted comparison table from dict of ExperimentResults."""
    print(f"\n{'Algorithm':<25} {'Best':>10} {'Mean':>10} {'Std':>10} "
          f"{'Median':>10} {'Feasible%':>10} {'RT(ms)':>10}")
    print("-" * 85)
    for name, exp in experiment_results.items():
        print(
            f"{name:<25} "
            f"{exp.best_objective:>10.4f} "
            f"{exp.mean_objective:>10.4f} "
            f"{exp.std_objective:>10.4f} "
            f"{exp.median_objective:>10.4f} "
            f"{exp.feasible_pct:>9.1f}% "
            f"{exp.mean_runtime_ms:>10.1f}"
        )
    print()
