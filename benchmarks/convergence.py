"""
benchmarks/convergence.py
=========================
Convergence plot generation for the benchmark suite.

Produces the key visualisation judges expect (Section 18.5):
    QPSO vs. PSO vs. Adaptive QPSO on the same convergence graph.

Also generates:
    - Ablation study convergence plots (A–E)
    - Diversity over time
    - Alpha schedule over time
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "figure.dpi": 120,
})

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "results"


def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def plot_convergence_comparison(
    convergence_data: dict[str, list],
    title: str = "Convergence Comparison",
    filename: str = "convergence_comparison.png",
    metric: str = "best_fitness",
    show: bool = False,
) -> Path:
    """Plot convergence curves for multiple algorithms on one chart.

    Parameters
    ----------
    convergence_data : dict[algorithm_name → list[ConvergencePoint]]
    title : str
    filename : str
    metric : str      "best_fitness" | "mean_fitness" | "diversity" | "alpha"
    show : bool       If True, call plt.show() (blocks).

    Returns
    -------
    Path   Saved figure path.
    """
    out = _ensure_output_dir()
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4"]
    for (algo_name, history), color in zip(convergence_data.items(), colors):
        if not history:
            continue
        if isinstance(history[0], (int, float, np.floating, np.integer)):
            iterations = list(range(len(history)))
            values = list(history)
        else:
            iterations = [
                cp.iteration if hasattr(cp, "iteration")
                else (cp["iteration"] if isinstance(cp, dict) else idx)
                for idx, cp in enumerate(history)
            ]
            values = [
                getattr(cp, metric, None) if hasattr(cp, metric)
                else (cp.get(metric, float("nan")) if isinstance(cp, dict) else cp)
                for cp in history
            ]
        ax.plot(iterations, values, label=algo_name, color=color, linewidth=2, alpha=0.85)

    ax.set_xlabel("Iteration")
    metric_labels = {
        "best_fitness": "Best Fitness",
        "mean_fitness": "Mean Fitness",
        "diversity": "Population Diversity",
        "alpha": "Alpha (Contraction-Expansion)",
    }
    ax.set_ylabel(metric_labels.get(metric, metric))
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    path = out / filename
    fig.savefig(path, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return path


def plot_convergence_with_diversity(
    history: list,
    algorithm_name: str = "Adaptive D-QPSO",
    filename: str = "adaptive_qpso_detail.png",
    show: bool = False,
) -> Path:
    """Plot best fitness + diversity + alpha on a single figure (3 subplots)."""
    out = _ensure_output_dir()
    iterations = [
        cp.iteration if hasattr(cp, "iteration")
        else (cp["iteration"] if isinstance(cp, dict) else idx)
        for idx, cp in enumerate(history)
    ]
    best_fit = [
        getattr(cp, "best_fitness", None) if hasattr(cp, "best_fitness")
        else (cp.get("best_fitness", 0.0) if isinstance(cp, dict) else float(cp))
        for cp in history
    ]
    diversity = [
        getattr(cp, "diversity", None) if hasattr(cp, "diversity")
        else (cp.get("diversity", 0.0) if isinstance(cp, dict) else 0.0)
        for cp in history
    ]
    alpha = [
        getattr(cp, "alpha", None) if hasattr(cp, "alpha")
        else (cp.get("alpha", 0.0) if isinstance(cp, dict) else 0.0)
        for cp in history
    ]

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

    axes[0].plot(iterations, best_fit, color="#2196F3", linewidth=2)
    axes[0].set_ylabel("Best Fitness")
    axes[0].set_title(f"{algorithm_name} — Convergence Detail")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(iterations, diversity, color="#4CAF50", linewidth=2)
    axes[1].set_ylabel("Population Diversity")
    axes[1].axhline(y=0.05, color="red", linestyle="--", alpha=0.6, label="Diversity threshold")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(iterations, alpha, color="#FF9800", linewidth=2)
    axes[2].set_ylabel("Alpha (α)")
    axes[2].set_xlabel("Iteration")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    path = out / filename
    fig.savefig(path, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return path


def plot_scalability(
    sizes: list[int],
    runtimes: dict[str, list[float]],
    filename: str = "scalability_runtime.png",
    show: bool = False,
) -> Path:
    """Problem size vs. runtime plot for scalability analysis."""
    out = _ensure_output_dir()
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0"]
    for (algo, times), color in zip(runtimes.items(), colors):
        ax.plot(sizes, times, marker="o", label=algo, color=color, linewidth=2)

    ax.set_xlabel("Number of Customers")
    ax.set_ylabel("Runtime (ms)")
    ax.set_title("Scalability: Problem Size vs. Runtime")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = out / filename
    fig.savefig(path, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return path


def plot_box_comparison(
    data: dict[str, np.ndarray],
    title: str = "Solution Quality Distribution (30 Runs)",
    ylabel: str = "Objective Value",
    filename: str = "box_comparison.png",
    show: bool = False,
) -> Path:
    """Box plots for comparing algorithm solution distributions."""
    out = _ensure_output_dir()
    fig, ax = plt.subplots(figsize=(10, 6))
    names = list(data.keys())
    values = [data[n] for n in names]
    bp = ax.boxplot(values, labels=names, patch_artist=True, notch=False)
    colors = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4"]
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    path = out / filename
    fig.savefig(path, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return path


def plot_ablation(
    ablation_results: dict[str, float],
    filename: str = "ablation_study.png",
    show: bool = False,
) -> Path:
    """Bar chart for ablation study results (A–E configurations)."""
    out = _ensure_output_dir()
    configs = list(ablation_results.keys())
    values = [ablation_results[c] for c in configs]

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#90CAF9", "#64B5F6", "#42A5F5", "#2196F3", "#1565C0"]
    bars = ax.bar(configs, values, color=colors[:len(configs)], edgecolor="white", linewidth=1.2)
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Mean Objective Value (30 runs)")
    ax.set_title("Ablation Study — Contribution of Each Component")
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01 * max(values),
            f"{val:.2f}", ha="center", va="bottom", fontsize=10
        )
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    path = out / filename
    fig.savefig(path, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return path
