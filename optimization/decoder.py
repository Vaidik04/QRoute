"""
optimization/decoder.py
=======================
Constraint-aware decoder: particle → permutation → feasible vehicle routes.

Section 7 of the build spec:
    "Do not randomly split the permutation. Sequentially assign customers
     to vehicles, checking capacity/time/duration as you go."

The decoder is the critical bridge between the continuous QPSO search space
and the discrete routing problem.  It must be:
- Deterministic given the same permutation + problem.
- Constraint-aware (checks capacity and time before assigning).
- Fast (called millions of times during optimization).

Time-dependent arrival tracking (Section 5.3):
    a_{k+1} = a_k + T_{v_k, v_{k+1}}(a_k)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .encoding import random_keys_to_permutation
from .entities import Route

if TYPE_CHECKING:
    from .problem import VRPProblem


def decode(
    keys: np.ndarray,
    problem: "VRPProblem",
    start_times: list[float] | None = None,
) -> list[Route]:
    """Decode a QPSO key vector into a list of feasible vehicle routes.

    Pipeline:
    1. keys → permutation (argsort)
    2. walk permutation left-to-right
    3. try to append each customer to the current vehicle route
       (checking capacity, time window, max duration)
    4. if it doesn't fit, open a new vehicle
    5. if no vehicle can take the customer, mark unserved (handled by repair)

    Parameters
    ----------
    keys : np.ndarray, shape (n_customers,)
        QPSO particle position (random keys in [0, 1]).
    problem : VRPProblem
    start_times : list[float] | None
        Departure time for each vehicle from the depot (default: 0 for all).

    Returns
    -------
    routes : list[Route]
        One Route per vehicle (some may be empty).  Unserved customers are
        listed in ``unserved`` (attached as attribute to the first route for
        repair to find).
    """
    permutation = random_keys_to_permutation(keys)
    return decode_permutation(permutation, problem, start_times)


def decode_permutation(
    permutation: list[int],
    problem: "VRPProblem",
    start_times: list[float] | None = None,
) -> list[Route]:
    """Decode a customer permutation (0-indexed) into routes.

    Parameters
    ----------
    permutation : list[int]
        0-indexed customer ids in visit order.
    problem : VRPProblem
    start_times : list[float] | None

    Returns
    -------
    list[Route]  — length == problem.n_vehicles.
    """
    n_vehicles = problem.n_vehicles
    vehicles = problem.vehicles
    n_customers = problem.n_customers

    if start_times is None:
        start_times = [0.0] * n_vehicles

    # Initialise one empty route per vehicle
    routes: list[Route] = [
        Route(vehicle_id=k) for k in range(n_vehicles)
    ]

    # Track current state of each vehicle's route construction
    # (last_node, current_time, current_load)
    states = [
        [0, start_times[k], 0.0]  # [last_matrix_idx, time, load]
        for k in range(n_vehicles)
    ]

    unserved: list[int] = []  # customer ids not assigned to any vehicle

    for customer_id in permutation:
        customer = problem.customers[customer_id]
        cust_matrix_idx = customer_id + 1  # depot=0, customers=1..N

        assigned = False
        for k in range(n_vehicles):
            vehicle = vehicles[k]
            if not vehicle.available:
                continue

            last_node, cur_time, cur_load = states[k]

            # --- Capacity check ---
            new_load = cur_load + customer.demand
            if new_load > vehicle.capacity + 1e-9:
                continue  # over capacity — try next vehicle

            # --- Time feasibility check ---
            travel = problem.travel_time(last_node, cust_matrix_idx, cur_time)
            arrival = cur_time + travel

            if problem.allow_waiting:
                # Wait until window opens if arriving early
                arrival = max(arrival, customer.time_window_open)

            if customer.has_time_window():
                if arrival > customer.time_window_close + 1e-6:
                    continue  # too late for this customer — try next vehicle

            # --- Duration check ---
            departure = arrival + customer.service_time
            # Check if we can still return to depot within max_duration
            if vehicle.max_duration > 0:
                # Conservative: assume direct return from here
                min_return_time = departure + problem.travel_time(
                    cust_matrix_idx, 0, departure
                )
                if min_return_time - start_times[k] > vehicle.max_duration + 1e-6:
                    continue

            # --- Road availability check ---
            if not problem.edge_available(last_node, cust_matrix_idx):
                continue  # closed road — try next vehicle

            # --- Assign to this vehicle ---
            routes[k].sequence.append(cust_matrix_idx)
            routes[k].arrival_times.append(arrival)
            routes[k].departure_times.append(departure)
            routes[k].total_demand += customer.demand
            states[k] = [cust_matrix_idx, departure, new_load]
            assigned = True
            break  # move on to next customer in permutation

        if not assigned:
            unserved.append(customer_id)

    # Finalise each route: compute totals + return-to-depot time
    for k, route in enumerate(routes):
        if route.is_empty():
            continue
        last_node, cur_time, _ = states[k]
        return_time = problem.travel_time(last_node, 0, cur_time)
        route.total_time = (cur_time + return_time) - start_times[k]
        route.total_distance = _compute_distance(route.sequence, problem)

    # Attach unserved list to the route object (used by repair)
    routes[0].unserved = unserved  # type: ignore[attr-defined]

    return routes


def _compute_distance(sequence: list[int], problem: "VRPProblem") -> float:
    """Total km for a sequence of matrix indices (depot→seq→depot)."""
    total = 0.0
    prev = 0  # depot
    for node in sequence:
        total += problem.distance(prev, node)
        prev = node
    total += problem.distance(prev, 0)  # return to depot
    return total


def get_unserved(routes: list[Route]) -> list[int]:
    """Extract the list of unserved customer ids from a decoded route set."""
    return getattr(routes[0], "unserved", []) if routes else []


def routes_to_sequence_list(routes: list[Route]) -> list[list[int]]:
    """Convert routes to the API format: each sub-list [depot, c1, c2, depot].

    Matrix indices are used (0 = depot, 1..N = customers).
    """
    result = []
    for route in routes:
        if not route.is_empty():
            result.append([0] + route.sequence + [0])
    return result
