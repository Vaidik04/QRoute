from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from backend.app.schemas.common import LatLon, GeoJSONFeatureCollection

class TripRouteRequest(BaseModel):
    origin: LatLon
    destination: LatLon
    mode: str = Field("car", example="car") # car, delivery, ev, emergency
    objective: str = Field("balanced", example="balanced") # time, distance, congestion, balanced

class RouteSummary(BaseModel):
    distance_km: float
    travel_time_min: float
    fitness: float

class TripRouteResponse(BaseModel):
    trip_id: str
    route_id: str
    algorithm: str
    status: str
    summary: RouteSummary
    geometry: GeoJSONFeatureCollection
    created_at: datetime
