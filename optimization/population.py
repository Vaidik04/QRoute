"""
optimization/population.py
==========================
Hybrid particle population initialisation for QPSO.

Section 11 of the build spec:
    "30% random, 20% nearest-neighbor, 20% greedy, 20% heuristic,
     10% seeded/reference — then convert to QPSO particle representations."

All generation uses a controlled numpy RNG (seed-reproducible).
The ablation study (benchmarks/reports.py) will compare hybrid vs.
pure-random initialisation to validate whether this actually helps.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import numpy as np

from .encoding import permutation_to_random_keys, random_keys_to_permutation
from .entities import Route

if TYPE_CHECKING:
    from .problem import VRPProblem


# ---------------------------------------------------------------------------
# Particle
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class Particle:
    """A QPSO particle.

    Stores both the continuous position (random-key vector) and the decoded
    discrete solution + fitness, for both current and personal-best state.

    Attributes
    ----------
    position : np.ndarray           Current random-key vector [0,1]^n.
    decoded_solution : list[Route]  Routes decoded from current position.
    fitness : float                 Current composite fitness.
    best_position : np.ndarray      Personal-best position.
    best_solution : list[Route]     Routes decoded from personal-best.
    best_fitness : float            Personal-best fitness.
    """
    position: np.ndarray
    decoded_solution: list[Route] = field(default_factory=list)
    fitness: float = float("inf")
    best_position: np.ndarray = field(default=None)  # type: ignore
    best_solution: list[Route] = field(default_factory=list)
    best_fitness: float = float("inf")

    def __post_init__(self) -> None:
        if self.best_position is None:
            self.best_position = self.position.copy()

    def update_personal_best(self) -> bool:
        """Update personal best if current fitness is better. Returns True if updated."""
        if self.fitness < self.best_fitness:
            self.best_fitness = self.fitness
            self.best_position = self.position.copy()
            self.best_solution = self.decoded_solution
            return True
        return False

    def clone(self) -> "Particle":
        return Particle(
            position=self.position.copy(),
            decoded_solution=list(self.decoded_solution),
            fitness=self.fitness,
            best_position=self.best_position.copy(),
            best_solution=list(self.best_solution),
            best_fitness=self.best_fitness,
        )


# ---------------------------------------------------------------------------
# Individual initialisation strategies
# ---------------------------------------------------------------------------

def _random_keys(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(0.0, 1.0, size=n)


def _nearest_neighbor_permutation(problem: "VRPProblem", rng: np.random.Generator) -> list[int]:
    """Nearest-neighbor heuristic: greedy closest-unvisited from depot."""
    unvisited = list(range(1, problem.n_customers + 1))  # matrix indices
    current = 0  # depot
    permutation = []
    while unvisited:
        # Find nearest unvisited (add small random jitter for diversity)
        dists = [
            problem.distance(current, c) + rng.uniform(0, 0.01)
            for c in unvisited
        ]
        nearest_idx = int(np.argmin(dists))
        next_node = unvisited.pop(nearest_idx)
        permutation.append(next_node - 1)  # convert to 0-indexed customer id
        current = next_node
    return permutation


def _greedy_demand_permutation(problem: "VRPProblem", rng: np.random.Generator) -> list[int]:
    """Sort customers by demand descending — large deliveries first."""
    customers = sorted(
        range(problem.n_customers),
        key=lambda i: problem.customers[i].demand,
        reverse=True,
    )
    # Add small random perturbation
    noise = rng.uniform(0, 0.1, size=len(customers))
    demands = [problem.customers[i].demand + noise[j] for j, i in enumerate(customers)]
    return [x for _, x in sorted(zip(demands, customers), reverse=True)]


def _priority_time_window_permutation(problem: "VRPProblem", rng: np.random.Generator) -> list[int]:
    """Heuristic: sort by priority DESC, then time_window_close ASC (urgency)."""
    customers = list(range(problem.n_customers))

    def sort_key(i):
        c = problem.customers[i]
        tw_close = c.time_window_close if c.has_time_window() else float("inf")
        return (-c.priority, tw_close + rng.uniform(0, 0.1))

    return sorted(customers, key=sort_key)


def _savings_permutation(problem: "VRPProblem", rng: np.random.Generator) -> list[int]:
    """Clarke-Wright savings heuristic ordering.

    Savings(i, j) = d(0,i) + d(0,j) - d(i,j)
    Higher savings = merge these customers on the same route first.
    Returns a permutation that roughly follows high-savings pairs.
    """
    n = problem.n_customers
    # Compute savings for all pairs
    savings = []
    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            s = (
                problem.distance(0, i)
                + problem.distance(0, j)
                - problem.distance(i, j)
            )
            savings.append((s + rng.uniform(0, 0.01), i, j))
    savings.sort(reverse=True)

    seen = set()
    result = []
    for _, i, j in savings:
        for node in [i, j]:
            if node not in seen:
                seen.add(node)
                result.append(node - 1)  # 0-indexed customer id
    # Append any missed
    for i in range(n):
        if i not in seen - {x + 1 for x in range(n)}:
            pass
    remaining = [i for i in range(n) if i not in result]
    result.extend(remaining)
    return result[:n]


# ---------------------------------------------------------------------------
# Hybrid initialiser
# ---------------------------------------------------------------------------

class HybridInitializer:
    """Creates a diverse initial particle population.

    Fractions (approximate):
        30%  random keys
        20%  nearest-neighbour heuristic
        20%  greedy (demand descending)
        20%  priority + time-window urgency
        10%  Clarke-Wright savings
    """

    def __init__(self, problem: "VRPProblem", rng: np.random.Generator) -> None:
        self.problem = problem
        self.rng = rng
        self.n = problem.n_customers

    def _perm_to_keys(self, permutation: list[int]) -> np.ndarray:
        return permutation_to_random_keys(permutation, rng=self.rng)

    def initialise(self, population_size: int) -> list[Particle]:
        """Generate ``population_size`` particles with hybrid initialisation."""
        n_random = max(1, int(population_size * 0.30))
        n_nn = max(1, int(population_size * 0.20))
        n_greedy = max(1, int(population_size * 0.20))
        n_priority = max(1, int(population_size * 0.20))
        n_savings = population_size - n_random - n_nn - n_greedy - n_priority

        particles = []

        # --- Random ---
        for _ in range(n_random):
            keys = _random_keys(self.n, self.rng)
            particles.append(Particle(position=keys))

        # --- Nearest-neighbour ---
        for _ in range(n_nn):
            perm = _nearest_neighbor_permutation(self.problem, self.rng)
            keys = self._perm_to_keys(perm)
            particles.append(Particle(position=keys))

        # --- Greedy demand ---
        for _ in range(n_greedy):
            perm = _greedy_demand_permutation(self.problem, self.rng)
            keys = self._perm_to_keys(perm)
            particles.append(Particle(position=keys))

        # --- Priority + TW ---
        for _ in range(n_priority):
            perm = _priority_time_window_permutation(self.problem, self.rng)
            keys = self._perm_to_keys(perm)
            particles.append(Particle(position=keys))

        # --- Savings ---
        for _ in range(max(0, n_savings)):
            perm = _savings_permutation(self.problem, self.rng)
            keys = self._perm_to_keys(perm)
            particles.append(Particle(position=keys))

        return particles

    def random_particle(self) -> Particle:
        """Generate a single random particle (used for diversification)."""
        keys = _random_keys(self.n, self.rng)
        return Particle(position=keys)

    def perturb_particle(self, particle: Particle, strength: float = 0.3) -> Particle:
        """Create a perturbed copy of a particle (for mutation/diversification).

        strength: fraction of dimensions randomised.
        """
        new_keys = particle.position.copy()
        n_perturb = max(1, int(strength * self.n))
        dims = self.rng.choice(self.n, size=n_perturb, replace=False)
        new_keys[dims] = self.rng.uniform(0.0, 1.0, size=n_perturb)
        return Particle(position=new_keys)
