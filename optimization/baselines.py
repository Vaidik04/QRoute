"""
optimization/baselines.py
=========================
Baseline optimizers for benchmarking against Adaptive D-QPSO.

All algorithms expose the SAME interface:
    BaseOptimizer.solve() -> OptimizationResult

This ensures the experiment_runner.py can compare them automatically
on an apples-to-apples basis (same decoder, same fitness, same constraints).

Algorithms implemented:
    DijkstraBaseline  — greedy nearest-neighbor sequential assignment
    AStarBaseline     — same as Dijkstra for matrix-level comparison
    PSOOptimizer      — standard continuous PSO (same random-key decode)
    GAOptimizer       — genetic algorithm (order crossover + mutation)
    ACOOptimizer      — ant colony optimization with pheromone update

Notes on honesty (Section 25):
- These are practical heuristic implementations, not exact solvers.
- Gap% comparisons to exact reference use OR-Tools (benchmarks/reports.py).
- Never claim "baseline X is slower" without benchmark data.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

import numpy as np

from .config import OptimizationConfig, ObjectiveWeights
from .decoder import decode, decode_permutation, get_unserved, routes_to_sequence_list
from .encoding import clip_keys, random_keys_to_permutation
from .fitness import calculate_fitness, vehicle_utilization
from .population import HybridInitializer, Particle
from .repair import repair
from .result import ConvergencePoint, OptimizationResult
from .qpso import QPSO

if TYPE_CHECKING:
    from .problem import VRPProblem


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseOptimizer:
    """Common interface for all optimizers."""

    ALGORITHM_NAME = "base"

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

    def solve(self) -> OptimizationResult:
        raise NotImplementedError

    def _evaluate_keys(self, keys: np.ndarray):
        """Full pipeline: keys → decode → repair → fitness."""
        routes = decode(keys, self.problem)
        if self.config.use_repair:
            routes, unserved = repair(routes, self.problem)
        else:
            unserved = getattr(routes[0], "unserved", []) if routes else []
        fitness = calculate_fitness(
            routes, self.problem, self.weights,
            unserved=unserved,
            penalty_coeff=self.config.penalty_coefficient,
        )
        return fitness, routes, unserved

    def _build_result(self, routes, fitness, convergence, iterations, runtime_ms):
        from .constraints import check_all
        if routes is None:
            return OptimizationResult.infeasible(self.ALGORITHM_NAME, "No solution.", runtime_ms)
        cr = check_all(routes, self.problem)
        unserved = getattr(routes[0], "unserved", []) if routes else []
        status = "FEASIBLE" if (cr.feasible and not unserved) else "INFEASIBLE"
        reason = "; ".join(cr.details[:3]) if not cr.feasible else ""
        if unserved:
            reason += f" {len(unserved)} customer(s) unassigned."
        route_lists = routes_to_sequence_list(routes)
        assignments = {r.vehicle_id: [c - 1 for c in r.sequence] for r in routes if not r.is_empty()}
        total_dist = sum(r.total_distance for r in routes)
        total_time = max((r.total_time for r in routes if not r.is_empty()), default=0.0)
        util = vehicle_utilization(routes, self.problem)
        if status == "FEASIBLE":
            return OptimizationResult.feasible_from_routes(
                algorithm=self.ALGORITHM_NAME,
                routes=route_lists, vehicle_assignments=assignments,
                objective_value=fitness, distance_km=total_dist,
                travel_time_min=total_time, vehicle_utilization=util,
                constraint_violations=cr.violation_count + len(unserved),
                iterations=iterations, runtime_ms=runtime_ms,
                convergence=convergence, population_size=getattr(self.config, "population_size", 0),
                random_seed=self.config.random_seed,
                feasible_routes=sum(1 for r in routes if not r.is_empty()),
            )
        return OptimizationResult.infeasible(self.ALGORITHM_NAME, reason, runtime_ms)


# ---------------------------------------------------------------------------
# Dijkstra / Greedy nearest-neighbor baseline
# ---------------------------------------------------------------------------

class DijkstraBaseline(BaseOptimizer):
    """Greedy nearest-neighbor sequential vehicle assignment.

    Used as the simplest baseline.  Not a true Dijkstra (matrices are
    pre-computed so shortest-path is already embedded in the matrix).
    """

    ALGORITHM_NAME = "greedy_nn"

    def solve(self) -> OptimizationResult:
        t_start = time.perf_counter()
        ok, reason = self.problem.is_feasible_instance()
        if not ok:
            return OptimizationResult.infeasible(self.ALGORITHM_NAME, reason)

        # Greedy nearest-neighbor permutation
        unvisited = list(range(1, self.problem.n_customers + 1))
        current = 0
        permutation = []
        while unvisited:
            dists = [self.problem.distance(current, c) for c in unvisited]
            nearest_idx = int(np.argmin(dists))
            next_node = unvisited.pop(nearest_idx)
            permutation.append(next_node - 1)
            current = next_node

        routes = decode_permutation(permutation, self.problem)
        if self.config.use_repair:
            routes, unserved = repair(routes, self.problem)
        else:
            unserved = []
        fitness = calculate_fitness(
            routes, self.problem, self.weights,
            unserved=unserved, penalty_coeff=self.config.penalty_coefficient,
        )
        runtime_ms = (time.perf_counter() - t_start) * 1000
        return self._build_result(routes, fitness, [], 1, runtime_ms)


class AStarBaseline(DijkstraBaseline):
    """A* heuristic baseline — uses time-window urgency as heuristic."""

    ALGORITHM_NAME = "astar"

    def solve(self) -> OptimizationResult:
        t_start = time.perf_counter()
        ok, reason = self.problem.is_feasible_instance()
        if not ok:
            return OptimizationResult.infeasible(self.ALGORITHM_NAME, reason)

        # A*-like: sort by (distance_from_depot + urgency_heuristic)
        def urgency(node: int) -> float:
            cust = self.problem.customers[node - 1]
            dist = self.problem.distance(0, node)
            # Heuristic: earlier deadline = higher urgency
            tw = cust.time_window_close if cust.has_time_window() else float("inf")
            return dist + max(0.0, 1000.0 / (tw + 1.0))

        unvisited = list(range(1, self.problem.n_customers + 1))
        permutation = [n - 1 for n in sorted(unvisited, key=urgency)]

        routes = decode_permutation(permutation, self.problem)
        if self.config.use_repair:
            routes, unserved = repair(routes, self.problem)
        else:
            unserved = []
        fitness = calculate_fitness(
            routes, self.problem, self.weights,
            unserved=unserved, penalty_coeff=self.config.penalty_coefficient,
        )
        runtime_ms = (time.perf_counter() - t_start) * 1000
        return self._build_result(routes, fitness, [], 1, runtime_ms)


# ---------------------------------------------------------------------------
# PSO — Standard Particle Swarm Optimisation
# ---------------------------------------------------------------------------

class PSOOptimizer(BaseOptimizer):
    """Standard PSO with inertia weight and acceleration coefficients.

    Uses the same random-key decode pipeline as QPSO for fair comparison.
    """

    ALGORITHM_NAME = "pso"

    def solve(self) -> OptimizationResult:
        t_start = time.perf_counter()
        ok, reason = self.problem.is_feasible_instance()
        if not ok:
            return OptimizationResult.infeasible(self.ALGORITHM_NAME, reason)

        n = self.problem.n_customers
        N = self.config.population_size
        T = self.config.max_iterations
        w = 0.729        # inertia weight (Clerc-Kennedy constriction)
        c1 = 1.494       # cognitive coefficient
        c2 = 1.494       # social coefficient

        # Initialise positions and velocities
        init = HybridInitializer(self.problem, self._rng)
        particles = init.initialise(N)
        velocities = [self._rng.uniform(-0.5, 0.5, n) for _ in range(N)]

        # Evaluate initial population
        for particle in particles:
            f, routes, unserved = self._evaluate_keys(particle.position)
            particle.fitness = f
            particle.decoded_solution = routes
            particle.update_personal_best()

        gbest_particle = min(particles, key=lambda p: p.best_fitness)
        gbest_pos = gbest_particle.best_position.copy()
        gbest_fitness = gbest_particle.best_fitness
        gbest_solution = gbest_particle.best_solution

        convergence = []
        for t in range(1, T + 1):
            if self.config.time_limit_seconds > 0:
                if (time.perf_counter() - t_start) > self.config.time_limit_seconds:
                    break

            for i, particle in enumerate(particles):
                r1 = self._rng.uniform(0, 1, n)
                r2 = self._rng.uniform(0, 1, n)
                velocities[i] = (
                    w * velocities[i]
                    + c1 * r1 * (particle.best_position - particle.position)
                    + c2 * r2 * (gbest_pos - particle.position)
                )
                particle.position = clip_keys(particle.position + velocities[i])
                f, routes, unserved = self._evaluate_keys(particle.position)
                particle.fitness = f
                particle.decoded_solution = routes
                particle.update_personal_best()
                if particle.best_fitness < gbest_fitness:
                    gbest_fitness = particle.best_fitness
                    gbest_pos = particle.best_position.copy()
                    gbest_solution = particle.best_solution

            mean_fit = float(np.mean([p.fitness for p in particles]))
            positions = np.array([p.position for p in particles])
            div = float(np.linalg.norm(positions - positions.mean(0), axis=1).mean())
            convergence.append(ConvergencePoint(t, gbest_fitness, mean_fit, div, w))

        runtime_ms = (time.perf_counter() - t_start) * 1000
        return self._build_result(gbest_solution, gbest_fitness, convergence, T, runtime_ms)


# ---------------------------------------------------------------------------
# GA — Genetic Algorithm
# ---------------------------------------------------------------------------

class GAOptimizer(BaseOptimizer):
    """Genetic Algorithm for CVRP.

    Representation: permutation of customer ids (0-indexed).
    Operators: Order Crossover (OX), swap mutation.
    Selection: tournament selection.
    Decodes via the same decoder as QPSO for fair comparison.
    """

    ALGORITHM_NAME = "ga"

    def solve(self) -> OptimizationResult:
        t_start = time.perf_counter()
        ok, reason = self.problem.is_feasible_instance()
        if not ok:
            return OptimizationResult.infeasible(self.ALGORITHM_NAME, reason)

        n = self.problem.n_customers
        N = self.config.population_size
        T = self.config.max_iterations
        mutation_rate = 0.2
        tournament_k = max(2, N // 10)

        # Initialise population as permutations
        def eval_perm(perm):
            from .encoding import permutation_to_random_keys
            keys = permutation_to_random_keys(perm, rng=self._rng)
            f, routes, unserved = self._evaluate_keys(keys)
            return f, routes

        pop = [self._rng.permutation(n).tolist() for _ in range(N)]
        fitnesses = []
        best_routes_list = [None] * N
        for i, perm in enumerate(pop):
            f, routes = eval_perm(perm)
            fitnesses.append(f)
            best_routes_list[i] = routes

        gbest_idx = int(np.argmin(fitnesses))
        gbest_fitness = fitnesses[gbest_idx]
        gbest_solution = best_routes_list[gbest_idx]
        gbest_perm = pop[gbest_idx][:]

        convergence = []
        for t in range(1, T + 1):
            if self.config.time_limit_seconds > 0:
                if (time.perf_counter() - t_start) > self.config.time_limit_seconds:
                    break

            new_pop = []
            new_fits = []
            new_routes_list = []

            # Elitism: keep best
            new_pop.append(gbest_perm[:])
            new_fits.append(gbest_fitness)
            new_routes_list.append(gbest_solution)

            while len(new_pop) < N:
                # Tournament selection
                p1 = self._tournament(pop, fitnesses, tournament_k)
                p2 = self._tournament(pop, fitnesses, tournament_k)
                # Order crossover
                child = self._ox_crossover(p1, p2)
                # Mutation
                if self._rng.random() < mutation_rate:
                    child = self._swap_mutate(child)
                f, routes = eval_perm(child)
                new_pop.append(child)
                new_fits.append(f)
                new_routes_list.append(routes)
                if f < gbest_fitness:
                    gbest_fitness = f
                    gbest_solution = routes
                    gbest_perm = child[:]

            pop = new_pop
            fitnesses = new_fits
            best_routes_list = new_routes_list

            mean_fit = float(np.mean(fitnesses))
            convergence.append(ConvergencePoint(t, gbest_fitness, mean_fit, 0.0, 0.0))

        runtime_ms = (time.perf_counter() - t_start) * 1000
        return self._build_result(gbest_solution, gbest_fitness, convergence, T, runtime_ms)

    def _tournament(self, pop, fitnesses, k):
        idxs = self._rng.choice(len(pop), size=k, replace=False)
        best = idxs[int(np.argmin([fitnesses[i] for i in idxs]))]
        return pop[best][:]

    def _ox_crossover(self, p1: list, p2: list) -> list:
        """Order crossover (OX)."""
        n = len(p1)
        a, b = sorted(self._rng.choice(n, 2, replace=False))
        child = [-1] * n
        child[a:b] = p1[a:b]
        fill = [x for x in p2 if x not in child[a:b]]
        j = 0
        for i in list(range(b, n)) + list(range(0, a)):
            child[i] = fill[j]
            j += 1
        return child

    def _swap_mutate(self, perm: list) -> list:
        """Random swap of two positions."""
        i, j = self._rng.choice(len(perm), 2, replace=False)
        perm = perm[:]
        perm[i], perm[j] = perm[j], perm[i]
        return perm


# ---------------------------------------------------------------------------
# ACO — Ant Colony Optimisation
# ---------------------------------------------------------------------------

class ACOOptimizer(BaseOptimizer):
    """Ant Colony Optimisation for CVRP.

    Pheromone update: min-max ant system (MMAS-lite).
    Heuristic: 1 / distance.
    Decodes via the same constraint-aware decoder as QPSO.
    """

    ALGORITHM_NAME = "aco"

    def solve(self) -> OptimizationResult:
        t_start = time.perf_counter()
        ok, reason = self.problem.is_feasible_instance()
        if not ok:
            return OptimizationResult.infeasible(self.ALGORITHM_NAME, reason)

        n = self.problem.n_customers
        N_ants = self.config.population_size
        T = self.config.max_iterations
        alpha_aco = 1.0    # pheromone importance
        beta_aco = 2.0     # heuristic importance
        rho = 0.1          # evaporation rate
        tau_min = 0.01
        tau_max = 10.0

        # Pheromone matrix (n+1 × n+1 for customer nodes, index 0 = depot)
        tau = np.full((n + 1, n + 1), (tau_min + tau_max) / 2.0)
        # Heuristic matrix: eta[i,j] = 1/dist (avoid division by zero)
        dist_mat = self.problem.distance_matrix.copy()
        dist_mat[dist_mat == 0] = 1e-10
        eta = 1.0 / dist_mat

        gbest_fitness = float("inf")
        gbest_solution = None
        convergence = []

        for t in range(1, T + 1):
            if self.config.time_limit_seconds > 0:
                if (time.perf_counter() - t_start) > self.config.time_limit_seconds:
                    break

            iter_best_fitness = float("inf")
            iter_best_routes = None

            for _ in range(N_ants):
                # Construct a solution for this ant
                permutation = self._construct_ant_tour(tau, eta, alpha_aco, beta_aco, n)
                from .encoding import permutation_to_random_keys
                keys = permutation_to_random_keys(permutation, rng=self._rng)
                f, routes, unserved = self._evaluate_keys(keys)
                if f < iter_best_fitness:
                    iter_best_fitness = f
                    iter_best_routes = routes
                if f < gbest_fitness:
                    gbest_fitness = f
                    gbest_solution = routes

            # Pheromone evaporation
            tau *= (1.0 - rho)

            # Pheromone deposit (iteration best)
            if iter_best_routes:
                deposit = 1.0 / (iter_best_fitness + 1e-10)
                for route in iter_best_routes:
                    seq = [0] + route.sequence + [0]
                    for a, b in zip(seq, seq[1:]):
                        tau[a, b] = min(tau_max, tau[a, b] + deposit)
                        tau[b, a] = min(tau_max, tau[b, a] + deposit)

            tau = np.clip(tau, tau_min, tau_max)

            mean_fit = iter_best_fitness  # approximate
            convergence.append(ConvergencePoint(t, gbest_fitness, mean_fit, 0.0, 0.0))

        runtime_ms = (time.perf_counter() - t_start) * 1000
        return self._build_result(gbest_solution, gbest_fitness, convergence, T, runtime_ms)

    def _construct_ant_tour(self, tau, eta, alpha, beta, n) -> list[int]:
        """Construct a probabilistic customer permutation for one ant."""
        unvisited = list(range(1, n + 1))  # matrix indices
        current = 0
        permutation = []
        while unvisited:
            probs = np.array([
                (tau[current, j] ** alpha) * (eta[current, j] ** beta)
                for j in unvisited
            ])
            probs_sum = probs.sum()
            if probs_sum < 1e-10:
                probs = np.ones(len(unvisited))
            probs /= probs.sum()
            next_idx = int(self._rng.choice(len(unvisited), p=probs))
            next_node = unvisited.pop(next_idx)
            permutation.append(next_node - 1)  # 0-indexed customer id
            current = next_node
        return permutation
