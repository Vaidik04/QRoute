"""
optimization/qpso.py
====================
Baseline Quantum-behaved Particle Swarm Optimisation (QPSO) for routing.

QPSO variant implemented:
    Sun, J., Feng, B., & Xu, W. (2004). "Particle swarm optimization with
    particles having quantum behavior." Proceedings of the 2004 Congress on
    Evolutionary Computation, 325–331.

    Sun, J., et al. (2012). "QPSO: a quantum-behaved particle swarm
    optimization algorithm." Springer.

Update equations (Global QPSO):
    mbest_t = (1/N) Σ_{i=1}^{N} pbest_i^t          [mean best position]
    φ       ~ U(0, 1)
    p_i^t   = φ · pbest_i^t + (1 − φ) · gbest^t    [attractor]
    u       ~ U(0, 1)
    x_i^{t+1} = p_i^t ± α · |mbest^t − x_i^t| · ln(1/u)

The ± is chosen randomly (50/50).  α is the contraction-expansion
coefficient — a fixed value in this baseline, adaptive in adaptive_qpso.py.

Discrete routing pipeline per iteration:
    continuous QPSO position
        → clip to [0, 1]
        → random-key vector
        → sort → permutation
        → constraint-aware decoder
        → repair operator
        → route
        → fitness
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

import numpy as np

from .config import OptimizationConfig, ObjectiveWeights
from .decoder import decode, get_unserved, routes_to_sequence_list
from .encoding import clip_keys
from .fitness import calculate_fitness, vehicle_utilization
from .population import HybridInitializer, Particle
from .repair import repair
from .result import ConvergencePoint, OptimizationResult

if TYPE_CHECKING:
    from .problem import VRPProblem


class QPSO:
    """Baseline Global QPSO for Capacitated VRP.

    Parameters
    ----------
    problem : VRPProblem
    config  : OptimizationConfig
    weights : ObjectiveWeights | None   Falls back to problem.objective_weights.
    """

    ALGORITHM_NAME = "qpso"

    def __init__(
        self,
        problem: "VRPProblem",
        config: OptimizationConfig,
        weights: Optional[ObjectiveWeights] = None,
    ) -> None:
        self.problem = problem
        self.config = config
        self.weights = weights or problem.objective_weights
        self._rng = np.random.default_rng(config.random_seed)

    # ------------------------------------------------------------------
    # Public API (shared with all baselines)
    # ------------------------------------------------------------------

    def solve(self) -> OptimizationResult:
        """Run QPSO and return an OptimizationResult.

        This is the standard entry point used by experiment_runner.py.
        """
        t_start = time.perf_counter()
        config = self.config
        problem = self.problem
        weights = self.weights

        # --- Pre-check instance feasibility ---
        ok, reason = problem.is_feasible_instance()
        if not ok:
            return OptimizationResult.infeasible(
                self.ALGORITHM_NAME, reason,
                runtime_ms=(time.perf_counter() - t_start) * 1000,
            )

        # --- Initialise population ---
        initialiser = HybridInitializer(problem, self._rng)
        population: list[Particle] = initialiser.initialise(config.population_size)

        # --- Evaluate initial population ---
        for particle in population:
            self._evaluate(particle)

        # --- Set up global best ---
        gbest_particle = min(population, key=lambda p: p.fitness)
        gbest_position = gbest_particle.position.copy()
        gbest_fitness = gbest_particle.fitness
        gbest_solution = gbest_particle.decoded_solution

        convergence: list[ConvergencePoint] = []
        prev_best = gbest_fitness
        alpha = config.alpha_max  # fixed in baseline

        # --- Main QPSO loop ---
        for iteration in range(1, config.max_iterations + 1):
            # Time limit check
            if config.time_limit_seconds > 0:
                elapsed = time.perf_counter() - t_start
                if elapsed > config.time_limit_seconds:
                    break

            # Compute mbest (mean of personal bests)
            mbest = np.mean(
                [p.best_position for p in population], axis=0
            )

            # Update each particle
            for particle in population:
                self._update_position(particle, mbest, gbest_position, alpha)
                self._evaluate(particle)
                improved = particle.update_personal_best()
                if particle.best_fitness < gbest_fitness:
                    gbest_fitness = particle.best_fitness
                    gbest_position = particle.best_position.copy()
                    gbest_solution = particle.best_solution

            # Local search on global best (every local_search_freq iterations)
            if (
                config.use_local_search
                and iteration % config.local_search_freq == 0
            ):
                gbest_solution, gbest_fitness, gbest_position = self._apply_local_search(
                    gbest_solution, gbest_fitness, gbest_position
                )

            # Convergence logging
            mean_fitness = float(np.mean([p.fitness for p in population]))
            diversity = self._compute_diversity(population)
            improvement = max(0.0, prev_best - gbest_fitness)
            convergence.append(
                ConvergencePoint(
                    iteration=iteration,
                    best_fitness=gbest_fitness,
                    mean_fitness=mean_fitness,
                    diversity=diversity,
                    alpha=alpha,
                    improvement=improvement,
                )
            )
            prev_best = gbest_fitness

            if config.verbose and iteration % 10 == 0:
                print(
                    f"  [{self.ALGORITHM_NAME}] iter={iteration:4d}  "
                    f"best={gbest_fitness:.4f}  mean={mean_fitness:.4f}  "
                    f"div={diversity:.4f}  α={alpha:.4f}"
                )

        # --- Build result ---
        runtime_ms = (time.perf_counter() - t_start) * 1000
        return self._build_result(
            gbest_solution, gbest_fitness, gbest_position,
            convergence, config.max_iterations,
            runtime_ms, alpha,
        )

    # ------------------------------------------------------------------
    # QPSO mechanics
    # ------------------------------------------------------------------

    def _update_position(
        self,
        particle: Particle,
        mbest: np.ndarray,
        gbest_position: np.ndarray,
        alpha: float,
    ) -> None:
        """Sun et al. Global QPSO position update.

        x_i^{t+1} = p_i ± α · |mbest − x_i| · ln(1/u)
        """
        n = len(particle.position)
        phi = self._rng.uniform(0.0, 1.0, size=n)
        u = self._rng.uniform(0.0, 1.0, size=n)
        # Avoid log(0)
        u = np.clip(u, 1e-10, 1.0 - 1e-10)
        sign = np.where(self._rng.random(n) < 0.5, 1.0, -1.0)

        # Attractor: convex combination of personal best and global best
        p = phi * particle.best_position + (1.0 - phi) * gbest_position

        # Quantum delta potential well update
        particle.position = p + sign * alpha * np.abs(mbest - particle.position) * np.log(1.0 / u)
        particle.position = clip_keys(particle.position)

    # ------------------------------------------------------------------
    # Evaluation pipeline
    # ------------------------------------------------------------------

    def _evaluate(self, particle: Particle) -> None:
        """Decode → repair → fitness. Updates particle in-place."""
        routes = decode(particle.position, self.problem)
        if self.config.use_repair:
            routes, unserved = repair(routes, self.problem)
        else:
            unserved = getattr(routes[0], "unserved", []) if routes else []
        fitness = calculate_fitness(
            routes, self.problem, self.weights,
            unserved=unserved,
            penalty_coeff=self.config.penalty_coefficient,
        )
        particle.decoded_solution = routes
        particle.fitness = fitness

    # ------------------------------------------------------------------
    # Diversity measurement
    # ------------------------------------------------------------------

    def _compute_diversity(self, population: list[Particle]) -> float:
        """Population diversity: mean Euclidean distance from centroid.

        D = (1/N) · Σ ‖x_i − x̄‖
        """
        positions = np.array([p.position for p in population])
        centroid = positions.mean(axis=0)
        dists = np.linalg.norm(positions - centroid, axis=1)
        return float(dists.mean())

    # ------------------------------------------------------------------
    # Local search hook (overridden by AdaptiveQPSO)
    # ------------------------------------------------------------------

    def _apply_local_search(
        self,
        routes,
        fitness: float,
        position: np.ndarray,
    ):
        """Apply local search to the global best. Returns (routes, fitness, position)."""
        from .local_search import two_opt, relocate_ls, swap_ls

        improved_routes = two_opt(routes, self.problem)
        improved_routes = relocate_ls(improved_routes, self.problem)
        improved_routes = swap_ls(improved_routes, self.problem)

        unserved = getattr(improved_routes[0], "unserved", []) if improved_routes else []
        new_fitness = calculate_fitness(
            improved_routes, self.problem, self.weights,
            unserved=unserved,
            penalty_coeff=self.config.penalty_coefficient,
        )

        if new_fitness < fitness:
            from .encoding import permutation_to_random_keys
            # Reconstruct a representative key vector from the improved solution
            full_perm = []
            for route in improved_routes:
                for cust_idx in route.sequence:
                    full_perm.append(cust_idx - 1)  # 0-indexed
            # Pad/fill missing customers
            all_customers = set(range(self.problem.n_customers))
            in_perm = set(full_perm)
            for c in all_customers - in_perm:
                full_perm.append(c)
            new_position = permutation_to_random_keys(full_perm, rng=self._rng)
            return improved_routes, new_fitness, new_position

        return routes, fitness, position

    # ------------------------------------------------------------------
    # Result builder
    # ------------------------------------------------------------------

    def _build_result(
        self,
        gbest_solution,
        gbest_fitness: float,
        gbest_position: np.ndarray,
        convergence: list[ConvergencePoint],
        iterations: int,
        runtime_ms: float,
        alpha: float,
    ) -> OptimizationResult:
        from .constraints import check_all

        if gbest_solution is None:
            return OptimizationResult.infeasible(
                self.ALGORITHM_NAME,
                "Optimizer produced no solution.",
                runtime_ms=runtime_ms,
            )

        constraint_result = check_all(gbest_solution, self.problem)
        unserved = getattr(gbest_solution[0], "unserved", []) if gbest_solution else []

        # Determine status
        if constraint_result.feasible and not unserved:
            status = "FEASIBLE"
            reason = ""
        else:
            status = "INFEASIBLE"
            reasons = constraint_result.details[:]
            if unserved:
                reasons.append(
                    f"{len(unserved)} customer(s) could not be assigned to any vehicle."
                )
            reason = "; ".join(reasons[:5])  # cap for readability

        route_lists = routes_to_sequence_list(gbest_solution)
        vehicle_assignments = {
            route.vehicle_id: [cid - 1 for cid in route.sequence]
            for route in gbest_solution
            if not route.is_empty()
        }

        total_distance = sum(r.total_distance for r in gbest_solution)
        total_time = max((r.total_time for r in gbest_solution if not r.is_empty()), default=0.0)
        util = vehicle_utilization(gbest_solution, self.problem)

        return OptimizationResult.feasible_from_routes(
            algorithm=self.ALGORITHM_NAME,
            routes=route_lists,
            vehicle_assignments=vehicle_assignments,
            objective_value=gbest_fitness,
            distance_km=total_distance,
            travel_time_min=total_time,
            vehicle_utilization=util,
            constraint_violations=constraint_result.violation_count + len(unserved),
            iterations=iterations,
            runtime_ms=runtime_ms,
            convergence=convergence,
            population_size=self.config.population_size,
            random_seed=self.config.random_seed,
            feasible_routes=sum(1 for r in gbest_solution if not r.is_empty()),
        ) if status == "FEASIBLE" else OptimizationResult.infeasible(
            self.ALGORITHM_NAME, reason, runtime_ms
        )
