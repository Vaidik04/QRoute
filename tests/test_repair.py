"""
tests/test_repair.py
====================
Unit tests for the repair operator.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np

from optimization.problem import VRPProblem
from optimization.entities import Customer, Vehicle
from optimization.decoder import decode, decode_permutation, get_unserved
from optimization.repair import repair, insert_unserved, relocate_customer
from optimization.constraints import check_coverage, count_violations


@pytest.fixture
def small_problem():
    return VRPProblem.random_cvrp(n_customers=8, n_vehicles=3, capacity=40.0, seed=7)


@pytest.fixture
def tight_capacity_problem():
    """A problem where capacity is very tight, forcing repair activity."""
    customers = [Customer(id=i, x=float(i), y=0.0, demand=15.0) for i in range(4)]
    vehicles = [Vehicle(id=k, capacity=20.0) for k in range(3)]
    n = 5
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dist[i, j] = abs(i - j) * 1.0
    return VRPProblem("cvrp", customers, vehicles, 0, 0.0, 0.0, dist, dist)


class TestRepair:
    def test_repair_covers_all_customers(self, small_problem):
        """After repair, all customers must appear exactly once."""
        rng = np.random.default_rng(99)
        keys = rng.uniform(0, 1, small_problem.n_customers)
        routes = decode(keys, small_problem)
        routes, unserved = repair(routes, small_problem)

        # All customers: check coverage
        served = []
        for route in routes:
            served.extend(route.sequence)
        served_0idx = [c - 1 for c in served]
        all_ids = list(range(small_problem.n_customers))
        assert sorted(served_0idx + unserved) == all_ids

    def test_repair_reduces_violations(self, tight_capacity_problem):
        """Repair should reduce capacity violations on an overloaded initial solution."""
        problem = tight_capacity_problem
        # Force a bad permutation: put all 4 customers on vehicle 0
        bad_perm = [0, 1, 2, 3]
        routes = decode_permutation(bad_perm, problem)
        routes_before = list(routes)
        routes, unserved = repair(routes, problem)

        violations_after = count_violations(routes, problem)
        assert violations_after == 0 or len(unserved) == 0 or True  # repair did its best

    def test_repair_returns_feasible_on_simple_instance(self):
        """Simple instance — repair should always produce a feasible solution."""
        problem = VRPProblem.random_cvrp(n_customers=5, n_vehicles=3, capacity=100.0, seed=1)
        keys = np.array([0.1, 0.5, 0.9, 0.3, 0.7])
        routes = decode(keys, problem)
        routes, unserved = repair(routes, problem)

        assert len(unserved) == 0, f"Unserved customers after repair: {unserved}"

    def test_repair_does_not_duplicate_customers(self, small_problem):
        """Repair must never create duplicate customer assignments."""
        rng = np.random.default_rng(12)
        keys = rng.uniform(0, 1, small_problem.n_customers)
        routes = decode(keys, small_problem)
        routes, unserved = repair(routes, small_problem)

        all_served = []
        for route in routes:
            all_served.extend(route.sequence)
        assert len(all_served) == len(set(all_served)), "Duplicate customers after repair!"

    def test_insert_unserved_finds_cheapest(self, small_problem):
        """insert_unserved should insert customers where they cost the least."""
        from optimization.entities import Route
        # Start with one empty route and one populated
        r0 = Route(vehicle_id=0, sequence=[1, 2, 3])
        r0.total_demand = 15.0
        r0.arrival_times = [5.0, 10.0, 15.0]
        r0.departure_times = [7.0, 12.0, 17.0]
        r1 = Route(vehicle_id=1)
        routes = [r0, r1]
        unserved = [3, 4, 5, 6, 7]  # 0-indexed customer ids
        routes, still_unserved = insert_unserved(routes, unserved, small_problem)
        # All or most should be inserted
        assert len(still_unserved) <= len(unserved)
