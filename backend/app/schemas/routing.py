from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.fleet import VehicleResponse

class RouteSegmentResponse(BaseModel):
    id: str
    route_id: str
    internal_edge_id: str
    sequence_order: int
    expected_travel_time_seconds: float
    model_config = ConfigDict(from_attributes=True)

class RouteResponse(BaseModel):
    id: str
    trip_id: str
    total_distance_meters: float
    total_duration_seconds: float
    route_geometry_geojson: Optional[str] = None
    created_at: datetime
    segments: List[RouteSegmentResponse] = []
    model_config = ConfigDict(from_attributes=True)

class TripBase(BaseModel):
    vehicle_id: str = Field(..., description="ID of assigned vehicle")
    status: str = Field("PLANNED", json_schema_extra={"example": "PLANNED"})
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    vehicle_id: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class TripResponse(TripBase):
    id: str
    vehicle: Optional[VehicleResponse] = None
    routes: List[RouteResponse] = []
    model_config = ConfigDict(from_attributes=True)
