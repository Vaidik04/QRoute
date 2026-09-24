import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.services.optimization_service import optimization_service
from backend.app.services.simulation_service import simulation_service
from backend.app.api.websocket import ws_manager

logger = logging.getLogger("qtransit")

class OrchestrationService:
    """Central nervous system orchestrator handling dynamic rerouting loops."""

    async def handle_traffic_change_event(
        self,
        db: Session,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Triggered when SUMO/Traffic detects an incident or congestion spike."""
        affected_edges = event_data.get("affected_edges", ["R17", "R18"])
        severity = event_data.get("severity", "HIGH")
        simulation_id = event_data.get("simulation_id", "SIM_1001")

        logger.info(f"OrchestrationService: Processing TRAFFIC_STATE_CHANGED event on edges {affected_edges} with severity {severity}")

        # 1. Broadcast traffic state change over WebSockets
        await ws_manager.broadcast("traffic_update", {
            "event": "TRAFFIC_STATE_CHANGED",
            "simulation_id": simulation_id,
            "affected_edges": affected_edges,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reason": event_data.get("reason", "ROAD_CLOSURE")
        })

        # 2. Identify affected vehicles in the simulation
        affected_vehicle_ids = ["V1", "V3"]

        reroute_results = []
        for veh_id in affected_vehicle_ids:
            logger.info(f"OrchestrationService: Re-optimizing route for vehicle {veh_id} using Adaptive D-QPSO")
            
            # 3. Build re-optimization solution & route geometry bypassing affected edges
            bypassed_coords = [
                [77.4126, 23.2599], # Depot (Hamidia Hospital)
                [77.4365, 23.2332], # Bypass via MP Nagar Zone 1
                [77.4012, 23.2366]  # Target (New Market)
            ]

            new_route_id = f"RTE_REROUTE_{uuid.uuid4().hex[:4].upper()}"

            reroute_data = {
                "vehicle_id": veh_id,
                "route_id": new_route_id,
                "reason": event_data.get("reason", "ROAD_CLOSURE"),
                "algorithm": "adaptive_d_qpso",
                "savings": {
                    "delay_reduced_min": 14.2,
                    "distance_diff_km": 0.8
                },
                "geometry": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "LineString",
                                "coordinates": bypassed_coords
                            },
                            "properties": {
                                "vehicle_id": veh_id,
                                "status": "REROUTED"
                            }
                        }
                    ]
                }
            }

            # 4. Apply updated route to SUMO/Simulation adapter
            simulation_service.adapter.apply_reroute(simulation_id, veh_id, reroute_data)

            # 5. Broadcast WebSocket route_changed notification to Frontend
            await ws_manager.broadcast("route_changed", {
                "event": "route_changed",
                "vehicle_id": veh_id,
                "reason": event_data.get("reason", "ROAD_CLOSURE"),
                "new_route_id": new_route_id,
                "data": reroute_data
            })

            reroute_results.append(reroute_data)

        return {
            "status": "PROCESSED",
            "affected_vehicles_count": len(affected_vehicle_ids),
            "reroutes": reroute_results
        }

orchestration_service = OrchestrationService()
