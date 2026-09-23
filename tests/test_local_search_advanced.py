"""
tests/test_local_search_advanced.py
===================================
Unit tests for the advanced local search operators:
- Or-opt (block relocations of size 1, 2, 3)
- 2-opt* (inter-route tail swaps)
- CROSS-exchange (sub-segment exchange)
- Variable Neighborhood Descent (VND)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from optimization.problem import VRPProblem
from optimization.entities import Route
from optimization.local_search import (
    or_opt,
    two_opt,
    two_opt_star,
    cross_exchange,
    variable_neighborhood_descent,
    run_all_ls,
    _route_dist,
)


@pytest.fixture
def problem_and_routes():
    problem = VRPProblem.random_cvrp(n_customers=12, n_vehicles=3, capacity=100.0, seed=42)
    # Construct 3 routes covering all 12 customers (1-indexed: 1..12)
    r0 = Route(vehicle_id=0, sequence=[1, 2, 3, 4])
    r1 = Route(vehicle_id=1, sequence=[5, 6, 7, 8])
    r2 = Route(vehicle_id=2, sequence=[9, 10, 11, 12])
    routes = [r0, r1, r2]
    for r in routes:
        r.total_demand = sum(problem.customers[cid - 1].demand for cid in r.sequence)
        r.total_distance = _route_dist(r.sequence, problem)
    return problem, routes


def _all_customers_in_routes(routes: list[Route], n_customers: int = 12):
    all_custs = []
    for r in routes:
        all_custs.extend(r.sequence)
    assert len(all_custs) == n_customers, f"Expected {n_customers} customers, got {len(all_custs)}"
    assert sorted(all_custs) == list(range(1, n_customers + 1)), "Customer duplication or omission detected"


class TestAdvancedLocalSearch:
    def test_or_opt_preserves_all_customers(self, problem_and_routes):
        problem, routes = problem_and_routes
        initial_dist = sum(r.total_distance for r in routes)
        improved = or_opt(routes, problem, max_segment_len=3)
        _all_customers_in_routes(improved)
        final_dist = sum(r.total_distance for r in improved)
        assert final_dist <= initial_dist + 1e-8

    def test_two_opt_star_preserves_all_customers(self, problem_and_routes):
        problem, routes = problem_and_routes
        initial_dist = sum(r.total_distance for r in routes)
        improved = two_opt_star(routes, problem)
        _all_customers_in_routes(improved)
        final_dist = sum(r.total_distance for r in improved)
        assert final_dist <= initial_dist + 1e-8

    def test_cross_exchange_preserves_all_customers(self, problem_and_routes):
        problem, routes = problem_and_routes
        initial_dist = sum(r.total_distance for r in routes)
        improved = cross_exchange(routes, problem, max_len=2)
        _all_customers_in_routes(improved)
        final_dist = sum(r.total_distance for r in improved)
        assert final_dist <= initial_dist + 1e-8

    def test_variable_neighborhood_descent(self, problem_and_routes):
        problem, routes = problem_and_routes
        initial_dist = sum(r.total_distance for r in routes)
        vnd_routes = variable_neighborhood_descent(routes, problem, max_vnd_iterations=3)
        _all_customers_in_routes(vnd_routes)
        final_dist = sum(r.total_distance for r in vnd_routes)
        # VND should never worsen solution quality
        assert final_dist <= initial_dist + 1e-8
        # Vehicle capacity must be respected
        for r in vnd_routes:
            veh = problem.vehicles[r.vehicle_id]
            assert r.total_demand <= veh.capacity + 1e-8

    def test_run_all_ls_calls_vnd(self, problem_and_routes):
        problem, routes = problem_and_routes
        out_routes = run_all_ls(routes, problem)
        _all_customers_in_routes(out_routes)
        for r in out_routes:
            assert r.total_distance >= 0.0
