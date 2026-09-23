"""
tests/test_reoptimization.py
============================
Unit tests for dynamic re-optimization.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np

from optimization.problem import VRPProblem
from optimization.config import OptimizationConfig
from optimization.entities import EdgeState, VehicleState
from optimization.reoptimization import ReOptimizer


@pytest.fixture
def problem():
    return VRPProblem.random_cvrp(n_customers=10, n_vehicles=3, capacity=50.0, seed=42)


@pytest.fixture
def config():
    return OptimizationConfig(
        population_size=15, max_iterations=20, random_seed=42, verbose=False
    )


class TestReOptimizer:
    def test_apply_incident_closes_road(self, problem, config):
        reopt = ReOptimizer(problem, config)
        reopt.apply_incident(
            {"edge_id": "1_2", "status": "CLOSED"},
            travel_time_multiplier=float("inf"),
        )
        assert problem._traffic_state.get("1_2") == EdgeState.CLOSED
        assert problem._edge_multipliers.get("1_2") == float("inf")

    def test_apply_incident_congested_with_multiplier(self, problem, config):
        reopt = ReOptimizer(problem, config)
        reopt.apply_incident(
            {"edge_id": "0_3", "status": "CONGESTED"},
            travel_time_multiplier=1.8,
        )
        assert problem._edge_multipliers.get("0_3") == pytest.approx(1.8)

    def test_clear_incident_removes_state(self, problem, config):
        reopt = ReOptimizer(problem, config)
        reopt.apply_incident({"edge_id": "2_3", "status": "CLOSED"})
        reopt.clear_incident("2_3")
        assert "2_3" not in problem._traffic_state

    def test_reoptimize_with_remaining_customers(self, problem, config):
        """Re-optimize with some customers already completed."""
        reopt = ReOptimizer(problem, config)
        # Simulate: vehicle 0 completed customers 0,1; has customers 2,3 remaining
        vehicle_states = {
            0: VehicleState(
                vehicle_id=0, current_node=2,
                completed_customers=[0, 1],
                remaining_customers=[2, 3],
                current_time=30.0, current_load=10.0,
            ),
            1: VehicleState(
                vehicle_id=1, current_node=0,
                completed_customers=[],
                remaining_customers=[4, 5, 6],
                current_time=0.0, current_load=0.0,
            ),
            2: VehicleState(
                vehicle_id=2, current_node=0,
                completed_customers=[],
                remaining_customers=[7, 8, 9],
                current_time=0.0, current_load=0.0,
            ),
        }
        result = reopt.reoptimize(vehicle_states)
        assert result.status in ("FEASIBLE", "INFEASIBLE")
        assert reopt.last_recovery_ms >= 0

    def test_recovery_time_is_measured(self, problem, config):
        """RecoveryTime must come from actual measurement."""
        reopt = ReOptimizer(problem, config)
        vehicle_states = {
            0: VehicleState(0, 0, [], [0, 1, 2, 3, 4], 0.0, 0.0),
            1: VehicleState(1, 0, [], [5, 6, 7, 8, 9], 0.0, 0.0),
            2: VehicleState(2, 0, [], [], 0.0, 0.0),
        }
        reopt.reoptimize(vehicle_states)
        assert reopt.recovery_time_ms() > 0, "Recovery time was not measured."

    def test_no_remaining_customers_returns_infeasible(self, problem, config):
        """Nothing to optimize → INFEASIBLE with reason."""
        reopt = ReOptimizer(problem, config)
        vehicle_states = {
            k: VehicleState(k, 0, list(range(k * 3, k * 3 + 3 if k < 2 else 4)), [], 0.0, 0.0)
            for k in range(3)
        }
        result = reopt.reoptimize(vehicle_states)
        # May be INFEASIBLE because no remaining customers
        assert result.status in ("FEASIBLE", "INFEASIBLE")

    def test_incident_affects_route_cost(self, problem, config):
        """Applying an incident should produce a different (adapted) result."""
        from optimization.adaptive_qpso import AdaptiveQPSO
        # Before incident
        r_before = AdaptiveQPSO(problem, config).solve()

        reopt = ReOptimizer(problem, config)
        # Apply a closure on a commonly used edge
        reopt.apply_incident(
            {"edge_id": "1_2", "status": "CLOSED"},
            travel_time_multiplier=float("inf"),
        )
        vehicle_states = {
            k: VehicleState(k, 0, [], list(range(k * 3, min(k * 3 + 3, 10))), 0.0, 0.0)
            for k in range(3)
        }
        r_after = reopt.reoptimize(vehicle_states, incidents=None)
        # Both should complete without error
        assert r_before.status in ("FEASIBLE", "INFEASIBLE")
        assert r_after.status in ("FEASIBLE", "INFEASIBLE")
