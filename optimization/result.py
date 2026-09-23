"""
optimization/result.py
======================
Unified Output Contract & Telemetry for the Q-TRANSIT NEXUS optimization engine.

OptimizationResult is the single canonical object returned by every algorithm
(Adaptive D-QPSO, QPSO, PSO, GA, ACO, Dijkstra …).

Features:
- Complete algorithmic metrics: distance, time, composite objective, violations.
- Convergence history: iteration-by-iteration telemetry (fitness, diversity, alpha).
- RFC 7946 Standard GeoJSON export (to_geojson): ready for Leaflet, Mapbox, or Deck.gl.
- Rich ASCII route & schedule terminal visualizer (visualize_ascii).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .problem import VRPProblem


@dataclass
class ConvergencePoint:
    """One iteration's snapshot of optimizer state."""
    iteration: int
    best_fitness: float
    mean_fitness: float
    diversity: float
    alpha: float
    improvement: float = 0.0

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "best_fitness": round(self.best_fitness, 6),
            "mean_fitness": round(self.mean_fitness, 6),
            "diversity": round(self.diversity, 6),
            "alpha": round(self.alpha, 6),
            "improvement": round(self.improvement, 6),
        }


@dataclass
class OptimizationResult:
    """The complete output contract for the routing and optimization engine."""
    status: str
    algorithm: str
    routes: list[list[int]] = field(default_factory=list)
    vehicle_assignments: dict = field(default_factory=dict)
    objective_value: float = float("inf")
    distance_km: float = 0.0
    travel_time_min: float = 0.0
    vehicle_utilization: float = 0.0
    constraint_violations: int = 0
    iterations: int = 0
    runtime_ms: float = 0.0
    population_size: int = 0
    convergence: list[ConvergencePoint] = field(default_factory=list)
    random_seed: Optional[int] = None
    feasible_routes: int = 0
    reason: str = ""
    cost_breakdown: dict = field(default_factory=dict)
    route_metrics: list[dict] = field(default_factory=list)

    @property
    def is_feasible(self) -> bool:
        return self.status == "FEASIBLE"

    @property
    def convergence_history(self) -> list[float]:
        return [cp.best_fitness for cp in self.convergence]

    @property
    def diversity_history(self) -> list[float]:
        return [cp.diversity for cp in self.convergence]

    @property
    def alpha_history(self) -> list[float]:
        return [cp.alpha for cp in self.convergence]

    # -----------------------------------------------------------------
    # Factory helpers
    # -----------------------------------------------------------------

    @classmethod
    def infeasible(cls, algorithm: str, reason: str, runtime_ms: float = 0.0) -> "OptimizationResult":
        """Return an INFEASIBLE result with a mandatory reason string."""
        return cls(
            status="INFEASIBLE",
            algorithm=algorithm,
            reason=reason,
            runtime_ms=runtime_ms,
        )

    @classmethod
    def feasible_from_routes(
        cls,
        algorithm: str,
        routes: list[list[int]],
        vehicle_assignments: dict,
        objective_value: float,
        distance_km: float,
        travel_time_min: float,
        vehicle_utilization: float,
        constraint_violations: int,
        iterations: int,
        runtime_ms: float,
        convergence: list[ConvergencePoint],
        population_size: int = 0,
        random_seed: Optional[int] = None,
        feasible_routes: int = 0,
        cost_breakdown: Optional[dict] = None,
        route_metrics: Optional[list] = None,
    ) -> "OptimizationResult":
        return cls(
            status="FEASIBLE",
            algorithm=algorithm,
            routes=routes,
            vehicle_assignments=vehicle_assignments,
            objective_value=objective_value,
            distance_km=distance_km,
            travel_time_min=travel_time_min,
            vehicle_utilization=vehicle_utilization,
            constraint_violations=constraint_violations,
            iterations=iterations,
            runtime_ms=runtime_ms,
            population_size=population_size,
            convergence=convergence,
            random_seed=random_seed,
            feasible_routes=feasible_routes,
            cost_breakdown=cost_breakdown or {},
            route_metrics=route_metrics or [],
        )

    # -----------------------------------------------------------------
    # GeoJSON Export (RFC 7946)
    # -----------------------------------------------------------------

    def to_geojson(self, problem: Optional["VRPProblem"] = None) -> dict:
        """Export routes and stops as a GeoJSON FeatureCollection.

        Parameters
        ----------
        problem : VRPProblem | None
            If supplied, real node coordinates (x, y) are mapped to GeoJSON [lng, lat].
            Otherwise, synthetic planar coordinates are emitted.

        Returns
        -------
        dict : GeoJSON FeatureCollection
        """
        features = []
        palette = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4"]

        def get_coords(node_idx: int) -> list[float]:
            if problem is not None:
                if node_idx == 0:
                    return [float(problem.depot_x), float(problem.depot_y)]
                cust = problem.customers[node_idx - 1]
                return [float(cust.x), float(cust.y)]
            return [float(node_idx * 1.5), float(node_idx * 1.2)]

        # 1. Depot Point Feature
        depot_coords = get_coords(0)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": depot_coords},
            "properties": {
                "type": "depot",
                "name": "Central Depot",
                "marker-color": "#1E293B",
                "marker-symbol": "warehouse",
            },
        })

        # 2. Customer Point Features
        visited = set()
        for route in self.routes:
            for node_idx in route:
                if node_idx == 0 or node_idx in visited:
                    continue
                visited.add(node_idx)
                coords = get_coords(node_idx)
                cust_props = {
                    "type": "customer",
                    "customer_id": int(node_idx) - 1,
                    "marker-color": "#475569",
                }
                if problem is not None and node_idx - 1 < len(problem.customers):
                    c = problem.customers[node_idx - 1]
                    cust_props["demand"] = float(c.demand)
                    cust_props["tw_open"] = float(c.time_window_open)
                    cust_props["tw_close"] = float(c.time_window_close)
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": coords},
                    "properties": cust_props,
                })

        # 3. Vehicle Route LineStrings
        for vid, route in enumerate(self.routes):
            if len(route) <= 2:
                continue  # Empty route [0, 0]
            line_coords = [get_coords(int(node)) for node in route]
            color = palette[vid % len(palette)]
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": line_coords},
                "properties": {
                    "type": "route",
                    "vehicle_id": int(vid),
                    "stops_count": int(len(route) - 2),
                    "sequence": [int(x) for x in route],
                    "stroke": color,
                    "stroke-width": 3.5,
                    "stroke-opacity": 0.85,
                },
            })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "algorithm": self.algorithm,
                "status": self.status,
                "total_distance_km": round(self.distance_km, 2),
                "total_time_min": round(self.travel_time_min, 2),
                "objective_value": round(self.objective_value, 4),
            },
            "features": features,
        }

    # -----------------------------------------------------------------
    # ASCII Visualizer
    # -----------------------------------------------------------------

    def visualize_ascii(self, problem: Optional["VRPProblem"] = None) -> str:
        """Produce an ASCII route plan and load gauge for terminal display."""
        if self.status != "FEASIBLE":
            return f"[INFEASIBLE] {self.reason}"

        border = "+" + "=" * 68 + "+"
        div = "+" + "-" * 68 + "+"

        lines = [
            border,
            f"| Q-TRANSIT NEXUS ROUTE DISPATCH PLAN -- {self.algorithm.upper():<27} |",
            border,
            f"| Total Dist: {self.distance_km:6.2f} km | Total Time: {self.travel_time_min:6.2f} min | Obj: {self.objective_value:7.2f}  |",
            div,
        ]

        for vid, cust_list in self.vehicle_assignments.items():
            cap = 100.0
            if problem is not None and vid < len(problem.vehicles):
                cap = problem.vehicles[vid].capacity
            load = 0.0
            if problem is not None:
                load = sum(problem.customers[c].demand for c in cust_list if c < len(problem.customers))

            pct = min(1.0, load / max(1e-6, cap))
            bar_len = 16
            filled = int(round(pct * bar_len))
            gauge = "#" * filled + "." * (bar_len - filled)

            lines.append(f"| Vehicle {vid:2d}: [{gauge}] {pct * 100:5.1f}% ({load:5.1f}/{cap:5.1f})")
            if cust_list:
                stops_str = " -> ".join(f"C{c}" for c in cust_list)
                lines.append(f"|   Depot -> {stops_str} -> Depot")
            else:
                lines.append("|   [Idle at Depot]")
            lines.append(div)

        lines[-1] = border
        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Serialisation
    # -----------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "algorithm": self.algorithm,
            "routes": self.routes,
            "vehicle_assignments": self.vehicle_assignments,
            "objective_value": round(self.objective_value, 4),
            "distance_km": round(self.distance_km, 2),
            "travel_time_min": round(self.travel_time_min, 2),
            "vehicle_utilization": round(self.vehicle_utilization, 4),
            "constraint_violations": self.constraint_violations,
            "iterations": self.iterations,
            "runtime_ms": round(self.runtime_ms, 2),
            "population_size": self.population_size,
            "random_seed": self.random_seed,
            "feasible_routes": self.feasible_routes,
            "cost_breakdown": self.cost_breakdown,
            "route_metrics": self.route_metrics,
            "convergence": [cp.to_dict() for cp in self.convergence],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary(self) -> str:
        """One-line human-readable summary."""
        if self.status == "INFEASIBLE":
            return f"[INFEASIBLE] {self.reason} (runtime={self.runtime_ms:.1f}ms)"
        return (
            f"[FEASIBLE | {self.algorithm}] "
            f"obj={self.objective_value:.2f}  "
            f"dist={self.distance_km:.1f}km  "
            f"time={self.travel_time_min:.1f}min  "
            f"violations={self.constraint_violations}  "
            f"iters={self.iterations}  "
            f"rt={self.runtime_ms:.0f}ms"
        )
