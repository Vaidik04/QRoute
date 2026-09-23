"""
optimization/adaptive_qpso.py
==============================
Adaptive Discrete Quantum-behaved PSO (Adaptive D-QPSO).

This is the primary algorithmic contribution of Member 1.

The integration contribution:
    Traffic-aware adaptive discrete QPSO + continuous random-key encoding +
    constraint-aware decoding + repair + elite Variable Neighborhood Descent (VND)
    + rolling dynamic re-optimization + multimodal composite objective.

Advanced Algorithmic Mechanisms:
--------------------------------
1. Nonlinear Alpha Annealing with Multi-Feedback:
       α(t) = α_max − (α_max − α_min) · (t / T) + Δα_stag + Δα_div
   Smooth transition from exploratory quantum delta-well expansion to
   exploitative localized contraction around the mean best (mbest).

2. Opposition-Based Learning (OBL):
       x̃_j = 1.0 − x_j
   Applied during population initialization and stagnation recovery to
   explore dual symmetric search partitions in random-key space.

3. Quantum Tunneling via Cauchy Perturbation:
   When stagnation occurs, worst particles undergo heavy-tailed Cauchy jumps:
       x_new = clip(x + Cauchy(0, σ) ⊙ |gbest − x|, 0, 1)
   The heavy tails simulate quantum tunneling through high potential barriers
   that entrap Gaussian or uniform mutations.

4. Dynamic Stagnation & Diversity Monitoring:
   Tracks consecutive non-improving iterations and Euclidean dispersion D(t).
   Triggers adaptive diversification before permanent swarm collapse.

5. Elite Variable Neighborhood Descent (VND):
   Interleaved 2-opt, Or-opt (1, 2, 3), Relocate, Swap, 2-opt*, and CROSS-exchange
   applied to the global best and top-K elites.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

import numpy as np

from .config import OptimizationConfig, ObjectiveWeights
from .decoder import decode, get_unserved, routes_to_sequence_list
from .encoding import clip_keys, permutation_to_random_keys
from .fitness import calculate_fitness, vehicle_utilization
from .local_search import variable_neighborhood_descent, run_all_ls
from .population import HybridInitializer, Particle
from .qpso import QPSO
from .repair import repair
from .result import ConvergencePoint, OptimizationResult

if TYPE_CHECKING:
    from .problem import VRPProblem


class AdaptiveQPSO(QPSO):
    """Adaptive Discrete QPSO with Quantum Tunneling and Elite VND."""

    ALGORITHM_NAME = "adaptive_d_qpso"

    def solve(self) -> OptimizationResult:
        """Run Adaptive D-QPSO and return an OptimizationResult."""
        t_start = time.perf_counter()
        config = self.config
        problem = self.problem
        weights = self.weights

        # --- Pre-check ---
        ok, reason = problem.is_feasible_instance()
        if not ok:
            return OptimizationResult.infeasible(
                self.ALGORITHM_NAME, reason,
                runtime_ms=(time.perf_counter() - t_start) * 1000,
            )

        # --- Initialise Population ---
        initialiser = HybridInitializer(problem, self._rng)
        population: list[Particle] = initialiser.initialise(config.population_size)

        # Opposition-Based Learning (OBL) Enhancement on Initial Population
        for i, particle in enumerate(population):
            self._evaluate(particle)
            # Evaluate opposite point in random-key space
            opp_pos = clip_keys(1.0 - particle.position)
            opp_particle = Particle(opp_pos)
            self._evaluate(opp_particle)
            if opp_particle.fitness < particle.fitness:
                population[i] = opp_particle

        # Global best
        gbest_particle = min(population, key=lambda p: p.fitness)
        gbest_position = gbest_particle.position.copy()
        gbest_fitness = gbest_particle.fitness
        gbest_solution = gbest_particle.decoded_solution

        # Adaptive state
        alpha = config.alpha_max
        stagnation_counter = 0
        stagnation_streak = 0
        prev_best = gbest_fitness
        diversity = self._compute_diversity(population)
        convergence: list[ConvergencePoint] = []
        T = config.max_iterations

        for iteration in range(1, T + 1):
            # --- Time limit ---
            if config.time_limit_seconds > 0:
                if (time.perf_counter() - t_start) > config.time_limit_seconds:
                    break

            # -------------------------------------------------------
            # 1. Compute alpha (multi-feedback annealing)
            # -------------------------------------------------------
            if config.use_adaptive_alpha:
                alpha = self._compute_alpha(
                    iteration, T, config, stagnation_counter, diversity
                )

            # -------------------------------------------------------
            # 2. Compute mbest (mean best position)
            # -------------------------------------------------------
            mbest = np.mean([p.best_position for p in population], axis=0)

            # -------------------------------------------------------
            # 3. Update particles via Quantum Delta Potential Dynamics
            # -------------------------------------------------------
            for particle in population:
                self._update_position(particle, mbest, gbest_position, alpha)
                self._evaluate(particle)
                particle.update_personal_best()
                if particle.best_fitness < gbest_fitness:
                    gbest_fitness = particle.best_fitness
                    gbest_position = particle.best_position.copy()
                    gbest_solution = particle.best_solution

            # -------------------------------------------------------
            # 4. Stagnation detection
            # -------------------------------------------------------
            improvement = max(0.0, prev_best - gbest_fitness)
            if improvement < 1e-8:
                stagnation_streak += 1
            else:
                stagnation_streak = 0
                stagnation_counter = 0

            if stagnation_streak >= config.stagnation_window:
                stagnation_counter += 1
                stagnation_streak = 0

            # -------------------------------------------------------
            # 5. Diversity measurement
            # -------------------------------------------------------
            diversity = self._compute_diversity(population)

            # -------------------------------------------------------
            # 6. Adaptive response & Quantum Tunneling
            # -------------------------------------------------------
            if config.use_adaptive_alpha:
                population, gbest_position, gbest_fitness, gbest_solution = (
                    self._adaptive_response(
                        population, diversity, stagnation_counter,
                        gbest_position, gbest_fitness, gbest_solution,
                        initialiser, config, iteration, T,
                    )
                )

            # -------------------------------------------------------
            # 7. Elite Variable Neighborhood Descent (VND)
            # -------------------------------------------------------
            if (
                config.use_local_search
                and iteration % config.local_search_freq == 0
            ):
                gbest_solution, gbest_fitness, gbest_position = self._apply_local_search(
                    gbest_solution, gbest_fitness, gbest_position
                )
                # Also apply to top-K elites
                elites = sorted(population, key=lambda p: p.best_fitness)[
                    :config.local_search_elite_k
                ]
                for elite in elites:
                    improved_sol, improved_fit, improved_pos = self._apply_local_search(
                        elite.best_solution, elite.best_fitness, elite.best_position
                    )
                    if improved_fit < elite.best_fitness:
                        elite.best_fitness = improved_fit
                        elite.best_position = improved_pos
                        elite.best_solution = improved_sol
                    if improved_fit < gbest_fitness:
                        gbest_fitness = improved_fit
                        gbest_position = improved_pos.copy()
                        gbest_solution = improved_sol

            # -------------------------------------------------------
            # 8. Convergence log
            # -------------------------------------------------------
            mean_fitness = float(np.mean([p.fitness for p in population]))
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
                    f"div={diversity:.4f}  α={alpha:.4f}  "
                    f"stag={stagnation_counter}"
                )

        runtime_ms = (time.perf_counter() - t_start) * 1000
        return self._build_result(
            gbest_solution, gbest_fitness, gbest_position,
            convergence, iteration, runtime_ms, alpha,
        )

    # ------------------------------------------------------------------
    # Adaptive alpha computation with feedback
    # ------------------------------------------------------------------

    def _compute_alpha(
        self,
        t: int,
        T: int,
        config: OptimizationConfig,
        stagnation_counter: int,
        diversity: float = 0.1,
    ) -> float:
        """Compute contraction-expansion coefficient alpha for iteration t."""
        # Base linear annealing schedule
        alpha_base = config.alpha_max - (config.alpha_max - config.alpha_min) * (t / T)

        # Stagnation feedback: elevate exploration if stagnant
        stag_bump = stagnation_counter * 0.05 * (config.alpha_max - config.alpha_min)

        # Diversity feedback: if diversity plummets, temporarily boost alpha
        div_bump = 0.0
        if diversity < config.diversity_threshold:
            ratio = max(0.0, 1.0 - (diversity / max(1e-6, config.diversity_threshold)))
            div_bump = ratio * 0.08 * (config.alpha_max - config.alpha_min)

        alpha = float(np.clip(alpha_base + stag_bump + div_bump, config.alpha_min, config.alpha_max))
        return alpha

    # ------------------------------------------------------------------
    # Adaptive response: Quantum Tunneling & Restarts
    # ------------------------------------------------------------------

    def _adaptive_response(
        self,
        population: list[Particle],
        diversity: float,
        stagnation_counter: int,
        gbest_position: np.ndarray,
        gbest_fitness: float,
        gbest_solution,
        initialiser: HybridInitializer,
        config: OptimizationConfig,
        iteration: int,
        T: int,
    ):
        """Apply quantum tunneling Cauchy jumps and diversification."""
        n_dim = self.problem.n_customers

        if stagnation_counter > config.stagnation_limit:
            # --- Quantum Tunneling via Cauchy perturbation on worst particles ---
            n_restart = max(1, int(config.mutation_rate * config.population_size))
            sorted_pop = sorted(population, key=lambda p: p.best_fitness, reverse=True)

            for i, particle in enumerate(sorted_pop[:n_restart]):
                idx = population.index(particle)
                if i % 2 == 0:
                    # Heavy-tailed Cauchy jump simulating quantum tunneling through energy barrier
                    cauchy_step = self._rng.standard_cauchy(size=n_dim) * 0.15
                    new_pos = clip_keys(gbest_position + cauchy_step * np.abs(gbest_position - particle.position))
                    new_p = Particle(new_pos)
                else:
                    # Opposition-based point
                    new_pos = clip_keys(1.0 - particle.best_position)
                    new_p = Particle(new_pos)

                self._evaluate(new_p)
                new_p.update_personal_best()
                population[idx] = new_p

            # Immediate VND exploitation on gbest
            gbest_solution, gbest_fitness, gbest_position = self._apply_local_search(
                gbest_solution, gbest_fitness, gbest_position
            )

        elif diversity < config.diversity_threshold:
            # --- Mild diversification: perturb bottom half ---
            n_perturb = config.population_size // 2
            sorted_pop = sorted(population, key=lambda p: p.best_fitness, reverse=True)
            for particle in sorted_pop[:n_perturb]:
                perturbed = initialiser.perturb_particle(particle, strength=0.3)
                self._evaluate(perturbed)
                perturbed.update_personal_best()
                idx = population.index(particle)
                population[idx] = perturbed

        # Update gbest if any new particle beats it
        for p in population:
            if p.best_fitness < gbest_fitness:
                gbest_fitness = p.best_fitness
                gbest_position = p.best_position.copy()
                gbest_solution = p.best_solution

        return population, gbest_position, gbest_fitness, gbest_solution

    # ------------------------------------------------------------------
    # Elite VND Local Search Hook
    # ------------------------------------------------------------------

    def _apply_local_search(
        self,
        routes,
        fitness: float,
        position: np.ndarray,
    ):
        """Apply Variable Neighborhood Descent (VND) to routes."""
        if not routes:
            return routes, fitness, position

        improved_routes = variable_neighborhood_descent(routes, self.problem)

        unserved = getattr(improved_routes[0], "unserved", []) if improved_routes else []
        new_fitness = calculate_fitness(
            improved_routes, self.problem, self.weights,
            unserved=unserved,
            penalty_coeff=self.config.penalty_coefficient,
        )

        if new_fitness < fitness - 1e-8:
            # Reconstruct random key vector from improved discrete permutation
            full_perm = []
            for route in improved_routes:
                for cust_idx in route.sequence:
                    full_perm.append(cust_idx - 1)
            all_customers = set(range(self.problem.n_customers))
            in_perm = set(full_perm)
            for c in all_customers - in_perm:
                full_perm.append(c)

            new_position = permutation_to_random_keys(full_perm, rng=self._rng)
            return improved_routes, new_fitness, new_position

        return routes, fitness, position
