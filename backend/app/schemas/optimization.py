from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class OptimizationDeliveryRequest(BaseModel):
    delivery_ids: List[str] = Field(..., min_length=1, description="List of delivery IDs to optimize")
    vehicle_ids: List[str] = Field(..., min_length=1, description="List of available vehicle IDs")
    algorithm: Optional[str] = Field("D-QPSO", description="Algorithm name interface parameter")

class OptimizationRunCreate(BaseModel):
    algorithm_name: str = Field("D-QPSO")

class OptimizationIterationResponse(BaseModel):
    iteration_number: int
    best_cost: float
    average_cost: Optional[float] = None
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class OptimizationSolutionResponse(BaseModel):
    id: str
    run_id: str
    vehicle_id: str
    customer_sequence_json: str
    total_cost: float
    total_distance: float
    model_config = ConfigDict(from_attributes=True)

class OptimizationMetricResponse(BaseModel):
    total_runtime_ms: float
    total_distance: float
    fleet_utilization: float
    model_config = ConfigDict(from_attributes=True)

class OptimizationRunResponse(BaseModel):
    id: str
    status: str
    algorithm_name: str
    created_at: datetime
    finished_at: Optional[datetime] = None
    solutions: List[OptimizationSolutionResponse] = []
    metrics: Optional[OptimizationMetricResponse] = None
    iterations: List[OptimizationIterationResponse] = []
    model_config = ConfigDict(from_attributes=True)
