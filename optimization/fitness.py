"""
optimization/fitness.py
=======================
Multi-objective fitness/cost calculators for the routing engine.

Section 5.4 objective function:
    F = w_t·C_t + w_d·C_d + w_c·C_c + w_r·C_r + P

where:
    C_t  = total travel time cost (minutes, normalised)
    C_d  = total distance cost (km, normalised)
    C_c  = congestion cost (fraction of route on congested roads × severity)
    C_r  = risk/reliability cost (priority × lateness)
    P    = penalty for unresolved constraint violations (large-M)

The weights are supplied by the caller (ObjectiveWeights) so the same
engine serves Fastest / Balanced / Green / Emergency profiles without
code duplication.

Priority lateness penalty (Section 17):
    C_p = Σ priority_i × lateness_i
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from .entities import EdgeState, Route

if TYPE_CHECKING:
    from .problem import VRPProblem
    from .config import ObjectiveWeights


# ---------------------------------------------------------------------------
# Sub-cost calculators
# ---------------------------------------------------------------------------

def time_cost(routes: list[Route]) -> float:
    """Total travel + service time across all routes (minutes)."""
    return sum(r.total_time for r in routes)


def distance_cost(routes: list[Route]) -> float:
    """Total route distance (km)."""
    return sum(r.total_distance for r in routes)


def congestion_cost(routes: list[Route], problem: "VRPProblem") -> float:
    """Estimate congestion cost based on traffic state of traversed edges.

    Congestion score = Σ (travel_time_with_traffic - nominal_travel_time)
    for all edges in all routes.  Closed edges contribute 0 here (they
    are caught by hard constraints / repair).

    NOTE: edge multipliers originate exclusively from the traffic module.
    """
    total = 0.0
    for route in routes:
        full_seq = [0] + route.sequence + [0]
        for a, b in zip(full_seq, full_seq[1:]):
            edge_key = f"{a}_{b}"
            multiplier = problem._edge_multipliers.get(edge_key, 1.0)
            nominal = problem.travel_time_matrix[a, b]
            actual = nominal * multiplier
            if actual < float("inf"):
                total += max(0.0, actual - nominal)
    return total


def risk_cost(routes: list[Route], problem: "VRPProblem") -> float:
    """Risk / reliability cost: priority × lateness for each customer.

    High-priority customers incur much higher cost when served late.
    Also penalises routes that traverse CLOSED or heavily congested edges.
    """
    total = 0.0
    for route in routes:
        for seq_pos, (cust_idx, arrival) in enumerate(
            zip(route.sequence, route.arrival_times)
        ):
            customer = problem.customers[cust_idx - 1]
            if math.isinf(customer.time_window_close):
                lateness = 0.0
            else:
                lateness = max(0.0, arrival - customer.time_window_close)
            total += customer.priority * lateness
    return total


def vehicle_utilization(routes: list[Route], problem: "VRPProblem") -> float:
    """Average load / capacity across non-empty routes."""
    non_empty = [r for r in routes if not r.is_empty()]
    if not non_empty:
        return 0.0
    utils = []
    for route in non_empty:
        vehicle = problem.vehicles[route.vehicle_id]
        utils.append(route.total_demand / vehicle.capacity)
    return float(np.mean(utils))


# ---------------------------------------------------------------------------
# Penalty terms
# ---------------------------------------------------------------------------

def unserved_penalty(unserved: list[int], problem: "VRPProblem", coeff: float) -> float:
    """Large-M penalty for each customer not assigned to any vehicle.

    Penalty = coeff × Σ demand_i for unserved customers.
    Using demand makes high-demand unserved customers cost more.
    """
    if not unserved:
        return 0.0
    total = sum(problem.customers[cid].demand for cid in unserved)
    return coeff * (len(unserved) + total)


def capacity_violation_penalty(routes: list[Route], problem: "VRPProblem", coeff: float) -> float:
    """Penalty for routes that exceed vehicle capacity (post-repair remainder)."""
    total = 0.0
    for route in routes:
        vehicle = problem.vehicles[route.vehicle_id]
        excess = max(0.0, route.total_demand - vehicle.capacity)
        if excess > 0:
            total += coeff * excess
    return total


def time_window_violation_penalty(routes: list[Route], problem: "VRPProblem", coeff: float) -> float:
    """Penalty for lateness violations."""
    if not problem.enforce_time_windows:
        return 0.0
    total = 0.0
    for route in routes:
        for cust_idx, arrival in zip(route.sequence, route.arrival_times):
            customer = problem.customers[cust_idx - 1]
            if customer.has_time_window():
                lateness = max(0.0, arrival - customer.time_window_close)
                total += coeff * customer.priority * lateness
    return total


def route_change_penalty(
    new_routes: list[Route],
    reference_routes: list[Route],
    weight: float,
) -> float:
    """Stability penalty during re-optimization (Section 14).

    Counts the number of customer-reassignments relative to the reference
    (previous) route plan.  Large changes cost more.

    F' = F + w_s × C_routechange
    """
    if not reference_routes or weight == 0.0:
        return 0.0

    # Build assignment maps: customer_idx → vehicle_id
    ref_assignment: dict[int, int] = {}
    for route in reference_routes:
        for cid in route.sequence:
            ref_assignment[cid] = route.vehicle_id

    new_assignment: dict[int, int] = {}
    for route in new_routes:
        for cid in route.sequence:
            new_assignment[cid] = route.vehicle_id

    changes = sum(
        1 for cid, vid in new_assignment.items()
        if ref_assignment.get(cid) != vid
    )
    return weight * changes


# ---------------------------------------------------------------------------
# Master fitness function
# ---------------------------------------------------------------------------

def calculate_fitness(
    routes: list[Route],
    problem: "VRPProblem",
    weights: "ObjectiveWeights",
    unserved: list[int] | None = None,
    reference_routes: list[Route] | None = None,
    penalty_coeff: float = 1e6,
) -> float:
    """Compute the composite weighted fitness value.

    F = w_t·C_t + w_d·C_d + w_c·C_c + w_r·C_r + P + route_change_penalty

    Parameters
    ----------
    routes : list[Route]
    problem : VRPProblem
    weights : ObjectiveWeights
    unserved : list[int] | None      0-indexed customer ids not served.
    reference_routes : list[Route] | None   Previous routes for stability penalty.
    penalty_coeff : float            Large-M coefficient.

    Returns
    -------
    float  — lower is better.
    """
    if unserved is None:
        unserved = []

    # Sub-costs
    c_t = time_cost(routes)
    c_d = distance_cost(routes)
    c_c = congestion_cost(routes, problem)
    c_r = risk_cost(routes, problem)

    # Weighted sum
    fitness = (
        weights.time * c_t
        + weights.distance * c_d
        + weights.congestion * c_c
        + weights.risk * c_r
    )

    # Penalty terms
    fitness += unserved_penalty(unserved, problem, penalty_coeff)
    fitness += capacity_violation_penalty(routes, problem, penalty_coeff)
    fitness += time_window_violation_penalty(routes, problem, penalty_coeff * 0.1)

    # Route-change stability (during re-optimization)
    if reference_routes and weights.stability > 0:
        fitness += route_change_penalty(routes, reference_routes, weights.stability)

    return fitness


def calculate_fitness_from_keys(
    keys,
    problem: "VRPProblem",
    weights: "ObjectiveWeights",
    penalty_coeff: float = 1e6,
):
    """Full pipeline: keys → decode → fitness.

    Convenience wrapper used by PSO/QPSO inner loops.
    Returns (fitness, routes, unserved).
    """
    from .decoder import decode, get_unserved

    routes = decode(keys, problem)
    unserved = get_unserved(routes)
    f = calculate_fitness(routes, problem, weights, unserved, penalty_coeff=penalty_coeff)
    return f, routes, unserved
