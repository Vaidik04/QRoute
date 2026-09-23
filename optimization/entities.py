"""
optimization/entities.py
========================
Core data structures for the Q-TRANSIT NEXUS optimization engine.

These are pure data containers — no optimization logic here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Edge / Road status
# ---------------------------------------------------------------------------

class EdgeState(Enum):
    """Status of a road segment.

    Severity multipliers are applied by the traffic module (Member 2),
    never hardcoded inside the optimizer.
    """
    OPEN = "open"
    CLOSED = "closed"          # impassable — infinite cost
    CONGESTED = "congested"    # high congestion, multiplier from traffic module
    SLOW = "slow"              # moderate congestion
    CONSTRUCTION = "construction"  # partial closure / slow


# ---------------------------------------------------------------------------
# Customer (delivery/stop node)
# ---------------------------------------------------------------------------

@dataclass
class Customer:
    """Represents a customer / delivery location.

    Attributes
    ----------
    id : int
        Unique customer identifier (0 = depot is never a Customer).
    x, y : float
        Geographic coordinates (latitude / longitude or local projection).
    demand : float
        Load units required (packages, kg, litres, etc.).
    service_time : float
        Minutes spent servicing this customer after arrival.
    time_window_open : float
        Earliest acceptable arrival time (minutes from route start).
    time_window_close : float
        Latest acceptable arrival time (minutes from route start).
        If 0 and open == 0, time window is unconstrained.
    priority : int
        1 (low) – 10 (critical). Used in lateness cost:
        ``C_p = Σ priority_i × lateness_i``.
    node_id : int
        Corresponding road-network node id (used for path lookup).
    """
    id: int
    x: float
    y: float
    demand: float
    service_time: float = 0.0
    time_window_open: float = 0.0
    time_window_close: float = float("inf")
    priority: int = 1
    node_id: Optional[int] = None

    def has_time_window(self) -> bool:
        """Return True if this customer has an active time window constraint."""
        return self.time_window_close < float("inf")

    def __post_init__(self) -> None:
        if self.demand < 0:
            raise ValueError(f"Customer {self.id}: demand cannot be negative.")
        if self.time_window_open > self.time_window_close:
            raise ValueError(
                f"Customer {self.id}: time_window_open > time_window_close."
            )
        if not (1 <= self.priority <= 10):
            raise ValueError(
                f"Customer {self.id}: priority must be 1–10, got {self.priority}."
            )


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------

@dataclass
class Vehicle:
    """Represents a vehicle in the fleet.

    Attributes
    ----------
    id : int
        Unique vehicle identifier.
    capacity : float
        Maximum load the vehicle can carry.
    max_duration : float
        Maximum total route duration in minutes (0 = unconstrained).
    start_node : int
        Depot node id where the vehicle starts and ends.
    speed_factor : float
        Multiplier on travel times (1.0 = nominal).
    available : bool
        Whether the vehicle is available for dispatch.

    EV-extension fields (ignored unless problem.is_ev is True)
    -----------------------------------------------------------
    battery_capacity : float   kWh capacity.
    current_soc : float        State of charge fraction in [0, 1].
    energy_per_km : float      kWh consumed per km (average).
    min_soc : float            Minimum allowed SoC before charging required.
    """
    id: int
    capacity: float
    max_duration: float = 0.0        # 0 means unconstrained
    start_node: int = 0
    speed_factor: float = 1.0
    available: bool = True

    # EV extension
    battery_capacity: float = 0.0
    current_soc: float = 1.0
    energy_per_km: float = 0.0
    min_soc: float = 0.2

    def is_ev(self) -> bool:
        return self.battery_capacity > 0.0

    def usable_capacity(self) -> float:
        return self.capacity if self.available else 0.0

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError(f"Vehicle {self.id}: capacity must be positive.")
        if not (0.0 <= self.current_soc <= 1.0):
            raise ValueError(f"Vehicle {self.id}: current_soc must be in [0,1].")


# ---------------------------------------------------------------------------
# Route (result of decoding a particle)
# ---------------------------------------------------------------------------

@dataclass
class Route:
    """A single vehicle's route — the result of decoding a particle.

    Attributes
    ----------
    vehicle_id : int
    sequence : list[int]
        Customer ids visited in order. Does NOT include depot endpoints
        (depot is prepended/appended by the evaluator when computing cost).
    arrival_times : list[float]
        Arrival time at each customer in ``sequence`` (minutes from departure).
    departure_times : list[float]
        Departure time = arrival + service_time (or time_window_open if early).
    total_distance : float
    total_time : float          Minutes including service + waiting.
    total_demand : float
    feasible : bool             All hard constraints satisfied.
    violation_details : list[str]
        Human-readable list of violations (empty when feasible).
    """
    vehicle_id: int
    sequence: list[int] = field(default_factory=list)
    arrival_times: list[float] = field(default_factory=list)
    departure_times: list[float] = field(default_factory=list)
    total_distance: float = 0.0
    total_time: float = 0.0
    total_demand: float = 0.0
    feasible: bool = True
    violation_details: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return len(self.sequence) == 0

    def customer_count(self) -> int:
        return len(self.sequence)


# ---------------------------------------------------------------------------
# Incident / traffic event (ingested from Member 2 / traffic module)
# ---------------------------------------------------------------------------

@dataclass
class TrafficIncident:
    """A traffic event received from the traffic module.

    Severity multipliers (e.g. 1.8× for congestion) are set by the
    traffic module — never generated inside the optimizer.

    Attributes
    ----------
    edge_id : str
        Road segment identifier (e.g. "R17").
    status : EdgeState
        New status of the edge.
    travel_time_multiplier : float
        Factor applied to nominal travel time. 1.0 = no change,
        2.0 = twice as long. Source: traffic module.
    affected_at : float
        Simulation/real timestamp (minutes) when the incident begins.
    estimated_duration : float
        Expected duration of the incident in minutes (0 = unknown).
    """
    edge_id: str
    status: EdgeState
    travel_time_multiplier: float = 1.0
    affected_at: float = 0.0
    estimated_duration: float = 0.0

    def __post_init__(self) -> None:
        if self.travel_time_multiplier < 1.0:
            raise ValueError(
                "travel_time_multiplier < 1.0 makes travel faster — "
                "this should come from the traffic module, not be set here."
            )


# ---------------------------------------------------------------------------
# VehicleState (used during dynamic re-optimization)
# ---------------------------------------------------------------------------

@dataclass
class VehicleState:
    """Current state of a vehicle mid-route, used for re-optimization.

    Attributes
    ----------
    vehicle_id : int
    current_node : int
        The road-network node the vehicle is currently at or heading to.
    completed_customers : list[int]
        Customer ids already served (prefix — must not be changed).
    remaining_customers : list[int]
        Customer ids not yet served (suffix — subject to re-optimization).
    current_time : float
        Current clock time (minutes from route start).
    current_load : float
        Current remaining vehicle load.
    """
    vehicle_id: int
    current_node: int
    completed_customers: list[int] = field(default_factory=list)
    remaining_customers: list[int] = field(default_factory=list)
    current_time: float = 0.0
    current_load: float = 0.0
