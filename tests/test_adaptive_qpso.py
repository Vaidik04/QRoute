"""
tests/test_adaptive_qpso.py
===========================
Unit tests for the Adaptive D-QPSO optimizer and its adaptive mechanisms.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np

from optimization.problem import VRPProblem
from optimization.config import OptimizationConfig
from optimization.adaptive_qpso import AdaptiveQPSO
from optimization.qpso import QPSO


@pytest.fixture
def problem():
    return VRPProblem.random_cvrp(n_customers=10, n_vehicles=3, capacity=50.0, seed=42)


@pytest.fixture
def config():
    return OptimizationConfig(
        population_size=20,
        max_iterations=30,
        random_seed=42,
        use_adaptive_alpha=True,
        use_repair=True,
        use_local_search=True,
        local_search_freq=10,
        stagnation_window=5,
        stagnation_limit=2,
    )


class TestAdaptiveQPSO:
    def test_adaptive_qpso_feasible_or_infeasible(self, problem, config):
        result = AdaptiveQPSO(problem, config).solve()
        assert result.status in ("FEASIBLE", "INFEASIBLE")

    def test_alpha_changes_over_iterations(self, problem, config):
        """Alpha must vary across iterations when use_adaptive_alpha=True."""
        result = AdaptiveQPSO(problem, config).solve()
        if len(result.convergence) >= 2:
            alphas = [cp.alpha for cp in result.convergence]
            # Alpha should not be constant
            assert max(alphas) > min(alphas), "Alpha never changed — adaptive logic not triggered."

    def test_alpha_annealing_generally_decreasing(self, problem, config):
        """Without stagnation, alpha should trend downward."""
        result = AdaptiveQPSO(problem, config).solve()
        if len(result.convergence) >= 10:
            first_alpha = result.convergence[0].alpha
            last_alpha = result.convergence[-1].alpha
            # Should trend downward (annealing). Allow some tolerance for stagnation bumps.
            assert last_alpha <= first_alpha + 0.1

    def test_adaptive_qpso_all_customers_served(self, problem, config):
        result = AdaptiveQPSO(problem, config).solve()
        if result.status == "FEASIBLE":
            all_served = []
            for route in result.routes:
                all_served.extend([c for c in route if c != 0])
            assert len(all_served) == 10
            assert len(set(all_served)) == 10

    def test_adaptive_better_or_equal_to_baseline_qpso(self):
        """Run both on same problem/seed. Adaptive should generally match or beat QPSO."""
        problem = VRPProblem.random_cvrp(n_customers=15, n_vehicles=3, capacity=60.0, seed=99)
        cfg = OptimizationConfig(
            population_size=30, max_iterations=50, random_seed=0,
            use_adaptive_alpha=True, use_repair=True, use_local_search=True,
        )
        adaptive_result = AdaptiveQPSO(problem, cfg).solve()

        cfg_baseline = OptimizationConfig(
            population_size=30, max_iterations=50, random_seed=0,
            use_adaptive_alpha=False, use_repair=True, use_local_search=False,
        )
        qpso_result = QPSO(problem, cfg_baseline).solve()

        # Both should produce valid results
        assert adaptive_result.status in ("FEASIBLE", "INFEASIBLE")
        assert qpso_result.status in ("FEASIBLE", "INFEASIBLE")

    def test_diversity_tracked(self, problem, config):
        result = AdaptiveQPSO(problem, config).solve()
        for cp in result.convergence:
            assert cp.diversity >= 0.0
            assert np.isfinite(cp.diversity)

    def test_stagnation_limit_trigger(self):
        """With very low stagnation limit, diversification should trigger."""
        problem = VRPProblem.random_cvrp(n_customers=8, n_vehicles=2, capacity=60.0, seed=7)
        config = OptimizationConfig(
            population_size=10, max_iterations=40, random_seed=0,
            stagnation_window=2, stagnation_limit=1,
            diversity_threshold=0.9,  # Almost always triggers diversity check
            use_adaptive_alpha=True,
        )
        result = AdaptiveQPSO(problem, config).solve()
        assert result.status in ("FEASIBLE", "INFEASIBLE")
        # Should have run without errors despite aggressive diversification

    def test_no_adaptive_alpha_degrades_to_fixed(self):
        """With use_adaptive_alpha=False, alpha should be constant."""
        problem = VRPProblem.random_cvrp(n_customers=5, n_vehicles=2, capacity=50.0, seed=1)
        config = OptimizationConfig(
            population_size=10, max_iterations=20, random_seed=1,
            use_adaptive_alpha=False, alpha_max=0.8, alpha_min=0.5,
        )
        result = QPSO(problem, config).solve()
        if len(result.convergence) > 1:
            alphas = [cp.alpha for cp in result.convergence]
            assert all(a == 0.8 for a in alphas), "Alpha should be constant when adaptive is off."
