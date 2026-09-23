"""
benchmarks/bhopal_generator.py
==============================
Synthetic Bhopal-network CVRP instances for the Category-B benchmark.

These are NOT compared directly against CVRPLIB instances — they are a
separate experiment family showing practical relevance to Bhopal's
transportation context (Section 18.3).

Bhopal coordinate bounding box (approximate):
    Lat: 23.15 – 23.35  (≈ 22 km N-S)
    Lon: 77.35 – 77.55  (≈ 20 km E-W)

Traffic patterns are modelled as time-of-day multipliers.
Road closures and incidents are injected via TrafficIncident objects.
"""

from optimization.problem import VRPProblem
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Bhopal area reference points (approximate lat/lon → local km coordinates)
# ---------------------------------------------------------------------------

BHOPAL_LANDMARKS = {
    "New_Market":       (23.233, 77.414),
    "MP_Nagar":         (23.231, 77.439),
    "Habibganj":        (23.232, 77.463),
    "AIIMS":            (23.198, 77.424),
    "TT_Nagar":         (23.240, 77.410),
    "Arera_Colony":     (23.213, 77.438),
    "Shahpura":         (23.193, 77.456),
    "Kolar_Road":       (23.167, 77.433),
    "Berasia_Road":     (23.278, 77.418),
    "Misrod":           (23.167, 77.488),
    "Mandideep":        (23.099, 77.529),
    "Hoshangabad_Rd":   (23.199, 77.381),
    "Govindpura":       (23.266, 77.488),
    "Bhopal_Station":   (23.269, 77.404),
    "DB_City_Mall":     (23.218, 77.440),
    "Depot_Central":    (23.235, 77.430),  # depot
}


def _latlon_to_km(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    """Convert lat/lon to local km coordinates relative to a reference point."""
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians(ref_lat))
    x = (lon - ref_lon) * km_per_deg_lon
    y = (lat - ref_lat) * km_per_deg_lat
    return x, y


def generate_bhopal_instance(
    n_customers: int = 20,
    n_vehicles: int = 3,
    capacity: float = 100.0,
    seed: int = 42,
    traffic_scenario: str = "normal",
    include_time_windows: bool = False,
) -> "VRPProblem":
    """Generate a synthetic Bhopal CVRP instance.

    Parameters
    ----------
    n_customers : int        Number of delivery points.
    n_vehicles : int
    capacity : float         Vehicle load capacity.
    seed : int               Random seed for reproducibility.
    traffic_scenario : str   "normal" | "morning_peak" | "evening_peak" |
                             "congested" | "closure"
    include_time_windows : bool

    Returns
    -------
    VRPProblem
    """
    from optimization.entities import Customer, Vehicle, TrafficIncident, EdgeState
    from optimization.problem import VRPProblem

    rng = np.random.default_rng(seed)

    # Reference: depot at DB_City_Mall
    depot_lat, depot_lon = BHOPAL_LANDMARKS["Depot_Central"]
    ref_lat, ref_lon = depot_lat, depot_lon

    depot_x, depot_y = _latlon_to_km(depot_lat, depot_lon, ref_lat, ref_lon)

    # Cluster customers around known landmarks + random spread
    landmark_coords = [
        _latlon_to_km(lat, lon, ref_lat, ref_lon)
        for lat, lon in BHOPAL_LANDMARKS.values()
        if (lat, lon) != (depot_lat, depot_lon)
    ]

    customers = []
    for i in range(n_customers):
        if i < len(landmark_coords):
            lx, ly = landmark_coords[i]
            # Small jitter around landmark
            cx = lx + rng.normal(0, 0.5)
            cy = ly + rng.normal(0, 0.5)
        else:
            # Random in Bhopal bounding box (roughly ±11km from depot)
            cx = rng.uniform(-10.0, 10.0)
            cy = rng.uniform(-10.0, 10.0)

        avg_demand = capacity * n_vehicles / (n_customers * 1.5)
        demand = float(rng.uniform(avg_demand * 0.5, avg_demand * 1.5))

        tw_open, tw_close = 0.0, float("inf")
        if include_time_windows:
            tw_open = float(rng.uniform(0, 180))
            tw_close = tw_open + float(rng.uniform(60, 240))

        customers.append(
            Customer(
                id=i,
                x=float(cx),
                y=float(cy),
                demand=demand,
                service_time=float(rng.uniform(3.0, 15.0)),
                time_window_open=tw_open,
                time_window_close=tw_close,
                priority=int(rng.integers(1, 6)),
            )
        )

    vehicles = [Vehicle(id=k, capacity=capacity) for k in range(n_vehicles)]

    # Distance matrix (Euclidean km)
    n = n_customers + 1
    all_x = np.array([depot_x] + [c.x for c in customers])
    all_y = np.array([depot_y] + [c.y for c in customers])
    dist_mat = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dist_mat[i, j] = math.hypot(all_x[i] - all_x[j], all_y[i] - all_y[j])

    # Traffic scenario multipliers
    # NOTE: these are for standalone benchmark generation only.
    # In production, multipliers come from the traffic module (Member 2).
    scenario_multipliers = {
        "normal":       1.0,
        "morning_peak": 1.6,
        "evening_peak": 1.8,
        "congested":    2.2,
        "closure":      None,  # handled below
    }
    base_speed_kmh = 30.0
    mult = scenario_multipliers.get(traffic_scenario, 1.0)

    if mult is None:
        mult = 1.0  # default for closure scenario

    tt_mat = dist_mat / (base_speed_kmh / mult) * 60.0  # minutes

    # Traffic state for closure scenario
    traffic_state = {}
    edge_multipliers = {}
    if traffic_scenario == "closure":
        # Close a few random edges (simulate road closures)
        n_closures = max(1, n // 5)
        for _ in range(n_closures):
            a = int(rng.integers(0, n))
            b = int(rng.integers(0, n))
            if a != b:
                edge_key = f"{a}_{b}"
                traffic_state[edge_key] = EdgeState.CLOSED
                edge_multipliers[edge_key] = float("inf")

    problem = VRPProblem(
        problem_type="cvrp" if not include_time_windows else "vrptw",
        customers=customers,
        vehicles=vehicles,
        depot_id=0,
        depot_x=float(depot_x),
        depot_y=float(depot_y),
        distance_matrix=dist_mat,
        travel_time_matrix=tt_mat,
        traffic_state={k: v for k, v in traffic_state.items()},
        edge_travel_multipliers=edge_multipliers,
        enforce_time_windows=include_time_windows,
    )
    # Tag scenario for reporting
    problem._scenario = traffic_scenario  # type: ignore[attr-defined]
    return problem


def generate_scalability_suite(
    sizes: list[int] = None,
    n_vehicles_fn=None,
    capacity: float = 150.0,
    seed_base: int = 100,
) -> list[tuple[int, "VRPProblem"]]:
    """Generate a suite of instances for scalability experiments.

    Returns list of (n_customers, problem) tuples.
    """
    if sizes is None:
        sizes = [10, 25, 50, 100, 200, 500]
    if n_vehicles_fn is None:
        # Rule of thumb: ceil(n_customers / 15) vehicles
        n_vehicles_fn = lambda n: max(2, math.ceil(n / 15))

    suite = []
    for i, n in enumerate(sizes):
        problem = generate_bhopal_instance(
            n_customers=n,
            n_vehicles=n_vehicles_fn(n),
            capacity=capacity,
            seed=seed_base + i,
        )
        suite.append((n, problem))
    return suite
