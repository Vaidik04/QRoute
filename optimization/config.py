"""
optimization/config.py
======================
Configuration dataclasses for the Adaptive D-QPSO optimizer.

Separate from problem data — these are algorithm hyper-parameters
and objective weights that callers send at request time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ObjectiveWeights:
    """Multi-objective weight profile.

    All weights should sum to 1.0 (enforced at validation).
    Frontend sends one of the named profiles; you can also pass custom floats.

    Named profiles
    --------------
    fastest   : {"time": 0.60, "distance": 0.15, "congestion": 0.20, "risk": 0.05}
    balanced  : {"time": 0.35, "distance": 0.35, "congestion": 0.20, "risk": 0.10}
    green     : {"time": 0.20, "distance": 0.55, "congestion": 0.15, "risk": 0.10}
    reliable  : {"time": 0.30, "distance": 0.20, "congestion": 0.15, "risk": 0.35}
    emergency : {"time": 0.70, "distance": 0.10, "congestion": 0.10, "risk": 0.10}
    """
    time: float = 0.35
    distance: float = 0.35
    congestion: float = 0.20
    risk: float = 0.10
    stability: float = 0.0   # Route-change penalty weight (active during re-opt)

    # Pre-built named profiles
    _PROFILES: dict = field(default=None, init=False, repr=False, compare=False)

    @classmethod
    def fastest(cls) -> "ObjectiveWeights":
        return cls(time=0.60, distance=0.15, congestion=0.20, risk=0.05)

    @classmethod
    def balanced(cls) -> "ObjectiveWeights":
        return cls(time=0.35, distance=0.35, congestion=0.20, risk=0.10)

    @classmethod
    def green(cls) -> "ObjectiveWeights":
        return cls(time=0.20, distance=0.55, congestion=0.15, risk=0.10)

    @classmethod
    def reliable(cls) -> "ObjectiveWeights":
        return cls(time=0.30, distance=0.20, congestion=0.15, risk=0.35)

    @classmethod
    def emergency(cls) -> "ObjectiveWeights":
        return cls(time=0.70, distance=0.10, congestion=0.10, risk=0.10)

    @classmethod
    def from_dict(cls, d: dict) -> "ObjectiveWeights":
        return cls(
            time=d.get("time", 0.35),
            distance=d.get("distance", 0.35),
            congestion=d.get("congestion", 0.20),
            risk=d.get("risk", 0.10),
            stability=d.get("stability", 0.0),
        )

    @classmethod
    def from_profile(cls, profile: str) -> "ObjectiveWeights":
        profiles = {
            "fastest": cls.fastest,
            "balanced": cls.balanced,
            "green": cls.green,
            "reliable": cls.reliable,
            "emergency": cls.emergency,
        }
        if profile not in profiles:
            raise ValueError(f"Unknown weight profile '{profile}'. Choose from {list(profiles)}.")
        return profiles[profile]()

    def validate(self) -> None:
        total = self.time + self.distance + self.congestion + self.risk
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"ObjectiveWeights (excluding stability) must sum to 1.0, got {total:.4f}."
            )
        for name, val in [("time", self.time), ("distance", self.distance),
                           ("congestion", self.congestion), ("risk", self.risk),
                           ("stability", self.stability)]:
            if val < 0:
                raise ValueError(f"Weight '{name}' cannot be negative.")

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "distance": self.distance,
            "congestion": self.congestion,
            "risk": self.risk,
            "stability": self.stability,
        }


@dataclass
class OptimizationConfig:
    """All algorithm hyper-parameters for the Adaptive D-QPSO engine.

    These values should be chosen from parameter-sensitivity experiments
    (benchmarks/reports.py) — never by guessing.

    Attributes
    ----------
    population_size : int           Number of particles (default: 50).
    max_iterations : int            Maximum QPSO iterations (default: 100).
    alpha_max : float               Maximum contraction-expansion coeff.
    alpha_min : float               Minimum contraction-expansion coeff.
    local_search_freq : int         Apply local search every N iterations.
    local_search_elite_k : int      Apply local search to top-K particles.
    stagnation_window : int         Iterations without improvement = stagnated.
    stagnation_limit : int          Stagnation episodes before diversification.
    diversity_threshold : float     Diversity below this triggers diversification.
    mutation_rate : float           Fraction of particles restarted on stagnation.
    random_seed : Optional[int]     Seed for reproducibility. None = random.
    time_limit_seconds : float      Wall-clock limit (0 = no limit).
    use_repair : bool               Apply repair operator on infeasible solutions.
    use_local_search : bool         Apply local search on elites.
    use_adaptive_alpha : bool       Enable adaptive alpha (vs. fixed).
    penalty_coefficient : float     Large-M factor for hard-constraint violations.
    verbose : bool                  Print progress to stdout.
    """
    population_size: int = 50
    max_iterations: int = 100
    alpha_max: float = 1.0
    alpha_min: float = 0.5
    local_search_freq: int = 10
    local_search_elite_k: int = 3
    stagnation_window: int = 15
    stagnation_limit: int = 3
    diversity_threshold: float = 0.05
    mutation_rate: float = 0.20
    random_seed: Optional[int] = 42
    time_limit_seconds: float = 0.0
    use_repair: bool = True
    use_local_search: bool = True
    use_adaptive_alpha: bool = True
    penalty_coefficient: float = 1e6
    verbose: bool = False

    def validate(self) -> None:
        if self.population_size < 2:
            raise ValueError("population_size must be >= 2.")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1.")
        if not (0 < self.alpha_min <= self.alpha_max):
            raise ValueError("Need 0 < alpha_min <= alpha_max.")
        if not (0.0 < self.mutation_rate <= 1.0):
            raise ValueError("mutation_rate must be in (0, 1].")

    def to_dict(self) -> dict:
        return {
            "population_size": self.population_size,
            "max_iterations": self.max_iterations,
            "alpha_max": self.alpha_max,
            "alpha_min": self.alpha_min,
            "local_search_freq": self.local_search_freq,
            "stagnation_window": self.stagnation_window,
            "random_seed": self.random_seed,
            "use_repair": self.use_repair,
            "use_local_search": self.use_local_search,
            "use_adaptive_alpha": self.use_adaptive_alpha,
        }
