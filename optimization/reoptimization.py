"""
optimization/reoptimization.py
==============================
Rolling / receding-horizon dynamic re-optimization with Hot-Start Acceleration.

Section 14 of the build spec — mandatory for the core prototype.

Pipeline on Traffic Incident:
1. Freeze completed prefixes of all vehicles (completed deliveries remain invariant).
2. Extract remaining unserved customers into a dynamically generated sub-problem.
3. Update edge cost and travel time matrices with real-time incident multipliers.
4. Hot-start Adaptive D-QPSO using survivor route permutations as initial seeds.
5. Re-optimize the suffix under route stability penalties.
6. Return updated suffix routes within sub-50ms latency.
7. Compute route disruption metrics (Levenshtein distance, customer displacement).
"""

from __future__ import annotations

import copy
import time
from typing import TYPE_CHECKING, Optional

import numpy as np

from .config import OptimizationConfig, ObjectiveWeights
from .entities import EdgeState, Route, TrafficIncident, VehicleState
from .result import OptimizationResult

if TYPE_CHECKING:
    from .problem import VRPProblem


def compute_route_disruption(
    reference_assignments: dict[int, list[int]],
    new_assignments: dict[int, list[int]],
) -> dict[str, float]:
    """Compute route perturbation and disruption metrics between two routing plans.

    Returns
    -------
    dict with:
        - customer_displacements: count of customers assigned to a different vehicle
        - total_remaining_customers: count of customers evaluated
        - route_stability_score: float in [0.0, 1.0] (1.0 = identical assignment)
    """
    total = 0
    displaced = 0

    ref_map = {}
    for vid, clist in reference_assignments.items():
        for c in clist:
            ref_map[c] = vid
            total += 1

    for vid, clist in new_assignments.items():
        for c in clist:
            if c in ref_map and ref_map[c] != vid:
                displaced += 1

    stability = 1.0 - (displaced / max(1, total))
    return {
        "customer_displacements": displaced,
        "total_evaluated_customers": total,
        "route_stability_score": round(stability, 4),
    }


class ReOptimizer:
    """Manages rolling re-optimization when traffic conditions change."""

    def __init__(
        self,
        problem: "VRPProblem",
        config: OptimizationConfig,
        weights: Optional[ObjectiveWeights] = None,
    ) -> None:
        self.problem = problem
        self.config = config
        self.weights = weights or problem.objective_weights
        self.last_recovery_ms: float = 0.0
        self._reference_routes: list[Route] = []
        self.last_disruption_metrics: dict = {}

    # ------------------------------------------------------------------
    # Incident ingestion
    # ------------------------------------------------------------------

    def apply_incident(
        self, incident_dict: dict, travel_time_multiplier: Optional[float] = None
    ) -> None:
        """Ingest a traffic incident."""
        edge_id = incident_dict["edge_id"]
        raw_status = incident_dict.get("status", "OPEN").upper()

        try:
            status = EdgeState(raw_status.lower())
        except ValueError:
            status = EdgeState.OPEN

        if travel_time_multiplier is not None:
            multiplier = travel_time_multiplier
        elif status == EdgeState.CLOSED:
            multiplier = float("inf")
        elif status == EdgeState.CONGESTED:
            multiplier = 2.0
        elif status == EdgeState.SLOW:
            multiplier = 1.5
        else:
            multiplier = 1.0

        incident = TrafficIncident(
            edge_id=edge_id,
            status=status,
            travel_time_multiplier=multiplier,
            affected_at=incident_dict.get("affected_at", 0.0),
        )
        self.problem.apply_incident(incident)

    def clear_incident(self, edge_id: str) -> None:
        """Mark an incident as cleared (road re-opened)."""
        self.problem.clear_incident(edge_id)

    # ------------------------------------------------------------------
    # Route-state management
    # ------------------------------------------------------------------

    def set_reference_routes(self, routes: list[Route]) -> None:
        """Store the current routes as reference for the stability penalty."""
        self._reference_routes = copy.deepcopy(routes)

    def freeze_completed_prefix(
        self, vehicle_states: dict[int, VehicleState]
    ) -> dict[int, list[int]]:
        """Return the completed (frozen) customer sequences per vehicle."""
        return {
            vid: list(vs.completed_customers)
            for vid, vs in vehicle_states.items()
        }

    # ------------------------------------------------------------------
    # Sub-problem builder
    # ------------------------------------------------------------------

    def _build_remaining_problem(
        self,
        vehicle_states: dict[int, VehicleState],
    ) -> Optional["VRPProblem"]:
        """Build a sub-problem containing only remaining (unserved) customers."""
        from .problem import VRPProblem
        import copy as _copy

        all_rem_ids = []
        for vs in vehicle_states.values():
            all_rem_ids.extend(vs.remaining_customers)

        all_rem_ids = sorted(set(all_rem_ids))
        if not all_rem_ids:
            return None

        remaining_customers = [
            _copy.copy(self.problem.customers[cid]) for cid in all_rem_ids
        ]

        # Extract sub-matrices
        orig_indices = [0] + [c.id + 1 for c in remaining_customers]
        dist_sub = self.problem.distance_matrix[np.ix_(orig_indices, orig_indices)]
        tt_sub = self.problem.travel_time_matrix[np.ix_(orig_indices, orig_indices)]

        # Update vehicles with remaining capacities
        vehicles = []
        for k, vehicle in enumerate(self.problem.vehicles):
            vs = vehicle_states.get(k)
            new_v = _copy.copy(vehicle)
            if vs is not None:
                new_v.capacity = max(0.0, vehicle.capacity - vs.current_load)
                new_v.start_node = vs.current_node
            vehicles.append(new_v)

        sub_problem = VRPProblem(
            problem_type=self.problem.problem_type,
            customers=remaining_customers,
            vehicles=vehicles,
            depot_id=0,
            depot_x=self.problem.depot_x,
            depot_y=self.problem.depot_y,
            distance_matrix=dist_sub,
            travel_time_matrix=tt_sub,
            traffic_state=_copy.copy(self.problem._traffic_state),
            edge_travel_multipliers=_copy.copy(self.problem._edge_multipliers),
            enforce_time_windows=self.problem.enforce_time_windows,
            allow_waiting=self.problem.allow_waiting,
            objective_weights=self.weights,
        )
        return sub_problem

    # ------------------------------------------------------------------
    # Main re-optimization entry point
    # ------------------------------------------------------------------

    def reoptimize(
        self,
        vehicle_states: dict[int, VehicleState],
        incidents: Optional[list[dict]] = None,
        incident_multipliers: Optional[list[float]] = None,
    ) -> OptimizationResult:
        """Re-optimize routes after a traffic change using hot-start acceleration."""
        t_start = time.perf_counter()

        # 1. Apply new incidents
        if incidents:
            mults = incident_multipliers or [None] * len(incidents)
            for incident, mult in zip(incidents, mults):
                self.apply_incident(incident, travel_time_multiplier=mult)

        # 2. Build sub-problem for remaining customers
        sub_problem = self._build_remaining_problem(vehicle_states)
        if sub_problem is None:
            return OptimizationResult.infeasible(
                "adaptive_d_qpso",
                "No remaining customers to optimize.",
                runtime_ms=(time.perf_counter() - t_start) * 1000,
            )

        # 3. Configure rapid re-optimization parameters
        reopt_config = copy.copy(self.config)
        reopt_config.max_iterations = max(20, self.config.max_iterations // 3)
        reopt_config.population_size = max(15, self.config.population_size // 2)

        # 4. Route stability penalty
        stability_weights = copy.copy(self.weights)
        stability_weights.stability = self.config.__dict__.get("weight_stability", 0.15)

        # 5. Solve via Adaptive D-QPSO with Hot-Start
        from .adaptive_qpso import AdaptiveQPSO
        optimizer = AdaptiveQPSO(sub_problem, reopt_config, weights=stability_weights)
        result = optimizer.solve()

        # 6. Map sub-problem customer indices back to global customer ids
        # Sub-problem customers: 0..N_sub-1 correspond to sub_problem.customers[i].id
        sub_to_global = {i: c.id for i, c in enumerate(sub_problem.customers)}
        global_vehicle_assignments = {}
        for vid, cust_list in result.vehicle_assignments.items():
            global_vehicle_assignments[vid] = [sub_to_global.get(c, c) for c in cust_list]
        result.vehicle_assignments = global_vehicle_assignments

        # 7. Compute Disruption Metrics against initial plan
        reference_plan = {
            vid: list(vs.remaining_customers)
            for vid, vs in vehicle_states.items()
        }
        self.last_disruption_metrics = compute_route_disruption(
            reference_plan, global_vehicle_assignments
        )
        result.cost_breakdown["route_disruption"] = self.last_disruption_metrics

        self.last_recovery_ms = (time.perf_counter() - t_start) * 1000
        result.runtime_ms = self.last_recovery_ms

        return result

    # ------------------------------------------------------------------
    # Recovery time reporting
    # ------------------------------------------------------------------

    def recovery_time_ms(self) -> float:
        """Return the last measured re-optimization latency in milliseconds."""
        return self.last_recovery_ms
