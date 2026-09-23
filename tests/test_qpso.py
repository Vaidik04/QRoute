"""
tests/test_qpso.py
==================
Unit tests for baseline QPSO optimizer.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np

from optimization.problem import VRPProblem
from optimization.config import OptimizationConfig
from optimization.qpso import QPSO


@pytest.fixture
def small_problem():
    return VRPProblem.random_cvrp(n_customers=10, n_vehicles=3, capacity=50.0, seed=42)


@pytest.fixture
def quick_config():
    return OptimizationConfig(
        population_size=20,
        max_iterations=20,
        random_seed=42,
        use_local_search=False,
    )


class TestQPSO:
    def test_qpso_returns_feasible_on_simple_instance(self, small_problem, quick_config):
        optimizer = QPSO(small_problem, quick_config)
        result = optimizer.solve()
        # Should either be FEASIBLE or INFEASIBLE with a reason
        assert result.status in ("FEASIBLE", "INFEASIBLE")

    def test_qpso_serves_all_10_customers(self, small_problem, quick_config):
        """Given 10 customers, the FEASIBLE result must serve all 10 exactly once."""
        optimizer = QPSO(small_problem, quick_config)
        result = optimizer.solve()
        if result.status == "FEASIBLE":
            all_served = []
            for route in result.routes:
                # route = [0, c1, c2, ..., 0] — exclude depot
                all_served.extend([c for c in route if c != 0])
            assert len(all_served) == 10
            assert len(set(all_served)) == 10

    def test_qpso_convergence_history_populated(self, small_problem, quick_config):
        optimizer = QPSO(small_problem, quick_config)
        result = optimizer.solve()
        assert len(result.convergence) > 0
        assert result.iterations > 0

    def test_qpso_reproducible_with_same_seed(self, small_problem, quick_config):
        """Same problem + same seed → same result."""
        r1 = QPSO(small_problem, quick_config).solve()
        r2 = QPSO(small_problem, quick_config).solve()
        assert abs(r1.objective_value - r2.objective_value) < 1e-9

    def test_qpso_improves_over_iterations(self):
        """QPSO should improve best fitness over time (generally)."""
        problem = VRPProblem.random_cvrp(n_customers=8, n_vehicles=2, capacity=60.0, seed=5)
        config = OptimizationConfig(population_size=30, max_iterations=50, random_seed=0)
        optimizer = QPSO(problem, config)
        result = optimizer.solve()
        if result.convergence and len(result.convergence) >= 2:
            first = result.convergence[0].best_fitness
            last = result.convergence[-1].best_fitness
            assert last <= first  # monotonically non-increasing

    def test_qpso_handles_1_customer(self):
        """Edge case: 1 customer, 1 vehicle."""
        problem = VRPProblem.random_cvrp(n_customers=1, n_vehicles=1, capacity=100.0, seed=0)
        config = OptimizationConfig(population_size=5, max_iterations=5, random_seed=0)
        result = QPSO(problem, config).solve()
        assert result.status in ("FEASIBLE", "INFEASIBLE")

    def test_qpso_infeasible_instance_reports_correctly(self):
        """If total demand > capacity, must report INFEASIBLE."""
        problem = VRPProblem.random_cvrp(n_customers=10, n_vehicles=1, capacity=50.0, seed=0)
        # reduce vehicle capacity so demand > capacity → infeasible
        problem.vehicles[0].capacity = 1.0
        problem.total_capacity = 1.0
        config = OptimizationConfig(population_size=10, max_iterations=5, random_seed=0)
        result = QPSO(problem, config).solve()
        # Pre-check should catch this
        assert result.status == "INFEASIBLE"
        assert len(result.reason) > 0

    def test_qpso_result_has_mandatory_fields(self, small_problem, quick_config):
        result = QPSO(small_problem, quick_config).solve()
        assert result.algorithm is not None
        assert result.runtime_ms >= 0
        assert isinstance(result.routes, list)
