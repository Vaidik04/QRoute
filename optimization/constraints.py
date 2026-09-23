"""
optimization/constraints.py
============================
Hard-constraint checkers for the Q-TRANSIT NEXUS routing engine.

Every checker returns a ConstraintResult so callers know *why* a
solution is infeasible, not just *that* it is.

Constraint set (Section 5.5):
1. Capacity       — Σ demand_i ≤ Q_k for each vehicle k
2. Time windows   — e_i ≤ arrival_i ≤ l_i
3. Vehicle avail  — vehicle must exist and be available
4. Road avail     — closed edges cannot be used
5. Coverage       — every customer served exactly once
6. Duration       — total route time ≤ vehicle.max_duration (if set)
7. EV range       — SOC must not drop below min_soc without charging
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .problem import VRPProblem
    from .entities import Route


@dataclass
class ConstraintResult:
    """Result of a constraint check."""
    feasible: bool
    violation_count: int = 0
    details: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.feasible = False
        self.violation_count += 1
        self.details.append(message)

    def merge(self, other: "ConstraintResult") -> None:
        if not other.feasible:
            self.feasible = False
            self.violation_count += other.violation_count
            self.details.extend(other.details)

    @classmethod
    def ok(cls) -> "ConstraintResult":
        return cls(feasible=True)


# ---------------------------------------------------------------------------
# Individual constraint checkers
# ---------------------------------------------------------------------------

def check_capacity(route: "Route", problem: "VRPProblem") -> ConstraintResult:
    """Vehicle must not carry more than its capacity."""
    result = ConstraintResult.ok()
    vehicle = problem.vehicles[route.vehicle_id]
    if route.total_demand > vehicle.capacity + 1e-9:
        result.add(
            f"Vehicle {route.vehicle_id}: demand {route.total_demand:.2f} "
            f"exceeds capacity {vehicle.capacity:.2f}."
        )
    return result


def check_time_windows(route: "Route", problem: "VRPProblem") -> ConstraintResult:
    """Every customer arrival must be within [time_window_open, time_window_close].

    Waiting is allowed when arrival is early (arrival < open).
    Lateness is always a violation.
    """
    result = ConstraintResult.ok()
    if not problem.enforce_time_windows:
        return result

    for seq_pos, (customer_idx, arrival) in enumerate(
        zip(route.sequence, route.arrival_times)
    ):
        customer = problem.customers[customer_idx - 1]  # matrix idx → customer
        if not customer.has_time_window():
            continue
        if arrival > customer.time_window_close + 1e-6:
            result.add(
                f"Vehicle {route.vehicle_id}, customer {customer.id}: "
                f"arrives at {arrival:.1f}min, window closes at "
                f"{customer.time_window_close:.1f}min "
                f"(late by {arrival - customer.time_window_close:.1f}min)."
            )
    return result


def check_road_availability(route: "Route", problem: "VRPProblem") -> ConstraintResult:
    """No closed edges may be used in the route."""
    result = ConstraintResult.ok()
    full_sequence = [0] + route.sequence + [0]  # include depot
    for a, b in zip(full_sequence, full_sequence[1:]):
        if not problem.edge_available(a, b):
            result.add(
                f"Vehicle {route.vehicle_id}: edge {a}→{b} is CLOSED."
            )
    return result


def check_vehicle_availability(route: "Route", problem: "VRPProblem") -> ConstraintResult:
    """Vehicle must exist and be marked available."""
    result = ConstraintResult.ok()
    if route.vehicle_id >= len(problem.vehicles):
        result.add(f"Vehicle {route.vehicle_id} does not exist.")
        return result
    vehicle = problem.vehicles[route.vehicle_id]
    if not vehicle.available:
        result.add(f"Vehicle {route.vehicle_id} is not available for dispatch.")
    return result


def check_duration(route: "Route", problem: "VRPProblem") -> ConstraintResult:
    """Route must not exceed vehicle.max_duration (if set > 0)."""
    result = ConstraintResult.ok()
    vehicle = problem.vehicles[route.vehicle_id]
    if vehicle.max_duration > 0 and route.total_time > vehicle.max_duration + 1e-6:
        result.add(
            f"Vehicle {route.vehicle_id}: route duration {route.total_time:.1f}min "
            f"exceeds max_duration {vehicle.max_duration:.1f}min."
        )
    return result


def check_ev_feasibility(route: "Route", problem: "VRPProblem") -> ConstraintResult:
    """EV battery must not drop below min_soc at any point.

    SOC simulation: SOC_next = SOC_current - energy_per_km × distance(i, j).
    If SOC_next < min_soc and no charging station is inserted, it's a violation.

    NOTE: This is a simplified feasibility check. Full EV route optimisation
    with charging-station insertion is handled by the decoder.
    """
    result = ConstraintResult.ok()
    if not problem.is_ev:
        return result

    vehicle = problem.vehicles[route.vehicle_id]
    if not vehicle.is_ev():
        return result

    soc = vehicle.current_soc * vehicle.battery_capacity  # kWh remaining
    full_sequence = [0] + route.sequence + [0]
    for a, b in zip(full_sequence, full_sequence[1:]):
        dist = problem.distance(a, b)
        energy_used = vehicle.energy_per_km * dist
        soc -= energy_used
        min_kwh = vehicle.min_soc * vehicle.battery_capacity
        if soc < min_kwh - 1e-6:
            result.add(
                f"Vehicle {route.vehicle_id} (EV): SOC drops to "
                f"{soc:.2f} kWh at edge {a}→{b}, below minimum "
                f"{min_kwh:.2f} kWh."
            )
    return result


def check_coverage(routes: list["Route"], problem: "VRPProblem") -> ConstraintResult:
    """Every customer must be served exactly once across all routes."""
    result = ConstraintResult.ok()
    served: dict[int, int] = {}  # customer_matrix_idx → count
    for route in routes:
        for cust_idx in route.sequence:
            served[cust_idx] = served.get(cust_idx, 0) + 1

    n = problem.n_customers
    expected = set(range(1, n + 1))  # matrix indices 1..N
    actual = set(served.keys())

    for cust_idx in expected - actual:
        customer = problem.customers[cust_idx - 1]
        result.add(f"Customer {customer.id} (matrix idx {cust_idx}) not served.")

    for cust_idx in actual - expected:
        result.add(f"Unknown customer matrix index {cust_idx} in routes.")

    for cust_idx, count in served.items():
        if count > 1:
            result.add(f"Customer matrix idx {cust_idx} served {count} times.")

    return result


# ---------------------------------------------------------------------------
# Full constraint check (all at once)
# ---------------------------------------------------------------------------

def check_all(
    routes: list["Route"],
    problem: "VRPProblem",
    check_coverage_flag: bool = True,
) -> ConstraintResult:
    """Run all hard constraints and return a merged ConstraintResult.

    Parameters
    ----------
    routes : list[Route]
    problem : VRPProblem
    check_coverage_flag : bool   Set False during partial/repair passes.
    """
    combined = ConstraintResult.ok()

    for route in routes:
        if route.is_empty():
            continue
        combined.merge(check_vehicle_availability(route, problem))
        combined.merge(check_capacity(route, problem))
        combined.merge(check_time_windows(route, problem))
        combined.merge(check_road_availability(route, problem))
        combined.merge(check_duration(route, problem))
        if problem.is_ev:
            combined.merge(check_ev_feasibility(route, problem))

    if check_coverage_flag:
        combined.merge(check_coverage(routes, problem))

    return combined


def count_violations(routes: list["Route"], problem: "VRPProblem") -> int:
    """Convenience function — returns total violation count."""
    return check_all(routes, problem).violation_count
