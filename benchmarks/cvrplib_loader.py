"""
benchmarks/cvrplib_loader.py
============================
Parser for CVRPLIB .vrp files (TSPLIB95 format).

Supported sections:
    NAME, COMMENT, DIMENSION, CAPACITY, NODE_COORD_SECTION,
    DEMAND_SECTION, DEPOT_SECTION, TIME_WINDOW_SECTION (optional)

Usage:
    problem = load_cvrplib("data/cvrplib/E-n22-k4.vrp")
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Optional

import numpy as np

# We import lazily to keep this module usable without the full optimization package
def _build_problem(customers, vehicles, depot_x, depot_y, dist_mat, tt_mat):
    from optimization.problem import VRPProblem
    return VRPProblem(
        problem_type="cvrp",
        customers=customers,
        vehicles=vehicles,
        depot_id=0,
        depot_x=depot_x,
        depot_y=depot_y,
        distance_matrix=dist_mat,
        travel_time_matrix=tt_mat,
    )


def load_cvrplib(filepath: str | Path) -> "VRPProblem":
    """Parse a CVRPLIB .vrp file and return a VRPProblem instance.

    Parameters
    ----------
    filepath : str or Path
        Path to the .vrp file.

    Returns
    -------
    VRPProblem
    """
    from optimization.entities import Customer, Vehicle

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"CVRPLIB file not found: {filepath}")

    text = filepath.read_text(encoding="utf-8", errors="ignore")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # --- Parse header fields ---
    meta = {}
    for line in lines:
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip().upper()] = val.strip()

    dimension = int(meta.get("DIMENSION", 0))
    capacity = float(meta.get("CAPACITY", 0))
    n_vehicles_hint = int(meta.get("VEHICLES", 0))

    # Try to infer vehicle count from filename (e.g. E-n22-k4 → 4 vehicles)
    if n_vehicles_hint == 0:
        match = re.search(r"-k(\d+)", filepath.stem, re.IGNORECASE)
        n_vehicles_hint = int(match.group(1)) if match else 5

    # --- Parse sections ---
    coords: dict[int, tuple[float, float]] = {}
    demands: dict[int, float] = {}
    depots: list[int] = []
    time_windows: dict[int, tuple[float, float]] = {}
    service_times: dict[int, float] = {}

    section = None
    for line in lines:
        upper = line.upper()
        if upper.startswith("NODE_COORD_SECTION"):
            section = "coords"
            continue
        elif upper.startswith("DEMAND_SECTION"):
            section = "demand"
            continue
        elif upper.startswith("DEPOT_SECTION"):
            section = "depot"
            continue
        elif upper.startswith("TIME_WINDOW_SECTION"):
            section = "tw"
            continue
        elif upper.startswith("SERVICE_TIME_SECTION"):
            section = "service"
            continue
        elif upper.startswith("EOF"):
            break
        elif re.match(r"[A-Z_]+\s*:", line):
            section = None
            continue

        if section == "coords":
            parts = line.split()
            if len(parts) >= 3:
                node_id = int(parts[0])
                coords[node_id] = (float(parts[1]), float(parts[2]))

        elif section == "demand":
            parts = line.split()
            if len(parts) >= 2:
                node_id = int(parts[0])
                demands[node_id] = float(parts[1])

        elif section == "depot":
            try:
                d = int(line)
                if d > 0:
                    depots.append(d)
            except ValueError:
                pass

        elif section == "tw":
            parts = line.split()
            if len(parts) >= 3:
                node_id = int(parts[0])
                time_windows[node_id] = (float(parts[1]), float(parts[2]))

        elif section == "service":
            parts = line.split()
            if len(parts) >= 2:
                node_id = int(parts[0])
                service_times[node_id] = float(parts[1])

    depot_node = depots[0] if depots else 1
    depot_x, depot_y = coords.get(depot_node, (0.0, 0.0))

    # Build customer list (excluding depot)
    customer_nodes = sorted(k for k in coords if k != depot_node)
    customers = []
    for idx, node_id in enumerate(customer_nodes):
        x, y = coords[node_id]
        tw = time_windows.get(node_id, (0.0, float("inf")))
        svc = service_times.get(node_id, 0.0)
        customers.append(
            Customer(
                id=idx,
                x=x,
                y=y,
                demand=demands.get(node_id, 0.0),
                service_time=svc,
                time_window_open=tw[0],
                time_window_close=tw[1],
                priority=1,
                node_id=node_id,
            )
        )

    vehicles = [
        Vehicle(id=k, capacity=capacity)
        for k in range(n_vehicles_hint)
    ]

    # Build distance matrix (N+1 × N+1, index 0 = depot)
    all_nodes = [depot_node] + customer_nodes
    n = len(all_nodes)
    dist_mat = np.zeros((n, n))
    for i, ni in enumerate(all_nodes):
        xi, yi = coords[ni]
        for j, nj in enumerate(all_nodes):
            xj, yj = coords[nj]
            dist_mat[i, j] = math.hypot(xi - xj, yi - yj)

    avg_speed = 30.0  # km/h — standard assumption for CVRPLIB
    tt_mat = dist_mat / avg_speed * 60.0  # minutes

    return _build_problem(customers, vehicles, depot_x, depot_y, dist_mat, tt_mat)


def list_bundled_instances() -> list[str]:
    """Return list of bundled CVRPLIB instance names in data/cvrplib/."""
    data_dir = Path(__file__).parent.parent / "data" / "cvrplib"
    if not data_dir.exists():
        return []
    return [p.stem for p in sorted(data_dir.glob("*.vrp"))]
