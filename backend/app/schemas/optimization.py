from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from backend.app.schemas.common import LatLon, ObjectiveWeights, GeoJSONFeatureCollection

class VehicleInput(BaseModel):
    id: str = Field(..., example="V1")
    vehicle_code: Optional[str] = "V-101"
    capacity: float = Field(100.0, example=100.0)
    battery_capacity: Optional[float] = None
    current_battery: Optional[float] = None

class CustomerInput(BaseModel):
    id: str = Field(..., example="C1")
    name: Optional[str] = "Customer 1"
    location: LatLon
    demand: float = Field(10.0, example=10.0)
    priority: int = Field(1, example=1)
    service_time_sec: int = Field(300, example=300)
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None

class DeliveryOptimizationRequest(BaseModel):
    depot: LatLon
    vehicles: List[VehicleInput]
    customers: List[CustomerInput]
    objective: ObjectiveWeights = Field(default_factory=ObjectiveWeights)
    algorithm: str = Field("adaptive_d_qpso", example="adaptive_d_qpso")

class OptimizationSubmissionResponse(BaseModel):
    optimization_id: str
    status: str # QUEUED

class VehicleRouteSolution(BaseModel):
    vehicle_id: str
    customers: List[str]
    distance_km: float
    travel_time_min: float
    geometry: GeoJSONFeatureCollection

class OptimizationRunStatusResponse(BaseModel):
    id: str
    status: str # QUEUED, RUNNING, COMPLETED, FAILED, INFEASIBLE
    algorithm: str
    iteration: Optional[int] = 0
    best_fitness: Optional[float] = 0.0
    summary: Optional[Dict[str, Any]] = None
    vehicles: Optional[List[VehicleRouteSolution]] = None

class OptimizationIterationPoint(BaseModel):
    iteration: int
    best_fitness: float
    mean_fitness: Optional[float] = 0.0
    diversity: Optional[float] = 0.0
    alpha: Optional[float] = 0.0

class OptimizationMetricsResponse(BaseModel):
    optimization_run_id: str
    distance_km: float
    travel_time_min: float
    congestion_cost: float
    penalty: float
    vehicles_used: int
    constraint_violations: int
    reroutes: int
    objective_value: float
