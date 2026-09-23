"""
tests/test_constraints.py
=========================
Unit tests for all hard-constraint checkers.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np

from optimization.problem import VRPProblem
from optimization.entities import Customer, Vehicle, Route
from optimization.constraints import (
    check_capacity, check_time_windows, check_road_availability,
    check_vehicle_availability, check_coverage, check_all, count_violations,
    ConstraintResult,
)


@pytest.fixture
def simple_problem():
    return VRPProblem.random_cvrp(n_customers=5, n_vehicles=2, capacity=50.0, seed=42)


def make_route(vehicle_id, sequence, total_demand, arrival_times=None):
    r = Route(vehicle_id=vehicle_id, sequence=sequence, total_demand=total_demand)
    r.arrival_times = arrival_times or [0.0] * len(sequence)
    r.departure_times = [t + 5.0 for t in r.arrival_times]
    return r


class TestCapacityConstraint:
    def test_within_capacity(self, simple_problem):
        route = make_route(0, [1, 2], total_demand=20.0)
        result = check_capacity(route, simple_problem)
        assert result.feasible

    def test_over_capacity(self, simple_problem):
        route = make_route(0, [1, 2, 3], total_demand=60.0)  # cap=50
        result = check_capacity(route, simple_problem)
        assert not result.feasible
        assert result.violation_count == 1

    def test_exactly_at_capacity(self, simple_problem):
        route = make_route(0, [1], total_demand=50.0)  # exactly full
        result = check_capacity(route, simple_problem)
        assert result.feasible

    def test_empty_route(self, simple_problem):
        route = Route(vehicle_id=0)
        result = check_capacity(route, simple_problem)
        assert result.feasible


class TestTimeWindowConstraint:
    def test_no_time_windows(self, simple_problem):
        simple_problem.enforce_time_windows = True
        route = make_route(0, [1, 2], 10.0, arrival_times=[5.0, 20.0])
        result = check_time_windows(route, simple_problem)
        # Default customers have infinite time window
        assert result.feasible

    def test_with_explicit_time_window_violation(self):
        """Customer with time window close=30, arrives at 60 — violation."""
        customers = [
            Customer(id=0, x=0, y=0, demand=5, time_window_open=0, time_window_close=30)
        ]
        vehicles = [Vehicle(id=0, capacity=50)]
        n = 2
        dist = np.array([[0.0, 1.0], [1.0, 0.0]])
        tt = np.array([[0.0, 2.0], [2.0, 0.0]])
        p = VRPProblem("cvrp", customers, vehicles, 0, 0.0, 0.0, dist, tt,
                        enforce_time_windows=True)
        route = make_route(0, [1], total_demand=5.0, arrival_times=[60.0])
        result = check_time_windows(route, p)
        assert not result.feasible
        assert result.violation_count >= 1

    def test_time_window_not_enforced(self, simple_problem):
        simple_problem.enforce_time_windows = False
        route = make_route(0, [1], 5.0, arrival_times=[9999.0])
        result = check_time_windows(route, simple_problem)
        assert result.feasible  # not enforced


class TestCoverageConstraint:
    def test_all_customers_served(self, simple_problem):
        r1 = make_route(0, [1, 2, 3], 20.0)
        r2 = make_route(1, [4, 5], 15.0)
        result = check_coverage([r1, r2], simple_problem)
        assert result.feasible

    def test_missing_customer(self, simple_problem):
        r1 = make_route(0, [1, 2], 10.0)
        r2 = make_route(1, [3, 4], 10.0)
        # Customer 5 missing
        result = check_coverage([r1, r2], simple_problem)
        assert not result.feasible

    def test_duplicate_customer(self, simple_problem):
        r1 = make_route(0, [1, 2, 3], 15.0)
        r2 = make_route(1, [2, 4, 5], 15.0)  # customer 2 duplicated
        result = check_coverage([r1, r2], simple_problem)
        assert not result.feasible


class TestVehicleAvailability:
    def test_unavailable_vehicle(self):
        customers = [Customer(id=0, x=0, y=0, demand=5)]
        vehicles = [Vehicle(id=0, capacity=50, available=False)]
        dist = np.zeros((2, 2))
        p = VRPProblem("cvrp", customers, vehicles, 0, 0, 0, dist, dist)
        route = make_route(0, [1], 5.0)
        result = check_vehicle_availability(route, p)
        assert not result.feasible

    def test_nonexistent_vehicle(self, simple_problem):
        route = make_route(99, [1], 5.0)
        result = check_vehicle_availability(route, simple_problem)
        assert not result.feasible


class TestRoadAvailability:
    def test_closed_road_detected(self, simple_problem):
        from optimization.entities import EdgeState
        simple_problem._traffic_state["0_1"] = EdgeState.CLOSED
        simple_problem._edge_multipliers["0_1"] = float("inf")
        route = make_route(0, [1, 2], 10.0)
        result = check_road_availability(route, simple_problem)
        assert not result.feasible

    def test_open_roads(self, simple_problem):
        route = make_route(0, [1, 2, 3], 15.0)
        result = check_road_availability(route, simple_problem)
        assert result.feasible
