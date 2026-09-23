from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class WebSocketEvent(BaseModel):
    event_type: str = Field(..., description="Event type: traffic_update, optimization_progress, route_changed, simulation_update, incident")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    payload: Dict[str, Any] = Field(..., description="Lightweight delta payload containing only changed entities")

class TrafficUpdateDeltaPayload(BaseModel):
    changed_edges: List[Dict[str, Any]] = Field(..., description="List of updated edge speeds and congestion factors")

class RouteChangedDeltaPayload(BaseModel):
    vehicle_id: str
    trip_id: str
    new_route_id: str
    total_distance_meters: float
    total_duration_seconds: float
    geometry_geojson: str

class OptimizationProgressPayload(BaseModel):
    run_id: str
    status: str
    current_iteration: int
    total_iterations: int
    best_cost: float
