from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.repositories.traffic import TrafficRepository
from app.repositories.routing import TripRepository
from app.repositories.fleet import VehicleRepository
from app.repositories.network import NetworkRepository
from app.adapters.traffic_adapter import TrafficAdapter
from app.adapters.optimization_adapter import OptimizationAdapter
from app.adapters.sumo_adapter import SUMOAdapter
from app.api.websocket import manager as ws_manager
from app.schemas.events import WebSocketEvent, RouteChangedDeltaPayload
from app.core.logging import logger

class OrchestratorService:
    """
    Central orchestration engine (Phase 8).
    Processes TRAFFIC_STATE_CHANGED events, triggers re-optimization with Member 1,
    applies route updates to Member 2 / SUMO, and broadcasts updates over WebSocket
    to mobile app clients.
    """
    def __init__(self, db: Session):
        self.db = db
        self.traffic_repo = TrafficRepository(db)
        self.trip_repo = TripRepository(db)
        self.veh_repo = VehicleRepository(db)
        self.net_repo = NetworkRepository(db)
        self.optimizer_adapter = OptimizationAdapter()
        self.sumo_adapter = SUMOAdapter()

    async def handle_traffic_state_changed(self, raw_traffic_event: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Orchestrator: Ingesting TRAFFIC_STATE_CHANGED event: {raw_traffic_event}")

        # 1. Store event in DB via TrafficAdapter
        validated_state = TrafficAdapter.normalize_traffic_payload(raw_traffic_event)
        traffic_obj = self.traffic_repo.create_traffic_state(validated_state)
        
        edge_id = validated_state.internal_edge_id
        congestion = validated_state.congestion_factor
        
        # 2. Decide if re-optimization is needed (e.g., congestion factor > 1.3 or speed dropped significantly)
        reoptimize_needed = congestion > 1.3 or validated_state.current_speed_kph < 20.0
        
        if not reoptimize_needed:
            logger.info(f"Orchestrator: Congestion on edge {edge_id} is acceptable ({congestion}x). Re-routing not triggered.")
            return {"status": "NO_REROUTE_NEEDED", "edge_id": edge_id}

        # 3. Find affected active vehicles
        active_vehicles = self.veh_repo.list_all()
        if not active_vehicles:
            logger.info("Orchestrator: No active vehicles found on network.")
            return {"status": "NO_ACTIVE_VEHICLES", "edge_id": edge_id}

        affected_vehicle = active_vehicles[0]
        logger.info(f"Orchestrator: Re-optimizing route for Vehicle '{affected_vehicle.plate_number}' due to congestion on edge '{edge_id}'.")

        # 4. Build re-optimization problem for Member 1
        nodes = self.net_repo.list_nodes()
        edges = self.net_repo.list_edges()
        
        problem = self.optimizer_adapter.build_problem(
            problem_id=f"reopt_{edge_id}",
            vehicles=[affected_vehicle],
            customers=[],
            edges=edges
        )

        # 5. Call Member 1 common solver interface
        opt_result, mapped_routes = self.optimizer_adapter.solve_and_map_geometry(problem, nodes, edges)
        
        route_info = mapped_routes.get(affected_vehicle.id, next(iter(mapped_routes.values())))

        # 6. Store new route in DB
        active_trips = self.trip_repo.get_by_vehicle_id(affected_vehicle.id)
        trip_id = active_trips[0].id if active_trips else "demo_trip_id"
        
        new_route = self.trip_repo.create_route_for_trip(
            trip_id=trip_id,
            total_distance=opt_result.total_distance,
            total_duration=opt_result.total_cost * 1.2,
            geojson_str=route_info["geojson"],
            segments=route_info["segments"]
        )

        # 7. Apply new route via Member 2 / SUMO
        self.sumo_adapter.inject_incident(edge_id, validated_state.current_speed_kph)

        # 8. Broadcast route_changed delta event over WebSocket to mobile app clients
        ws_event = WebSocketEvent(
            event_type="route_changed",
            payload={
                "vehicle_id": affected_vehicle.id,
                "trip_id": trip_id,
                "new_route_id": new_route.id,
                "total_distance_meters": new_route.total_distance_meters,
                "total_duration_seconds": new_route.total_duration_seconds,
                "geometry_geojson": new_route.route_geometry_geojson
            }
        )
        
        await ws_manager.broadcast(ws_event.model_dump())
        logger.info(f"Orchestrator: Successfully broadcast route_changed WebSocket update to mobile client for Vehicle {affected_vehicle.id}")

        return {
            "status": "REOPTIMIZED_AND_BROADCAST",
            "vehicle_id": affected_vehicle.id,
            "new_route_id": new_route.id,
            "edge_id": edge_id
        }
