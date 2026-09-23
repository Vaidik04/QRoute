"""
tests/test_result_advanced.py
=============================
Unit tests for the advanced result contract:
- GeoJSON export (RFC 7946)
- ASCII route and schedule visualizer
- Route disruption metrics
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json

from optimization.problem import VRPProblem
from optimization.result import OptimizationResult, ConvergencePoint
from optimization.reoptimization import compute_route_disruption


@pytest.fixture
def problem_and_result():
    problem = VRPProblem.random_cvrp(n_customers=6, n_vehicles=2, capacity=50.0, seed=42)
    routes = [[0, 1, 2, 3, 0], [0, 4, 5, 6, 0]]
    vehicle_assignments = {0: [0, 1, 2], 1: [3, 4, 5]}
    res = OptimizationResult.feasible_from_routes(
        algorithm="adaptive_d_qpso",
        routes=routes,
        vehicle_assignments=vehicle_assignments,
        objective_value=124.5,
        distance_km=32.1,
        travel_time_min=45.2,
        vehicle_utilization=0.75,
        constraint_violations=0,
        iterations=50,
        runtime_ms=85.0,
        convergence=[
            ConvergencePoint(iteration=1, best_fitness=150.0, mean_fitness=170.0, diversity=0.2, alpha=1.0),
            ConvergencePoint(iteration=50, best_fitness=124.5, mean_fitness=130.0, diversity=0.04, alpha=0.3),
        ],
        feasible_routes=2,
    )
    return problem, res


class TestAdvancedResultContract:
    def test_geojson_export(self, problem_and_result):
        problem, res = problem_and_result
        geojson = res.to_geojson(problem=problem)

        assert geojson["type"] == "FeatureCollection"
        assert "features" in geojson
        assert len(geojson["features"]) > 0

        # Check for point (depot + customers) and linestring (routes)
        geom_types = {f["geometry"]["type"] for f in geojson["features"]}
        assert "Point" in geom_types
        assert "LineString" in geom_types

        # Verify serializability
        serialized = json.dumps(geojson)
        assert len(serialized) > 100

    def test_ascii_visualizer(self, problem_and_result):
        problem, res = problem_and_result
        ascii_out = res.visualize_ascii(problem=problem)
        assert "Q-TRANSIT NEXUS ROUTE DISPATCH PLAN" in ascii_out
        assert "Vehicle  0" in ascii_out
        assert "Depot ->" in ascii_out

    def test_route_disruption_metrics(self):
        plan_a = {0: [1, 2, 3], 1: [4, 5, 6]}
        plan_b = {0: [1, 2, 4], 1: [3, 5, 6]}  # 3 and 4 swapped
        metrics = compute_route_disruption(plan_a, plan_b)
        assert metrics["customer_displacements"] == 2
        assert metrics["total_evaluated_customers"] == 6
        assert metrics["route_stability_score"] == pytest.approx(1.0 - 2/6, rel=1e-3)
