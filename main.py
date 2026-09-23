"""
main.py
=======
CLI entry point for the Q-TRANSIT NEXUS Optimization Engine (Member 1).

Usage:
    python main.py --demo          # Quick end-to-end demo on Bhopal 15-node instance
    python main.py --benchmark     # Standard benchmark suite with statistical summary & LaTeX table
    python main.py --reopt-demo    # Dynamic re-optimization demo on incident injection
    python main.py --quantum-demo  # Quantum Lab (QUBO/QAOA vs Brute-force vs Adaptive D-QPSO)
    python main.py --plot          # Generate & save convergence and scalability plots to ./plots/
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from optimization.config import OptimizationConfig, ObjectiveWeights
from optimization.problem import VRPProblem
from optimization.entities import VehicleState
from optimization.adaptive_qpso import AdaptiveQPSO
from optimization.qpso import QPSO
from optimization.reoptimization import ReOptimizer
from benchmarks.bhopal_generator import generate_bhopal_instance
from benchmarks.experiment_runner import compare_algorithms
from benchmarks.statistics import print_comparison_table
from benchmarks.convergence import (
    plot_convergence_comparison,
    plot_convergence_with_diversity,
    plot_scalability,
)
from quantum.small_instance_experiment import run_small_instance_experiment


def run_demo() -> None:
    """Run a quick end-to-end demo on a Bhopal 15-node CVRP instance."""
    print("=" * 70)
    print(" Q-TRANSIT NEXUS — End-to-End Optimization Demo (Bhopal 15-node)")
    print("=" * 70)

    # 1. Generate problem instance
    print("\n[1/3] Generating realistic Bhopal instance (15 customers, 3 vehicles)...")
    problem = generate_bhopal_instance(
        n_customers=15,
        n_vehicles=3,
        capacity=100.0,
        seed=42,
        traffic_scenario="evening_peak",
    )
    print(f"  Depot: Central Depot ({problem.depot_x:.2f}, {problem.depot_y:.2f})")
    print(f"  Customers: {problem.n_customers}")
    print(f"  Vehicles: {problem.n_vehicles} (capacity: {problem.vehicles[0].capacity})")
    total_demand = sum(c.demand for c in problem.customers)
    print(f"  Total Customer Demand: {total_demand:.1f}")

    # 2. Configure optimizer
    cfg = OptimizationConfig(
        population_size=40,
        max_iterations=100,
        random_seed=42,
        alpha_max=1.0,
        alpha_min=0.3,
        use_adaptive_alpha=True,
        use_local_search=True,
        use_repair=True,
        verbose=False,
    )

    # 3. Solve with Standard QPSO
    print("\n[2/3] Solving with Standard Baseline QPSO...")
    t0 = time.perf_counter()
    qpso_opt = QPSO(problem, cfg)
    qpso_res = qpso_opt.solve()
    qpso_time = (time.perf_counter() - t0) * 1000
    print(f"  Standard QPSO: Cost={qpso_res.objective_value:.2f}, "
          f"Distance={qpso_res.distance_km:.2f} km, Time={qpso_time:.1f} ms, "
          f"Feasible={qpso_res.is_feasible}")

    # 4. Solve with Adaptive D-QPSO
    print("\n[3/3] Solving with Adaptive Discrete QPSO (Proposed Method)...")
    t0 = time.perf_counter()
    aqpso_opt = AdaptiveQPSO(problem, cfg)
    aqpso_res = aqpso_opt.solve()
    aqpso_time = (time.perf_counter() - t0) * 1000
    print(f"  Adaptive D-QPSO: Cost={aqpso_res.objective_value:.2f}, "
          f"Distance={aqpso_res.distance_km:.2f} km, Time={aqpso_time:.1f} ms, "
          f"Feasible={aqpso_res.is_feasible}")

    # Route breakdown
    improvement = ((qpso_res.objective_value - aqpso_res.objective_value)
                   / max(1e-6, qpso_res.objective_value)) * 100
    print(f"\nOptimization Result:")
    print(f"  Cost Improvement: {improvement:+.2f}%")

    # Display Rich Terminal ASCII Plan
    print("\n" + aqpso_res.visualize_ascii(problem))

    # Export RFC 7946 GeoJSON FeatureCollection
    geojson_out = aqpso_res.to_geojson(problem)
    out_dir = PROJECT_ROOT / "data" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = out_dir / "demo_routes.geojson"
    import json
    geojson_path.write_text(json.dumps(geojson_out, indent=2))
    print(f"\n[GeoJSON] Exported valid RFC 7946 FeatureCollection to {geojson_path}")
    print("          (Ready for instant Leaflet / Mapbox / Deck.gl map visualization)")
    print("\nDemo completed successfully.\n")


def run_benchmark_suite() -> None:
    """Run standard benchmark comparing optimizers with statistics & LaTeX output."""
    print("=" * 70)
    print(" Q-TRANSIT NEXUS — Standard Benchmark Suite")
    print("=" * 70)

    from optimization.baselines import (
        DijkstraBaseline,
        AStarBaseline,
        PSOOptimizer,
        GAOptimizer,
        ACOOptimizer,
    )

    n_cust = 20
    n_runs = 5  # Fast 5-run evaluation for CLI demonstration
    print(f"\nRunning benchmark on Bhopal {n_cust}-node instance ({n_runs} runs per algorithm)...")
    problem = generate_bhopal_instance(n_customers=n_cust, n_vehicles=4, capacity=100.0, seed=42)
    cfg = OptimizationConfig(population_size=30, max_iterations=60, random_seed=42, verbose=False)

    algorithms = [
        DijkstraBaseline,
        AStarBaseline,
        PSOOptimizer,
        GAOptimizer,
        ACOOptimizer,
        QPSO,
        AdaptiveQPSO,
    ]

    results = compare_algorithms(
        optimizer_classes=algorithms,
        problem=problem,
        config=cfg,
        n_runs=n_runs,
        problem_name=f"Bhopal_{n_cust}",
        verbose=False,
    )

    print("\n" + "=" * 70)
    print(" BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    print_comparison_table(results)

    # Output LaTeX table snippet
    print("\nLaTeX Table Output:")
    print("-" * 50)
    print("\\begin{table}[ht]")
    print("\\centering")
    print("\\begin{tabular}{lrrrrr}")
    print("\\hline")
    print("Algorithm & Best Cost & Mean Cost & Std Dev & Mean Time (ms) & Feasible (\\%) \\\\")
    print("\\hline")
    for name, exp in results.items():
        print(f"{name:15s} & {exp.best_objective:8.2f} & {exp.mean_objective:8.2f} & "
              f"{exp.std_objective:7.2f} & {exp.mean_runtime_ms:8.1f} & {exp.feasible_pct:6.1f} \\\\")
    print("\\hline")
    print("\\end{tabular}")
    print("\\caption{Optimization performance comparison on Bhopal 20-node CVRP instance}")
    print("\\label{tab:algorithm_comparison}")
    print("\\end{table}")
    print("-" * 50)


def run_reopt_demo() -> None:
    """Simulate incident injection and dynamic route re-optimization."""
    print("=" * 70)
    print(" Q-TRANSIT NEXUS — Rolling Dynamic Re-Optimization Demo")
    print("=" * 70)

    # 1. Initial 15-customer problem
    problem = generate_bhopal_instance(n_customers=15, n_vehicles=3, capacity=100.0, seed=123)
    cfg = OptimizationConfig(population_size=30, max_iterations=80, random_seed=123, verbose=False)

    print("\n[Step 1] Initial optimization before trip start...")
    initial_opt = AdaptiveQPSO(problem, cfg)
    init_res = initial_opt.solve()
    print(f"  Initial Solution: Cost={init_res.objective_value:.2f}, Feasible={init_res.is_feasible}")
    for vid, cust_list in init_res.vehicle_assignments.items():
        if cust_list:
            print(f"    V{vid} Initial Planned: {cust_list}")

    # 2. Simulate vehicles partially executing routes
    # Freeze first 1 customer of each route as already served
    reoptimizer = ReOptimizer(problem, cfg)

    vehicle_states = {}
    for vid, cust_list in init_res.vehicle_assignments.items():
        if not cust_list:
            continue
        completed = [cust_list[0]]
        remaining = list(cust_list[1:])
        curr_load = sum(problem.customers[cid].demand for cid in completed)
        vehicle_states[vid] = VehicleState(
            vehicle_id=vid,
            current_node=completed[-1] + 1,  # 1-indexed node
            current_load=curr_load,
            completed_customers=completed,
            remaining_customers=remaining,
        )

    print("\n[Step 2] Execution in progress (completed prefix frozen):")
    for vid, vs in vehicle_states.items():
        print(f"    V{vid}: Completed={vs.completed_customers} -> At Node {vs.current_node} -> Remaining={vs.remaining_customers}")

    # 3. Simulate Traffic Incident (Road Closure on link between depot and next customer)
    v_with_rem = [vs for vs in vehicle_states.values() if vs.remaining_customers]
    incident_edge = f"0_{v_with_rem[0].remaining_customers[0] + 1}" if v_with_rem else "0_1"
    print(f"\n[Step 3] INCOMING TRAFFIC INCIDENT from Traffic Module:")
    print(f"  Incident: Edge '{incident_edge}' CLOSED (severity: HIGH, multiplier: inf)")

    incident = {
        "edge_id": incident_edge,
        "status": "CLOSED",
        "severity": "HIGH",
    }

    # 4. Trigger rolling re-optimization
    print("\n[Step 4] Triggering rolling horizon re-optimizer...")
    t0 = time.perf_counter()
    reopt_res = reoptimizer.reoptimize(
        vehicle_states=vehicle_states,
        incidents=[incident],
        incident_multipliers=[float("inf")],
    )
    recovery_time = (time.perf_counter() - t0) * 1000

    print(f"  Re-optimization Status: {reopt_res.status}")
    print(f"  Recovery Time: {recovery_time:.2f} ms")
    print(f"  Re-optimized Suffix Routes:")
    for vid, cust_list in reopt_res.vehicle_assignments.items():
        if cust_list:
            print(f"    V{vid} Suffix: {cust_list}")
    print("\nDynamic Re-optimization demo finished successfully.\n")


def run_quantum_demo() -> None:
    """Run Quantum Lab demonstration on tiny CVRP instances (4-5 customers)."""
    print("=" * 70)
    print(" Q-TRANSIT NEXUS — Quantum Lab (QUBO & QAOA Demonstration)")
    print("=" * 70)
    res = run_small_instance_experiment(n_customers=4, seed=42, n_qaoa_layers=2)
    print("\nSummary of Quantum Lab Experiment (n=4):")
    if "brute_force" in res and "energy" in res["brute_force"]:
        print(f"  Exact Brute-Force Energy : {res['brute_force']['energy']:.4f} (Runtime: {res['brute_force']['runtime_ms']:.1f} ms)")
    if "qaoa" in res and "energy" in res["qaoa"]:
        print(f"  QAOA ({res['qaoa']['algorithm']}) Energy: {res['qaoa']['energy']:.4f} (Runtime: {res['qaoa']['runtime_ms']:.1f} ms, Qubits: {res['qaoa']['n_qubits']})")
    if "adaptive_d_qpso" in res:
        print(f"  Adaptive D-QPSO Objective: {res['adaptive_d_qpso']['objective']:.4f} (Runtime: {res['adaptive_d_qpso']['runtime_ms']:.1f} ms)")
    print("\nQuantum demo completed successfully.\n")


def run_plots_demo() -> None:
    """Generate and save convergence and scalability plots to ./plots/."""
    print("=" * 70)
    print(" Q-TRANSIT NEXUS — Generating Convergence & Scalability Plots")
    print("=" * 70)

    plots_dir = PROJECT_ROOT / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # 1. Convergence comparison
    print("[1/2] Generating convergence comparison plot...")
    problem = generate_bhopal_instance(n_customers=20, n_vehicles=3, capacity=100.0, seed=42)
    cfg = OptimizationConfig(population_size=30, max_iterations=60, random_seed=42, verbose=False)

    from optimization.qpso import QPSO
    from optimization.baselines import PSOOptimizer, GAOptimizer

    optimizers = {
        "Adaptive D-QPSO": AdaptiveQPSO(problem, cfg),
        "Standard QPSO": QPSO(problem, cfg),
        "Classical PSO": PSOOptimizer(problem, cfg),
        "Genetic Algorithm": GAOptimizer(problem, cfg),
    }

    histories = {}
    for name, opt in optimizers.items():
        res = opt.solve()
        histories[name] = res.convergence_history

    out_file = str(plots_dir / "convergence_comparison.png")
    plot_convergence_comparison(
        histories,
        title="Convergence Comparison (Bhopal 20-node CVRP)",
        filename=out_file,
    )
    print(f"  Saved: {out_file}")

    # 2. Adaptive D-QPSO Detail (Fitness, Diversity, Alpha)
    print("[2/2] Generating Adaptive D-QPSO telemetry plot (fitness, diversity, alpha)...")
    aq_opt = AdaptiveQPSO(problem, cfg)
    aq_res = aq_opt.solve()
    detail_file = "adaptive_qpso_detail.png"
    saved_detail = plot_convergence_with_diversity(
        history=aq_res.convergence,
        algorithm_name="Adaptive D-QPSO",
        filename=detail_file,
    )
    print(f"  Saved: {saved_detail}")
    print("\nPlots generated and saved successfully.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Q-TRANSIT NEXUS Optimization Engine CLI (Member 1)"
    )
    parser.add_argument("--demo", action="store_true", help="Run quick end-to-end demo on Bhopal instance")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark suite across all optimizers")
    parser.add_argument("--reopt-demo", action="store_true", help="Run dynamic re-optimization demo on incident injection")
    parser.add_argument("--quantum-demo", action="store_true", help="Run Quantum Lab (QUBO & QAOA experiment)")
    parser.add_argument("--plot", action="store_true", help="Generate convergence plots to ./plots/")

    args = parser.parse_args()

    # If no flags provided, show help and run demo
    if not (args.demo or args.benchmark or args.reopt_demo or args.quantum_demo or args.plot):
        print("No specific flag selected. Defaulting to --demo. (Use --help to view all options)\n")
        run_demo()
        return

    if args.demo:
        run_demo()
    if args.benchmark:
        run_benchmark_suite()
    if args.reopt_demo:
        run_reopt_demo()
    if args.quantum_demo:
        run_quantum_demo()
    if args.plot:
        run_plots_demo()


if __name__ == "__main__":
    main()
