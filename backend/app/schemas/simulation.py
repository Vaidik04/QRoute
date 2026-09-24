from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class SimulationStartRequest(BaseModel):
    scenario: str = Field("evening_peak_closure", example="evening_peak_closure")
    duration_sec: int = Field(1800, example=1800)
    vehicles: int = Field(50, example=50)
    routing_algorithm: str = Field("adaptive_d_qpso", example="adaptive_d_qpso")

class SimulationStartResponse(BaseModel):
    simulation_id: str
    status: str # STARTED

class SimulatedVehicleState(BaseModel):
    id: str
    lat: float
    lon: float
    speed_kmh: float
    route_id: Optional[str] = None
    status: str = "MOVING"

class SimulationStateResponse(BaseModel):
    simulation_id: str
    simulation_time: float
    status: str # RUNNING, PAUSED, STOPPED
    vehicles: List[SimulatedVehicleState]

class SimulationMetricsResponse(BaseModel):
    simulation_id: str
    timestamp: datetime
    average_speed: float
    average_delay: float
    queue_length: float
    throughput: float
    waiting_time: float
    reroutes: int
