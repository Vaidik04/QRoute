"""
quantum/small_instance_experiment.py
=====================================
Comparison of QUBO/QAOA vs. brute-force vs. Adaptive D-QPSO for tiny instances.

This validates the QUBO formulation against an exact reference and shows
how the quantum-inspired and quantum approaches compare on problems where
exact solutions are computable.

Results should be reported honestly:
- QAOA on simulator ≠ real quantum computer
- For n ≤ 6, brute force is exact
- Adaptive D-QPSO remains the recommended approach for n > 6
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from .qubo import build_qubo_matrix, brute_force_qubo, decode_qubo_solution, qubo_energy
from .qaoa import run_qaoa


def run_small_instance_experiment(
    n_customers: int = 5,
    seed: int = 42,
    n_qaoa_layers: int = 2,
    run_qaoa_flag: bool = True,
    run_aqpso: bool = True,
) -> dict:
    """Compare QUBO/QAOA, brute-force, and Adaptive D-QPSO on a small instance.

    Parameters
    ----------
    n_customers : int   Must be ≤ 6.
    seed : int
    n_qaoa_layers : int QAOA circuit depth.
    run_qaoa_flag : bool
    run_aqpso : bool

    Returns
    -------
    dict of results per method.
    """
    if n_customers > 6:
        raise ValueError("Small-instance experiment limited to n ≤ 6.")

    from optimization.problem import VRPProblem
    problem = VRPProblem.random_cvrp(
        n_customers=n_customers, n_vehicles=1, capacity=200.0, seed=seed
    )

    print(f"\n=== Quantum Lab: Small Instance Experiment (n={n_customers}) ===")
    results = {"n_customers": n_customers, "seed": seed}

    # --- 1. Build QUBO ---
    t0 = time.perf_counter()
    Q, n_cust, n_pos = build_qubo_matrix(problem, n_customers=n_customers)
    n_vars = n_cust * n_pos
    results["n_qubo_variables"] = n_vars
    print(f"  QUBO: {n_vars} binary variables ({n_cust}×{n_pos})")

    # --- 2. Brute-force (exact reference) ---
    if n_vars <= 20:
        t_bf = time.perf_counter()
        bf_x, bf_energy = brute_force_qubo(Q, n_vars)
        bf_perm = decode_qubo_solution(bf_x, n_cust, n_pos)
        bf_time = (time.perf_counter() - t_bf) * 1000
        results["brute_force"] = {
            "energy": float(bf_energy),
            "permutation": bf_perm,
            "feasible": len(bf_perm) == n_cust,
            "runtime_ms": round(bf_time, 2),
        }
        print(f"  Brute-force: energy={bf_energy:.4f}  perm={bf_perm}  rt={bf_time:.1f}ms")
    else:
        results["brute_force"] = {"note": "skipped (n_vars > 20)"}
        print(f"  Brute-force: skipped (n_vars={n_vars} > 20)")

    # --- 3. QAOA ---
    if run_qaoa_flag:
        qaoa_result = run_qaoa(Q, n_cust, n_pos, n_layers=n_qaoa_layers, seed=seed)
        results["qaoa"] = {
            "algorithm": qaoa_result.algorithm,
            "energy": float(qaoa_result.best_energy),
            "permutation": qaoa_result.permutation,
            "feasible": qaoa_result.feasible,
            "runtime_ms": round(qaoa_result.runtime_ms, 2),
            "n_qubits": qaoa_result.n_qubits,
            "n_layers": qaoa_result.n_layers,
            "approximation_ratio": qaoa_result.approximation_ratio,
            "ground_state_fidelity": qaoa_result.ground_state_fidelity,
        }
        fidelity_str = f"  fidelity={qaoa_result.ground_state_fidelity:.3f}" if qaoa_result.ground_state_fidelity is not None else ""
        approx_str = f"  approx_ratio={qaoa_result.approximation_ratio:.3f}" if qaoa_result.approximation_ratio is not None else ""
        print(
            f"  QAOA ({qaoa_result.algorithm}): energy={qaoa_result.best_energy:.4f}{approx_str}{fidelity_str}  "
            f"perm={qaoa_result.permutation}  rt={qaoa_result.runtime_ms:.1f}ms"
        )

    # --- 4. Adaptive D-QPSO ---
    if run_aqpso:
        from optimization.adaptive_qpso import AdaptiveQPSO
        from optimization.config import OptimizationConfig
        cfg = OptimizationConfig(population_size=20, max_iterations=50, random_seed=seed)
        t_aq = time.perf_counter()
        opt = AdaptiveQPSO(problem, cfg)
        aqpso_result = opt.solve()
        aqpso_time = (time.perf_counter() - t_aq) * 1000
        results["adaptive_d_qpso"] = {
            "objective": round(aqpso_result.objective_value, 4),
            "distance_km": round(aqpso_result.distance_km, 4),
            "status": aqpso_result.status,
            "runtime_ms": round(aqpso_result.runtime_ms, 2),
        }
        print(
            f"  Adaptive D-QPSO: obj={aqpso_result.objective_value:.4f}  "
            f"status={aqpso_result.status}  rt={aqpso_result.runtime_ms:.1f}ms"
        )

    # --- Save ---
    out = Path(__file__).parent.parent / "data" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"quantum_experiment_n{n_customers}.json").write_text(
        json.dumps(results, indent=2, default=str)
    )

    return results
