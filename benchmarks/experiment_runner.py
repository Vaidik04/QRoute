"""
benchmarks/experiment_runner.py
================================
30-independent-run experiment harness.

Runs any algorithm (QPSO, PSO, GA, ACO, Adaptive QPSO, baselines)
on any problem for N independent runs, collecting:
    best, mean, median, std, runtime_ms, feasible_count per run.

Usage:
    from benchmarks.experiment_runner import run_experiment
    results = run_experiment(AdaptiveQPSO, problem, config, n_runs=30)
    print(results.summary_table())
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Type

import numpy as np

from optimization.config import OptimizationConfig, ObjectiveWeights
from optimization.result import OptimizationResult


@dataclass
class RunRecord:
    """Results from a single independent run."""
    run_id: int
    seed: int
    status: str
    objective_value: float
    distance_km: float
    travel_time_min: float
    constraint_violations: int
    iterations: int
    runtime_ms: float
    feasible: bool
    convergence_length: int


@dataclass
class ExperimentResults:
    """Aggregated results from 30 independent runs."""
    algorithm: str
    problem_name: str
    n_runs: int
    runs: list[RunRecord] = field(default_factory=list)

    # Aggregates (computed in summarize())
    best_objective: float = float("inf")
    mean_objective: float = float("inf")
    median_objective: float = float("inf")
    std_objective: float = 0.0
    mean_runtime_ms: float = 0.0
    std_runtime_ms: float = 0.0
    feasible_count: int = 0
    feasible_pct: float = 0.0
    best_distance_km: float = float("inf")
    mean_distance_km: float = float("inf")

    def summarize(self) -> None:
        """Compute aggregate statistics from individual run records."""
        feasible_runs = [r for r in self.runs if r.feasible]
        self.feasible_count = len(feasible_runs)
        self.feasible_pct = 100.0 * self.feasible_count / self.n_runs if self.n_runs > 0 else 0.0

        all_objs = [r.objective_value for r in self.runs]
        feasible_objs = [r.objective_value for r in feasible_runs]
        runtimes = [r.runtime_ms for r in self.runs]

        if all_objs:
            self.best_objective = float(np.min(all_objs))
            self.mean_objective = float(np.mean(all_objs))
            self.median_objective = float(np.median(all_objs))
            self.std_objective = float(np.std(all_objs))
        if runtimes:
            self.mean_runtime_ms = float(np.mean(runtimes))
            self.std_runtime_ms = float(np.std(runtimes))
        if feasible_runs:
            self.best_distance_km = float(min(r.distance_km for r in feasible_runs))
            self.mean_distance_km = float(np.mean([r.distance_km for r in feasible_runs]))

    def objective_values(self) -> np.ndarray:
        return np.array([r.objective_value for r in self.runs])

    def runtime_values(self) -> np.ndarray:
        return np.array([r.runtime_ms for r in self.runs])

    def summary_table(self) -> str:
        """Human-readable summary table."""
        return (
            f"Algorithm: {self.algorithm}\n"
            f"Problem  : {self.problem_name}\n"
            f"Runs     : {self.n_runs}\n"
            f"Feasible : {self.feasible_count}/{self.n_runs} ({self.feasible_pct:.1f}%)\n"
            f"Obj Best : {self.best_objective:.4f}\n"
            f"Obj Mean : {self.mean_objective:.4f} +/- {self.std_objective:.4f}\n"
            f"Obj Median: {self.median_objective:.4f}\n"
            f"Dist Best: {self.best_distance_km:.2f} km\n"
            f"Runtime  : {self.mean_runtime_ms:.1f} +/- {self.std_runtime_ms:.1f} ms\n"
        )

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "problem_name": self.problem_name,
            "n_runs": self.n_runs,
            "feasible_count": self.feasible_count,
            "feasible_pct": round(self.feasible_pct, 2),
            "best_objective": round(self.best_objective, 4),
            "mean_objective": round(self.mean_objective, 4),
            "median_objective": round(self.median_objective, 4),
            "std_objective": round(self.std_objective, 4),
            "best_distance_km": round(self.best_distance_km, 2),
            "mean_distance_km": round(self.mean_distance_km, 2),
            "mean_runtime_ms": round(self.mean_runtime_ms, 2),
            "std_runtime_ms": round(self.std_runtime_ms, 2),
        }


def run_experiment(
    optimizer_class,
    problem,
    config: OptimizationConfig,
    n_runs: int = 30,
    seed_base: int = 42,
    problem_name: str = "unnamed",
    weights: Optional[ObjectiveWeights] = None,
    verbose: bool = False,
) -> ExperimentResults:
    """Run an optimizer for n_runs independent runs and collect statistics.

    Parameters
    ----------
    optimizer_class : class   Any class with .solve() → OptimizationResult.
    problem : VRPProblem
    config : OptimizationConfig
    n_runs : int              30 per Section 18.4.
    seed_base : int           Run i uses seed = seed_base + i.
    problem_name : str        Label for reporting.
    weights : ObjectiveWeights | None
    verbose : bool

    Returns
    -------
    ExperimentResults
    """
    import copy

    results = ExperimentResults(
        algorithm=optimizer_class.ALGORITHM_NAME,
        problem_name=problem_name,
        n_runs=n_runs,
    )

    for run_id in range(n_runs):
        seed = seed_base + run_id
        run_config = copy.copy(config)
        run_config.random_seed = seed

        optimizer = optimizer_class(problem, run_config, weights)
        result: OptimizationResult = optimizer.solve()

        record = RunRecord(
            run_id=run_id,
            seed=seed,
            status=result.status,
            objective_value=result.objective_value,
            distance_km=result.distance_km,
            travel_time_min=result.travel_time_min,
            constraint_violations=result.constraint_violations,
            iterations=result.iterations,
            runtime_ms=result.runtime_ms,
            feasible=result.status == "FEASIBLE",
            convergence_length=len(result.convergence),
        )
        results.runs.append(record)

        if verbose:
            print(
                f"  Run {run_id+1:2d}/{n_runs}  seed={seed}  "
                f"{result.summary()}"
            )

    results.summarize()
    return results


def compare_algorithms(
    optimizer_classes: list,
    problem,
    config: OptimizationConfig,
    n_runs: int = 30,
    problem_name: str = "unnamed",
    weights: Optional[ObjectiveWeights] = None,
    verbose: bool = True,
) -> dict[str, ExperimentResults]:
    """Run multiple algorithms on the same problem and collect all results.

    Returns dict of algorithm_name → ExperimentResults.
    """
    all_results = {}
    for cls in optimizer_classes:
        if verbose:
            print(f"\nRunning {cls.ALGORITHM_NAME} ({n_runs} runs)...")
        exp = run_experiment(
            cls, problem, config, n_runs=n_runs,
            problem_name=problem_name, weights=weights, verbose=verbose,
        )
        all_results[cls.ALGORITHM_NAME] = exp
        if verbose:
            print(exp.summary_table())
    return all_results
