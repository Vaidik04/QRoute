"""
optimization/local_search.py
============================
Elite Local Search Suite & Variable Neighborhood Descent (VND).

This module implements a comprehensive set of discrete neighborhood operators
tailored for Multi-Vehicle Capacitated Time-Dependent Routing (CVRP/VRPTW).

Operators:
    1. two_opt(routes, problem)          — Intra-route 2-opt (segment reversal)
    2. or_opt(routes, problem, max_len)  — Relocate blocks of size 1, 2, 3 (intra & inter)
    3. relocate_ls(routes, problem)      — Move single customer to cheapest feasible position
    4. swap_ls(routes, problem)          — Exchange customer pairs within/between routes
    5. two_opt_star(routes, problem)     — Inter-route 2-opt* (route tail exchange)
    6. cross_exchange(routes, problem)   — Swap sub-segments between two routes
    7. variable_neighborhood_descent()   — Systematic VND over all neighborhoods
    8. run_all_ls(routes, problem)       — Master runner calling VND
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Optional

from .entities import Route
from .repair import recompute_route_totals, _insertion_cost

if TYPE_CHECKING:
    from .problem import VRPProblem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _route_dist(sequence: list[int], problem: "VRPProblem") -> float:
    """Compute total distance of a sequence (depot → seq → depot)."""
    if not sequence:
        return 0.0
    total = 0.0
    prev = 0
    for node in sequence:
        total += problem.distance(prev, node)
        prev = node
    total += problem.distance(prev, 0)
    return total


def _sequence_demand(sequence: list[int], problem: "VRPProblem") -> float:
    """Sum demand for a sequence of 1-indexed customer nodes."""
    return sum(problem.customers[node - 1].demand for node in sequence)


# ---------------------------------------------------------------------------
# 1. Intra-route 2-opt (Segment Reversal)
# ---------------------------------------------------------------------------

def two_opt(routes: list[Route], problem: "VRPProblem") -> list[Route]:
    """Apply 2-opt to each route independently.

    For each route, try reversing every sub-segment [i, j].
    Accept if it reduces the route distance.
    Runs until local minimum is reached for each route.
    """
    improved_routes = []
    for route in routes:
        if len(route.sequence) < 3:
            improved_routes.append(copy.copy(route))
            continue

        seq = route.sequence[:]
        best_dist = _route_dist(seq, problem)
        improved = True
        while improved:
            improved = False
            n = len(seq)
            for i in range(n - 1):
                for j in range(i + 1, n):
                    # Reverse segment [i..j]
                    new_seq = seq[:i] + seq[i:j + 1][::-1] + seq[j + 1:]
                    new_dist = _route_dist(new_seq, problem)
                    if new_dist < best_dist - 1e-9:
                        seq = new_seq
                        best_dist = new_dist
                        improved = True
                        break
                if improved:
                    break

        new_route = copy.copy(route)
        new_route.sequence = seq
        improved_routes.append(new_route)

    recompute_route_totals(improved_routes, problem)
    return improved_routes


# ---------------------------------------------------------------------------
# 2. Or-opt: Relocation of contiguous segments of length 1, 2, and 3
# ---------------------------------------------------------------------------

def or_opt(
    routes: list[Route],
    problem: "VRPProblem",
    max_segment_len: int = 3,
) -> list[Route]:
    """Apply Or-opt: relocate contiguous customer blocks of length L in {1, 2, 3}.

    Tests relocations within the same route and across different vehicle routes.
    Accepts moves that reduce total distance while satisfying vehicle capacities.
    """
    routes = [copy.copy(r) for r in routes]
    for r in routes:
        r.sequence = r.sequence[:]

    improved = True
    while improved:
        improved = False
        # Try larger segment lengths first (3, 2, 1)
        for seg_len in range(max_segment_len, 0, -1):
            for src_k, src_route in enumerate(routes):
                if len(src_route.sequence) < seg_len:
                    continue

                n_src = len(src_route.sequence)
                for i in range(n_src - seg_len + 1):
                    block = src_route.sequence[i:i + seg_len]
                    block_demand = _sequence_demand(block, problem)
                    rem_src_seq = src_route.sequence[:i] + src_route.sequence[i + seg_len:]

                    src_old_dist = _route_dist(src_route.sequence, problem)

                    for dst_k, dst_route in enumerate(routes):
                        dst_vehicle = problem.vehicles[dst_k]
                        if not dst_vehicle.available:
                            continue

                        # Capacity check for inter-route moves
                        if dst_k != src_k:
                            if dst_route.total_demand + block_demand > dst_vehicle.capacity + 1e-9:
                                continue

                        target_seq = rem_src_seq if dst_k == src_k else dst_route.sequence
                        dst_old_dist = _route_dist(dst_route.sequence, problem) if dst_k != src_k else src_old_dist

                        # Try all insertion positions
                        best_insertion_pos = -1
                        best_delta = -1e-9

                        for pos in range(len(target_seq) + 1):
                            if dst_k == src_k and pos == i:
                                continue  # Same position, no change

                            cand_seq = target_seq[:pos] + block + target_seq[pos:]
                            cand_dist = _route_dist(cand_seq, problem)

                            if dst_k == src_k:
                                delta = cand_dist - src_old_dist
                            else:
                                rem_src_dist = _route_dist(rem_src_seq, problem)
                                delta = (rem_src_dist + cand_dist) - (src_old_dist + dst_old_dist)

                            if delta < best_delta:
                                best_delta = delta
                                best_insertion_pos = pos

                        if best_insertion_pos >= 0:
                            # Apply the move
                            if dst_k == src_k:
                                src_route.sequence = (
                                    rem_src_seq[:best_insertion_pos]
                                    + block
                                    + rem_src_seq[best_insertion_pos:]
                                )
                            else:
                                src_route.sequence = rem_src_seq
                                src_route.total_demand -= block_demand
                                dst_route.sequence = (
                                    dst_route.sequence[:best_insertion_pos]
                                    + block
                                    + dst_route.sequence[best_insertion_pos:]
                                )
                                dst_route.total_demand += block_demand

                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break

    recompute_route_totals(routes, problem)
    return routes


# ---------------------------------------------------------------------------
# 3. Relocate: Move one customer to cheapest feasible position
# ---------------------------------------------------------------------------

def relocate_ls(routes: list[Route], problem: "VRPProblem") -> list[Route]:
    """Move each customer to its cheapest feasible position across all routes."""
    routes = [copy.copy(r) for r in routes]
    for r in routes:
        r.sequence = r.sequence[:]

    improved = True
    while improved:
        improved = False
        for src_k, src_route in enumerate(routes):
            if src_route.is_empty():
                continue
            for ci, cust_idx in enumerate(list(src_route.sequence)):
                cust = problem.customers[cust_idx - 1]
                src_prev = src_route.sequence[ci - 1] if ci > 0 else 0
                src_next = src_route.sequence[ci + 1] if ci < len(src_route.sequence) - 1 else 0
                removal_gain = (
                    problem.distance(src_prev, cust_idx)
                    + problem.distance(cust_idx, src_next)
                    - problem.distance(src_prev, src_next)
                )

                best_delta = -1e-9
                best_dst_k = -1
                best_pos = -1

                for dst_k, dst_route in enumerate(routes):
                    vehicle = problem.vehicles[dst_k]
                    if not vehicle.available:
                        continue

                    if dst_k == src_k:
                        tmp_seq = [x for x in src_route.sequence if x != cust_idx]
                    else:
                        tmp_seq = dst_route.sequence[:]

                    extra_load = cust.demand if dst_k != src_k else 0.0
                    if dst_route.total_demand + extra_load > vehicle.capacity + 1e-9:
                        continue

                    insertion_cost_val, pos = _insertion_cost(cust_idx, tmp_seq, problem)
                    if insertion_cost_val == float("inf"):
                        continue
                    delta = insertion_cost_val - removal_gain
                    if delta < best_delta:
                        best_delta = delta
                        best_dst_k = dst_k
                        best_pos = pos

                if best_dst_k >= 0:
                    src_route.sequence.remove(cust_idx)
                    src_route.total_demand -= cust.demand
                    if best_dst_k != src_k:
                        dst_route = routes[best_dst_k]
                        dst_route.sequence.insert(best_pos, cust_idx)
                        dst_route.total_demand += cust.demand
                    else:
                        src_route.sequence.insert(best_pos, cust_idx)
                    improved = True
                    break
            if improved:
                break

    recompute_route_totals(routes, problem)
    return routes


# ---------------------------------------------------------------------------
# 4. Swap: Exchange pairs of customers
# ---------------------------------------------------------------------------

def swap_ls(routes: list[Route], problem: "VRPProblem") -> list[Route]:
    """Swap pairs of customers (intra or inter-route) if it reduces total distance."""
    routes = [copy.copy(r) for r in routes]
    for r in routes:
        r.sequence = r.sequence[:]

    improved = True
    while improved:
        improved = False
        for i, route_a in enumerate(routes):
            for j, route_b in enumerate(routes):
                if i > j:
                    continue
                for pi, ca_idx in enumerate(route_a.sequence):
                    ca = problem.customers[ca_idx - 1]
                    start_j = pi + 1 if i == j else 0
                    for pj, cb_idx in enumerate(route_b.sequence[start_j:], start=start_j):
                        cb = problem.customers[cb_idx - 1]
                        if i != j:
                            new_a_demand = route_a.total_demand - ca.demand + cb.demand
                            new_b_demand = route_b.total_demand - cb.demand + ca.demand
                            if (new_a_demand > problem.vehicles[i].capacity + 1e-9 or
                                    new_b_demand > problem.vehicles[j].capacity + 1e-9):
                                continue

                        delta = _swap_delta(
                            route_a.sequence, pi, route_b.sequence, pj, problem, i == j
                        )
                        if delta < -1e-9:
                            route_a.sequence[pi] = cb_idx
                            route_b.sequence[pj] = ca_idx
                            if i != j:
                                route_a.total_demand = route_a.total_demand - ca.demand + cb.demand
                                route_b.total_demand = route_b.total_demand - cb.demand + ca.demand
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break

    recompute_route_totals(routes, problem)
    return routes


def _swap_delta(seq_a, pi, seq_b, pj, problem, intra_route):
    """Compute cost change from swapping seq_a[pi] with seq_b[pj]."""
    ca = seq_a[pi]
    cb = seq_b[pj]

    def prev_node(seq, idx):
        return seq[idx - 1] if idx > 0 else 0

    def next_node(seq, idx):
        return seq[idx + 1] if idx < len(seq) - 1 else 0

    if intra_route and abs(pi - pj) == 1:
        lo, hi = min(pi, pj), max(pi, pj)
        before = prev_node(seq_a, lo)
        after = next_node(seq_a, hi)
        old = (problem.distance(before, seq_a[lo])
               + problem.distance(seq_a[lo], seq_a[hi])
               + problem.distance(seq_a[hi], after))
        new = (problem.distance(before, seq_a[hi])
               + problem.distance(seq_a[hi], seq_a[lo])
               + problem.distance(seq_a[lo], after))
        return new - old

    pa_prev, pa_next = prev_node(seq_a, pi), next_node(seq_a, pi)
    pb_prev, pb_next = prev_node(seq_b, pj), next_node(seq_b, pj)

    old_cost = (
        problem.distance(pa_prev, ca) + problem.distance(ca, pa_next)
        + problem.distance(pb_prev, cb) + problem.distance(cb, pb_next)
    )
    new_cost = (
        problem.distance(pa_prev, cb) + problem.distance(cb, pa_next)
        + problem.distance(pb_prev, ca) + problem.distance(ca, pb_next)
    )
    return new_cost - old_cost


# ---------------------------------------------------------------------------
# 5. 2-opt* (Inter-Route Tail Swap)
# ---------------------------------------------------------------------------

def two_opt_star(routes: list[Route], problem: "VRPProblem") -> list[Route]:
    """Apply inter-route 2-opt* (swapping route tails between vehicles).

    For route A and route B:
        Route A: (0, a_1, ..., a_i, a_{i+1}, ..., a_m, 0)
        Route B: (0, b_1, ..., b_j, b_{j+1}, ..., b_n, 0)

    Try reconnecting:
        Case 1: (0..a_i) + (b_{j+1}..0) and (0..b_j) + (a_{i+1}..0)
        Case 2: (0..a_i) + reversed(0..b_j) etc.

    Accept if valid capacity and reduces total distance.
    """
    routes = [copy.copy(r) for r in routes]
    for r in routes:
        r.sequence = r.sequence[:]

    improved = True
    while improved:
        improved = False
        n_routes = len(routes)
        for i in range(n_routes - 1):
            route_a = routes[i]
            veh_a = problem.vehicles[i]
            if not veh_a.available:
                continue

            for j in range(i + 1, n_routes):
                route_b = routes[j]
                veh_b = problem.vehicles[j]
                if not veh_b.available:
                    continue

                if not route_a.sequence and not route_b.sequence:
                    continue

                seq_a = route_a.sequence
                seq_b = route_b.sequence
                curr_dist_sum = _route_dist(seq_a, problem) + _route_dist(seq_b, problem)

                best_delta = -1e-9
                best_new_a = None
                best_new_b = None

                # Cut points in route_a: split into seq_a[:cut_a] and seq_a[cut_a:]
                for cut_a in range(len(seq_a) + 1):
                    prefix_a = seq_a[:cut_a]
                    suffix_a = seq_a[cut_a:]
                    dem_prefix_a = _sequence_demand(prefix_a, problem)
                    dem_suffix_a = _sequence_demand(suffix_a, problem)

                    for cut_b in range(len(seq_b) + 1):
                        prefix_b = seq_b[:cut_b]
                        suffix_b = seq_b[cut_b:]
                        dem_prefix_b = _sequence_demand(prefix_b, problem)
                        dem_suffix_b = _sequence_demand(suffix_b, problem)

                        # Option 1: cross suffixes
                        cand_a1 = prefix_a + suffix_b
                        cand_b1 = prefix_b + suffix_a
                        if (dem_prefix_a + dem_suffix_b <= veh_a.capacity + 1e-9 and
                                dem_prefix_b + dem_suffix_a <= veh_b.capacity + 1e-9):
                            dist1 = _route_dist(cand_a1, problem) + _route_dist(cand_b1, problem)
                            delta1 = dist1 - curr_dist_sum
                            if delta1 < best_delta:
                                best_delta = delta1
                                best_new_a = cand_a1
                                best_new_b = cand_b1

                        # Option 2: reverse cross (prefix_a + reversed(prefix_b))
                        cand_a2 = prefix_a + prefix_b[::-1]
                        cand_b2 = suffix_a[::-1] + suffix_b
                        if (dem_prefix_a + dem_prefix_b <= veh_a.capacity + 1e-9 and
                                dem_suffix_a + dem_suffix_b <= veh_b.capacity + 1e-9):
                            dist2 = _route_dist(cand_a2, problem) + _route_dist(cand_b2, problem)
                            delta2 = dist2 - curr_dist_sum
                            if delta2 < best_delta:
                                best_delta = delta2
                                best_new_a = cand_a2
                                best_new_b = cand_b2

                if best_new_a is not None and best_new_b is not None:
                    route_a.sequence = best_new_a
                    route_b.sequence = best_new_b
                    improved = True
                    break
            if improved:
                break

    recompute_route_totals(routes, problem)
    return routes


# ---------------------------------------------------------------------------
# 6. CROSS-Exchange: Swap sub-segments between two routes
# ---------------------------------------------------------------------------

def cross_exchange(
    routes: list[Route],
    problem: "VRPProblem",
    max_len: int = 2,
) -> list[Route]:
    """Apply CROSS-Exchange: swap sub-segments of length up to max_len between routes.

    Segment A in route i (length 1..max_len) is exchanged with
    Segment B in route j (length 1..max_len).
    """
    routes = [copy.copy(r) for r in routes]
    for r in routes:
        r.sequence = r.sequence[:]

    improved = True
    while improved:
        improved = False
        n_routes = len(routes)
        for i in range(n_routes - 1):
            route_a = routes[i]
            veh_a = problem.vehicles[i]
            if not veh_a.available or not route_a.sequence:
                continue

            for j in range(i + 1, n_routes):
                route_b = routes[j]
                veh_b = problem.vehicles[j]
                if not veh_b.available or not route_b.sequence:
                    continue

                curr_dist_sum = _route_dist(route_a.sequence, problem) + _route_dist(route_b.sequence, problem)

                best_delta = -1e-9
                best_new_a = None
                best_new_b = None

                seq_a = route_a.sequence
                seq_b = route_b.sequence

                for len_a in range(1, min(max_len, len(seq_a)) + 1):
                    for idx_a in range(len(seq_a) - len_a + 1):
                        seg_a = seq_a[idx_a:idx_a + len_a]
                        dem_a = _sequence_demand(seg_a, problem)

                        for len_b in range(1, min(max_len, len(seq_b)) + 1):
                            for idx_b in range(len(seq_b) - len_b + 1):
                                seg_b = seq_b[idx_b:idx_b + len_b]
                                dem_b = _sequence_demand(seg_b, problem)

                                # Capacity feasibility
                                new_dem_a = route_a.total_demand - dem_a + dem_b
                                new_dem_b = route_b.total_demand - dem_b + dem_a
                                if (new_dem_a > veh_a.capacity + 1e-9 or
                                        new_dem_b > veh_b.capacity + 1e-9):
                                    continue

                                cand_a = seq_a[:idx_a] + seg_b + seq_a[idx_a + len_a:]
                                cand_b = seq_b[:idx_b] + seg_a + seq_b[idx_b + len_b:]

                                cand_dist = _route_dist(cand_a, problem) + _route_dist(cand_b, problem)
                                delta = cand_dist - curr_dist_sum

                                if delta < best_delta:
                                    best_delta = delta
                                    best_new_a = cand_a
                                    best_new_b = cand_b

                if best_new_a is not None and best_new_b is not None:
                    route_a.sequence = best_new_a
                    route_b.sequence = best_new_b
                    improved = True
                    break
            if improved:
                break

    recompute_route_totals(routes, problem)
    return routes


# Backwards compatibility alias
def exchange_ls(routes: list[Route], problem: "VRPProblem") -> list[Route]:
    """Exchange operator (alias for cross_exchange)."""
    return cross_exchange(routes, problem)


# ---------------------------------------------------------------------------
# 7. Variable Neighborhood Descent (VND)
# ---------------------------------------------------------------------------

def variable_neighborhood_descent(
    routes: list[Route],
    problem: "VRPProblem",
    max_vnd_iterations: int = 5,
) -> list[Route]:
    """Variable Neighborhood Descent (VND) exploring multiple neighborhoods.

    Neighborhood sequence:
        N1: 2-opt (intra-route)
        N2: Or-opt (intra & inter blocks 1..3)
        N3: Relocate (cheapest insertion)
        N4: Swap (pairwise exchange)
        N5: 2-opt* (inter-route tail swap)
        N6: CROSS-Exchange (block exchange)

    Strategy:
        Whenever an operator achieves an improvement, reset back to N1.
        Terminate when no operator can improve the current solution.
    """
    neighborhoods = [
        ("two_opt", two_opt),
        ("or_opt", or_opt),
        ("relocate", relocate_ls),
        ("swap", swap_ls),
        ("two_opt_star", two_opt_star),
        ("cross_exchange", cross_exchange),
    ]

    curr_routes = routes
    recompute_route_totals(curr_routes, problem)
    best_dist = sum(r.total_distance for r in curr_routes)

    for _ in range(max_vnd_iterations):
        k = 0
        overall_improved = False
        while k < len(neighborhoods):
            name, operator = neighborhoods[k]
            cand_routes = operator(curr_routes, problem)
            cand_dist = sum(r.total_distance for r in cand_routes)

            if cand_dist < best_dist - 1e-8:
                curr_routes = cand_routes
                best_dist = cand_dist
                overall_improved = True
                k = 0  # Loop back to finest neighborhood N1
            else:
                k += 1

        if not overall_improved:
            break

    recompute_route_totals(curr_routes, problem)
    return curr_routes


# ---------------------------------------------------------------------------
# 8. Master Runner
# ---------------------------------------------------------------------------

def run_all_ls(routes: list[Route], problem: "VRPProblem") -> list[Route]:
    """Master local search runner executing full Variable Neighborhood Descent (VND)."""
    return variable_neighborhood_descent(routes, problem)
