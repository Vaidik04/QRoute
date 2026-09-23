"""
optimization/repair.py
======================
Repair operator: attempts to fix infeasible solutions before penalising.

Section 8 of the build spec:
    "Before penalising, attempt: relocate, exchange, route split,
     insert into another vehicle, remove/reinsert by minimum added cost."

Repair pipeline:
    decoded routes + unserved list
         → try relocate (move customer between routes)
         → try exchange (swap customers between routes)
         → try route split (capacity-overflow route → two routes)
         → try insert-into-cheapest for unserved customers
         → remaining unserved → heavy penalty (handled by fitness)

The repair is *not* a local-search improver — it is a feasibility restorer.
Run it once per particle decode, before computing fitness.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .entities import Route
from .decoder import _compute_distance

if TYPE_CHECKING:
    from .problem import VRPProblem


# ---------------------------------------------------------------------------
# Insertion cost helper
# ---------------------------------------------------------------------------

def _insertion_cost(
    cust_matrix_idx: int,
    route_sequence: list[int],
    problem: "VRPProblem",
    current_time: float = 0.0,
) -> tuple[float, int]:
    """Find the cheapest position to insert ``cust_matrix_idx`` into a route.

    Returns (added_cost, best_position_index).
    Best position = index in the sequence *before* which to insert.
    Returns (inf, -1) if no feasible insertion exists.
    """
    best_cost = float("inf")
    best_pos = -1
    seq = route_sequence

    for pos in range(len(seq) + 1):
        # Nodes before and after the insertion point
        prev = seq[pos - 1] if pos > 0 else 0      # depot if pos==0
        nxt = seq[pos] if pos < len(seq) else 0     # depot if pos==len

        # Cost of detour: remove (prev→next) add (prev→cust + cust→next)
        removed = problem.distance(prev, nxt)
        added = (
            problem.distance(prev, cust_matrix_idx)
            + problem.distance(cust_matrix_idx, nxt)
        )
        delta = added - removed

        # Quick time feasibility (arrival at customer)
        # Compute approximate arrival by replaying from depot
        t = current_time
        prev_node = 0
        feasible_tw = True
        for i, node in enumerate(seq[:pos] + [cust_matrix_idx] + seq[pos:]):
            t += problem.travel_time(prev_node, node, t)
            if i == pos:  # This is our inserted customer
                cust = problem.customers[cust_matrix_idx - 1]
                if problem.allow_waiting:
                    t = max(t, cust.time_window_open)
                if cust.has_time_window() and t > cust.time_window_close + 1e-6:
                    feasible_tw = False
                    break
                t += cust.service_time
            else:
                cust = problem.customers[node - 1]
                if problem.allow_waiting:
                    t = max(t, cust.time_window_open)
                t += cust.service_time
            prev_node = node

        if feasible_tw and delta < best_cost:
            best_cost = delta
            best_pos = pos

    return best_cost, best_pos


# ---------------------------------------------------------------------------
# Repair operators
# ---------------------------------------------------------------------------

def relocate_customer(
    routes: list[Route],
    problem: "VRPProblem",
) -> tuple[list[Route], bool]:
    """Move one customer from an over-capacity route to another route.

    Returns (routes, improved) where improved=True if at least one move was made.
    """
    improved = False
    for src_k, src_route in enumerate(routes):
        vehicle = problem.vehicles[src_k]
        if src_route.total_demand <= vehicle.capacity + 1e-9:
            continue  # route is fine

        # Try to relocate customers from this over-capacity route
        to_relocate = []
        remaining_demand = src_route.total_demand
        for cust_idx in list(src_route.sequence):
            cust = problem.customers[cust_idx - 1]
            # Try each other route
            best_delta = float("inf")
            best_dst_k = -1
            best_pos = -1
            for dst_k, dst_route in enumerate(routes):
                if dst_k == src_k:
                    continue
                dst_vehicle = problem.vehicles[dst_k]
                new_load = dst_route.total_demand + cust.demand
                if new_load > dst_vehicle.capacity + 1e-9:
                    continue
                if not dst_vehicle.available:
                    continue
                delta, pos = _insertion_cost(cust_idx, dst_route.sequence, problem)
                if delta < best_delta:
                    best_delta = delta
                    best_dst_k = dst_k
                    best_pos = pos

            if best_dst_k >= 0:
                # Move customer
                src_route.sequence.remove(cust_idx)
                src_route.total_demand -= cust.demand
                dst_route = routes[best_dst_k]
                dst_route.sequence.insert(best_pos, cust_idx)
                dst_route.total_demand += cust.demand
                improved = True
                break  # restart after one move to avoid stale indices

    return routes, improved


def exchange_customers(
    routes: list[Route],
    problem: "VRPProblem",
) -> tuple[list[Route], bool]:
    """Swap one customer between two routes to resolve capacity violations."""
    improved = False
    for i, route_a in enumerate(routes):
        veh_a = problem.vehicles[i]
        for j, route_b in enumerate(routes):
            if i >= j:
                continue
            veh_b = problem.vehicles[j]
            for ca_idx in list(route_a.sequence):
                ca = problem.customers[ca_idx - 1]
                for cb_idx in list(route_b.sequence):
                    cb = problem.customers[cb_idx - 1]
                    # Check if swap resolves capacity
                    new_a_load = route_a.total_demand - ca.demand + cb.demand
                    new_b_load = route_b.total_demand - cb.demand + ca.demand
                    if (
                        new_a_load <= veh_a.capacity + 1e-9
                        and new_b_load <= veh_b.capacity + 1e-9
                    ):
                        # Do the swap
                        pos_a = route_a.sequence.index(ca_idx)
                        pos_b = route_b.sequence.index(cb_idx)
                        route_a.sequence[pos_a] = cb_idx
                        route_b.sequence[pos_b] = ca_idx
                        route_a.total_demand = new_a_load
                        route_b.total_demand = new_b_load
                        improved = True
                        return routes, improved  # one swap per call
    return routes, improved


def insert_unserved(
    routes: list[Route],
    unserved: list[int],
    problem: "VRPProblem",
) -> tuple[list[Route], list[int]]:
    """Insert unserved customers into existing routes at the cheapest feasible position.

    Returns (routes, still_unserved).
    """
    still_unserved = []
    # Sort by demand descending — try hardest customers first
    ordered = sorted(unserved, key=lambda cid: problem.customers[cid].demand, reverse=True)

    for customer_id in ordered:
        cust_matrix_idx = customer_id + 1
        cust = problem.customers[customer_id]
        best_delta = float("inf")
        best_route_k = -1
        best_pos = -1

        for k, route in enumerate(routes):
            vehicle = problem.vehicles[k]
            new_load = route.total_demand + cust.demand
            if new_load > vehicle.capacity + 1e-9:
                continue
            if not vehicle.available:
                continue
            delta, pos = _insertion_cost(cust_matrix_idx, route.sequence, problem)
            if delta < best_delta:
                best_delta = delta
                best_route_k = k
                best_pos = pos

        if best_route_k >= 0:
            route = routes[best_route_k]
            route.sequence.insert(best_pos, cust_matrix_idx)
            route.total_demand += cust.demand
        else:
            still_unserved.append(customer_id)

    return routes, still_unserved


def split_overloaded_route(
    routes: list[Route],
    problem: "VRPProblem",
) -> list[Route]:
    """Split an over-capacity route by moving overflow customers to a spare vehicle.

    Only activates if there is a vehicle with no assigned customers (spare vehicle).
    """
    spare_routes = [
        (k, r) for k, r in enumerate(routes)
        if r.is_empty() and problem.vehicles[k].available
    ]
    if not spare_routes:
        return routes

    for k, src_route in enumerate(routes):
        vehicle = problem.vehicles[k]
        if src_route.total_demand <= vehicle.capacity + 1e-9:
            continue

        # Move excess customers to the first spare vehicle
        spare_k, spare_route = spare_routes.pop(0)
        excess_demand = 0.0
        to_move = []
        for cust_idx in reversed(src_route.sequence):
            cust = problem.customers[cust_idx - 1]
            if (src_route.total_demand - excess_demand - cust.demand
                    <= vehicle.capacity + 1e-9):
                break
            to_move.append(cust_idx)
            excess_demand += cust.demand

        for cust_idx in to_move:
            src_route.sequence.remove(cust_idx)
            src_route.total_demand -= problem.customers[cust_idx - 1].demand
            spare_route.sequence.append(cust_idx)
            spare_route.total_demand += problem.customers[cust_idx - 1].demand

        if not spare_routes:
            break  # no more spare vehicles

    return routes


# ---------------------------------------------------------------------------
# Recompute route totals after in-place modification
# ---------------------------------------------------------------------------

def recompute_route_totals(routes: list[Route], problem: "VRPProblem") -> None:
    """Recompute total_distance and total_demand for all routes after repair."""
    for route in routes:
        if route.is_empty():
            route.total_distance = 0.0
            route.total_demand = 0.0
            route.total_time = 0.0
            route.arrival_times = []
            route.departure_times = []
            continue

        # Demand
        route.total_demand = sum(
            problem.customers[cid - 1].demand for cid in route.sequence
        )
        # Distance
        route.total_distance = _compute_distance(route.sequence, problem)

        # Arrival times (sequential, time-dependent)
        arrivals = []
        departures = []
        t = 0.0
        prev = 0
        for node in route.sequence:
            t += problem.travel_time(prev, node, t)
            cust = problem.customers[node - 1]
            if problem.allow_waiting:
                t = max(t, cust.time_window_open)
            arrivals.append(t)
            t += cust.service_time
            departures.append(t)
            prev = node
        # Return to depot
        t += problem.travel_time(prev, 0, t)
        route.arrival_times = arrivals
        route.departure_times = departures
        route.total_time = t


# ---------------------------------------------------------------------------
# Master repair function
# ---------------------------------------------------------------------------

def repair(
    routes: list[Route],
    problem: "VRPProblem",
    max_passes: int = 3,
) -> tuple[list[Route], list[int]]:
    """Run the full repair pipeline.

    Tries up to ``max_passes`` rounds of relocate + exchange + split + insert.

    Returns
    -------
    (routes, still_unserved)
        still_unserved: 0-indexed customer ids that could not be assigned.
    """
    unserved = getattr(routes[0], "unserved", []) if routes else []

    for _ in range(max_passes):
        # 1. Split overloaded routes using spare vehicles
        routes = split_overloaded_route(routes, problem)
        # 2. Relocate customers from overloaded routes
        routes, _ = relocate_customer(routes, problem)
        # 3. Exchange customers between routes
        routes, _ = exchange_customers(routes, problem)
        # 4. Insert unserved customers cheaply
        routes, unserved = insert_unserved(routes, unserved, problem)

        if not unserved:
            break

    # Recompute all totals with corrected sequences
    recompute_route_totals(routes, problem)

    # Attach still_unserved for fitness to find
    if routes:
        routes[0].unserved = unserved  # type: ignore[attr-defined]

    return routes, unserved
