"""
optimization/problem.py
=======================
VRPProblem: the complete routing problem instance.

This is the single truth about the problem being solved.
All optimisers, decoders, fitness calculators, and repair operators
receive a VRPProblem — they never hold their own copies of matrices.

Two-level architecture (Section 3)
-----------------------------------
Road-level shortest paths → travel-time/distance matrices → QPSO.
VRPProblem operates at the *customer/vehicle* level, not the road-graph level.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .entities import Customer, Vehicle, EdgeState, TrafficIncident
from .config import ObjectiveWeights


# ---------------------------------------------------------------------------
# Charging station (EV extension)
# ---------------------------------------------------------------------------

@dataclass
class ChargingStation:
    """A charging point that EV routes may visit."""
    id: int
    node_id: int
    x: float
    y: float
    charging_rate_kwh_per_min: float  # How fast it charges
    available: bool = True


# ---------------------------------------------------------------------------
# VRPProblem
# ---------------------------------------------------------------------------

class VRPProblem:
    """Complete Vehicle Routing Problem instance.

    Supports:
    - CVRP (Capacitated VRP)
    - VRPTW (VRP with Time Windows)
    - Time-dependent travel times
    - EV range constraints
    - Road closures / incident injection

    Parameters
    ----------
    problem_type : str          "cvrp" | "vrptw" | "ev_vrp"
    customers : list[Customer]  All delivery locations (depot excluded).
    vehicles : list[Vehicle]
    depot_id : int              Customer-array index 0 is always the depot.
    depot_x, depot_y : float   Depot coordinates.
    distance_matrix : np.ndarray  Shape (N+1, N+1), N = #customers.
                                  Index 0 = depot.
    travel_time_matrix : np.ndarray | list[np.ndarray]
        Static: shape (N+1, N+1).
        Time-dependent: list of matrices keyed by time-slot index.
        Access via self.travel_time(i, j, t).
    time_slots : list[float]    Breakpoints for time-dependent matrices (minutes).
    traffic_state : dict        edge_id → EdgeState (injected by traffic module).
    edge_travel_multipliers : dict  edge_id → float (injected by traffic module).
    charging_stations : list[ChargingStation]  (EV only)
    enforce_time_windows : bool
    allow_waiting : bool        Vehicles may wait at early arrival.
    objective_weights : ObjectiveWeights
    """

    def __init__(
        self,
        problem_type: str,
        customers: list[Customer],
        vehicles: list[Vehicle],
        depot_id: int,
        depot_x: float,
        depot_y: float,
        distance_matrix: np.ndarray,
        travel_time_matrix,   # np.ndarray or list[np.ndarray]
        time_slots: Optional[list[float]] = None,
        traffic_state: Optional[dict] = None,
        edge_travel_multipliers: Optional[dict] = None,
        charging_stations: Optional[list] = None,
        enforce_time_windows: bool = True,
        allow_waiting: bool = True,
        objective_weights: Optional[ObjectiveWeights] = None,
    ) -> None:
        self.problem_type = problem_type.lower()
        self.customers = customers
        self.vehicles = vehicles
        self.depot_id = depot_id
        self.depot_x = depot_x
        self.depot_y = depot_y
        self.n_customers = len(customers)
        self.n_vehicles = len(vehicles)

        # Matrices — stored as float64 numpy arrays
        self.distance_matrix = np.asarray(distance_matrix, dtype=np.float64)
        if isinstance(travel_time_matrix, list):
            self._time_dependent = True
            self.travel_time_matrices = [
                np.asarray(m, dtype=np.float64) for m in travel_time_matrix
            ]
            self.travel_time_matrix = self.travel_time_matrices[0]  # default
        else:
            self._time_dependent = False
            self.travel_time_matrix = np.asarray(travel_time_matrix, dtype=np.float64)
            self.travel_time_matrices = [self.travel_time_matrix]
        self.time_slots = time_slots or [0.0]

        # Traffic (injected by Member 2 — never generated here)
        self._traffic_state: dict = traffic_state or {}
        self._edge_multipliers: dict = edge_travel_multipliers or {}

        # EV extension
        self.charging_stations = charging_stations or []
        self.is_ev = any(v.is_ev() for v in vehicles)

        # Constraint flags
        self.enforce_time_windows = enforce_time_windows
        self.allow_waiting = allow_waiting

        # Objective weights (can be overridden per request)
        self.objective_weights = objective_weights or ObjectiveWeights.balanced()

        # Pre-computed aggregates
        self.total_demand = sum(c.demand for c in customers)
        self.total_capacity = sum(v.capacity for v in vehicles if v.available)

        self._validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        n = self.n_customers + 1  # +1 for depot (index 0)
        if self.distance_matrix.shape != (n, n):
            raise ValueError(
                f"distance_matrix must be ({n},{n}), got {self.distance_matrix.shape}."
            )
        if self.travel_time_matrix.shape != (n, n):
            raise ValueError(
                f"travel_time_matrix must be ({n},{n}), got {self.travel_time_matrix.shape}."
            )

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------

    def customer_index(self, customer_id: int) -> int:
        """Convert customer id → matrix index (depot=0, customers=1..N)."""
        return customer_id + 1  # depot has matrix index 0

    def matrix_index(self, node: int) -> int:
        """node=0 is depot; nodes 1..N are customers 0..N-1 by convention.
        We use: depot→0, customer k (0-based)→k+1.
        """
        return node  # caller manages offset

    # ------------------------------------------------------------------
    # Travel time (time-dependent)
    # ------------------------------------------------------------------

    def _time_slot_index(self, t: float) -> int:
        """Return the time-slot index for time t (minutes)."""
        if len(self.time_slots) == 1:
            return 0
        for idx in range(len(self.time_slots) - 1, -1, -1):
            if t >= self.time_slots[idx]:
                return idx
        return 0

    def travel_time(self, i: int, j: int, t: float = 0.0) -> float:
        """Travel time from matrix-index i to j, departing at time t.

        For time-dependent matrices, picks the correct slot.
        Applies edge-level multipliers injected by the traffic module.
        Returns inf if any edge on the path is CLOSED.
        """
        if i == j:
            return 0.0
        slot = self._time_slot_index(t)
        base_time = self.travel_time_matrices[slot][i, j]
        # Apply global traffic multiplier for this edge pair if provided
        edge_key = f"{i}_{j}"
        multiplier = self._edge_multipliers.get(edge_key, 1.0)
        return base_time * multiplier

    def distance(self, i: int, j: int) -> float:
        """Euclidean distance from matrix-index i to j (km)."""
        return float(self.distance_matrix[i, j])

    def edge_available(self, i: int, j: int) -> bool:
        """Return True if the road between nodes i and j is not CLOSED."""
        edge_key = f"{i}_{j}"
        state = self._traffic_state.get(edge_key, EdgeState.OPEN)
        return state != EdgeState.CLOSED

    # ------------------------------------------------------------------
    # Traffic update API (called by reoptimization.py)
    # ------------------------------------------------------------------

    def apply_incident(self, incident: TrafficIncident) -> None:
        """Ingest a traffic incident from the traffic module.

        The ``incident.travel_time_multiplier`` is set by the traffic
        module — this optimizer never computes severity multipliers.
        """
        edge_key = incident.edge_id
        self._traffic_state[edge_key] = incident.status
        if incident.status == EdgeState.CLOSED:
            self._edge_multipliers[edge_key] = float("inf")
        else:
            self._edge_multipliers[edge_key] = incident.travel_time_multiplier

    def clear_incident(self, edge_id: str) -> None:
        """Remove an incident (road re-opened or congestion cleared)."""
        self._traffic_state.pop(edge_id, None)
        self._edge_multipliers.pop(edge_id, None)

    # ------------------------------------------------------------------
    # Feasibility pre-check
    # ------------------------------------------------------------------

    def is_feasible_instance(self) -> tuple[bool, str]:
        """Quick pre-check before launching the optimizer.

        Returns (True, '') or (False, reason_string).
        """
        if not self.vehicles:
            return False, "No vehicles available."
        available = [v for v in self.vehicles if v.available]
        if not available:
            return False, "All vehicles are unavailable."
        if self.total_demand > self.total_capacity:
            return (
                False,
                f"Total demand ({self.total_demand:.1f}) exceeds available "
                f"vehicle capacity ({self.total_capacity:.1f}).",
            )
        if self.n_customers == 0:
            return False, "No customers to serve."
        return True, ""

    # ------------------------------------------------------------------
    # Serialisation helpers (for the API contract)
    # ------------------------------------------------------------------

    def customer_list(self) -> list[dict]:
        return [
            {
                "id": c.id,
                "x": c.x,
                "y": c.y,
                "demand": c.demand,
                "service_time": c.service_time,
                "time_window": [c.time_window_open, c.time_window_close],
                "priority": c.priority,
            }
            for c in self.customers
        ]

    def vehicle_list(self) -> list[dict]:
        return [
            {
                "id": v.id,
                "capacity": v.capacity,
                "max_duration": v.max_duration,
                "available": v.available,
            }
            for v in self.vehicles
        ]

    # ------------------------------------------------------------------
    # Helpers used by baselines and tests
    # ------------------------------------------------------------------

    def compute_route_distance(self, sequence: list[int]) -> float:
        """Total distance for a route including depot at start/end.

        sequence: list of matrix indices (0=depot, 1..N=customers).
        """
        total = 0.0
        full = [0] + sequence + [0]
        for a, b in zip(full, full[1:]):
            total += self.distance(a, b)
        return total

    def compute_route_time(self, sequence: list[int], start_time: float = 0.0) -> tuple[float, list[float]]:
        """Total travel + service time and arrival times for a sequence.

        Returns (total_time, arrival_times_list).
        Arrival times are at each customer in ``sequence`` (excluding depot).
        """
        arrival_times = []
        t = start_time
        prev = 0  # depot
        for node in sequence:
            t += self.travel_time(prev, node, t)
            arrival_times.append(t)
            # Wait if early (if allowed)
            customer = self.customers[node - 1]  # node 1 → customers[0]
            if self.allow_waiting:
                t = max(t, customer.time_window_open)
            t += customer.service_time
            prev = node
        # Return to depot
        t += self.travel_time(prev, 0, t)
        return t - start_time, arrival_times

    # ------------------------------------------------------------------
    # Factory: build from dict (API contract / JSON input)
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict, weights: Optional[ObjectiveWeights] = None) -> "VRPProblem":
        """Construct from the JSON request body (Section 4 of spec).

        Expected keys: problem_type, nodes, vehicles, depot, customers,
        travel_time_matrix, distance_matrix, traffic_state, constraints,
        objective_weights.
        """
        customers = [
            Customer(
                id=c["id"],
                x=c.get("x", 0.0),
                y=c.get("y", 0.0),
                demand=c.get("demand", 0.0),
                service_time=c.get("service_time", 0.0),
                time_window_open=c.get("time_window", [0, float("inf")])[0],
                time_window_close=c.get("time_window", [0, float("inf")])[1],
                priority=c.get("priority", 1),
                node_id=c.get("node_id"),
            )
            for c in data.get("customers", [])
        ]

        vehicles = [
            Vehicle(
                id=v["id"],
                capacity=v["capacity"],
                max_duration=v.get("max_duration", 0.0),
                start_node=data.get("depot", 0),
                speed_factor=v.get("speed_factor", 1.0),
                available=v.get("available", True),
                battery_capacity=v.get("battery_capacity", 0.0),
                current_soc=v.get("current_soc", 1.0),
                energy_per_km=v.get("energy_per_km", 0.0),
            )
            for v in data.get("vehicles", [])
        ]

        traffic = data.get("traffic_state", {})
        traffic_state = {k: EdgeState(v) for k, v in traffic.items()} if traffic else {}

        obj_weights = weights
        if obj_weights is None and "objective_weights" in data:
            obj_weights = ObjectiveWeights.from_dict(data["objective_weights"])

        depot_node = data.get("nodes", [{"x": 0.0, "y": 0.0}])[0]

        return cls(
            problem_type=data.get("problem_type", "cvrp"),
            customers=customers,
            vehicles=vehicles,
            depot_id=data.get("depot", 0),
            depot_x=depot_node.get("x", 0.0),
            depot_y=depot_node.get("y", 0.0),
            distance_matrix=np.array(data["distance_matrix"], dtype=np.float64),
            travel_time_matrix=np.array(data["travel_time_matrix"], dtype=np.float64),
            traffic_state=traffic_state,
            enforce_time_windows=data.get("constraints", {}).get("enforce_time_windows", True),
            allow_waiting=data.get("constraints", {}).get("allow_waiting", True),
            objective_weights=obj_weights or ObjectiveWeights.balanced(),
        )

    # ------------------------------------------------------------------
    # Factory: build synthetic CVRP for testing
    # ------------------------------------------------------------------

    @classmethod
    def random_cvrp(
        cls,
        n_customers: int = 10,
        n_vehicles: int = 3,
        capacity: float = 50.0,
        seed: int = 42,
        area_km: float = 50.0,
    ) -> "VRPProblem":
        """Generate a random CVRP instance for quick testing.

        Coordinates are sampled from [0, area_km] × [0, area_km].
        Travel time = Euclidean distance / average_speed (30 km/h).
        """
        rng = np.random.default_rng(seed)
        avg_speed = 30.0  # km/h

        # Depot at centre
        depot_x, depot_y = area_km / 2, area_km / 2

        # Customers
        xs = rng.uniform(0, area_km, n_customers)
        ys = rng.uniform(0, area_km, n_customers)
        avg_demand = capacity * n_vehicles / (n_customers * 1.5)
        demands = rng.uniform(avg_demand * 0.5, avg_demand * 1.5, n_customers)

        customers = [
            Customer(
                id=i,
                x=float(xs[i]),
                y=float(ys[i]),
                demand=float(demands[i]),
                service_time=rng.uniform(2.0, 10.0),
                priority=int(rng.integers(1, 6)),
            )
            for i in range(n_customers)
        ]

        vehicles = [
            Vehicle(id=k, capacity=capacity)
            for k in range(n_vehicles)
        ]

        # Build N+1 × N+1 matrices (index 0 = depot, 1..N = customers)
        all_x = np.array([depot_x] + [c.x for c in customers])
        all_y = np.array([depot_y] + [c.y for c in customers])
        n = n_customers + 1
        dist = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dist[i, j] = math.hypot(all_x[i] - all_x[j], all_y[i] - all_y[j])

        time_mat = dist / avg_speed * 60.0  # minutes

        return cls(
            problem_type="cvrp",
            customers=customers,
            vehicles=vehicles,
            depot_id=0,
            depot_x=depot_x,
            depot_y=depot_y,
            distance_matrix=dist,
            travel_time_matrix=time_mat,
        )
