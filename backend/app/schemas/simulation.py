from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class SimulationStartRequest(BaseModel):
    sumo_config_path: Optional[str] = Field("data/sumo/bhopal.sumocfg", description="Path to SUMO configuration file")

class SimulationMetricResponse(BaseModel):
    step_number: int
    active_vehicles: int
    average_speed_kph: float
    total_emissions: float
    model_config = ConfigDict(from_attributes=True)

class SimulationRunResponse(BaseModel):
    id: str
    sumo_config_path: str
    status: str
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    metrics: List[SimulationMetricResponse] = []
    model_config = ConfigDict(from_attributes=True)
